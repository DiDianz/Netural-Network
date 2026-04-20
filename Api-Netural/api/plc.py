# api/plc.py
"""
PLC 设备管理 API — 设备 CRUD + DB 点位管理 + 连接/读取
"""
import json
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.database import get_db
from core.plc_service import plc_manager
from models.plc_device import PlcDevice
from models.plc_db_point import PlcDbPoint

router = APIRouter(prefix="/plc", tags=["PLC管理"])
logger = logging.getLogger("api.plc")


# ============================================================
#  PLC 设备 CRUD
# ============================================================

@router.get("/device/list")
async def list_devices(db: Session = Depends(get_db)):
    """获取所有 PLC 设备列表"""
    devices = db.query(PlcDevice).order_by(PlcDevice.create_time.desc()).all()
    data = []
    for d in devices:
        # 实时检查连接状态
        actual_status = "connected" if plc_manager.is_connected(d.id) else "disconnected" # type: ignore
        if d.status != actual_status and actual_status == "disconnected": # type: ignore
            d.status = "disconnected" # type: ignore
            db.commit()
        point_count = db.query(func.count(PlcDbPoint.id)).filter(
            PlcDbPoint.device_id == d.id
        ).scalar() or 0
        data.append({
            "id": d.id, "name": d.name, "ip": d.ip, "port": d.port,
            "rack": d.rack, "slot": d.slot, "status": d.status,
            "remark": d.remark, "point_count": point_count,
            "create_time": d.create_time.strftime("%Y-%m-%d %H:%M:%S") if d.create_time else None, # type: ignore
            "update_time": d.update_time.strftime("%Y-%m-%d %H:%M:%S") if d.update_time else None, # type: ignore
        })
    return {"code": 200, "data": data}


@router.get("/device/detail")
async def get_device(device_id: int = Query(...), db: Session = Depends(get_db)):
    """获取单个设备详情"""
    device = db.query(PlcDevice).filter(PlcDevice.id == device_id).first()
    if not device:
        raise HTTPException(400, "设备不存在")
    return {"code": 200, "data": {
        "id": device.id, "name": device.name, "ip": device.ip,
        "port": device.port, "rack": device.rack, "slot": device.slot,
        "status": device.status, "remark": device.remark,
    }}


@router.post("/device/add")
async def add_device(
    name: str = Query(..., min_length=1, max_length=100),
    ip: str = Query(..., min_length=7, max_length=50),
    port: int = Query(102, ge=1, le=65535),
    rack: int = Query(0, ge=0),
    slot: int = Query(1, ge=0),
    remark: str = Query(""),
    db: Session = Depends(get_db)
):
    """新增 PLC 设备"""
    device = PlcDevice(name=name, ip=ip, port=port, rack=rack, slot=slot, remark=remark)
    db.add(device)
    db.commit()
    db.refresh(device)
    return {"code": 200, "msg": "添加成功", "data": {"id": device.id}}


@router.put("/device/update")
async def update_device(
    id: int = Query(...),
    name: str = Query(None),
    ip: str = Query(None),
    port: int = Query(None, ge=1, le=65535),
    rack: int = Query(None, ge=0),
    slot: int = Query(None, ge=0),
    remark: str = Query(None),
    db: Session = Depends(get_db)
):
    """更新 PLC 设备"""
    device = db.query(PlcDevice).filter(PlcDevice.id == id).first()
    if not device:
        raise HTTPException(400, "设备不存在")
    if name is not None:
        device.name = name # type: ignore
    if ip is not None:
        device.ip = ip # type: ignore
    if port is not None:
        device.port = port # type: ignore
    if rack is not None:
        device.rack = rack # type: ignore
    if slot is not None:
        device.slot = slot # type: ignore
    if remark is not None:
        device.remark = remark # type: ignore
    db.commit()
    return {"code": 200, "msg": "更新成功"}


@router.delete("/device/delete")
async def delete_device(device_id: int = Query(...), db: Session = Depends(get_db)):
    """删除 PLC 设备 (同时删除关联的 DB 点位)"""
    device = db.query(PlcDevice).filter(PlcDevice.id == device_id).first()
    if not device:
        raise HTTPException(400, "设备不存在")
    # 先断开连接
    plc_manager.disconnect(device_id)
    # 删除关联的 DB 点位
    db.query(PlcDbPoint).filter(PlcDbPoint.device_id == device_id).delete()
    db.delete(device)
    db.commit()
    return {"code": 200, "msg": "删除成功"}


# ============================================================
#  PLC 连接管理
# ============================================================

