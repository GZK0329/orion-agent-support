"""
错误日志 API
管理员可查看模型调用失败的记录，用于迭代优化
"""
from fastapi import APIRouter, Header, HTTPException, Query

from app.api.auth import validate_admin_token
from app.memory.session_store import session_store

router = APIRouter(prefix="/error-logs", tags=["错误日志"])


def _require_admin(x_admin_token: str) -> None:
    if not validate_admin_token(x_admin_token):
        raise HTTPException(status_code=403, detail="需要管理员权限")


@router.get("/")
async def list_errors(
    session_id: str = Query(default=""),
    x_admin_token: str = Header(default=""),
):
    """获取错误日志列表（仅管理员）"""
    _require_admin(x_admin_token)
    return session_store.list_error_logs(session_id=session_id or None)
