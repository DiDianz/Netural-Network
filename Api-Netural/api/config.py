# api/config.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from deps import get_current_user
from models.user import SysUser
from models.sys_config import SysConfig

router = APIRouter(prefix="/system/config", tags=["系统设置"])


@router.get("/list")
async def list_configs(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有系统配置"""
    configs = db.query(SysConfig).order_by(SysConfig.config_id).all()
    return {
        "code": 200,
        "data": [
            {
                "config_id": c.config_id,
                "config_name": c.config_name,
                "config_key": c.config_key,
                "config_value": c.config_value,
                "config_type": c.config_type,
                "remark": c.remark or "",
            }
            for c in configs
        ]
    }


@router.get("/get/{config_key}")
async def get_config(
    config_key: str,
    db: Session = Depends(get_db)
):
    """根据 key 获取配置值（内部用，无需认证）"""
    config = db.query(SysConfig).filter(SysConfig.config_key == config_key).first()
    if not config:
        return {"code": 200, "data": {"config_key": config_key, "config_value": ""}}
    return {"code": 200, "data": {"config_key": config.config_key, "config_value": config.config_value}}


@router.put("/update")
async def update_config(
    data: dict,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新配置"""
    config_id = data.get("config_id")
    config_value = data.get("config_value", "")

    config = db.query(SysConfig).filter(SysConfig.config_id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    config.config_value = str(config_value)
    db.commit()
    return {"code": 200, "msg": "修改成功"}


@router.post("/add")
async def add_config(
    data: dict,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """新增配置"""
    config = SysConfig(
        config_name=data.get("config_name", ""),
        config_key=data.get("config_key", ""),
        config_value=data.get("config_value", ""),
        config_type=data.get("config_type", "N"),
        remark=data.get("remark", ""),
    )
    db.add(config)
    db.commit()
    return {"code": 200, "msg": "新增成功", "config_id": config.config_id}


@router.delete("/delete/{config_id}")
async def delete_config(
    config_id: int,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除配置"""
    config = db.query(SysConfig).filter(SysConfig.config_id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    if config.config_type == "Y":
        raise HTTPException(status_code=400, detail="系统内置配置不可删除")
    db.delete(config)
    db.commit()
    return {"code": 200, "msg": "删除成功"}
