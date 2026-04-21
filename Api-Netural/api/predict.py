# api/predict.py
import json
import asyncio
import time
import numpy as np
from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from core.database import get_db
from core.model_manager import model_manager
from core.data_manager import data_manager
from core.plc_service import plc_manager
from models.predict_history import PredictHistory

router = APIRouter(prefix="/predict", tags=["预测"])


@router.get("/stream")
async def predict_stream(
    interval: float = Query(1.0, ge=0.1, le=10.0),
    model_key: str = Query(None),
    use_uploaded: bool = Query(False)
):
    model_manager._interval = interval
    if use_uploaded:
        data_manager.reset_index()

    async def event_generator():
        try:
            async for prediction in model_manager.stream_predictions(model_key, use_uploaded):
                yield f"data: {json.dumps(prediction, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            model_manager.stop()

    return StreamingResponse(event_generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})


# ========== 独立模式：PLC + 点位 → 模型推理 ==========
from core.plc_simulator import plc_simulator
from models.plc_db_point import PlcDbPoint


@router.get("/plc-stream")
async def plc_predict_stream(
    device_id: int = Query(..., description="PLC 设备 ID"),
    model_key: str = Query(..., description="模型标识: lstm / gru / transformer"),
    point_ids: str = Query("", description="逗号分隔的点位 ID，不传则读取所有启用点位"),
    interval: float = Query(1.0, ge=0.1, le=30.0),
    use_saved_model: str = Query("", description="已保存模型版本 ID"),
    db: Session = Depends(get_db)
):
    """
    独立模式 SSE 预测流 — 指定 PLC 设备 + 数据点位 → 模型推理
    """
    from models.plc_device import PlcDevice

    # 校验设备
    device = db.query(PlcDevice).filter(PlcDevice.id == device_id).first()
    if not device:
        raise HTTPException(404, "PLC 设备不存在")

    is_simulated = plc_simulator.is_simulating(device_id)
    is_real_connected = plc_manager.is_connected(device_id)
    if not is_simulated and not is_real_connected:
        raise HTTPException(400, "PLC 设备未连接或未启动模拟")

    # 校验模型
    if model_key not in model_manager.models:
        raise HTTPException(400, f"模型不存在: {model_key}")

    # 如果指定了已保存模型，加载权重
    if use_saved_model and use_saved_model in model_manager.saved_models:
        model_manager.load_model_weights(model_key, use_saved_model)
        print(f"独立预测: 已加载模型权重 {use_saved_model}")

    # 获取点位
    query = db.query(PlcDbPoint).filter(
        PlcDbPoint.device_id == device_id,
        PlcDbPoint.is_active == 1
    )
    if point_ids:
        pids = [int(x.strip()) for x in point_ids.split(",") if x.strip()]
        query = query.filter(PlcDbPoint.id.in_(pids))
    points = query.all()
    if not points:
        raise HTTPException(400, "没有可用的启用点位")

    point_list = [{
        "id": p.id, "point_name": p.point_name,
        "db_number": p.db_number, "start_address": p.start_address,
        "data_type": p.data_type, "bit_index": p.bit_index
    } for p in points]

    model = model_manager.models[model_key]["model"]
    model.eval()
    input_dim = model_manager.input_dim
    window_size = model_manager.window_size

    # buffer
    buffer = []
    for _ in range(window_size):
        buffer.append(list(np.random.randn(input_dim).astype(float)))

    async def event_generator():
        import torch
        tick = 0
        try:
            while True:
                tick += 1
                timestamp = time.time()

                # 1. 读取 PLC 数据（模拟 or 真实）
                if is_simulated:
                    plc_result = plc_simulator.read_multiple(device_id, point_list)
                else:
                    plc_result = plc_manager.read_multiple(device_id, point_list)

                if not plc_result["success"]:
                    yield f"data: {json.dumps({'error': plc_result['msg'], 'tick': tick}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(interval)
                    continue

                # 2. 转为特征向量
                values = []
                for item in plc_result["data"]:
                    if item["success"] and item["value"] is not None:
                        values.append(float(item["value"]))
                    else:
                        values.append(0.0)

                padded = values[:input_dim]
                while len(padded) < input_dim:
                    padded.append(0.0)
                buffer.append(padded)
                while len(buffer) > window_size:
                    buffer.pop(0)

                # 3. 推理
                try:
                    input_seq = np.array(buffer, dtype=np.float32)
                    input_tensor = torch.tensor(input_seq).unsqueeze(0).to(model_manager.device)

                    with torch.no_grad():
                        pred = model(input_tensor).cpu().numpy()[0]

                    # MC Dropout
                    model.train()
                    mc_preds = []
                    for _ in range(10):
                        with torch.no_grad():
                            p = model(input_tensor).cpu().numpy()[0]
                        mc_preds.append(float(p))
                    model.eval()

                    mean_pred = float(np.mean(mc_preds))
                    std_pred = float(np.std(mc_preds))

                    payload = {
                        "timestamp": timestamp,
                        "tick": tick,
                        "model_key": model_key,
                        "model_name": model_manager.models[model_key]["display_name"],
                        "prediction": round(mean_pred, 6),
                        "confidence_upper": round(mean_pred + 2 * std_pred, 6),
                        "confidence_lower": round(mean_pred - 2 * std_pred, 6),
                        "uncertainty": round(std_pred, 6),
                        "simulated": is_simulated,
                        "plc_points": plc_result["data"]
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e), 'tick': tick}, ensure_ascii=False)}\n\n"

                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


