# api/instance.py
"""
预测实例管理 — 每个实例独立连接 PLC + 独立预测
"""
import json
import asyncio
import time
import numpy as np
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.model_manager import model_manager
from core.plc_service import plc_manager
from models.prediction_instance import PredictionInstance
from models.plc_db_point import PlcDbPoint

router = APIRouter(prefix="/instance", tags=["预测实例"])


@router.get("/list")
async def list_instances(db: Session = Depends(get_db)):
    """获取所有预测实例"""
    instances = db.query(PredictionInstance).order_by(PredictionInstance.order_num).all()
    data = []
    for inst in instances:
        # 获取关联的 PLC 设备名称
        from models.plc_device import PlcDevice
        device = db.query(PlcDevice).filter(PlcDevice.id == inst.device_id).first()
        device_name = device.name if device else f"设备#{inst.device_id}"
        device_connected = plc_manager.is_connected(inst.device_id) if device else False

        # 获取点位名称列表
        point_names = []
        if inst.point_ids:
            try:
                pids = [int(x.strip()) for x in inst.point_ids.split(",") if x.strip()]
                if pids:
                    pts = db.query(PlcDbPoint).filter(PlcDbPoint.id.in_(pids)).all()
                    point_names = [p.point_name for p in pts]
            except (ValueError, AttributeError):
                pass

        data.append({
            "id": inst.id,
            "name": inst.name,
            "device_id": inst.device_id,
            "device_name": device_name,
            "device_connected": device_connected,
            "point_ids": inst.point_ids or "",
            "point_names": point_names,
            "model_key": inst.model_key,
            "base_model_id": inst.base_model_id or "",
            "interval": (inst.interval or 10) / 10.0,
            "order_num": inst.order_num,
            "is_active": inst.is_active,
            "create_time": inst.create_time.strftime("%Y-%m-%d %H:%M:%S") if inst.create_time else None,
        })
    return {"code": 200, "data": data}


@router.get("/detail")
async def get_instance(instance_id: int = Query(...), db: Session = Depends(get_db)):
    """获取单个实例详情"""
    inst = db.query(PredictionInstance).filter(PredictionInstance.id == instance_id).first()
    if not inst:
        raise HTTPException(404, "实例不存在")

    # 获取点位名称列表
    point_names = []
    if inst.point_ids:
        try:
            pids = [int(x.strip()) for x in inst.point_ids.split(",") if x.strip()]
            if pids:
                pts = db.query(PlcDbPoint).filter(PlcDbPoint.id.in_(pids)).all()
                point_names = [p.point_name for p in pts]
        except (ValueError, AttributeError):
            pass

    # 获取设备名称
    from models.plc_device import PlcDevice
    device = db.query(PlcDevice).filter(PlcDevice.id == inst.device_id).first()
    device_name = device.name if device else f"设备#{inst.device_id}"

    return {"code": 200, "data": {
        "id": inst.id,
        "name": inst.name,
        "device_id": inst.device_id,
        "device_name": device_name,
        "point_ids": inst.point_ids or "",
        "point_names": point_names,
        "model_key": inst.model_key,
        "base_model_id": inst.base_model_id or "",
        "interval": (inst.interval or 10) / 10.0,
        "order_num": inst.order_num,
        "is_active": inst.is_active,
    }}


