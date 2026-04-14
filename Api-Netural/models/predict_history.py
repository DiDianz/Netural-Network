# models/predict_history.py
from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from core.database import Base


class PredictHistory(Base):
    """预测历史记录表"""
    __tablename__ = "predict_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_key = Column(String(50), nullable=False, index=True, comment="模型标识")
    model_name = Column(String(100), nullable=False, comment="模型名称")
    prediction = Column(Float, nullable=False, comment="预测值")
    confidence_upper = Column(Float, comment="置信上界")
    confidence_lower = Column(Float, comment="置信下界")
    uncertainty = Column(Float, comment="不确定性")
    input_window_size = Column(Integer, comment="输入窗口大小")
    created_at = Column(DateTime, default=datetime.now, index=True, comment="创建时间")
