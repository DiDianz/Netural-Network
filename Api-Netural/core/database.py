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
    """将已有 PLC 设备的 port=102 改为 port=NULL（无端口）"""
    try:
        db.execute(text("UPDATE plc_device SET port = NULL WHERE port = 102"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"PLC port 迁移跳过: {e}")


def _migrate_operation_log_type(db):
    """为 operation_log 表添加 log_type 列（全链路日志）"""
    try:
        db.execute(text("SELECT TOP 1 log_type FROM operation_log"))
        print("operation_log.log_type 列已存在")
    except Exception:
        try:
            db.execute(text("ALTER TABLE operation_log ADD log_type NVARCHAR(20) DEFAULT 'api'"))
            db.commit()
            print("operation_log 表已添加 log_type 列")
        except Exception as e:
            db.rollback()
            print(f"operation_log log_type 迁移失败: {e}")


def _deduplicate_roles(db):
    """清理重复角色：按 role_key 去重，保留 role_id 最小的记录"""
    try:
        from models.role import SysRole
        from models.menu import sys_role_menu
        from models.user import sys_user_role

        # 找出重复的 role_key（保留 id 最小的）
        dupes = db.execute(text("""
            SELECT role_key, MIN(role_id) AS keep_id
            FROM sys_role
            GROUP BY role_key
            HAVING COUNT(*) > 1
        """)).fetchall()

        if not dupes:
            print("角色表无重复数据")
            return

        total_deleted = 0
        for role_key, keep_id in dupes:
            # 获取该 role_key 下所有 role_id（排除要保留的）
            ids = db.execute(text(
                "SELECT role_id FROM sys_role WHERE role_key = :key AND role_id != :keep"
            ), {"key": role_key, "keep": keep_id}).fetchall()

            for (dup_id,) in ids:
                # 先删关联表
                db.execute(sys_role_menu.delete().where(sys_role_menu.c.role_id == dup_id))
                db.execute(sys_user_role.delete().where(sys_user_role.c.role_id == dup_id))
                # 再删角色
                db.execute(text("DELETE FROM sys_role WHERE role_id = :id"), {"id": dup_id})
                total_deleted += 1
                print(f"  删除重复角色: role_key={role_key}, role_id={dup_id} (保留 {keep_id})")

        db.commit()
        print(f"角色去重完成，共删除 {total_deleted} 条重复记录")
    except Exception as e:
        db.rollback()
        print(f"角色去重失败: {e}")


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


def _sync_saved_models_to_db(db):
    """将本地 registry.json 中的已保存模型同步到数据库，并补录未注册的 _best.pth 文件"""
    from models.saved_model import SavedModel
    from pathlib import Path
    import json as _json
    from datetime import datetime

    base_dir = Path(__file__).parent.parent / "saved_models"

    synced = 0

    # 1. 同步通用模型 registry
    registry_path = base_dir / "registry.json"
    registry = {}
    if registry_path.exists():
        try:
            registry = _json.loads(registry_path.read_text())
            for model_id, info in registry.items():
                existing = db.query(SavedModel).filter(SavedModel.model_id == model_id).first()
                if existing:
                    continue
                record = SavedModel(
                    model_id=model_id,
                    model_type="general",
                    model_key=info.get("model_key", ""),
                    display_name=info.get("display_name", ""),
                    name=info.get("name", ""),
                    filename=info.get("filename", ""),
                    epochs=info.get("epochs", 0),
                    best_val_loss=info.get("best_val_loss", 0),
                    trained_at=datetime.strptime(info["trained_at"], "%Y-%m-%d %H:%M:%S") if info.get("trained_at") else datetime.now(),
                    remark=info.get("remark", ""),
                    file_size_kb=info.get("file_size_kb", 0),
                    schema_id=info.get("schema_id", "default"),
                    input_dim=info.get("input_dim", 0),
                )
                db.add(record)
                synced += 1
        except Exception as e:
            print(f"同步通用模型注册表失败: {e}")

    # 1.5 补录未在 registry 中的 _best.pth 文件
    best_meta = {
        "lstm_best.pth": {"model_key": "lstm", "display_name": "LSTM + Attention"},
        "gru_best.pth": {"model_key": "gru", "display_name": "GRU"},
        "transformer_best.pth": {"model_key": "transformer", "display_name": "Transformer"},
    }
    registry_changed = False
    for fname, meta in best_meta.items():
        fpath = base_dir / fname
        if not fpath.exists():
            continue
        model_id = f"{meta['model_key']}_best"
        # 检查是否已在 registry 或数据库中
        in_registry = model_id in registry or any(
            v.get("filename") == fname for v in registry.values()
        )
        in_db = db.query(SavedModel).filter(SavedModel.model_id == model_id).first()
        if in_db:
            continue
        # 写入 registry
        if not in_registry:
            mtime = datetime.fromtimestamp(fpath.stat().st_mtime)
            entry = {
                "model_id": model_id,
                "model_key": meta["model_key"],
                "display_name": meta["display_name"],
                "name": f"{meta['display_name']}_{mtime.strftime('%Y%m%d')}_best",
                "filename": fname,
                "epochs": 0,
                "best_val_loss": 0,
                "trained_at": mtime.strftime("%Y-%m-%d %H:%M:%S"),
                "remark": "从 best 权重文件自动同步",
                "file_size_kb": round(fpath.stat().st_size / 1024, 1),
                "schema_id": "default",
                "input_dim": 11,
            }
            registry[model_id] = entry
            registry_changed = True
            print(f"  registry.json 已补录: {model_id} ({fname})")
        # 写入数据库
        reg_entry = registry.get(model_id, {})
        record = SavedModel(
            model_id=model_id,
            model_type="general",
            model_key=meta["model_key"],
            display_name=meta["display_name"],
            name=reg_entry.get("name", f"{meta['display_name']}_best"),
            filename=fname,
            epochs=reg_entry.get("epochs", 0),
            best_val_loss=reg_entry.get("best_val_loss", 0),
            trained_at=datetime.strptime(reg_entry["trained_at"], "%Y-%m-%d %H:%M:%S") if reg_entry.get("trained_at") else datetime.now(),
            remark=reg_entry.get("remark", "从 best 权重文件自动同步"),
            file_size_kb=reg_entry.get("file_size_kb", round(fpath.stat().st_size / 1024, 1)),
            schema_id=reg_entry.get("schema_id", "default"),
            input_dim=reg_entry.get("input_dim", 11),
        )
        db.add(record)
        synced += 1
        print(f"  数据库已补录: {model_id} ({fname})")

    # 回写 registry.json
    if registry_changed:
        try:
            registry_path.write_text(_json.dumps(registry, ensure_ascii=False, indent=2))
            print("  registry.json 已更新")
        except Exception as e:
            print(f"  写入 registry.json 失败: {e}")

    # 2. 同步烘丝机模型 registry
    dryer_registry_path = base_dir / "dryer" / "registry.json"
    if dryer_registry_path.exists():
        try:
            dryer_reg = _json.loads(dryer_registry_path.read_text())
            for version, info in dryer_reg.get("versions", {}).items():
                existing = db.query(SavedModel).filter(SavedModel.model_id == version).first()
                if existing:
                    continue
                metrics = info.get("metrics", {})
                config = info.get("config", {})
                record = SavedModel(
                    model_id=version,
                    model_type="dryer",
                    model_key="dryer",
                    display_name="烘丝机出口水分模型",
                    name=version,
                    filename=f"{version}.pth",
                    epochs=metrics.get("epochs", 0),
                    best_val_loss=metrics.get("best_test_loss", 0),
                    r2=metrics.get("final_r2", 0),
                    trained_at=datetime.fromisoformat(info["created_at"]) if info.get("created_at") else datetime.now(),
                    file_size_kb=round((base_dir / "dryer" / f"{version}.pth").stat().st_size / 1024, 1) if (base_dir / "dryer" / f"{version}.pth").exists() else 0,
                    schema_id="dryer",
                    input_dim=config.get("input_dim", 12),
                    remark=f"active={'Y' if version == dryer_reg.get('active_version') else 'N'}",
                )
                db.add(record)
                synced += 1
        except Exception as e:
            print(f"同步烘丝机模型注册表失败: {e}")

    if synced > 0:
        db.commit()
        print(f"已同步 {synced} 个模型到数据库")


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
            _migrate_operation_log_type(db)
            _deduplicate_roles(db)
            _sync_saved_models_to_db(db)
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

        # 操作日志菜单（如果不存在）
        if "操作日志" not in existing_names:
            system_parent = existing_names.get("系统管理")
            if system_parent:
                new_menus.append(SysMenu(menu_name="操作日志", parent_id=system_parent.menu_id, order_num=5,
                    path="log", component="system/log/index", menu_type="C",
                    visible="0", status="0", icon="log"))

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
