# schemas/dryer.py
from pydantic import BaseModel, Field
from typing import Optional, List


class TrainRequest(BaseModel):
    """训练请求"""
    epochs: int = Field(100, ge=10, le=500, description="训练轮次")
    batch_size: int = Field(32, ge=8, le=128, description="批大小")
    learning_rate: float = Field(0.001, gt=0, le=0.1, description="学习率")
    window_size: int = Field(10, ge=3, le=50, description="滑动窗口大小")
    hidden_dim: int = Field(128, ge=32, le=512, description="隐藏层维度")
    num_layers: int = Field(2, ge=1, le=4, description="LSTM层数")
    dropout: float = Field(0.2, ge=0, le=0.5, description="Dropout比例")
    test_ratio: float = Field(0.2, ge=0.1, le=0.4, description="测试集比例")
    feature_weights: Optional[List[float]] = Field(None, description="初始特征权重 (12个, 0~1)")
    target_range: List[float] = Field([14.0, 15.0], description="目标出口水分范围")


class PredictRequest(BaseModel):
    """预测请求"""
    data: List[List[float]] = Field(..., description="输入数据 (seq_len × 12)")
    model_version: Optional[str] = Field(None, description="指定模型版本")


class PLCPredictRequest(BaseModel):
    """PLC实时预测请求"""
    device_id: int = Field(..., description="PLC设备ID")
    point_ids: Optional[str] = Field(None, description="逗号分隔的点位ID")
    model_version: Optional[str] = Field(None, description="指定模型版本")
    interval: float = Field(1.0, ge=0.1, le=30.0, description="预测间隔(秒)")


class FeatureWeightUpdate(BaseModel):
    """特征权重更新"""
    weights: List[float] = Field(..., min_length=12, max_length=12, description="12个特征权重 (0~1)")


class ModelVersion(BaseModel):
    """模型版本信息"""
    version: str
    created_at: str
    metrics: dict
    config: dict
    is_active: bool = False
