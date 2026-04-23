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


def _migrate_prediction_instance(db):
    """为 prediction_instance 表添加缺失的列"""
    try:
        # 检查 base_model_id 列是否存在
        db.execute(text("SELECT TOP 1 base_model_id FROM prediction_instance"))
        print("prediction_instance 表已是最新")
    except Exception:
        try:
            db.execute(text("ALTER TABLE prediction_instance ADD base_model_id NVARCHAR(50) DEFAULT ''"))
            db.commit()
            print("prediction_instance 表已添加 base_model_id 列")
        except Exception as e:
            db.rollback()
            print(f"prediction_instance 迁移失败: {e}")

    # 检查 instance_type 列
    try:
        db.execute(text("SELECT TOP 1 instance_type FROM prediction_instance"))
    except Exception:
        try:
            db.execute(text("ALTER TABLE prediction_instance ADD instance_type NVARCHAR(50) DEFAULT 'realtime'"))
            db.commit()
            print("prediction_instance 表已添加 instance_type 列")
        except Exception as e:
            db.rollback()
            print(f"prediction_instance instance_type 迁移失败: {e}")


def _migrate_menu_as_instance_type(db):
    """为 sys_menu 表添加 as_instance_type 列，并初始化标记"""
    try:
        db.execute(text("SELECT TOP 1 as_instance_type FROM sys_menu"))
        # 列已存在，检查是否需要初始化标记
        _init_instance_type_flags(db)
    except Exception:
        try:
            db.execute(text("ALTER TABLE sys_menu ADD as_instance_type NVARCHAR(1) DEFAULT 'N'"))
            db.commit()
            print("sys_menu 表已添加 as_instance_type 列")
            _init_instance_type_flags(db)
        except Exception as e:
            db.rollback()
            print(f"sys_menu as_instance_type 迁移失败: {e}")


