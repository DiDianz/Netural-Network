# models/prediction_instance.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from core.database import Base


class PredictionInstance(Base):
    """预测实例 — 每个实例独立连接一个 PLC，独立运行预测"""
    __tablename__ = "prediction_instance"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="实例ID")
    name = Column(String(100), nullable=False, comment="实例名称（菜单显示名称）")
    device_id = Column(Integer, nullable=False, comment="PLC 设备ID")
    point_ids = Column(String(500), default="", comment="点位ID列表，逗号分隔，空=全部启用点位")
    model_key = Column(String(50), default="lstm", comment="模型类型: lstm/gru/transformer")
    base_model_id = Column(String(50), default="", comment="基于的已保存模型版本ID，空=默认权重")
    interval = Column(Integer, default=10, comment="预测间隔(秒*10)，如10=1.0s")
    order_num = Column(Integer, default=0, comment="排序")
    is_active = Column(Integer, default=1, comment="是否启用 1启用 0停用")
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)
