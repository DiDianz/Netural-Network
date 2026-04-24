# main.py — 增强版：全链路日志（API + 数据库 + 错误 + 前端）
import time
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
from api.plc import router as plc_router
from api.config import router as config_router
from api.instance import router as instance_router
from api.dryer import router as dryer_router
from api.feature import router as feature_router
from api.log import router as log_router

# 导入模型以确保表被注册
from models.predict_history import PredictHistory
from models.train_log import TrainLog
from models.train_trend import TrainTrend
from models.plc_device import PlcDevice
from models.plc_db_point import PlcDbPoint
from models.sys_config import SysConfig
from models.prediction_instance import PredictionInstance
from models.saved_model import SavedModel
from models.operation_log import OperationLog


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("正在初始化数据库...")
    init_db()

    # ★ 启动数据库操作日志监听
    from core.logger import setup_db_logger
    setup_db_logger()

    # 自动插入特征方案菜单
    from core.feature_schema import init_menu_on_startup
    init_menu_on_startup()

    print("系统启动完成（全链路日志已启用）")
    yield
    from core.plc_service import plc_manager
    plc_manager.disconnect_all()
    print("系统关闭")


app = FastAPI(
    title="神经网络预测系统",
    version="3.2.0",  # 版本升级
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

# ========== 全局异常处理器 ==========
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理的异常，记录到日志"""
    error_msg = f"{type(exc).__name__}: {str(exc)}"
    tb = traceback.format_exc()

    try:
        from core.logger import write_error_log
        user_name = ""
        auth_header = request.headers.get("authorization", "")
        if auth_header:
            try:
                from core.security import decode_token
                token = auth_header.replace("Bearer ", "")
                payload = decode_token(token)
                user_name = payload.get("sub", "")
            except Exception:
                pass

        write_error_log(
            module=_get_module(request.url.path),
            error_msg=f"{error_msg}\n{tb[-1000:]}",  # 截取最后1000字符的堆栈
            user_name=user_name,
            url=request.url.path,
        )
    except Exception:
        pass

    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误", "error": str(exc)[:200]}
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404 也记录"""
    try:
        from core.logger import write_log
        write_log(
            log_type="error",
            module="路由",
            action="404-NotFound",
            method=request.method,
            url=request.url.path,
            status=404,
            error_msg=f"路径不存在: {request.url.path}",
        )
    except Exception:
        pass
    return JSONResponse(status_code=404, content={"detail": "路径不存在"})


# ========== 操作日志中间件（增强版） ==========
# 不需要记录日志的路径
SKIP_LOG_PATHS = {
    "/health", "/docs", "/openapi.json", "/redoc",
    "/log/list", "/log/modules",
}
SKIP_LOG_PREFIXES = (
    "/predict/stream", "/predict/plc-stream", "/predict/multi-stream",
    "/model/train/stream", "/model/train/upload/stream",
    "/instance/stream", "/plc/read/stream", "/dryer/train",
    "/dryer/plc-stream", "/log/record",
)

# URL → 模块名映射
MODULE_MAP = {
    "/auth/": "认证",
    "/system/user": "用户管理",
    "/user/": "用户管理",
    "/role/": "角色管理",
    "/menu/": "菜单管理",
    "/predict/": "预测",
    "/model/": "模型管理",
    "/upload/": "文件上传",
    "/plc/": "PLC管理",
    "/instance/": "预测实例",
    "/dryer/": "烘丝机预测",
    "/feature/": "特征方案",
    "/log/": "操作日志",
    "/system/config": "系统设置",
}


def _get_module(url: str) -> str:
    for prefix, name in MODULE_MAP.items():
        if prefix in url:
            return name
    return "其他"


def _get_action(method: str, url: str) -> str:
    """根据方法和路径推断操作动作"""
    action_map = {
        "GET": "查询",
        "POST": "新增",
        "PUT": "修改",
        "DELETE": "删除",
    }
    base = action_map.get(method, method)
    parts = url.rstrip("/").split("/")
    if parts:
        last = parts[-1].split("?")[0]
        if last and last not in ("v1", "api"):
            return f"{base}-{last}"
    return base


def _extract_user_name(request: Request) -> str:
    """从请求中提取用户名"""
    auth_header = request.headers.get("authorization", "")
    if not auth_header:
        return ""
    try:
        from core.security import decode_token
        token = auth_header.replace("Bearer ", "")
        payload = decode_token(token)
        return payload.get("sub", "")
    except Exception:
        return ""


@app.middleware("http")
async def log_request_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method

    # 跳过不需要记录的路径
    if path in SKIP_LOG_PATHS or any(path.startswith(p) for p in SKIP_LOG_PREFIXES):
        return await call_next(request)

    if method == "OPTIONS":
        return await call_next(request)

    start_time = time.time()
    response = await call_next(request)
    cost_ms = int((time.time() - start_time) * 1000)
    status_code = response.status_code

    # ★ 记录所有 API 调用（不再跳过 200）
    try:
        from core.logger import write_log

        user_name = _extract_user_name(request)
        module = _get_module(path)
        action = _get_action(method, path)

        # 获取请求参数
        params = ""
        if method == "GET":
            params = str(request.query_params)[:2000]
        elif method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
                params = body.decode("utf-8", errors="ignore")[:2000]
            except Exception:
                pass

        ip = request.client.host if request.client else ""

        error_msg = ""
        if status_code >= 400:
            error_msg = f"HTTP {status_code}"

        write_log(
            log_type="api",
            user_name=user_name,
            module=module,
            action=action,
            method=method,
            url=path,
            params=params,
            ip=ip,
            status=status_code,
            error_msg=error_msg,
            result="成功" if status_code < 400 else "失败",
            cost_ms=cost_ms,
        )
    except Exception:
        pass

    return response


# 注册所有路由
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(role_router)
app.include_router(menu_router)
app.include_router(predict_router)
app.include_router(model_router)
app.include_router(ws_router)
app.include_router(upload_router)
app.include_router(plc_router)
app.include_router(config_router)
app.include_router(instance_router)
app.include_router(dryer_router)
app.include_router(feature_router)
app.include_router(log_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
