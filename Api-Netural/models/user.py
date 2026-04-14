# models/user.py
from sqlalchemy import Column, Integer, String, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

# 用户-角色关联表
sys_user_role = Table(
    "sys_user_role",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("sys_user.user_id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("sys_role.role_id"), primary_key=True),
)


class SysUser(Base):
    __tablename__ = "sys_user"

    user_id = Column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    user_name = Column(String(30), nullable=False, unique=True, comment="用户账号")
    nick_name = Column(String(30), nullable=False, comment="用户昵称")
    password = Column(String(200), nullable=False, default="", comment="密码")
    email = Column(String(50), default="", comment="邮箱")
    phonenumber = Column(String(11), default="", comment="手机号")
    sex = Column(String(1), default="0", comment="性别(0男 1女 2未知)")
    avatar = Column(String(200), default="", comment="头像地址")
    status = Column(String(1), default="0", comment="状态(0正常 1停用)")
    del_flag = Column(String(1), default="0", comment="删除标志(0存在 2删除)")
    login_ip = Column(String(128), default="", comment="最后登录IP")
    login_date = Column(DateTime, comment="最后登录时间")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    remark = Column(String(500), comment="备注")

    # 关联角色
    roles = relationship("SysRole", secondary=sys_user_role, back_populates="users", lazy="joined")

    @property
    def role_keys(self) -> list:
        return [role.role_key for role in self.roles] if self.roles else []

    @property
    def is_admin(self) -> bool:
        return "admin" in self.role_keys
