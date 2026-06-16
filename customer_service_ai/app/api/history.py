"""
历史对话 API
提供会话列表查询、消息查询、删除功能
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.memory.session_store import session_store

router = APIRouter(prefix="/history", tags=["历史对话"])


class SessionItem(BaseModel):
    session_id: str
    title: str
    message_count: int
    created_at: int


class MessageItem(BaseModel):
    type: str
    content: str


@router.get("/", response_model=list[SessionItem])
async def list_sessions():
    """获取所有历史会话摘要"""
    return session_store.list_sessions()


@router.get("/{session_id}", response_model=list[MessageItem])
async def get_session_messages(session_id: str):
    """获取指定会话的消息列表"""
    raw = session_store.get_raw_messages(session_id)
    if not raw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    result = []
    for m in raw:
        result.append({
            "type": m.get("type", ""),
            "content": m.get("data", {}).get("content", ""),
        })
    return result


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str):
    """删除指定会话"""
    deleted = session_store.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
