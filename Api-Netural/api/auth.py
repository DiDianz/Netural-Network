# api/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from core.database import get_db
from core.security import verify_password, create_access_token
from schemas.auth import LoginRequest, LoginResponse
from models.user import SysUser

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录
    返回 JWT Token，前端存入 localStorage
    """
    # 查询用户
    user = db.query(SysUser).filter(
        SysUser.user_name == body.username,
        SysUser.del_flag == "0"
    ).first()

    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")

    if user.status == "1": # type: ignore
        raise HTTPException(status_code=401, detail="账号已停用")

    if not verify_password(body.password, user.password): # type: ignore
        raise HTTPException(status_code=401, detail="密码错误")

    # 更新登录信息
    user.login_date = datetime.now(timezone.utc) # type: ignore
    db.commit()

    # 生成 Token
    token = create_access_token(data={
        "user_id": user.user_id,
        "username": user.user_name,
        "roles": user.role_keys
    })

    return LoginResponse(
        token=token,
        expire_time="24h"
    )


@router.post("/logout")
async def logout():
    """退出登录（前端清除 token 即可）"""
    return {"code": 200, "msg": "退出成功"}
