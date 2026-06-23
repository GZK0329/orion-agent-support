"""
Agent 配置管理 API
管理员可查看和修改 prompt、阈值等配置，修改后自动热重载
"""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.api.auth import validate_admin_token
from app.services import config_service

router = APIRouter(prefix="/config", tags=["Agent 配置"])


class ConfigUpdate(BaseModel):
    key: str
    value: str


def _require_admin(x_admin_token: str) -> None:
    if not validate_admin_token(x_admin_token):
        raise HTTPException(status_code=403, detail="需要管理员权限")


@router.get("/")
async def list_configs(x_admin_token: str = Header(default="")):
    """列出所有配置（仅管理员）"""
    _require_admin(x_admin_token)
    return await config_service.list_configs()


@router.put("/")
async def update_config(
    req: ConfigUpdate,
    x_admin_token: str = Header(default=""),
):
    """更新配置（仅管理员），修改后自动热重载"""
    _require_admin(x_admin_token)
    await config_service.set_config(req.key, req.value)
    return {"message": f"配置 {req.key} 已更新", "value": req.value}


@router.post("/reload")
async def reload_config(x_admin_token: str = Header(default="")):
    """手动清空缓存强制重新加载（仅管理员）"""
    _require_admin(x_admin_token)
    config_service.invalidate_cache()
    return {"message": "配置缓存已清空，将在下次读取时重新加载"}
