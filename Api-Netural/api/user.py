# api/user.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from core.database import get_db
from deps import get_current_user
from core.security import hash_password, verify_password
from models.user import SysUser
from models.role import SysRole
from schemas.user import (
    UserInfo, UserItem, UserCreate, UserUpdate,
    UserResetPwd, UserListResponse
)

router = APIRouter(prefix="/system/user", tags=["用户管理"])


@router.get("/info", response_model=UserInfo)
async def get_user_info(current_user: SysUser = Depends(get_current_user)):
    """获取当前用户信息（含角色和权限）"""
    return UserInfo(
        user_id=current_user.user_id, # type: ignore
        user_name=current_user.user_name,# type: ignore
        nick_name=current_user.nick_name,# type: ignore
        email=current_user.email or "",# type: ignore
        phonenumber=current_user.phonenumber or "",# type: ignore
        avatar=current_user.avatar or "",# type: ignore
        roles=current_user.role_keys,
        permissions=["*:*:*"] if current_user.is_admin else []
    )


@router.get("/list", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user_name: str = Query("", description="账号模糊搜索"),
    phonenumber: str = Query("", description="手机号模糊搜索"),
    status: str = Query("", description="状态筛选"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """用户列表（分页）"""
    query = db.query(SysUser).options(
        joinedload(SysUser.roles)
    ).filter(SysUser.del_flag == "0")

    if user_name:
        query = query.filter(SysUser.user_name.like(f"%{user_name}%"))
    if phonenumber:
        query = query.filter(SysUser.phonenumber.like(f"%{phonenumber}%"))
    if status:
        query = query.filter(SysUser.status == status)

    total = query.count()
    users = query.order_by(SysUser.user_id).offset((page - 1) * page_size).limit(page_size).all()

    rows = []
    for u in users:
        rows.append(UserItem(
            user_id=u.user_id, # type: ignore
            user_name=u.user_name, # type: ignore
            nick_name=u.nick_name, # type: ignore
            email=u.email or "", # type: ignore
            phonenumber=u.phonenumber or "", # type: ignore
            sex=u.sex or "0", # type: ignore
            status=u.status or "0", # type: ignore
            login_date=u.login_date, # type: ignore
            create_time=u.create_time, # type: ignore
            role_ids=[r.role_id for r in u.roles],
            role_names=[r.role_name for r in u.roles],
        ))

    return UserListResponse(total=total, rows=rows)


@router.get("/get/{user_id}", response_model=UserItem)
async def get_user(
    user_id: int,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户详情"""
    user = db.query(SysUser).options(
        joinedload(SysUser.roles)
    ).filter(SysUser.user_id == user_id, SysUser.del_flag == "0").first()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return UserItem(
        user_id=user.user_id, # type: ignore
        user_name=user.user_name, # type: ignore
        nick_name=user.nick_name, # type: ignore
        email=user.email or "", # type: ignore
        phonenumber=user.phonenumber or "", # type: ignore
        sex=user.sex or "0", # type: ignore
        status=user.status or "0", # type: ignore
        login_date=user.login_date, # type: ignore
        create_time=user.create_time, # type: ignore
        role_ids=[r.role_id for r in user.roles],
        role_names=[r.role_name for r in user.roles],
    )


@router.post("/add")
async def add_user(
    data: UserCreate,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """新增用户"""
    # 检查用户名是否已存在
    existing = db.query(SysUser).filter(SysUser.user_name == data.user_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = SysUser(
        user_name=data.user_name,
        nick_name=data.nick_name,
        password=hash_password(data.password),
        email=data.email,
        phonenumber=data.phonenumber,
        sex=data.sex,
        status=data.status,
        remark=data.remark,
        del_flag="0",
    )

    # 分配角色
    if data.role_ids:
        roles = db.query(SysRole).filter(SysRole.role_id.in_(data.role_ids)).all()
        user.roles = roles

    db.add(user)
    db.commit()
    db.refresh(user)
    return {"msg": "新增成功", "user_id": user.user_id}


@router.put("/update")
async def update_user(
    data: UserUpdate,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改用户"""
    user = db.query(SysUser).filter(
        SysUser.user_id == data.user_id,
        SysUser.del_flag == "0"
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 禁止修改 admin 的角色
    if user.user_name == "admin" and data.role_ids != [1]: # type: ignore
        raise HTTPException(status_code=400, detail="不能修改管理员角色")

    user.nick_name = data.nick_name # type: ignore
    user.email = data.email # type: ignore
    user.phonenumber = data.phonenumber # type: ignore
    user.sex = data.sex # type: ignore
    user.status = data.status # type: ignore
    user.remark = data.remark # type: ignore

    # 更新角色
    if data.role_ids is not None:
        roles = db.query(SysRole).filter(SysRole.role_id.in_(data.role_ids)).all()
        user.roles = roles

    db.commit()
    return {"msg": "修改成功"}


@router.delete("/delete/{user_id}")
async def delete_user(
    user_id: int,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除用户（逻辑删除）"""
    user = db.query(SysUser).filter(
        SysUser.user_id == user_id,
        SysUser.del_flag == "0"
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.user_name == "admin": # type: ignore
        raise HTTPException(status_code=400, detail="不能删除管理员")

    user.del_flag = "2" # type: ignore
    db.commit()
    return {"msg": "删除成功"}


@router.put("/resetPwd")
async def reset_password(
    data: UserResetPwd,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """重置密码"""
    user = db.query(SysUser).filter(
        SysUser.user_id == data.user_id,
        SysUser.del_flag == "0"
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.password = hash_password(data.new_password) # type: ignore
    db.commit()
    return {"msg": "密码重置成功"}