@router.post("/device/connect")
async def connect_device(device_id: int = Query(...), db: Session = Depends(get_db)):
    """连接 PLC 设备"""
    device = db.query(PlcDevice).filter(PlcDevice.id == device_id).first()
    if not device:
        raise HTTPException(400, "设备不存在")

    result = plc_manager.connect(device_id, device.ip, device.port, device.rack, device.slot) # type: ignore
    if result["success"]:
        device.status = "connected" # type: ignore
        db.commit()
        return {"code": 200, "msg": "连接成功"}
    else:
        device.status = "error" # type: ignore
        db.commit()
        raise HTTPException(400, result["msg"])


@router.post("/device/disconnect")
async def disconnect_device(device_id: int = Query(...), db: Session = Depends(get_db)):
    """断开 PLC 设备"""
    plc_manager.disconnect(device_id)
    device = db.query(PlcDevice).filter(PlcDevice.id == device_id).first()
    if device:
        device.status = "disconnected" # type: ignore
        db.commit()
    return {"code": 200, "msg": "已断开连接"}


@router.post("/device/connect-all")
async def connect_all_devices(db: Session = Depends(get_db)):
    """连接所有已配置的 PLC 设备"""
    devices = db.query(PlcDevice).all()
    results = []
    for d in devices:
        r = plc_manager.connect(d.id, d.ip, d.port, d.rack, d.slot) # type: ignore
        d.status = "connected" if r["success"] else "error" # type: ignore
        results.append({"id": d.id, "name": d.name, "success": r["success"], "msg": r["msg"]})
    db.commit()
    return {"code": 200, "data": results}


@router.post("/device/disconnect-all")
async def disconnect_all_devices(db: Session = Depends(get_db)):
    """断开所有 PLC 设备"""
    plc_manager.disconnect_all()
    db.query(PlcDevice).update({"status": "disconnected"})
    db.commit()
    return {"code": 200, "msg": "已断开全部连接"}


# ============================================================
#  PLC DB 点位管理
# ============================================================

