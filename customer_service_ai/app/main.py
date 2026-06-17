"""
FastAPI 应用入口
类似 Spring Boot 的 Application 类
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.demos import router as demos_router
from app.api.history import router as history_router
from app.api.documents import router as documents_router
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期（类似 Spring Boot 的 ApplicationRunner）"""
    init_db()
    yield


app = FastAPI(
    title="智能客服助手",
    description="基于 LangChain + RAG + DeepSeek 的智能客服系统",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS 配置，允许前端开发服务器跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(demos_router)
app.include_router(history_router)
app.include_router(documents_router)


@app.get("/", summary="健康检查")
async def root():
    return {"message": "智能客服助手已启动", "version": "0.1.0"}
