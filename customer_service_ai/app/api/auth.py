"""
管理员认证 API
提供简单的密码登录，控制文档管理权限
"""
import hashlib
import secrets

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/auth", tags=["认证"])

# 生成一个固定的 admin token（程序重启后会变化，但用户可以重新登录）
_admin_token: str = ""


def _make_token() -> str:
    return hashlib.sha256(
        (settings.admin_password + secrets.token_hex(8)).encode()
    ).hexdigest()


def validate_admin_token(token: str) -> bool:
    """校验 admin token（供其他模块使用）"""
    return bool(settings.admin_password) and token == _admin_token


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(req: LoginRequest):
    """管理员登录"""
    if not settings.admin_password:
        raise HTTPException(status_code=403, detail="管理员功能未启用")

    if req.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="密码错误")

    global _admin_token
    _admin_token = _make_token()
    return {"token": _admin_token}
