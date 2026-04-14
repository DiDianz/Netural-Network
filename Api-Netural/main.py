# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.database import init_db

# 导入所有路由
from api.auth import router as auth_router
from api.user import router as user_router
from api.menu import router as menu_router
from api.predict import router as predict_router
from api.model import router as model_router
from api.websocket import router as ws_router
from api.upload import router as upload_router

# 导入模型以确保表被注册
from models.predict_history import PredictHistory
from models.train_log import TrainLog
from models.train_trend import TrainTrend 

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("正在初始化数据库...")
    init_db()
    print("系统启动完成")
    yield
    print("系统关闭")


app = FastAPI(
    title="神经网络预测系统",
    version="3.0.0",
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
app.include_router(menu_router)
app.include_router(predict_router)
app.include_router(model_router)
app.include_router(ws_router)
app.include_router(upload_router) 

@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
