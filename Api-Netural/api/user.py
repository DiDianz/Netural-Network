# api/user.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from deps import get_current_user
from schemas.user import UserInfo
from models.user import SysUser

router = APIRouter(prefix="/system/user", tags=["用户管理"])


@router.get("/info", response_model=UserInfo)
async def get_user_info(current_user: SysUser = Depends(get_current_user)):
    """获取当前用户信息（含角色和权限）"""
    return UserInfo(
        user_id=current_user.user_id, # type: ignore
        user_name=current_user.user_name, # type: ignore
        nick_name=current_user.nick_name, # type: ignore
        email=current_user.email or "", # type: ignore
        phonenumber=current_user.phonenumber or "", # type: ignore
        avatar=current_user.avatar or "", # type: ignore
        roles=current_user.role_keys,
        permissions=["*:*:*"] if current_user.is_admin else []
    )
