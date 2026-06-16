"""
API 请求/响应模型
类似 Java 中的 DTO / VO
"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """对话请求"""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="用户问题",
    )
    session_id: str = Field(
        default="default",
        max_length=100,
        description="会话 ID，同一会话内 AI 会记住之前的对话",
    )


class ChatResponse(BaseModel):
    """对话响应"""

    answer: str = Field(..., description="AI 回答")
    session_id: str = Field(default="default", description="当前会话 ID")
