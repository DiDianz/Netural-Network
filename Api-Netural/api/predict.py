# api/predict.py
import json
import asyncio
from fastapi import APIRouter, Query, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from core.database import get_db
from core.model_manager import model_manager
from core.data_manager import data_manager
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