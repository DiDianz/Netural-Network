# api/log.py
"""
操作日志 API — 查询 / 新增 / 清空
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta

from core.database import get_db
from models.operation_log import OperationLog

router = APIRouter(prefix="/log", tags=["操作日志"])


@router.get("/list")
async def list_logs(
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
    """查询操作日志"""
    query = db.query(OperationLog)

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


@router.delete("/clear")
async def clear_logs(
    days: int = Query(30, ge=1, le=365, description="保留最近N天的日志"),
    db: Session = Depends(get_db)
):
    """清理旧日志"""
    cutoff = datetime.now() - timedelta(days=days)
    deleted = db.query(OperationLog).filter(OperationLog.create_time < cutoff).delete()
    db.commit()
    return {"code": 200, "msg": f"已清理 {deleted} 条 {days} 天前的日志"}


@router.post("/record")
async def record_log(
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
        user_name=user_name,
        module=module,
        action=action,
        method=method,
        url=url,
        params=params[:2000] if params else "",
        ip=ip,
        status=status,
        error_msg=error_msg[:2000] if error_msg else "",
        result=result,
        cost_ms=cost_ms,
    )
    db.add(record)
    db.commit()
    return {"code": 200}