@router.post("/save")
async def save_prediction(model_key: str = Query(...), db: Session = Depends(get_db)):
    result = model_manager.predict_once(model_key)
    record = PredictHistory(
        model_key=result["model_key"], model_name=result["model_name"],
        prediction=result["prediction"], confidence_upper=result["confidence_upper"],
        confidence_lower=result["confidence_lower"], uncertainty=result["uncertainty"],
        input_window_size=result["input_window_size"]
    )
    db.add(record)
    db.commit()
    return {"code": 200, "msg": "保存成功", "data": result}


@router.get("/history")
async def get_history(
    model_key: str = Query(None),
    keyword: str = Query(None, description="关键字搜索"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """获取预测历史，支持关键字搜索"""
    query = db.query(PredictHistory)

    if model_key:
        query = query.filter(PredictHistory.model_key == model_key)

    if keyword:
        like_kw = f"%{keyword}%"
        query = query.filter(
            PredictHistory.model_key.like(like_kw) |
            PredictHistory.model_name.like(like_kw)
        )

    total = query.count()
    records = query.order_by(PredictHistory.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "code": 200, "total": total,
        "data": [
            {
                "id": r.id, "model_key": r.model_key, "model_name": r.model_name,
                "prediction": r.prediction, "confidence_upper": r.confidence_upper,
                "confidence_lower": r.confidence_lower, "uncertainty": r.uncertainty,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at is not None else None
            }
            for r in reversed(records)
        ]
    }


@router.get("/actual-values")
async def get_actual_values(
    file_ids: str = Query(None),
    limit: int = Query(500, ge=1, le=5000)
):
    ids = [f.strip() for f in file_ids.split(",") if f.strip()] if file_ids else None
    values = data_manager.get_all_actual_values(limit=limit, file_ids=ids) # type: ignore
    return {"code": 200, "data": values}


# ========== 多 PLC 多模型同时预测 ==========
@router.get("/multi-stream")
async def multi_predict_stream(
    devices: str = Query(..., description='JSON: [{"device_id":1,"point_ids":"1,2"}]'),
    model_keys: str = Query(..., description="逗号分隔: lstm,gru,transformer"),
    interval: float = Query(1.0, ge=0.1, le=30.0),
    db: Session = Depends(get_db)
):
    """
    多 PLC + 多模型 并行预测 SSE 流
    每次 tick: 读取所有 PLC 数据 → 所有模型推理 → 统一推送
    """
    from models.plc_db_point import PlcDbPoint

    # 解析设备列表
    try:
        device_list = json.loads(devices)
    except json.JSONDecodeError:
        raise HTTPException(400, "devices 参数格式错误，请传 JSON 数组")

    if not device_list:
        raise HTTPException(400, "至少选择一个 PLC 设备")

    # 解析模型列表
    keys = [k.strip() for k in model_keys.split(",") if k.strip()]
    for k in keys:
        if k not in model_manager.models:
            raise HTTPException(400, f"模型不存在: {k}")

    # 构建每个设备的点位信息
    device_points = {}
    for dev in device_list:
        did = dev.get("device_id")
        if did is None:
            raise HTTPException(400, "device_id 不能为空")
        if not plc_manager.is_connected(did):
            raise HTTPException(400, f"PLC 设备 {did} 未连接")

        query = db.query(PlcDbPoint).filter(
            PlcDbPoint.device_id == did,
            PlcDbPoint.is_active == 1
        )
        point_ids_str = dev.get("point_ids", "")
        if point_ids_str:
            pids = [int(x.strip()) for x in point_ids_str.split(",") if x.strip()]
            query = query.filter(PlcDbPoint.id.in_(pids))

        points = query.all()
        if not points:
            raise HTTPException(400, f"PLC 设备 {did} 没有可用的启用点位")

        device_points[did] = [{
            "id": p.id, "point_name": p.point_name,
            "db_number": p.db_number, "start_address": p.start_address,
            "data_type": p.data_type, "bit_index": p.bit_index
        } for p in points]

    # 每个模型维护独立的 buffer（从 PLC 读取的真实数据填充）
    model_buffers = {}
    for k in keys:
        model_manager.models[k]["model"].eval()
        model_buffers[k] = {
            "values": [],  # 最近 N 步的 PLC 数值
            "device_name": ""
        }

    async def event_generator():
        try:
            tick = 0
            while True:
                tick += 1
                timestamp = time.time()

                # 1. 并行读取所有 PLC
                plc_data = {}
                for did, pts in device_points.items():
                    result = plc_manager.read_multiple(did, pts)
                    if result["success"]:
                        values = []
                        for item in result["data"]:
                            if item["success"] and item["value"] is not None:
                                values.append(float(item["value"]))
                            else:
                                values.append(0.0)
                        plc_data[did] = {
                            "device_id": did,
                            "points": result["data"],
                            "feature_vector": values
                        }
                    else:
                        plc_data[did] = {
                            "device_id": did,
                            "points": [],
                            "feature_vector": [],
                            "error": result["msg"]
                        }

                # 2. 用 PLC 数据更新各模型 buffer 并推理
                predictions = []
                for k in keys:
                    model = model_manager.models[k]["model"]
                    model.eval()
                    buf = model_buffers[k]

                    # 将 PLC 数据转为特征向量（填充到 input_dim）
                    for did, pdata in plc_data.items():
                        feat = pdata["feature_vector"]
                        if not feat:
                            continue
                        # 截断或填充到 input_dim
                        padded = feat[:model_manager.input_dim]
                        while len(padded) < model_manager.input_dim:
                            padded.append(0.0)
                        buf["values"].append(padded)
                        buf["device_name"] = f"PLC-{did}"

                    # 保持 window_size 长度
                    while len(buf["values"]) > model_manager.window_size:
                        buf["values"].pop(0)

                    # 如果数据不够窗口大小，用随机填充
                    while len(buf["values"]) < model_manager.window_size:
                        buf["values"].insert(0, list(np.random.randn(model_manager.input_dim).astype(float)))

                    # 推理
                    try:
                        import torch
                        input_seq = np.array(buf["values"], dtype=np.float32)
                        input_tensor = torch.tensor(input_seq).unsqueeze(0).to(model_manager.device)

                        with torch.no_grad():
                            pred = model(input_tensor).cpu().numpy()[0]

                        # MC Dropout 不确定性估计
                        model.train()
                        mc_preds = []
                        for _ in range(10):
                            with torch.no_grad():
                                p = model(input_tensor).cpu().numpy()[0]
                            mc_preds.append(float(p))
                        model.eval()

                        mean_pred = float(np.mean(mc_preds))
                        std_pred = float(np.std(mc_preds))

                        predictions.append({
                            "model_key": k,
                            "model_name": model_manager.models[k]["display_name"],
                            "prediction": round(mean_pred, 6),
                            "confidence_upper": round(mean_pred + 2 * std_pred, 6),
                            "confidence_lower": round(mean_pred - 2 * std_pred, 6),
                            "uncertainty": round(std_pred, 6),
                            "tick": tick
                        })
                        model_manager.models[k]["total_predictions"] += 1

                    except Exception as e:
                        predictions.append({
                            "model_key": k,
                            "model_name": model_manager.models[k]["display_name"],
                            "error": str(e),
                            "tick": tick
                        })

                # 3. 组装 payload 并推送
                payload = {
                    "timestamp": timestamp,
                    "tick": tick,
                    "plc_data": {
                        str(did): {
                            "device_id": did,
                            "points": pdata["points"]
                        } for did, pdata in plc_data.items()
                    },
                    "predictions": predictions
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


# # api/predict.py
# import json
# import asyncio
# from fastapi import APIRouter, Query, Depends
# from fastapi.responses import StreamingResponse
# from sqlalchemy.orm import Session
# from core.database import get_db
# from core.model_manager import model_manager
# from models.predict_history import PredictHistory
# from core.data_manager import data_manager

# router = APIRouter(prefix="/predict", tags=["预测"])


# @router.get("/stream")
# async def predict_stream(
#     interval: float = Query(1.0, description="预测间隔(秒)", ge=0.1, le=10.0),
#     model_key: str = Query(None, description="模型标识"),
#     use_uploaded: bool = Query(False, description="使用上传数据")  
# ):
#     """
#     SSE 接口 — 一次请求，持续推送预测数据
#     """
#     model_manager._interval = interval

#     if use_uploaded:
#         data_manager.reset_index()  
        
#     async def event_generator():
#         try:
#             async for prediction in model_manager.stream_predictions(model_key):
#                 data = json.dumps(prediction, ensure_ascii=False)
#                 yield f"data: {data}\n\n"
#         except asyncio.CancelledError:
#             model_manager.stop()

#     return StreamingResponse(
#         event_generator(),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection": "keep-alive",
#             "X-Accel-Buffering": "no"
#         }
#     )


# @router.post("/save")
# async def save_prediction(
#     model_key: str = Query(...),
#     db: Session = Depends(get_db)
# ):
#     """保存当前最新预测到数据库"""
#     result = model_manager.predict_once(model_key)

#     record = PredictHistory(
#         model_key=result["model_key"],
#         model_name=result["model_name"],
#         prediction=result["prediction"],
#         confidence_upper=result["confidence_upper"],
#         confidence_lower=result["confidence_lower"],
#         uncertainty=result["uncertainty"],
#         input_window_size=result["input_window_size"]
#     )
#     db.add(record)
#     db.commit()

#     return {"code": 200, "msg": "保存成功", "data": result}


# @router.get("/history")
# async def get_history(
#     model_key: str = Query(None),
#     limit: int = Query(200, ge=1, le=1000),
#     db: Session = Depends(get_db)
# ):
#     """获取历史预测数据"""
#     query = db.query(PredictHistory)

#     if model_key:
#         query = query.filter(PredictHistory.model_key == model_key)

#     records = query.order_by(PredictHistory.created_at.desc()).limit(limit).all()

#     return {
#         "code": 200,
#         "data": [
#             {
#                 "id": r.id,
#                 "model_key": r.model_key,
#                 "model_name": r.model_name,
#                 "prediction": r.prediction,
#                 "confidence_upper": r.confidence_upper,
#                 "confidence_lower": r.confidence_lower,
#                 "uncertainty": r.uncertainty,
#                 "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at is not None else None 
#             }
#             for r in reversed(records)
#         ],
#         "total": query.count()
#     }

# # ========== 新增：获取上传数据的实际值 ==========
# @router.get("/actual-values")
# async def get_actual_values(
#     file_ids: str = Query(None, description="逗号分隔的文件ID"),
#     limit: int = Query(500, ge=1, le=5000)
# ):
#     ids = [f.strip() for f in file_ids.split(",") if f.strip()] if file_ids else None
#     values = data_manager.get_all_actual_values(limit=limit, file_ids=ids) # type: ignore
#     return {"code": 200, "data": values}