# api/model.py
import json
import asyncio
import uuid
import time
import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from core.database import get_db
from core.model_manager import model_manager
from core.data_manager import data_manager, training_job_manager
from schemas.model import SwitchRequest, TrainRequest
from models.train_log import TrainLog
from models.train_trend import TrainTrend

router = APIRouter(prefix="/model", tags=["模型管理"])
logger = logging.getLogger("api.model")


@router.get("/list")
async def list_models():
    return {"code": 200, "data": model_manager.list_models()}


@router.post("/switch")
async def switch_model(body: SwitchRequest):
    try:
        result = model_manager.switch_model(body.model_key)
        return {"code": 200, "data": result, "msg": "切换成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
async def model_status():
    return {"code": 200, "data": model_manager.get_status()}


@router.post("/train/start")
async def start_training(body: TrainRequest, db: Session = Depends(get_db)):
    if model_manager.training_state["is_training"]:
        existing_key = model_manager.training_state.get("model_key")
        if existing_key == body.model_key or training_job_manager.is_model_training(body.model_key):
            raise HTTPException(status_code=400, detail="该模型已有训练任务在进行中")
    try:
        asyncio.create_task(
            model_manager.train_model(
                model_key=body.model_key, epochs=body.epochs,
                lr=body.lr, batch_size=body.batch_size, db=db,
                base_model_id=body.base_model_id, model_name=body.model_name
            )
        )
        msg = f"已开始训练 {body.model_key} 模型"
        if body.base_model_id:
            msg += f" (基于已有模型 {body.base_model_id})"
        return {"code": 200, "msg": msg}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/train/stop")
async def stop_training():
    model_manager.stop_training()
    return {"code": 200, "msg": "已发送停止信号"}


@router.get("/train/status")
async def train_status():
    return {"code": 200, "data": model_manager.get_training_state()}


@router.get("/train/stream")
async def train_stream(model_key: str = Query("lstm"), epochs: int = Query(50), lr: float = Query(0.001)):
    if not model_manager.training_state["is_training"]:
        asyncio.create_task(model_manager.train_model(model_key=model_key, epochs=epochs, lr=lr))
        await asyncio.sleep(0.5)

    async def event_generator():
        last_epoch = 0
        while True:
            state = model_manager.get_training_state()
            if state["epoch"] > last_epoch or state.get("done"):
                yield f"data: {json.dumps(state, ensure_ascii=False)}\n\n"
                last_epoch = state["epoch"]
            if state.get("done") or not state["is_training"]:
                final = model_manager.get_training_state()
                final["done"] = True
                yield f"data: {json.dumps(final, ensure_ascii=False)}\n\n"
                break
            await asyncio.sleep(0.2)

    return StreamingResponse(event_generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})


