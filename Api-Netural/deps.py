# deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import verify_token
from models.user import SysUser

security_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> SysUser:
    """获取当前登录用户"""
    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token 格式错误")

    user = db.query(SysUser).filter(
        SysUser.user_id == user_id,
        SysUser.del_flag == "0",
        SysUser.status == "0"
    ).first()

    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    return user


def get_current_admin(current_user: SysUser = Depends(get_current_user)) -> SysUser:
    """获取当前管理员用户"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user
