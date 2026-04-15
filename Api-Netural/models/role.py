# models/role.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base
from models.user import sys_user_role
from models.menu import sys_role_menu


class SysRole(Base):
    __tablename__ = "sys_role"

    role_id = Column(Integer, primary_key=True, autoincrement=True, comment="角色ID")
    role_name = Column(String(30), nullable=False, comment="角色名称")
    role_key = Column(String(100), nullable=False, comment="角色权限字符串")
    sort = Column(Integer, nullable=False, comment="显示顺序")
    status = Column(String(1), nullable=False, comment="状态(0正常 1停用)")
    del_flag = Column(String(1), default="0", comment="删除标志")
    create_time = Column(DateTime, default=datetime.now)
    remark = Column(String(500), comment="备注")

    users = relationship("SysUser", secondary=sys_user_role, back_populates="roles")
    menus = relationship("SysMenu", secondary=sys_role_menu, lazy="joined")