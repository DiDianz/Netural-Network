# models/saved_model.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from core.database import Base


class SavedModel(Base):
    """已保存模型表 — 通用模型 + 烘丝机模型统一存储"""
    __tablename__ = "saved_model"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(50), nullable=False, unique=True, index=True, comment="模型版本ID")
    model_type = Column(String(20), nullable=False, default="general", comment="模型类型: general/dryer")
    model_key = Column(String(50), nullable=False, comment="模型标识: lstm/gru/transformer/dryer")
    display_name = Column(String(100), default="", comment="模型显示名称")
    name = Column(String(200), default="", comment="自定义名称")
    filename = Column(String(200), default="", comment="文件名")
    epochs = Column(Integer, default=0, comment="训练轮次")
    best_val_loss = Column(Float, default=0, comment="最优验证损失")
    r2 = Column(Float, default=0, comment="R² 决定系数")
    trained_at = Column(DateTime, default=datetime.now, comment="训练完成时间")
    remark = Column(Text, default="", comment="备注")
    file_size_kb = Column(Float, default=0, comment="文件大小(KB)")
    schema_id = Column(String(50), default="default", comment="特征方案ID")
    input_dim = Column(Integer, default=0, comment="输入特征维度")
    extra_json = Column(Text, default="{}", comment="扩展字段(JSON)")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
