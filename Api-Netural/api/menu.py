# api/menu.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from deps import get_current_user
from models.user import SysUser
from models.menu import SysMenu

router = APIRouter(prefix="/system/menu", tags=["菜单管理"])


@router.get("/list")
async def get_menu_list(current_user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    获取当前用户的菜单树
    若依前端期望的格式: { code: 200, data: [...] }
    """
    # 查询所有正常显示的菜单
    menus = db.query(SysMenu).filter(
        SysMenu.status == "0",
        SysMenu.visible == "0"
    ).order_by(SysMenu.order_num).all()

    # 构建树形结构
    menu_tree = _build_menu_tree(menus, parent_id=0)

    return {"code": 200, "data": menu_tree}


def _build_menu_tree(menus: list, parent_id: int) -> list:
    """递归构建菜单树"""
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id:
            node = {
                "name": _to_camel_case(menu.path) if menu.path else menu.menu_name,
                "path": f"/{menu.path}" if menu.parent_id == 0 else menu.path,
                "hidden": False,
                "redirect": "noRedirect" if menu.menu_type == "M" else None,
                "component": "Layout" if menu.menu_type == "M" and menu.parent_id == 0
                             else (menu.component or None),
                "meta": {
                    "title": menu.menu_name,
                    "icon": menu.icon or "list",
                    "noCache": False,
                },
                "children": _build_menu_tree(menus, menu.menu_id) if menu.menu_type == "M" else []
            }
            # 如果是目录且有子菜单，设置重定向到第一个子菜单
            if menu.menu_type == "M" and node["children"]:
                node["redirect"] = f'{node["path"]}/{node["children"][0]["path"]}'

            tree.append(node)
    return tree


def _to_camel_case(s: str) -> str:
    """下划线转驼峰"""
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])
