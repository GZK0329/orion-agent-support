"""
FastAPI 应用入口
类似 Spring Boot 的 Application 类
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.history import router as history_router

app = FastAPI(
    title="智能客服助手",
    description="基于 LangChain + RAG + DeepSeek 的智能客服系统",
    version="0.1.0",
)

# CORS 配置，允许前端开发服务器跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(history_router)


@app.get("/", summary="健康检查")
async def root():
    return {"message": "智能客服助手已启动", "version": "0.1.0"}
