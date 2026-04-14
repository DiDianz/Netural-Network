# schemas/user.py
from pydantic import BaseModel
from typing import Optional

class UserInfo(BaseModel):
    user_id: int
    user_name: str
    nick_name: str
    email: str = ""
    phonenumber: str = ""
    avatar: str = ""
    roles: list[str] = []
    permissions: list[str] = ["*:*:*"]  # 简化: admin 全部权限

    class Config:
        from_attributes = True