@router.post("/add")
async def add_instance(
    name: str = Query(..., min_length=1, max_length=100),
    device_id: int = Query(...),
    point_ids: str = Query("", description="逗号分隔的点位ID"),
    model_key: str = Query("lstm"),
    base_model_id: str = Query("", description="已保存模型版本ID"),
    interval: float = Query(1.0, ge=0.1, le=30.0),
    db: Session = Depends(get_db)
):
    """新增预测实例"""
    if model_key not in model_manager.models:
        raise HTTPException(400, f"模型不存在: {model_key}")

    # 如果指定了 base_model_id，校验它是否存在且类型匹配
    if base_model_id:
        if base_model_id not in model_manager.saved_models:
            raise HTTPException(400, f"已保存模型不存在: {base_model_id}")
        saved = model_manager.saved_models[base_model_id]
        if saved["model_key"] != model_key:
            raise HTTPException(400, f"模型类型不匹配: 已保存模型是 {saved['model_key']}，但选择了 {model_key}")

    from models.plc_device import PlcDevice
    device = db.query(PlcDevice).filter(PlcDevice.id == device_id).first()
    if not device:
        raise HTTPException(400, "PLC 设备不存在")

    # 获取最大排序号
    max_order = db.query(PredictionInstance.order_num).order_by(
        PredictionInstance.order_num.desc()
    ).first()
    next_order = (max_order[0] + 1) if max_order else 0

    inst = PredictionInstance(
        name=name,
        device_id=device_id,
        point_ids=point_ids,
        model_key=model_key,
        base_model_id=base_model_id,
        interval=int(interval * 10),
        order_num=next_order,
        is_active=1
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return {"code": 200, "msg": "创建成功", "data": {"id": inst.id}}


@router.put("/update")
async def update_instance(
    id: int = Query(...),
    name: str = Query(None),
    device_id: int = Query(None),
    point_ids: str = Query(None),
    model_key: str = Query(None),
    base_model_id: str = Query(None),
    interval: float = Query(None, ge=0.1, le=30.0),
    is_active: int = Query(None),
    db: Session = Depends(get_db)
):
    """更新预测实例"""
    inst = db.query(PredictionInstance).filter(PredictionInstance.id == id).first()
    if not inst:
        raise HTTPException(404, "实例不存在")

    if name is not None:
        inst.name = name
    if device_id is not None:
        from models.plc_device import PlcDevice
        device = db.query(PlcDevice).filter(PlcDevice.id == device_id).first()
        if not device:
            raise HTTPException(400, "PLC 设备不存在")
        inst.device_id = device_id
    if point_ids is not None:
        inst.point_ids = point_ids
    if model_key is not None:
        if model_key not in model_manager.models:
            raise HTTPException(400, f"模型不存在: {model_key}")
        inst.model_key = model_key
    if base_model_id is not None:
        if base_model_id and base_model_id not in model_manager.saved_models:
            raise HTTPException(400, f"已保存模型不存在: {base_model_id}")
        inst.base_model_id = base_model_id
    if interval is not None:
        inst.interval = int(interval * 10)
    if is_active is not None:
        inst.is_active = is_active

    db.commit()
    return {"code": 200, "msg": "更新成功"}


@router.delete("/delete")
async def delete_instance(instance_id: int = Query(...), db: Session = Depends(get_db)):
    """删除预测实例"""
    inst = db.query(PredictionInstance).filter(PredictionInstance.id == instance_id).first()
    if not inst:
        raise HTTPException(404, "实例不存在")
    db.delete(inst)
    db.commit()
    return {"code": 200, "msg": "删除成功"}


# ========== 单实例预测流 ==========

@router.get("/stream")
async def instance_predict_stream(
    instance_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """
    单实例 SSE 预测流 — 读取该实例绑定的 PLC，用指定模型推理
    """
    inst = db.query(PredictionInstance).filter(PredictionInstance.id == instance_id).first()
    if not inst:
        raise HTTPException(404, "实例不存在")
    if not inst.is_active:
        raise HTTPException(400, "实例已停用")

    device_id = inst.device_id
    model_key = inst.model_key
    interval = (inst.interval or 10) / 10.0
    base_model_id = inst.base_model_id or ""

    if not plc_manager.is_connected(device_id):
        raise HTTPException(400, f"PLC 设备 {device_id} 未连接")
    if model_key not in model_manager.models:
        raise HTTPException(400, f"模型不存在: {model_key}")

    # 如果指定了已保存模型，先加载权重
    if base_model_id and base_model_id in model_manager.saved_models:
        model_manager.load_model_weights(model_key, base_model_id)
        print(f"实例 {inst.id}: 已加载模型权重 {base_model_id}")

    # 获取点位
    query = db.query(PlcDbPoint).filter(
        PlcDbPoint.device_id == device_id,
        PlcDbPoint.is_active == 1
    )
    if inst.point_ids:
        pids = [int(x.strip()) for x in inst.point_ids.split(",") if x.strip()]
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

    # 每个实例独立的 buffer
    buffer = []
    # 预填充随机数据
    for _ in range(window_size):
        buffer.append(list(np.random.randn(input_dim).astype(float)))

    async def event_generator():
        import torch
        tick = 0
        try:
            while True:
                tick += 1
                timestamp = time.time()

                # 1. 读取 PLC 数据
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

                # 填充到 input_dim
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
                        "instance_id": inst.id,
                        "model_key": model_key,
                        "model_name": model_manager.models[model_key]["display_name"],
                        "prediction": round(mean_pred, 6),
                        "confidence_upper": round(mean_pred + 2 * std_pred, 6),
                        "confidence_lower": round(mean_pred - 2 * std_pred, 6),
                        "uncertainty": round(std_pred, 6),
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
