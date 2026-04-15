# schemas/user.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserInfo(BaseModel):
    user_id: int
    user_name: str
    nick_name: str
    email: str = ""
    phonenumber: str = ""
    avatar: str = ""
    roles: list[str] = []
    permissions: list[str] = ["*:*:*"]

    class Config:
        from_attributes = True


class UserItem(BaseModel):
    user_id: int
    user_name: str
    nick_name: str
    email: str = ""
    phonenumber: str = ""
    sex: str = "0"
    status: str = "0"
    login_date: Optional[datetime] = None
    create_time: Optional[datetime] = None
    role_ids: list[int] = []
    role_names: list[str] = []

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    user_name: str
    nick_name: str
    password: str
    email: str = ""
    phonenumber: str = ""
    sex: str = "0"
    status: str = "0"
    remark: str = ""
    role_ids: list[int] = []


class UserUpdate(BaseModel):
    user_id: int
    nick_name: str
    email: str = ""
    phonenumber: str = ""
    sex: str = "0"
    status: str = "0"
    remark: str = ""
    role_ids: list[int] = []


class UserResetPwd(BaseModel):
    user_id: int
    new_password: str


class UserListQuery(BaseModel):
    page: int = 1
    page_size: int = 10
    user_name: str = ""
    phonenumber: str = ""
    status: str = ""


class UserListResponse(BaseModel):
    total: int
    rows: list[UserItem]