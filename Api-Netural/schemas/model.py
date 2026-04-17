# schemas/model.py
from pydantic import BaseModel, Field
from typing import Optional, List


# ========== 模型信息 ==========

class ModelInfo(BaseModel):
    key: str
    name: str
    display_name: str
    description: str
    status: str
    is_current: bool = False
    accuracy: Optional[float] = None
    trained_at: Optional[str] = None
    total_predictions: int = 0
    params_count: int = 0
    device: str = "cpu"


# ========== 模型列表响应 ==========

class ModelListResponse(BaseModel):
    code: int = 200
    data: List[ModelInfo] = []


# ========== 切换模型请求 ==========

class SwitchRequest(BaseModel):
    model_key: str = Field(..., min_length=1, max_length=50, description="模型标识: lstm / gru / transformer")


class SwitchResponse(BaseModel):
    code: int = 200
    data: dict = {}
    msg: str = "切换成功"


# ========== 训练请求 ==========

class TrainRequest(BaseModel):
    model_key: str = Field(..., min_length=1, max_length=50, description="模型标识")
    epochs: int = Field(default=50, ge=1, le=500, description="训练轮次")
    lr: float = Field(default=0.001, gt=0, le=1, description="学习率")
    batch_size: int = Field(default=32, ge=1, le=256, description="批大小")
    base_model_id: Optional[str] = Field(default=None, description="基础模型版本ID，用于继续训练")
    model_name: Optional[str] = Field(default=None, max_length=100, description="自定义模型名称")


# ========== 训练日志条目 ==========

class TrainLogEntry(BaseModel):
    epoch: int = 0
    loss: float = 0
    val_loss: float = 0
    lr: float = 0
    time: float = 0


# ========== 训练状态响应 ==========

class TrainStatusResponse(BaseModel):
    is_training: bool = False
    model_key: Optional[str] = None
    epoch: int = 0
    total_epochs: int = 0
    loss: float = 0
    val_loss: float = 0
    best_val_loss: float = 0
    progress: float = 0
    lr: float = 0
    elapsed: float = 0
    logs: List[TrainLogEntry] = []
    loss_history: List[float] = []
    val_loss_history: List[float] = []
    done: bool = False
    message: str = ""
    error: str = ""


# ========== 预测历史记录 ==========

class PredictionHistoryItem(BaseModel):
    id: int = 0
    model_key: str = ""
    model_name: str = ""
    prediction: float = 0
    confidence_upper: float = 0
    confidence_lower: float = 0
    uncertainty: float = 0
    created_at: Optional[str] = None


class PredictionHistoryResponse(BaseModel):
    code: int = 200
    data: List[PredictionHistoryItem] = []
    total: int = 0


# ========== 训练历史记录 ==========

class TrainHistoryItem(BaseModel):
    id: int = 0
    model_key: str = ""
    model_name: str = ""
    total_epochs: int = 0
    best_val_loss: Optional[float] = None
    duration_seconds: Optional[float] = None
    status: str = ""
    created_at: Optional[str] = None


class TrainHistoryResponse(BaseModel):
    code: int = 200
    data: List[TrainHistoryItem] = []


# ========== 通用响应 ==========

class CommonResponse(BaseModel):
    code: int = 200
    msg: str = ""
    data: Optional[dict] = None
