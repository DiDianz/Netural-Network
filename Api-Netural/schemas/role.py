# schemas/role.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RoleItem(BaseModel):
    role_id: int
    role_name: str
    role_key: str
    sort: int
    status: str
    remark: str = ""
    create_time: Optional[datetime] = None
    menu_ids: list[int] = []

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    role_name: str
    role_key: str
    sort: int = 0
    status: str = "0"
    remark: str = ""
    menu_ids: list[int] = []


class RoleUpdate(BaseModel):
    role_name: str
    role_key: str
    sort: int = 0
    status: str = "0"
    remark: str = ""
    menu_ids: list[int] = []


class RoleListResponse(BaseModel):
    total: int
    rows: list[RoleItem]