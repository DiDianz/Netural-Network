# models/menu.py
from sqlalchemy import Column, Integer, String, DateTime, Table, ForeignKey
from datetime import datetime
from core.database import Base

# 角色-菜单关联表
sys_role_menu = Table(
    "sys_role_menu",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("sys_role.role_id"), primary_key=True),
    Column("menu_id", Integer, ForeignKey("sys_menu.menu_id"), primary_key=True),
)


class SysMenu(Base):
    __tablename__ = "sys_menu"

    menu_id = Column(Integer, primary_key=True, autoincrement=True, comment="菜单ID")
    menu_name = Column(String(50), nullable=False, comment="菜单名称")
    parent_id = Column(Integer, default=0, comment="父菜单ID")
    order_num = Column(Integer, default=0, comment="显示顺序")
    path = Column(String(200), default="", comment="路由地址")
    component = Column(String(255), default="", comment="组件路径")
    menu_type = Column(String(1), default="", comment="菜单类型(M目录 C菜单 F按钮)")
    visible = Column(String(1), default="0", comment="是否显示(0显示 1隐藏)")
    status = Column(String(1), default="0", comment="菜单状态(0正常 1停用)")
    icon = Column(String(100), default="#", comment="菜单图标")
    create_time = Column(DateTime, default=datetime.now)
    remark = Column(String(500), comment="备注")