# models/train_trend.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from core.database import Base


class TrainTrend(Base):
    """训练趋势数据表（每个 epoch 存一条）"""
    __tablename__ = "train_trend"

    id = Column(Integer, primary_key=True, autoincrement=True)
    train_id = Column(String(50), nullable=False, index=True, comment="训练批次ID")
    model_key = Column(String(50), nullable=False, index=True, comment="模型标识")
    model_name = Column(String(100), nullable=False, comment="模型名称")
    epoch = Column(Integer, nullable=False, comment="当前轮次")
    total_epochs = Column(Integer, nullable=False, comment="总轮次")
    train_loss = Column(Float, comment="训练损失")
    val_loss = Column(Float, comment="验证损失")
    best_val_loss = Column(Float, comment="最优验证损失")
    learning_rate = Column(Float, comment="学习率")
    elapsed_seconds = Column(Float, comment="累计耗时(秒)")
    predictions_json = Column(Text, comment="预测值JSON数组")
    actuals_json = Column(Text, comment="实际值JSON数组")
    created_at = Column(DateTime, default=datetime.now, index=True, comment="创建时间")
