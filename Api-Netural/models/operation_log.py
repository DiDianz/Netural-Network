# models/operation_log.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from core.database import Base


class OperationLog(Base):
    """操作日志表"""
    __tablename__ = "operation_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
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
    create_time = Column(DateTime, default=datetime.now, comment="操作时间")