@router.get("/point/list")
async def list_points(
    device_id: int = Query(None),
    keyword: str = Query(None),
    is_active: int = Query(None, description="1启用 0停用"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """获取 DB 点位列表"""
    query = db.query(PlcDbPoint)
    if device_id:
        query = query.filter(PlcDbPoint.device_id == device_id)
    if keyword:
        like_kw = f"%{keyword}%"
        query = query.filter(
            PlcDbPoint.point_name.like(like_kw) |
            PlcDbPoint.description.like(like_kw)
        )
    if is_active is not None:
        query = query.filter(PlcDbPoint.is_active == is_active)

    total = query.count()
    points = query.order_by(PlcDbPoint.create_time.desc()).offset(offset).limit(limit).all()
    return {
        "code": 200, "total": total,
        "data": [{
            "id": p.id, "device_id": p.device_id, "point_name": p.point_name,
            "db_number": p.db_number, "start_address": p.start_address,
            "data_type": p.data_type, "bit_index": p.bit_index,
            "description": p.description, "is_active": p.is_active,
            "create_time": p.create_time.strftime("%Y-%m-%d %H:%M:%S") if p.create_time else None, # type: ignore
            "update_time": p.update_time.strftime("%Y-%m-%d %H:%M:%S") if p.update_time else None, # type: ignore
        } for p in points]
    }


@router.post("/point/add")
async def add_point(
    device_id: int = Query(...),
    point_name: str = Query(..., min_length=1, max_length=100),
    db_number: int = Query(..., ge=0),
    start_address: int = Query(..., ge=0),
    data_type: str = Query("REAL"),
    bit_index: int = Query(0, ge=0, le=7),
    description: str = Query(""),
    is_active: int = Query(1),
    db: Session = Depends(get_db)
):
    """新增 DB 点位"""
    # 检查设备是否存在
    device = db.query(PlcDevice).filter(PlcDevice.id == device_id).first()
    if not device:
        raise HTTPException(400, "设备不存在")

    valid_types = ["REAL", "INT", "DINT", "BOOL", "WORD"]
    if data_type.upper() not in valid_types:
        raise HTTPException(400, f"不支持的数据类型，仅支持: {', '.join(valid_types)}")

    point = PlcDbPoint(
        device_id=device_id, point_name=point_name,
        db_number=db_number, start_address=start_address,
        data_type=data_type.upper(), bit_index=bit_index,
        description=description, is_active=is_active
    )
    db.add(point)
    db.commit()
    db.refresh(point)
    return {"code": 200, "msg": "添加成功", "data": {"id": point.id}}


@router.put("/point/update")
async def update_point(
    id: int = Query(...),
    point_name: str = Query(None),
    db_number: int = Query(None, ge=0),
    start_address: int = Query(None, ge=0),
    data_type: str = Query(None),
    bit_index: int = Query(None, ge=0, le=7),
    description: str = Query(None),
    is_active: int = Query(None),
    db: Session = Depends(get_db)
):
    """更新 DB 点位"""
    point = db.query(PlcDbPoint).filter(PlcDbPoint.id == id).first()
    if not point:
        raise HTTPException(400, "点位不存在")
    if point_name is not None:
        point.point_name = point_name # type: ignore
    if db_number is not None:
        point.db_number = db_number # type: ignore
    if start_address is not None:
        point.start_address = start_address # type: ignore
    if data_type is not None:
        valid_types = ["REAL", "INT", "DINT", "BOOL", "WORD"]
        if data_type.upper() not in valid_types:
            raise HTTPException(400, f"不支持的数据类型，仅支持: {', '.join(valid_types)}")
        point.data_type = data_type.upper() # type: ignore
    if bit_index is not None:
        point.bit_index = bit_index # type: ignore
    if description is not None:
        point.description = description # type: ignore
    if is_active is not None:
        point.is_active = is_active # type: ignore
    db.commit()
    return {"code": 200, "msg": "更新成功"}


@router.delete("/point/delete")
async def delete_point(point_id: int = Query(...), db: Session = Depends(get_db)):
    """删除 DB 点位"""
    point = db.query(PlcDbPoint).filter(PlcDbPoint.id == point_id).first()
    if not point:
        raise HTTPException(400, "点位不存在")
    db.delete(point)
    db.commit()
    return {"code": 200, "msg": "删除成功"}


# ============================================================
#  PLC 数据读取
# ============================================================

@router.get("/read/single")
async def read_single_point(
    device_id: int = Query(...),
    db_number: int = Query(..., ge=0),
    start_address: int = Query(..., ge=0),
    data_type: str = Query("REAL"),
    bit_index: int = Query(0, ge=0, le=7)
):
    """读取单个 DB 点位的值"""
    result = plc_manager.read_value(device_id, db_number, start_address, data_type, bit_index)
    if result["success"]:
        return {"code": 200, "data": {"value": result["value"]}}
    raise HTTPException(400, result["msg"])


@router.get("/read/batch")
async def read_batch_points(
    device_id: int = Query(...),
    point_ids: str = Query(None, description="逗号分隔的点位ID，不传则读取该设备所有启用的点位"),
    db: Session = Depends(get_db)
):
    """批量读取 DB 点位的值"""
    query = db.query(PlcDbPoint).filter(
        PlcDbPoint.device_id == device_id,
        PlcDbPoint.is_active == 1
    )
    if point_ids:
        ids = [int(x.strip()) for x in point_ids.split(",") if x.strip()]
        query = query.filter(PlcDbPoint.id.in_(ids))

    points = query.all()
    if not points:
        raise HTTPException(400, "没有可读取的点位")

    point_list = [{
        "id": p.id, "point_name": p.point_name,
        "db_number": p.db_number, "start_address": p.start_address,
        "data_type": p.data_type, "bit_index": p.bit_index
    } for p in points]

    result = plc_manager.read_multiple(device_id, point_list)
    if result["success"]:
        return {"code": 200, "data": result["data"]}
    raise HTTPException(400, result["msg"])


@router.get("/read/stream")
async def read_stream(
    device_id: int = Query(...),
    interval: float = Query(1.0, ge=0.1, le=30.0),
    point_ids: str = Query(None, description="逗号分隔的点位ID"),
    db: Session = Depends(get_db)
):
    """SSE 持续读取 PLC 数据流"""
    query = db.query(PlcDbPoint).filter(
        PlcDbPoint.device_id == device_id,
        PlcDbPoint.is_active == 1
    )
    if point_ids:
        ids = [int(x.strip()) for x in point_ids.split(",") if x.strip()]
        query = query.filter(PlcDbPoint.id.in_(ids))

    points = query.all()
    if not points:
        raise HTTPException(400, "没有可读取的点位")

    point_list = [{
        "id": p.id, "point_name": p.point_name,
        "db_number": p.db_number, "start_address": p.start_address,
        "data_type": p.data_type, "bit_index": p.bit_index
    } for p in points]

    async def event_generator():
        try:
            while True:
                if not plc_manager.is_connected(device_id):
                    yield f"data: {json.dumps({'error': '设备未连接'}, ensure_ascii=False)}\n\n"
                    break
                result = plc_manager.read_multiple(device_id, point_list)
                if result["success"]:
                    payload = {
                        "timestamp": asyncio.get_event_loop().time(),
                        "device_id": device_id,
                        "points": result["data"]
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'error': result['msg']}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )
