# # api/menu.py
# from fastapi import APIRouter, Depends
# from sqlalchemy.orm import Session
# from core.database import get_db
# from deps import get_current_user
# from models.user import SysUser
# from models.menu import SysMenu

# router = APIRouter(prefix="/system/menu", tags=["菜单管理"])


# @router.get("/list")
# async def get_menu_list(current_user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
#     """
#     获取当前用户的菜单树
#     若依前端期望的格式: { code: 200, data: [...] }
#     """
#     # 查询所有正常显示的菜单
#     menus = db.query(SysMenu).filter(
#         SysMenu.status == "0",
#         SysMenu.visible == "0"
#     ).order_by(SysMenu.order_num).all()

#     # 构建树形结构
#     menu_tree = _build_menu_tree(menus, parent_id=0)

#     return {"code": 200, "data": menu_tree}


# def _build_menu_tree(menus: list, parent_id: int) -> list:
#     """递归构建菜单树"""
#     tree = []
#     for menu in menus:
#         if menu.parent_id == parent_id:
#             node = {
#                 "name": _to_camel_case(menu.path) if menu.path else menu.menu_name,
#                 "path": f"/{menu.path}" if menu.parent_id == 0 else menu.path,
#                 "hidden": False,
#                 "redirect": "noRedirect" if menu.menu_type == "M" else None,
#                 "component": "Layout" if menu.menu_type == "M" and menu.parent_id == 0
#                              else (menu.component or None),
#                 "meta": {
#                     "title": menu.menu_name,
#                     "icon": menu.icon or "list",
#                     "noCache": False,
#                 },
#                 "children": _build_menu_tree(menus, menu.menu_id) if menu.menu_type == "M" else []
#             }
#             # 如果是目录且有子菜单，设置重定向到第一个子菜单
#             if menu.menu_type == "M" and node["children"]:
#                 node["redirect"] = f'{node["path"]}/{node["children"][0]["path"]}'

#             tree.append(node)
#     return tree


# def _to_camel_case(s: str) -> str:
#     """下划线转驼峰"""
#     parts = s.split("_")
#     return parts[0] + "".join(p.capitalize() for p in parts[1:])

# api/menu.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from deps import get_current_user
from models.user import SysUser
from models.menu import SysMenu
from schemas.menu import MenuItem

router = APIRouter(prefix="/system/menu", tags=["菜单管理"])


def build_menu_tree(menus: list[SysMenu], parent_id: int = 0) -> list[MenuItem]:
    """递归构建菜单树"""
    tree = []
    for m in menus:
        if (m.parent_id or 0) == parent_id: # type: ignore
            children = build_menu_tree(menus, m.menu_id)# type: ignore
            tree.append(MenuItem(
                menu_id=m.menu_id,# type: ignore
                menu_name=m.menu_name,# type: ignore
                parent_id=m.parent_id or 0,# type: ignore
                order_num=m.order_num or 0,# type: ignore
                path=m.path or "",# type: ignore
                component=m.component or "",# type: ignore
                menu_type=m.menu_type or "",# type: ignore
                visible=m.visible or "0",# type: ignore
                status=m.status or "0",# type: ignore
                icon=m.icon or "#",# type: ignore# type: ignore
                create_time=m.create_time,# type: ignore
                remark=m.remark or "",# type: ignore
                children=children,
            ))
    tree.sort(key=lambda x: x.order_num)
    return tree


def to_sidebar_format(menus: list[SysMenu]) -> list[dict]:
    """转换为前端 Sidebar 需要的格式"""
    tree = []
    # 一级菜单
    for m in menus:
        if (m.parent_id or 0) == 0:# type: ignore
            node = {
                "name": m.menu_name,
                "path": "/" + m.path if m.path and not m.path.startswith("/") else m.path,# type: ignore
                "hidden": m.visible != "0",
                "meta": {
                    "title": m.menu_name,
                    "icon": m.icon or "",
                },
                "children": [],
            }
            # 二级菜单
            for c in menus:
                if (c.parent_id or 0) == m.menu_id:# type: ignore
                    node["children"].append({
                        "name": c.menu_name,
                        "path": c.path,
                        "hidden": c.visible != "0",
                        "meta": {
                            "title": c.menu_name,
                            "icon": c.icon or "",
                        },
                    })
            tree.append(node)
    return tree


@router.get("/list")
async def menu_list(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """菜单列表（Sidebar 用）"""
    menus = db.query(SysMenu).filter(
        SysMenu.status == "0"
    ).order_by(SysMenu.order_num).all()
    return to_sidebar_format(menus)


@router.get("/tree")
async def get_menu_tree(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取菜单树（全部，用于菜单管理页）"""
    menus = db.query(SysMenu).order_by(SysMenu.order_num).all()
    return build_menu_tree(menus)


@router.get("/treeselect")
async def get_menu_tree_select(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取菜单树（角色分配权限用）"""
    menus = db.query(SysMenu).filter(
        SysMenu.status == "0"
    ).order_by(SysMenu.order_num).all()
    return build_menu_tree(menus)