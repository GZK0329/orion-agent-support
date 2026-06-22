"""
FastAPI 应用入口
类似 Spring Boot 的 Application 类
"""
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.demos import router as demos_router
from app.api.history import router as history_router
from app.api.documents import router as documents_router
from app.api.feedback import router as feedback_router
from app.api.error_logs import router as error_logs_router
from app.database import init_db
from app.middleware import RequestIdMiddleware
from app.models.schemas import ErrorResponse


def setup_logging():
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[request_id]: <8}</cyan> | <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        "data/logs/app_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[request_id]: <8} | {message}",
        level="DEBUG",
    )
    logger.configure(extra={"request_id": "-"})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期（类似 Spring Boot 的 ApplicationRunner）"""
    setup_logging()
    logger.info("应用启动，正在初始化数据库…")
    init_db()
    logger.info("数据库初始化完成")
    yield
    logger.info("应用关闭")


app = FastAPI(
    title="智能客服助手",
    description="基于 LangChain + RAG + DeepSeek 的智能客服系统",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(RequestIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    req_id = getattr(request.state, "request_id", "-")
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=str(exc.detail),
            error_type="http_error",
            request_id=req_id,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "-")
    logger.opt(exception=True).error(f"未捕获异常: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail="服务内部错误，请稍后重试",
            error_type="internal_error",
            request_id=req_id,
        ).model_dump(),
    )


app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(demos_router)
app.include_router(history_router)
app.include_router(documents_router)
app.include_router(feedback_router)
app.include_router(error_logs_router)


@app.get("/", summary="健康检查")
async def root():
    return {"message": "智能客服助手已启动", "version": "0.2.0"}
