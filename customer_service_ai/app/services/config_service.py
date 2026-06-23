"""
Agent 配置服务
从数据库读取可配置项（prompt、阈值等），内存缓存 TTL 30s
管理员通过 API 修改后，最多 30s 自动生效，无需重启
"""
import time
from typing import Optional

from loguru import logger
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.db_models import AgentConfig

_CACHE_TTL = 30
_cache: dict[str, tuple[float, str]] = {}

_DEFAULTS = {
    "agent_system_prompt": "",  # 空则用代码里的默认 prompt
    "confidence_threshold": "0.5",
    "retrieval_rerank_top_k": "5",
}


async def get_config(key: str) -> str:
    """读取配置值，优先内存缓存，其次 DB，最后默认值"""
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AgentConfig).where(AgentConfig.key == key)
        )
        row = result.scalar_one_or_none()
        value = row.value if row else _DEFAULTS.get(key, "")

    _cache[key] = (now, value)
    return value


async def get_config_float(key: str, default: float = 0.0) -> float:
    try:
        return float(await get_config(key))
    except (ValueError, TypeError):
        return default


async def get_config_int(key: str, default: int = 0) -> int:
    try:
        return int(await get_config(key))
    except (ValueError, TypeError):
        return default


async def set_config(key: str, value: str) -> None:
    """写入配置并刷新缓存"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AgentConfig).where(AgentConfig.key == key)
        )
        row = result.scalar_one_or_none()
        if row:
            row.value = value
        else:
            db.add(AgentConfig(key=key, value=value))
        await db.commit()

    _cache[key] = (time.time(), value)
    logger.info(f"配置已更新: {key}={value[:50]}...")


async def list_configs() -> list[dict]:
    """列出所有配置"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AgentConfig))
        rows = result.scalars().all()
        return [
            {"key": r.key, "value": r.value, "updated_at": str(r.updated_at)}
            for r in rows
        ]


def invalidate_cache() -> None:
    """清空内存缓存（管理员手动刷新时调用）"""
    _cache.clear()
    logger.info("配置缓存已清空")
