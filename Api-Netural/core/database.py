# # core/database.py
# from sqlalchemy import create_engine, text
# from sqlalchemy.orm import sessionmaker, DeclarativeBase
# from core.config import get_settings

# settings = get_settings()

# engine = create_engine(
#     settings.SQLALCHEMY_DATABASE_URI,
#     pool_size=20,            # 连接池大小
#     max_overflow=10,         # 溢出连接数
#     pool_timeout=30,         # 获取连接超时
#     pool_recycle=3600,       # 连接回收时间(秒)
#     pool_pre_ping=True,      # 连接前检测
#     echo=settings.APP_DEBUG, # SQL 日志
# )

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# class Base(DeclarativeBase):
#     pass


# def get_db():
#     """数据库会话依赖"""
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# def init_db():
#     """初始化数据库 — 建表 + 初始化数据"""
#     Base.metadata.create_all(bind=engine)

#     db = SessionLocal()
#     try:
#         # 检查是否已初始化
#         result = db.execute(text("SELECT COUNT(*) FROM sys_user")).scalar()
#         if result and result > 0:
#             print("数据库已初始化，跳过")
#             return

#         _init_roles(db)
#         _init_menus(db)
#         _init_admin_user(db)
#         db.commit()
#         print("数据库初始化完成")
#     except Exception as e:
#         db.rollback()
#         print(f"数据库初始化失败: {e}")
#     finally:
#         db.close()


# def _init_roles(db):
#     """初始化角色"""
#     from models.role import SysRole
#     roles = [
#         SysRole(role_id=1, role_name="admin",    role_key="admin",    sort=1, status="0", remark="超级管理员"),
#         SysRole(role_id=2, role_name="普通用户",  role_key="user",     sort=2, status="0", remark="普通用户"),
#     ]
#     db.add_all(roles)


# def _init_menus(db):
#     """初始化菜单 — 若依风格菜单结构"""
#     from models.menu import SysMenu
#     menus = [
#         # 一级菜单
#         SysMenu(menu_id=1, menu_name="系统管理", parent_id=0, order_num=1,
#                 path="system", component="", menu_type="M", visible="0",
#                 status="0", icon="system"),
#         SysMenu(menu_id=2, menu_name="神经网络预测", parent_id=0, order_num=2,
#                 path="prediction", component="", menu_type="C", visible="0",
#                 status="0", icon="chart"),

#         # 系统管理子菜单
#         SysMenu(menu_id=10, menu_name="用户管理", parent_id=1, order_num=1,
#                 path="user", component="system/user/index", menu_type="C",
#                 visible="0", status="0", icon="user"),
#         SysMenu(menu_id=11, menu_name="角色管理", parent_id=1, order_num=2,
#                 path="role", component="system/role/index", menu_type="C",
#                 visible="0", status="0", icon="peoples"),
#         SysMenu(menu_id=12, menu_name="菜单管理", parent_id=1, order_num=3,
#                 path="menu", component="system/menu/index", menu_type="C",
#                 visible="0", status="0", icon="tree-table"),

#         # 神经网络预测子菜单
#         SysMenu(menu_id=20, menu_name="实时预测", parent_id=2, order_num=1,
#                 path="realtime", component="prediction/realtime/index", menu_type="C",
#                 visible="0", status="0", icon="monitor"),
#         SysMenu(menu_id=21, menu_name="历史记录", parent_id=2, order_num=2,
#                 path="history", component="prediction/history/index", menu_type="C",
#                 visible="0", status="0", icon="date"),
#         SysMenu(menu_id=22, menu_name="模型管理", parent_id=2, order_num=3,
#                 path="models", component="prediction/models/index", menu_type="C",
#                 visible="0", status="0", icon="code"),
#     ]
#     db.add_all(menus)


# def _init_admin_user(db):
#     """初始化管理员"""
#     from models.user import SysUser
#     from passlib.hash import bcrypt

#     admin = SysUser(
#         user_id=1,
#         user_name="admin",
#         nick_name="管理员",
#         password=bcrypt.hash("admin123"),
#         email="admin@neural-predict.com",
#         phonenumber="13800000000",
#         sex="0",
#         status="0",  # 正常
#         del_flag="0",
#     )
#     admin.roles = [db.query(getattr(__import__('models.role', fromlist=['SysRole']), 'SysRole')).filter_by(role_id=1).first()]
#     db.add(admin)

# core/database.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_size=20,          # 连接池大小
    max_overflow=10,       # 溢出连接数
    pool_timeout=30,       # 获取连接超时
    pool_recycle=3600,     # 连接回收时间(秒)
    pool_pre_ping=True,    # 连接前检测
    echo=settings.APP_DEBUG,  # SQL 日志
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """数据库会话依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库 — 建表 + 初始化数据"""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 检查是否已初始化
        result = db.execute(text("SELECT COUNT(*) FROM sys_user")).scalar()
        if result and result > 0:
            print("数据库已初始化，跳过")
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
    """初始化角色"""
    from models.role import SysRole
    roles = [
        SysRole(role_id=1, role_name="管理员", role_key="admin", sort=1, status="0", remark="超级管理员"),
        SysRole(role_id=2, role_name="普通用户", role_key="user", sort=2, status="0", remark="普通用户"),
    ]
    db.add_all(roles)


def _init_menus(db):
    """初始化菜单"""
    from models.menu import SysMenu
    menus = [
        # 一级菜单
        SysMenu(menu_id=1, menu_name="系统管理", parent_id=0, order_num=1,
                path="system", component="", menu_type="M", visible="0",
                status="0", icon="system"),
        SysMenu(menu_id=2, menu_name="神经网络预测", parent_id=0, order_num=2,
                path="prediction", component="", menu_type="M", visible="0",
                status="0", icon="chart"),

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
    ]
    db.add_all(menus)


def _init_admin_user(db):
    """初始化管理员"""
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
    """初始化角色-菜单关联（admin 拥有全部菜单）"""
    from models.role import SysRole
    from models.menu import SysMenu, sys_role_menu

    admin_role = db.query(SysRole).filter_by(role_id=1).first()
    all_menus = db.query(SysMenu).all()
    admin_role.menus = all_menus