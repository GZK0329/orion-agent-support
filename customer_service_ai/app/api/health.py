"""
健康检查 API
返回各组件状态，供 K8s probe 或运维监控使用
"""
import time

from fastapi import APIRouter
from loguru import logger
from sqlalchemy import text

from app.config import settings
from app.database import async_engine

router = APIRouter(tags=["健康检查"])


@router.get("/health")
async def health():
    checks = {}
    overall = "ok"

    # Database
    try:
        t0 = time.time()
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = {
            "status": "ok",
            "latency_ms": int((time.time() - t0) * 1000),
        }
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}
        overall = "degraded"

    # ChromaDB / Vector Store
    try:
        from app.services.rag_service import get_vector_store
        vs = get_vector_store()
        count = vs._collection.count()
        checks["vector_store"] = {
            "status": "ok",
            "collection": settings.collection_name,
            "chunks": count,
        }
    except Exception as e:
        checks["vector_store"] = {"status": "error", "detail": str(e)}
        overall = "degraded"

    # LLM connectivity (lightweight ping via embedding)
    try:
        from app.services.embedding_service import get_embedding_model
        emb = get_embedding_model()
        t0 = time.time()
        emb.embed_query("ping")
        checks["llm"] = {
            "status": "ok",
            "latency_ms": int((time.time() - t0) * 1000),
        }
    except Exception as e:
        checks["llm"] = {"status": "error", "detail": str(e)}
        overall = "degraded"

    logger.debug(f"健康检查结果: {overall}")
    return {
        "status": overall,
        "version": "0.2.0",
        "uptime_seconds": int(time.time() - _start_time) if _start_time else 0,
        "checks": checks,
    }


_start_time: float | None = None


def record_start_time():
    global _start_time
    _start_time = time.time()
