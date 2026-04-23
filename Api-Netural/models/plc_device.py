# models/plc_device.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from core.database import Base


class PlcDevice(Base):
    """PLC 设备表"""
    __tablename__ = "plc_device"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="设备ID")
    name = Column(String(100), nullable=False, comment="设备名称")
    ip = Column(String(50), nullable=False, comment="PLC IP 地址")
    port = Column(Integer, default=None, comment="PLC 端口 (None=无端口)")
    rack = Column(Integer, default=0, comment="机架号")
    slot = Column(Integer, default=1, comment="插槽号")
    status = Column(String(20), default="disconnected", comment="连接状态: disconnected/connected/error")
    remark = Column(String(500), default="", comment="备注")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
