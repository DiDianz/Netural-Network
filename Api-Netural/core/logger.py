# core/logger.py — 全链路日志工具
"""
提供：
1. write_log()        — 通用日志写入（任何地方都能调用）
2. setup_db_logger()  — SQLAlchemy 事件监听，自动记录 INSERT/UPDATE/DELETE
"""
import traceback
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.orm import Session


def write_log(
    db_session: Session = None,
    log_type: str = "api",
    user_name: str = "",
    module: str = "",
    action: str = "",
    method: str = "",
    url: str = "",
    params: str = "",
    ip: str = "",
    status: int = 200,
    error_msg: str = "",
    result: str = "",
    cost_ms: int = 0,
):
    """写入一条操作日志，失败不抛异常"""
    try:
        from models.operation_log import OperationLog
        from core.database import SessionLocal

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

        if db_session:
            db_session.add(record)
            db_session.flush()  # 不 commit，让调用方控制事务
        else:
            # 独立写入（用于异步/无 session 场景）
            _db = SessionLocal()
            try:
                _db.add(record)
                _db.commit()
            except Exception:
                _db.rollback()
            finally:
                _db.close()
    except Exception:
        pass  # 日志写入不能影响主业务


def write_error_log(module: str, error_msg: str, user_name: str = "", url: str = ""):
    """快捷写入错误日志"""
    write_log(
        log_type="error",
        user_name=user_name,
        module=module,
        action="系统错误",
        url=url,
        status=500,
        error_msg=error_msg,
        result="错误",
    )


# ========== 数据库操作日志监听 ==========

# 需要监听的表（排除日志表本身和不需要记录的表）
_SKIP_TABLES = {
    "operation_log",  # 不记录日志表自身的操作
    "train_log",      # 训练日志太频繁，跳过
    "train_trend",    # 训练趋势数据太频繁
}

# 表名 → 模块名映射
_TABLE_MODULE_MAP = {
    "sys_user": "用户管理",
    "sys_role": "角色管理",
    "sys_menu": "菜单管理",
    "predict_history": "预测",
    "plc_device": "PLC管理",
    "plc_db_point": "PLC管理",
    "prediction_instance": "预测实例",
    "saved_model": "模型管理",
    "sys_config": "系统设置",
    "feature_scheme": "特征方案",
    "feature_column": "特征方案",
}


def _table_to_module(table_name: str) -> str:
    return _TABLE_MODULE_MAP.get(table_name, "数据操作")


def _before_flush(session, flush_context, instances):
    """在 flush 前捕获新增/修改/删除的对象"""
    try:
        pending_logs = []

        # 新增的对象
        for obj in session.new:
            table = getattr(obj, "__tablename__", "")
            if table in _SKIP_TABLES or not table:
                continue
            pending_logs.append({
                "log_type": "db",
                "module": _table_to_module(table),
                "action": f"INSERT-{table}",
                "method": "INSERT",
                "url": f"DB:{table}",
                "params": _safe_serialize(obj),
                "result": "新增成功",
            })

        # 修改的对象
        for obj in session.dirty:
            table = getattr(obj, "__tablename__", "")
            if table in _SKIP_TABLES or not table:
                continue
            # 只记录真正有变更的
            from sqlalchemy.orm import inspect
            insp = inspect(obj)
            if not insp.modified:
                continue
            changes = _get_changes(insp)
            pending_logs.append({
                "log_type": "db",
                "module": _table_to_module(table),
                "action": f"UPDATE-{table}",
                "method": "UPDATE",
                "url": f"DB:{table}",
                "params": changes[:2000] if changes else "",
                "result": "修改成功",
            })

        # 删除的对象
        for obj in session.deleted:
            table = getattr(obj, "__tablename__", "")
            if table in _SKIP_TABLES or not table:
                continue
            pending_logs.append({
                "log_type": "db",
                "module": _table_to_module(table),
                "action": f"DELETE-{table}",
                "method": "DELETE",
                "url": f"DB:{table}",
                "params": _safe_serialize(obj),
                "result": "删除成功",
            })

        # 存到 session info 里，commit 后写入
        if pending_logs:
            session.info["_pending_db_logs"] = pending_logs

    except Exception:
        pass


def _after_commit(session):
    """commit 成功后写入日志"""
    try:
        pending = session.info.pop("_pending_db_logs", None)
        if not pending:
            return
        from core.database import SessionLocal
        _db = SessionLocal()
        try:
            from models.operation_log import OperationLog
            for log_data in pending:
                _db.add(OperationLog(**log_data))
            _db.commit()
        except Exception:
            _db.rollback()
        finally:
            _db.close()
    except Exception:
        pass


def _safe_serialize(obj) -> str:
    """安全序列化对象的关键字段"""
    try:
        from sqlalchemy.orm import inspect
        insp = inspect(obj)
        pk = insp.identity
        pk_str = str(pk[0]) if pk and len(pk) == 1 else str(pk)
        table = getattr(obj, "__tablename__", "unknown")
        return f"table={table}, pk={pk_str}"
    except Exception:
        return str(type(obj).__name__)


def _get_changes(insp) -> str:
    """获取对象的变更字段"""
    try:
        history = insp.attrs
        changes = []
        for attr_key in history:
            attr = getattr(history, attr_key, None)
            if attr is None:
                continue
            hist = attr.history
            if hist.has_changes():
                old_val = hist.deleted[0] if hist.deleted else None
                new_val = hist.added[0] if hist.added else None
                # 跳过大字段
                old_str = str(old_val)[:100] if old_val is not None else "NULL"
                new_str = str(new_val)[:100] if new_val is not None else "NULL"
                changes.append(f"{attr_key}: {old_str} → {new_str}")
        return "; ".join(changes[:20])  # 最多记录20个字段变更
    except Exception:
        return ""


def setup_db_logger():
    """注册 SQLAlchemy 事件监听器，在应用启动时调用"""
    event.listen(Session, "before_flush", _before_flush)
    event.listen(Session, "after_commit", _after_commit)
    print("[Logger] 数据库操作日志监听已启用")
