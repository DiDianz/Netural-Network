# api/role.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from core.database import get_db
from deps import get_current_user
from models.user import SysUser
from models.role import SysRole
from models.menu import SysMenu, sys_role_menu
from schemas.role import RoleItem, RoleCreate, RoleUpdate, RoleListResponse

router = APIRouter(prefix="/system/role", tags=["角色管理"])


@router.get("/list", response_model=RoleListResponse)
async def list_roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    role_name: str = Query(""),
    status: str = Query(""),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """角色列表"""
    query = db.query(SysRole).filter(SysRole.del_flag == "0")

    if role_name:
        query = query.filter(SysRole.role_name.like(f"%{role_name}%"))
    if status:
        query = query.filter(SysRole.status == status)

    total = query.count()
    roles = query.order_by(SysRole.sort).offset((page - 1) * page_size).limit(page_size).all()

    rows = []
    for r in roles:
        rows.append(RoleItem(
            role_id=r.role_id, # type: ignore
            role_name=r.role_name,# type: ignore
            role_key=r.role_key,# type: ignore
            sort=r.sort,# type: ignore
            status=r.status,# type: ignore
            remark=r.remark or "",# type: ignore
            create_time=r.create_time,# type: ignore
            menu_ids=[m.menu_id for m in r.menus],
        ))

    return RoleListResponse(total=total, rows=rows)


@router.get("/options")
async def role_options(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """角色选项列表（下拉框用，不分页）"""
    roles = db.query(SysRole).filter(
        SysRole.del_flag == "0",
        SysRole.status == "0"
    ).order_by(SysRole.sort).all()

    return [
        {"role_id": r.role_id, "role_name": r.role_name, "role_key": r.role_key}
        for r in roles
    ]