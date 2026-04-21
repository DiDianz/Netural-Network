# main.py — 注册 PLC 路由
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.database import init_db

# 导入所有路由
from api.auth import router as auth_router
from api.user import router as user_router
from api.role import router as role_router
from api.menu import router as menu_router
from api.predict import router as predict_router
from api.model import router as model_router
from api.websocket import router as ws_router
from api.upload import router as upload_router
from api.plc import router as plc_router  # PLC 管理
from api.config import router as config_router  # 系统设置
from api.instance import router as instance_router  # 预测实例管理

# 导入模型以确保表被注册
from models.predict_history import PredictHistory
from models.train_log import TrainLog
from models.train_trend import TrainTrend
from models.plc_device import PlcDevice      # PLC 设备表
from models.plc_db_point import PlcDbPoint   # PLC 点位表
from models.sys_config import SysConfig       # 系统配置表
from models.prediction_instance import PredictionInstance  # 预测实例表

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("正在初始化数据库...")
    init_db()
    print("系统启动完成")
    yield
    # 关闭时断开所有 PLC 连接
    from core.plc_service import plc_manager
    plc_manager.disconnect_all()
    print("系统关闭")


app = FastAPI(
    title="神经网络预测系统",
    version="3.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有路由
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(role_router)
app.include_router(menu_router)
app.include_router(predict_router)
app.include_router(model_router)
app.include_router(ws_router)
app.include_router(upload_router)
app.include_router(plc_router)  # PLC 管理路由
app.include_router(config_router)  # 系统设置路由
app.include_router(instance_router)  # 预测实例管理路由

@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
