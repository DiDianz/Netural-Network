# models/sys_config.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from core.database import Base


class SysConfig(Base):
    __tablename__ = "sys_config"

    config_id = Column(Integer, primary_key=True, autoincrement=True, comment="参数主键")
    config_name = Column(String(100), default="", comment="参数名称")
    config_key = Column(String(100), default="", comment="参数键名")
    config_value = Column(String(500), default="", comment="参数键值")
    config_type = Column(String(1), default="N", comment="系统内置（Y是 N否）")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    remark = Column(String(500), default="", comment="备注")
