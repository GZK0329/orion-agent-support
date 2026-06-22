"""
用户反馈 API
提交对 AI 回答的 👍/👎，管理员可查看反馈列表
"""
from fastapi import APIRouter, Header, HTTPException, Query, status

from app.api.auth import validate_admin_token
from app.memory.session_store import session_store
from app.models.schemas import FeedbackCreate

router = APIRouter(prefix="/feedback", tags=["反馈收集"])


def _require_admin(x_admin_token: str) -> None:
    if not validate_admin_token(x_admin_token):
        raise HTTPException(status_code=403, detail="需要管理员权限")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def submit_feedback(req: FeedbackCreate):
    """提交用户反馈（无需登录）"""
    feedback_id = await session_store.add_feedback(
        session_id=req.session_id,
        question=req.question,
        answer=req.answer,
        feedback=req.feedback,
        comment=req.comment,
        source=req.source,
    )
    return {"id": feedback_id, "message": "反馈已记录"}


@router.get("/")
async def list_feedback(
    session_id: str = Query(default=""),
    x_admin_token: str = Header(default=""),
):
    """获取反馈列表（仅管理员）"""
    _require_admin(x_admin_token)
    return await session_store.list_feedback(session_id=session_id or None)
