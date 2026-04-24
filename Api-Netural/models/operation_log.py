# models/operation_log.py — 增强版：支持日志类型分类
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from datetime import datetime
from core.database import Base


class OperationLog(Base):
    """操作日志表 — 覆盖 API / 数据库 / 错误 / 前端 四类日志"""
    __tablename__ = "operation_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_type = Column(String(20), default="api", index=True,
                      comment="日志类型: api=接口调用, db=数据库操作, error=错误, frontend=前端操作")
    user_name = Column(String(50), default="", comment="操作用户")
    module = Column(String(50), default="", comment="功能模块")
    action = Column(String(100), default="", comment="操作动作")
    method = Column(String(10), default="", comment="请求方法")
    url = Column(String(500), default="", comment="请求地址")
    params = Column(Text, default="", comment="请求参数")
    ip = Column(String(50), default="", comment="操作IP")
    status = Column(Integer, default=200, comment="响应状态码")
    error_msg = Column(Text, default="", comment="错误信息")
    result = Column(String(200), default="", comment="操作结果")
    cost_ms = Column(Integer, default=0, comment="耗时(ms)")
    create_time = Column(DateTime, default=datetime.now, index=True, comment="操作时间")

    # 复合索引，加速常见查询
    __table_args__ = (
        Index("ix_log_type_time", "log_type", "create_time"),
        Index("ix_log_user_time", "user_name", "create_time"),
    )