@router.get("/train/history")
async def train_history(
    model_key: str = Query(None),
    keyword: str = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(TrainLog)
    if model_key:
        query = query.filter(TrainLog.model_key == model_key)
    if keyword:
        like_kw = f"%{keyword}%"
        query = query.filter(
            TrainLog.model_key.like(like_kw) |
            TrainLog.model_name.like(like_kw) |
            TrainLog.remark.like(like_kw) |
            TrainLog.status.like(like_kw)
        )
    total = query.count()
    records = query.order_by(TrainLog.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "code": 200, "total": total,
        "data": [
            {"id": r.id, "model_key": r.model_key, "model_name": r.model_name,
             "epoch": r.epoch, "total_epochs": r.total_epochs,
             "train_loss": r.train_loss, "val_loss": r.val_loss,
             "learning_rate": r.learning_rate, "status": r.status,
             "best_val_loss": r.best_val_loss, "duration_seconds": r.duration_seconds,
             "remark": r.remark,
             "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at is not None else None}
            for r in records
        ]
    }


# ========== 上传数据训练 ==========

@router.post("/train/upload")
async def start_training_with_upload(
    model_key: str = Query(...),
    file_ids: str = Query(..., description="逗号分隔的文件ID"),
    epochs: int = Query(50, ge=1, le=500),
    lr: float = Query(0.001, gt=0, le=1),
    batch_size: int = Query(32, ge=1, le=256),
    base_model_id: str = Query(None, description="基础模型版本ID，用于继续训练"),
    model_name: str = Query(None, description="自定义模型名称"),
    db: Session = Depends(get_db)
):
    if model_manager.training_state["is_training"]:
        existing_key = model_manager.training_state.get("model_key")
        if existing_key == model_key or training_job_manager.is_model_training(model_key):
            raise HTTPException(400, "该模型已有训练任务在进行中")

    if model_key not in model_manager.models:
        raise HTTPException(400, f"模型不存在: {model_key}")

    ids = [f.strip() for f in file_ids.split(",") if f.strip()]
    if not ids:
        raise HTTPException(400, "请选择训练数据")

    grouped = data_manager.get_grouped_data(ids)
    combined = []
    for brand, rows in grouped.items():
        for row in rows:
            combined.append(row + [brand])

    if not combined:
        raise HTTPException(400, "训练数据为空或未找到品牌分组数据")

    logger.info(f"训练请求: model={model_key}, files={ids}, combined_rows={len(combined)}, "
                f"cols={len(combined[0]) if combined else 0}")

    if len(combined) < model_manager.window_size + 10:
        raise HTTPException(400,
            f"数据量不足（共 {len(combined)} 行），至少需要 {model_manager.window_size + 10} 行。"
            f"请检查上传文件的数据行数是否足够。")

    job_id = str(uuid.uuid4())[:8]
    job = {
        "job_id": job_id, "model_key": model_key, "total_epochs": epochs,
        "is_training": True, "start_time": time.time()
    }
    training_job_manager.add_job(job_id, job)

    asyncio.create_task(
        model_manager.train_model_with_data1(
            model_key=model_key, data=combined, job_id=job_id,
            epochs=epochs, lr=lr, batch_size=batch_size, db=db,
            base_model_id=base_model_id, model_name=model_name
        )
    )
    msg = f"已开始用上传数据训练 {model_key} 模型"
    if base_model_id:
        msg += f" (基于已有模型 {base_model_id})"
    return {"code": 200, "msg": msg, "job_id": job_id}


@router.post("/train/upload/stop")
async def stop_upload_training(model_key: str = Query(...)):
    job = training_job_manager.get_model_job(model_key)
    if job:
        job["is_training"] = False
        return {"code": 200, "msg": f"已停止 {model_key} 训练"}
    raise HTTPException(400, "该模型没有进行中的训练任务")


@router.get("/train/upload/stream")
async def train_upload_stream():
    async def event_generator():
        try:
            while True:
                active = {jid: j for jid, j in training_job_manager.jobs.items() if j.get("is_training")}
                if not active:
                    all_jobs = list(training_job_manager.jobs.values())
                    if all_jobs:
                        last = all_jobs[-1]
                        yield f"data: {json.dumps({**last, 'done': True}, ensure_ascii=False)}\n\n"
                    break
                state = list(active.values())[0]
                yield f"data: {json.dumps(state, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.3)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})


# ========== 训练趋势 ==========

@router.get("/train/trend")
async def get_train_trend(
    train_id: str = Query(None),
    model_key: str = Query(None),
    keyword: str = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db)
):
    query = db.query(TrainTrend)
    if train_id:
        query = query.filter(TrainTrend.train_id == train_id)
    if model_key:
        query = query.filter(TrainTrend.model_key == model_key)
    if keyword:
        like_kw = f"%{keyword}%"
        query = query.filter(
            TrainTrend.train_id.like(like_kw) |
            TrainTrend.model_key.like(like_kw) |
            TrainTrend.model_name.like(like_kw)
        )
    records = query.order_by(TrainTrend.epoch.asc()).limit(limit).all()
    return {
        "code": 200, "total": len(records),
        "data": [
            {"id": r.id, "train_id": r.train_id, "model_key": r.model_key,
             "model_name": r.model_name, "epoch": r.epoch, "total_epochs": r.total_epochs,
             "train_loss": r.train_loss, "val_loss": r.val_loss,
             "best_val_loss": r.best_val_loss, "learning_rate": r.learning_rate,
             "elapsed_seconds": r.elapsed_seconds,
             "predictions": json.loads(str(r.predictions_json)) if r.predictions_json is not None else [],
             "actuals": json.loads(str(r.actuals_json)) if r.actuals_json is not None else [],
             "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at is not None else None}
            for r in records
        ]
    }


@router.get("/train/trend/list")
async def list_train_trends(
    keyword: str = Query(None),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db)
):
    from sqlalchemy import func
    query = db.query(
        TrainTrend.train_id, TrainTrend.model_key, TrainTrend.model_name,
        func.max(TrainTrend.total_epochs).label("total_epochs"),
        func.max(TrainTrend.best_val_loss).label("best_val_loss"),
        func.max(TrainTrend.elapsed_seconds).label("total_seconds"),
        func.max(TrainTrend.created_at).label("created_at"),
        func.count(TrainTrend.id).label("epoch_count")
    ).group_by(TrainTrend.train_id, TrainTrend.model_key, TrainTrend.model_name)

    if keyword:
        like_kw = f"%{keyword}%"
        query = query.filter(
            TrainTrend.train_id.like(like_kw) |
            TrainTrend.model_key.like(like_kw) |
            TrainTrend.model_name.like(like_kw)
        )

    records = query.order_by(func.max(TrainTrend.created_at).desc()).limit(limit).all()
    return {
        "code": 200,
        "data": [
            {"train_id": r.train_id, "model_key": r.model_key, "model_name": r.model_name,
             "total_epochs": r.total_epochs, "best_val_loss": r.best_val_loss,
             "total_seconds": round(r.total_seconds, 1) if r.total_seconds else 0,
             "epoch_count": r.epoch_count,
             "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None}
            for r in records
        ]
    }


# ========== 模型版本管理 ==========

@router.get("/saved/list")
async def list_saved_models(model_key: str = Query(None)):
    """列出所有保存的模型版本"""
    return {"code": 200, "data": model_manager.list_saved_models(model_key)}


@router.delete("/saved/{model_id}")
async def delete_saved_model(model_id: str):
    """删除一个保存的模型版本"""
    try:
        result = model_manager.delete_saved_model(model_id)
        return {"code": 200, "data": result, "msg": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/saved/{model_id}/load")
async def load_saved_model(model_id: str):
    """加载一个已保存的模型版本到当前模型"""
    try:
        entry = model_manager.saved_models.get(model_id)
        if not entry:
            raise HTTPException(status_code=404, detail="模型版本不存在")
        result = model_manager.load_model_weights(entry["model_key"], model_id)
        return {"code": 200, "data": result, "msg": "加载成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/saved/{model_id}/rename")
async def rename_saved_model(model_id: str, body: dict):
    """重命名一个已保存的模型版本"""
    new_name = body.get("name", "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="名称不能为空")
    try:
        result = model_manager.rename_saved_model(model_id, new_name)
        return {"code": 200, "data": result, "msg": "重命名成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
