# models/train_log.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from core.database import Base


class TrainLog(Base):
    """训练日志表"""
    __tablename__ = "train_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_key = Column(String(50), nullable=False, index=True, comment="模型标识")
    model_name = Column(String(100), nullable=False, comment="模型名称")
    epoch = Column(Integer, nullable=False, comment="训练轮次")
    total_epochs = Column(Integer, nullable=False, comment="总轮次")
    train_loss = Column(Float, comment="训练损失")
    val_loss = Column(Float, comment="验证损失")
    learning_rate = Column(Float, comment="学习率")
    status = Column(String(20), default="running", comment="状态: running/completed/failed")
    best_val_loss = Column(Float, comment="最优验证损失")
    duration_seconds = Column(Float, comment="训练耗时(秒)")
    created_at = Column(DateTime, default=datetime.now, index=True, comment="创建时间")
    remark = Column(Text, comment="备注")
