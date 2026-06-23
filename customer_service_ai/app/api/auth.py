"""
管理员认证 API
JWT access + refresh token，支持过期刷新
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/auth", tags=["认证"])

_admin_token: str = ""


def _get_jwt_secret() -> str:
    if not settings.jwt_secret:
        return hashlib.sha256((settings.admin_password or "default").encode()).hexdigest()
    return settings.jwt_secret


def _make_token() -> str:
    return hashlib.sha256(
        (settings.admin_password + secrets.token_hex(8)).encode()
    ).hexdigest()


def validate_admin_token(token: str) -> bool:
    """校验 admin token（同时支持旧 plain token 和新 JWT access token）"""
    if not settings.admin_password:
        return False
    if token == _admin_token:
        return True
    try:
        payload = pyjwt.decode(token, _get_jwt_secret(), algorithms=["HS256"])
        return payload.get("type") == "access"
    except Exception:
        return False


def create_access_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_expire_minutes)
    return pyjwt.encode(
        {"type": "access", "exp": expire, "sub": "admin"},
        _get_jwt_secret(),
        algorithm="HS256",
    )


def create_refresh_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    return pyjwt.encode(
        {"type": "refresh", "exp": expire, "sub": "admin"},
        _get_jwt_secret(),
        algorithm="HS256",
    )


def verify_token(token: str) -> dict:
    try:
        return pyjwt.decode(token, _get_jwt_secret(), algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token 无效")


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/login")
async def login(req: LoginRequest):
    if not settings.admin_password:
        raise HTTPException(status_code=403, detail="管理员功能未启用")

    if req.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="密码错误")

    global _admin_token
    _admin_token = _make_token()

    access_token = create_access_token()
    return {
        "token": access_token,
        "access_token": access_token,
        "refresh_token": create_refresh_token(),
        "token_type": "bearer",
    }


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=LoginResponse)
async def refresh(req: RefreshRequest):
    payload = verify_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="无效的 refresh token")

    return LoginResponse(
        access_token=create_access_token(),
        refresh_token=create_refresh_token(),
    )


def require_admin(authorization: str = Header(default="")) -> None:
    """从 Authorization Header 校验 JWT access token"""
    if not settings.admin_password:
        raise HTTPException(status_code=403, detail="管理员功能未启用")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="缺少有效的 Authorization Header")

    payload = verify_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="需要 access token")
