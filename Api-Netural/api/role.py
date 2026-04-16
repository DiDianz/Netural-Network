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
            role_id=r.role_id,
            role_name=r.role_name,
            role_key=r.role_key,
            sort=r.sort,
            status=r.status,
            remark=r.remark or "",
            create_time=r.create_time,
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


@router.get("/get/{role_id}")
async def get_role(
    role_id: int,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取角色详情"""
    role = db.query(SysRole).options(
        joinedload(SysRole.menus)
    ).filter(SysRole.role_id == role_id, SysRole.del_flag == "0").first()

    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    return {
        "role_id": role.role_id,
        "role_name": role.role_name,
        "role_key": role.role_key,
        "sort": role.sort,
        "status": role.status,
        "remark": role.remark or "",
        "menu_ids": [m.menu_id for m in role.menus],
    }


@router.post("/add")
async def add_role(
    data: RoleCreate,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """新增角色"""
    # 检查 role_key 是否重复
    existing = db.query(SysRole).filter(SysRole.role_key == data.role_key).first()
    if existing:
        raise HTTPException(status_code=400, detail="角色权限字符串已存在")

    role = SysRole(
        role_name=data.role_name,
        role_key=data.role_key,
        sort=data.sort,
        status=data.status,
        remark=data.remark,
        del_flag="0",
    )

    # 关联菜单
    if data.menu_ids:
        menus = db.query(SysMenu).filter(SysMenu.menu_id.in_(data.menu_ids)).all()
        role.menus = menus

    db.add(role)
    db.commit()
    db.refresh(role)
    return {"msg": "新增成功", "role_id": role.role_id}


@router.put("/update")
async def update_role(
    data: RoleUpdate,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改角色"""
    role = db.query(SysRole).filter(
        SysRole.role_id == data.role_id,
        SysRole.del_flag == "0"
    ).first()

    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 禁止修改 admin 角色的 key
    if role.role_key == "admin" and data.role_key != "admin":
        raise HTTPException(status_code=400, detail="不能修改管理员角色标识")

    role.role_name = data.role_name
    role.role_key = data.role_key
    role.sort = data.sort
    role.status = data.status
    role.remark = data.remark

    # 更新菜单关联
    if data.menu_ids is not None:
        menus = db.query(SysMenu).filter(SysMenu.menu_id.in_(data.menu_ids)).all()
        role.menus = menus

    db.commit()
    return {"msg": "修改成功"}


@router.delete("/delete/{role_id}")
async def delete_role(
    role_id: int,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除角色（逻辑删除）"""
    role = db.query(SysRole).filter(
        SysRole.role_id == role_id,
        SysRole.del_flag == "0"
    ).first()

    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    if role.role_key == "admin":
        raise HTTPException(status_code=400, detail="不能删除管理员角色")

    # 检查是否有用户关联此角色
    if role.users:
        raise HTTPException(status_code=400, detail="该角色下存在用户，不允许删除")

    role.del_flag = "2"
    db.commit()
    return {"msg": "删除成功"}