# ============================================================
#  PLC 模拟器 API — 追加到 api/plc.py 文件末尾
#  同时需要在文件顶部 import 区添加:
#    from core.plc_simulator import plc_simulator
# ============================================================


@router.post("/device/simulate")
async def simulate_device(
    device_id: int = Query(...),
    interval: float = Query(1.0, ge=0.1, le=10.0),
    min_val: float = Query(0),
    max_val: float = Query(100),
    pattern: str = Query("random", regex="^(random|sine|step|sawtooth)$"),
    db: Session = Depends(get_db)
):
    """
    模拟PLC启动 — 生成模拟数据供预测系统使用
    pattern: random(随机波动) | sine(正弦波) | step(阶梯变化) | sawtooth(锯齿波)
    """
    device = db.query(PlcDevice).filter(PlcDevice.id == device_id).first()
    if not device:
        raise HTTPException(400, "设备不存在")

    points = db.query(PlcDbPoint).filter(
        PlcDbPoint.device_id == device_id,
        PlcDbPoint.is_active == 1
    ).all()

    if not points:
        raise HTTPException(400, "该设备没有启用的DB点位，请先添加点位")

    point_list = [{"id": p.id, "point_name": p.point_name} for p in points]

    config = {
        "interval": interval,
        "min_val": min_val,
        "max_val": max_val,
        "pattern": pattern
    }

    result = plc_simulator.start_simulate(device_id, point_list, config)
    if result["success"]:
        device.status = "simulated"  # type: ignore
        db.commit()
        return {"code": 200, "msg": "模拟启动成功", "data": {"point_count": len(points)}}
    else:
        raise HTTPException(400, result["msg"])


@router.post("/device/simulate/stop")
async def stop_simulate_device(
    device_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """停止模拟PLC"""
    plc_simulator.stop_simulate(device_id)
    device = db.query(PlcDevice).filter(PlcDevice.id == device_id).first()
    if device:
        device.status = "disconnected"  # type: ignore
        db.commit()
    return {"code": 200, "msg": "已停止模拟"}
