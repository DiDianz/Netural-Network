# schemas/menu.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MenuItem(BaseModel):
    menu_id: int
    menu_name: str
    parent_id: int = 0
    order_num: int = 0
    path: str = ""
    component: str = ""
    menu_type: str = ""
    visible: str = "0"
    status: str = "0"
    icon: str = "#"
    create_time: Optional[datetime] = None
    remark: str = ""
    children: list["MenuItem"] = []

    class Config:
        from_attributes = True


class MenuCreate(BaseModel):
    menu_name: str
    parent_id: int = 0
    order_num: int = 0
    path: str = ""
    component: str = ""
    menu_type: str = "C"
    visible: str = "0"
    status: str = "0"
    icon: str = "#"
    remark: str = ""


class MenuUpdate(BaseModel):
    menu_id: int
    menu_name: str
    parent_id: int = 0
    order_num: int = 0
    path: str = ""
    component: str = ""
    menu_type: str = "C"
    visible: str = "0"
    status: str = "0"
    icon: str = "#"
    remark: str = ""


class MenuTreeResponse(BaseModel):
    menus: list[MenuItem]