def _migrate_plc_port(db):
    """将已有 PLC 设备的 port=102 改为 port=0（使用默认端口）"""
    try:
        db.execute(text("UPDATE plc_device SET port = 0 WHERE port = 102"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"PLC port 迁移跳过: {e}")


def _init_instance_type_flags(db):
    """为已有的可作为实例类型的菜单设置标记"""
    try:
        # 烘丝机出口水分模型
        db.execute(text(
            "UPDATE sys_menu SET as_instance_type = 'Y' WHERE menu_name = '烘丝机出口水分模型' AND as_instance_type = 'N'"
        ))
        # 实时预测
        db.execute(text(
            "UPDATE sys_menu SET as_instance_type = 'Y' WHERE menu_name = '实时预测' AND as_instance_type = 'N'"
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"初始化实例类型标记失败: {e}")


def init_db():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        result = db.execute(text("SELECT COUNT(*) FROM sys_user")).scalar()
        if result and result > 0:
            print("数据库已初始化，跳过")
            _migrate_menus(db)
            _migrate_prediction_instance(db)
            _migrate_menu_as_instance_type(db)
            _migrate_plc_port(db)
            return

        _init_roles(db)
        _init_menus(db)
        _init_admin_user(db)
        _init_role_menu(db)
        _init_configs(db)
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
        SysMenu(menu_id=13, menu_name="系统设置", parent_id=1, order_num=4,
                path="config", component="system/config/index", menu_type="C",
                visible="0", status="0", icon="setting"),

        # 神经网络预测子菜单
        SysMenu(menu_id=20, menu_name="实时预测", parent_id=2, order_num=1,
                path="realtime", component="prediction/realtime/index", menu_type="C",
                visible="0", status="0", icon="monitor", as_instance_type="Y"),
        SysMenu(menu_id=21, menu_name="历史记录", parent_id=2, order_num=2,
                path="history", component="prediction/history/index", menu_type="C",
                visible="0", status="0", icon="date"),
        SysMenu(menu_id=22, menu_name="模型管理", parent_id=2, order_num=3,
                path="models", component="prediction/models/index", menu_type="C",
                visible="0", status="0", icon="code"),
        SysMenu(menu_id=24, menu_name="已保存模型", parent_id=2, order_num=5,
                path="saved-models", component="prediction/saved-models/index", menu_type="C",
                visible="0", status="0", icon="folder"),
        SysMenu(menu_id=25, menu_name="烘丝机出口水分模型", parent_id=2, order_num=7,
                path="dryer", component="prediction/dryer/index", menu_type="C",
                visible="0", status="0", icon="trend-charts", as_instance_type="Y"),
        SysMenu(menu_id=26, menu_name="预测实例管理", parent_id=2, order_num=6,
                path="instances", component="prediction/instances/index", menu_type="C",
                visible="0", status="0", icon="list"),

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
    from models.sys_config import SysConfig
    try:
        existing_names = {m.menu_name: m for m in db.query(SysMenu).all()}
        new_menus = []

        # PLC管理 - 独立父级菜单（如果不存在）
        if "PLC管理" not in existing_names:
            plc_parent = SysMenu(menu_name="PLC管理", parent_id=0, order_num=3,
                path="plc", component="", menu_type="M", visible="0",
                status="0", icon="international")
            new_menus.append(plc_parent)
            db.flush()  # 获取自增 ID

            # 把 PLC 相关子菜单移到新的父级下
            for m in db.query(SysMenu).all():
                if m.menu_name in ("PLC设备管理", "PLC点位管理", "设备列表", "点位管理"):
                    if m.parent_id != 0:  # 确认是子菜单
                        m.parent_id = plc_parent.menu_id
        else:
            # PLC管理已存在，确保子菜单正确关联
            plc_parent = existing_names["PLC管理"]
            for m in db.query(SysMenu).all():
                if m.menu_name in ("PLC设备管理", "PLC点位管理", "设备列表", "点位管理"):
                    if m.parent_id != plc_parent.menu_id and m.parent_id != 0:
                        m.parent_id = plc_parent.menu_id

        # 已保存模型菜单（如果不存在）
        if "已保存模型" not in existing_names:
            prediction_parent = existing_names.get("神经网络预测")
            if prediction_parent:
                new_menus.append(SysMenu(menu_name="已保存模型", parent_id=prediction_parent.menu_id, order_num=5,
                    path="saved-models", component="prediction/saved-models/index", menu_type="C",
                    visible="0", status="0", icon="folder"))

        # 系统设置菜单（如果不存在）
        if "系统设置" not in existing_names:
            system_parent = existing_names.get("系统管理")
            if system_parent:
                new_menus.append(SysMenu(menu_name="系统设置", parent_id=system_parent.menu_id, order_num=4,
                    path="config", component="system/config/index", menu_type="C",
                    visible="0", status="0", icon="setting"))

        # 预测实例管理菜单（如果不存在）
        if "预测实例管理" not in existing_names:
            prediction_parent = existing_names.get("神经网络预测")
            if prediction_parent:
                new_menus.append(SysMenu(menu_name="预测实例管理", parent_id=prediction_parent.menu_id, order_num=6,
                    path="instances", component="prediction/instances/index", menu_type="C",
                    visible="0", status="0", icon="list"))

        # 删除模型训练菜单（不应显示在侧边栏）
        if "模型训练" in existing_names:
            training_menu = existing_names["模型训练"]
            from models.menu import sys_role_menu
            db.execute(sys_role_menu.delete().where(sys_role_menu.c.menu_id == training_menu.menu_id))
            db.query(SysMenu).filter(SysMenu.menu_id == training_menu.menu_id).delete()

        # 烘丝机出口水分模型菜单（如果不存在）
        if "烘丝机出口水分模型" not in existing_names:
            prediction_parent = existing_names.get("神经网络预测")
            if prediction_parent:
                new_menus.append(SysMenu(menu_name="烘丝机出口水分模型", parent_id=prediction_parent.menu_id, order_num=7,
                    path="dryer", component="prediction/dryer/index", menu_type="C",
                    visible="0", status="0", icon="trend-charts"))

        if new_menus:
            db.add_all(new_menus)

        # 初始化系统配置（如果不存在）
        existing_configs = {c.config_key for c in db.query(SysConfig.config_key).all()} if db.query(SysConfig).count() > 0 else set()
        if "model_delete_local_file" not in existing_configs:
            db.add(SysConfig(config_name="删除模型时同时删除本地文件",
                config_key="model_delete_local_file", config_value="false",
                config_type="Y", remark="启用后，删除已保存模型版本时将同时删除本地 .pth 文件"))
        if "prediction_instance_types" not in existing_configs:
            db.add(SysConfig(config_name="预测实例类型",
                config_key="prediction_instance_types",
                config_value='[{"key":"realtime","name":"实时预测[通用]","desc":"通用神经网络实时预测，支持 LSTM/GRU/Transformer"},{"key":"dryer","name":"烘丝机出口水分模型","desc":"烘丝机专用预测模型，LSTM+Attention 架构"}]',
                config_type="Y", remark="新建预测实例时可选的实例类型（JSON 格式）"))

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


def _init_configs(db):
    """初始化系统配置"""
    from models.sys_config import SysConfig
    configs = [
        SysConfig(config_id=1, config_name="删除模型时同时删除本地文件",
                  config_key="model_delete_local_file", config_value="false",
                  config_type="Y", remark="启用后，删除已保存模型版本时将同时删除本地 .pth 文件"),
        SysConfig(config_id=2, config_name="预测实例类型",
                  config_key="prediction_instance_types",
                  config_value='[{"key":"realtime","name":"实时预测[通用]","desc":"通用神经网络实时预测，支持 LSTM/GRU/Transformer"},{"key":"dryer","name":"烘丝机出口水分模型","desc":"烘丝机专用预测模型，LSTM+Attention 架构"}]',
                  config_type="Y", remark="新建预测实例时可选的实例类型（JSON 格式）"),
    ]
    db.add_all(configs)
