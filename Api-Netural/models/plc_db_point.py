# models/plc_db_point.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from core.database import Base


class PlcDbPoint(Base):
    """PLC DB 点位表"""
    __tablename__ = "plc_db_point"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="点位ID")
    device_id = Column(Integer, ForeignKey("plc_device.id"), nullable=False, comment="所属设备ID")
    point_name = Column(String(100), nullable=False, comment="点位名称")
    db_number = Column(Integer, nullable=False, comment="DB 块编号")
    start_address = Column(Integer, nullable=False, comment="起始字节地址")
    data_type = Column(String(20), nullable=False, default="REAL", comment="数据类型: REAL/INT/DINT/BOOL/WORD")
    bit_index = Column(Integer, default=0, comment="位索引 (仅 BOOL 类型有效)")
    description = Column(String(500), default="", comment="点位描述")
    is_active = Column(Integer, default=1, comment="是否启用 (1启用 0停用)")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
