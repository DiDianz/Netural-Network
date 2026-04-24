# api/log.py — 增强版：支持 log_type 筛选
"""
操作日志 API — 查询 / 新增 / 清空 / 统计
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta

from core.database import get_db
from models.operation_log import OperationLog

router = APIRouter(prefix="/log", tags=["操作日志"])


@router.get("/list")
async def list_logs(
    log_type: str = Query(None, description="日志类型: api/db/error/frontend"),
    user_name: str = Query(None, description="操作用户"),
    module: str = Query(None, description="功能模块"),
    action: str = Query(None, description="操作动作"),
    status: int = Query(None, description="状态码"),
    keyword: str = Query(None, description="关键字搜索"),
    start_time: str = Query(None, description="开始时间 YYYY-MM-DD"),
    end_time: str = Query(None, description="结束时间 YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """查询操作日志（支持按类型筛选）"""
    query = db.query(OperationLog)

    if log_type:
        query = query.filter(OperationLog.log_type == log_type)
    if user_name:
        query = query.filter(OperationLog.user_name.like(f"%{user_name}%"))
    if module:
        query = query.filter(OperationLog.module.like(f"%{module}%"))
    if action:
        query = query.filter(OperationLog.action.like(f"%{action}%"))
    if status is not None:
        query = query.filter(OperationLog.status == status)
    if keyword:
        like_kw = f"%{keyword}%"
        query = query.filter(
            OperationLog.user_name.like(like_kw) |
            OperationLog.module.like(like_kw) |
            OperationLog.action.like(like_kw) |
            OperationLog.url.like(like_kw) |
            OperationLog.error_msg.like(like_kw)
        )
    if start_time:
        try:
            st = datetime.strptime(start_time, "%Y-%m-%d")
            query = query.filter(OperationLog.create_time >= st)
        except ValueError:
            pass
    if end_time:
        try:
            et = datetime.strptime(end_time, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(OperationLog.create_time < et)
        except ValueError:
            pass

    total = query.count()
    records = query.order_by(desc(OperationLog.create_time)).offset(offset).limit(limit).all()

    return {
        "code": 200,
        "total": total,
        "data": [
            {
                "id": r.id,
                "log_type": r.log_type or "api",
                "user_name": r.user_name or "",
                "module": r.module or "",
                "action": r.action or "",
                "method": r.method or "",
                "url": r.url or "",
                "params": r.params or "",
                "ip": r.ip or "",
                "status": r.status,
                "error_msg": r.error_msg or "",
                "result": r.result or "",
                "cost_ms": r.cost_ms or 0,
                "create_time": r.create_time.strftime("%Y-%m-%d %H:%M:%S") if r.create_time else "",
            }
            for r in records
        ]
    }


@router.get("/modules")
async def get_modules(db: Session = Depends(get_db)):
    """获取所有模块名称（用于筛选下拉）"""
    rows = db.query(OperationLog.module).distinct().all()
    modules = sorted(set(r[0] for r in rows if r[0]))
    return {"code": 200, "data": modules}


@router.get("/stats")
async def get_stats(
    days: int = Query(7, ge=1, le=90, description="统计最近N天"),
    db: Session = Depends(get_db)
):
    """日志统计概览"""
    cutoff = datetime.now() - timedelta(days=days)

    # 按类型统计
    type_stats = db.query(
        OperationLog.log_type,
        func.count(OperationLog.id)
    ).filter(
        OperationLog.create_time >= cutoff
    ).group_by(OperationLog.log_type).all()

    # 按状态统计
    status_stats = db.query(
        OperationLog.status,
        func.count(OperationLog.id)
    ).filter(
        OperationLog.create_time >= cutoff
    ).group_by(OperationLog.status).all()

    # 今日总数
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = db.query(func.count(OperationLog.id)).filter(
        OperationLog.create_time >= today
    ).scalar()

    # 今日错误数
    today_error = db.query(func.count(OperationLog.id)).filter(
        OperationLog.create_time >= today,
        OperationLog.status >= 400
    ).scalar()

    return {
        "code": 200,
        "data": {
            "by_type": {r[0]: r[1] for r in type_stats},
            "by_status": {str(r[0]): r[1] for r in status_stats},
            "today_total": today_count,
            "today_error": today_error,
        }
    }


@router.delete("/clear")
async def clear_logs(
    days: int = Query(30, ge=1, le=365, description="保留最近N天的日志"),
    log_type: str = Query(None, description="只清理指定类型，不传则清理全部"),
    db: Session = Depends(get_db)
):
    """清理旧日志"""
    cutoff = datetime.now() - timedelta(days=days)
    query = db.query(OperationLog).filter(OperationLog.create_time < cutoff)
    if log_type:
        query = query.filter(OperationLog.log_type == log_type)
    deleted = query.delete()
    db.commit()
    return {"code": 200, "msg": f"已清理 {deleted} 条 {days} 天前的日志"}


@router.post("/record")
async def record_log(
    log_type: str = Query("frontend", description="日志类型"),
    user_name: str = Query(""),
    module: str = Query(""),
    action: str = Query(""),
    method: str = Query(""),
    url: str = Query(""),
    params: str = Query(""),
    ip: str = Query(""),
    status: int = Query(200),
    error_msg: str = Query(""),
    result: str = Query(""),
    cost_ms: int = Query(0),
    db: Session = Depends(get_db)
):
    """前端主动上报操作日志"""
    record = OperationLog(
        log_type=log_type,
        user_name=user_name[:50] if user_name else "",
        module=module[:50] if module else "",
        action=action[:100] if action else "",
        method=method[:10] if method else "",
        url=url[:500] if url else "",
        params=params[:2000] if params else "",
        ip=ip[:50] if ip else "",
        status=status,
        error_msg=error_msg[:2000] if error_msg else "",
        result=result[:200] if result else "",
        cost_ms=cost_ms,
    )
    db.add(record)
    db.commit()
    return {"code": 200, "msg": "记录成功"}
