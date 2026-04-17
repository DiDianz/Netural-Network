# core/database.py — 添加 PLC 菜单初始化
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=settings.APP_DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        result = db.execute(text("SELECT COUNT(*) FROM sys_user")).scalar()
        if result and result > 0:
            print("数据库已初始化，跳过")
            _migrate_menus(db)
            return

        _init_roles(db)
        _init_menus(db)
        _init_admin_user(db)
        _init_role_menu(db)
        db.commit()
        print("数据库初始化完成")
    except Exception as e:
        db.rollback()
        print(f"数据库初始化失败: {e}")
    finally:
        db.close()


def _init_roles(db):
    from models.role import SysRole
    roles = [
        SysRole(role_id=1, role_name="管理员", role_key="admin", sort=1, status="0", remark="超级管理员"),
        SysRole(role_id=2, role_name="普通用户", role_key="user", sort=2, status="0", remark="普通用户"),
    ]
    db.add_all(roles)


def _init_menus(db):
    from models.menu import SysMenu
    menus = [
        # 一级菜单
        SysMenu(menu_id=1, menu_name="系统管理", parent_id=0, order_num=1,
                path="system", component="", menu_type="M", visible="0",
                status="0", icon="system"),
        SysMenu(menu_id=2, menu_name="神经网络预测", parent_id=0, order_num=2,
                path="prediction", component="", menu_type="M", visible="0",
                status="0", icon="chart"),
        SysMenu(menu_id=3, menu_name="PLC管理", parent_id=0, order_num=3,
                path="plc", component="", menu_type="M", visible="0",
                status="0", icon="international"),

        # 系统管理子菜单
        SysMenu(menu_id=10, menu_name="用户管理", parent_id=1, order_num=1,
                path="user", component="system/user/index", menu_type="C",
                visible="0", status="0", icon="user"),
        SysMenu(menu_id=11, menu_name="角色管理", parent_id=1, order_num=2,
                path="role", component="system/role/index", menu_type="C",
                visible="0", status="0", icon="peoples"),
        SysMenu(menu_id=12, menu_name="菜单管理", parent_id=1, order_num=3,
                path="menu", component="system/menu/index", menu_type="C",
                visible="0", status="0", icon="tree-table"),

        # 神经网络预测子菜单
        SysMenu(menu_id=20, menu_name="实时预测", parent_id=2, order_num=1,
                path="realtime", component="prediction/realtime/index", menu_type="C",
                visible="0", status="0", icon="monitor"),
        SysMenu(menu_id=21, menu_name="历史记录", parent_id=2, order_num=2,
                path="history", component="prediction/history/index", menu_type="C",
                visible="0", status="0", icon="date"),
        SysMenu(menu_id=22, menu_name="模型管理", parent_id=2, order_num=3,
                path="models", component="prediction/models/index", menu_type="C",
                visible="0", status="0", icon="code"),
        SysMenu(menu_id=23, menu_name="模型训练", parent_id=2, order_num=4,
                path="training", component="prediction/training/index", menu_type="C",
                visible="0", status="0", icon="cpu"),
        SysMenu(menu_id=24, menu_name="已保存模型", parent_id=2, order_num=5,
                path="saved-models", component="prediction/saved-models/index", menu_type="C",
                visible="0", status="0", icon="folder"),

        # PLC管理子菜单
        SysMenu(menu_id=31, menu_name="PLC设备管理", parent_id=3, order_num=1,
                path="device", component="prediction/plc/device/index", menu_type="C",
                visible="0", status="0", icon="cpu"),
        SysMenu(menu_id=32, menu_name="PLC点位管理", parent_id=3, order_num=2,
                path="point", component="prediction/plc/point/index", menu_type="C",
                visible="0", status="0", icon="list"),
    ]
    db.add_all(menus)


def _migrate_menus(db):
    """增量迁移菜单：为已有数据库添加新增的菜单项"""
    from models.menu import SysMenu
    try:
        existing_ids = {m.menu_id for m in db.query(SysMenu.menu_id).all()}
        new_menus = []

        # PLC管理 - 独立父级菜单
        if 3 not in existing_ids:
            new_menus.append(SysMenu(menu_id=3, menu_name="PLC管理", parent_id=0, order_num=3,
                path="plc", component="", menu_type="M", visible="0",
                status="0", icon="international"))

        # 已保存模型菜单
        if 24 not in existing_ids:
            new_menus.append(SysMenu(menu_id=24, menu_name="已保存模型", parent_id=2, order_num=5,
                path="saved-models", component="prediction/saved-models/index", menu_type="C",
                visible="0", status="0", icon="folder"))

        # PLC 菜单从 prediction 下迁移到独立父级
        for mid in [30, 31, 32]:
            menu = db.query(SysMenu).filter(SysMenu.menu_id == mid).first()
            if menu:
                if mid == 30:
                    # 删除旧的 PLC 目录（子菜单会由前端重新关联）
                    db.delete(menu)
                elif mid in [31, 32]:
                    # 将 PLC 子菜单移到新父级 menu_id=3
                    menu.parent_id = 3

        if new_menus:
            db.add_all(new_menus)

        if new_menus or True:  # always commit the parent_id updates
            db.commit()
            if new_menus:
                print(f"菜单迁移完成，新增 {len(new_menus)} 个菜单")
            else:
                print("菜单迁移检查完成")
    except Exception as e:
        db.rollback()
        print(f"菜单迁移失败: {e}")


def _init_admin_user(db):
    from models.user import SysUser
    from models.role import SysRole
    from passlib.hash import bcrypt

    admin_role = db.query(SysRole).filter_by(role_id=1).first()

    admin = SysUser(
        user_id=1,
        user_name="admin",
        nick_name="管理员",
        password=bcrypt.hash("admin123"),
        email="admin@neural-predict.com",
        phonenumber="13800000000",
        sex="0",
        status="0",
        del_flag="0",
    )
    admin.roles = [admin_role]
    db.add(admin)


def _init_role_menu(db):
    from models.role import SysRole
    from models.menu import SysMenu

    admin_role = db.query(SysRole).filter_by(role_id=1).first()
    all_menus = db.query(SysMenu).all()
    admin_role.menus = all_menus
