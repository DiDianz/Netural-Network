# core/feature_schema.py
"""
特征方案管理器 — 支持自定义特征列 + 权重
数据持久化到 feature_schemas.json
"""
import json
import os
import uuid
import time
import logging
from threading import Lock
from typing import Optional

logger = logging.getLogger("feature_schema")

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "feature_schemas.json")
_lock = Lock()


class FeatureSchemaManager:
    """管理多套特征方案，每套方案定义特征列名称和对应权重"""

    DEFAULT_SCHEMA = {
        "id": "default",
        "name": "烘丝机默认方案",
        "description": "系统内置的 11 特征方案",
        "features": [
            {"name": "proc_steam_vol", "label": "蒸汽流量", "weight": 1.0},
            {"name": "proc_air_temp", "label": "热风温度", "weight": 1.0},
            {"name": "input_moist", "label": "入口水分", "weight": 1.0},
            {"name": "input_moist_SP", "label": "入口水分设定值", "weight": 1.0},
            {"name": "moist_remove", "label": "排湿量", "weight": 1.0},
            {"name": "out_moist_SP", "label": "出口水分设定值", "weight": 1.0},
            {"name": "out_temp", "label": "出口温度", "weight": 1.0},
            {"name": "mat_flow_PV", "label": "物料流量实际值", "weight": 1.0},
            {"name": "total_mat_flow", "label": "累计物料流量", "weight": 1.0},
            {"name": "env_temp", "label": "环境温度", "weight": 1.0},
            {"name": "env_moist", "label": "环境湿度", "weight": 1.0},
        ],
        "target": {"name": "out_moist", "label": "出口水分"},
        "brand_column": {"name": "brandID", "label": "品牌标识"},
        "is_builtin": True,
        "created_at": "2025-01-01 00:00:00",
        "updated_at": "2025-01-01 00:00:00",
    }

    def __init__(self):
        self.schemas: dict = {}
        self._load()

    def _load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.schemas = {s["id"]: s for s in data}
                logger.info(f"已加载 {len(self.schemas)} 个特征方案")
            except Exception as e:
                logger.error(f"加载特征方案失败: {e}")
                self.schemas = {}
        if "default" not in self.schemas:
            self.schemas["default"] = self.DEFAULT_SCHEMA.copy()
            self._save()

    def _save(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(list(self.schemas.values()), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存特征方案失败: {e}")

    def list_schemas(self) -> list:
        result = []
        for s in self.schemas.values():
            result.append({
                "id": s["id"],
                "name": s["name"],
                "description": s.get("description", ""),
                "feature_count": len(s["features"]),
                "feature_names": [f["name"] for f in s["features"]],
                "target": s["target"]["name"],
                "is_builtin": s.get("is_builtin", False),
                "created_at": s.get("created_at", ""),
                "updated_at": s.get("updated_at", ""),
            })
        return result

    def get_schema(self, schema_id: str) -> Optional[dict]:
        return self.schemas.get(schema_id)

    def create_schema(self, name: str, features: list, target: dict,
                      brand_column: dict = None, description: str = "") -> dict:
        schema_id = str(uuid.uuid4())[:8]
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        schema = {
            "id": schema_id,
            "name": name,
            "description": description,
            "features": features,
            "target": target,
            "brand_column": brand_column or {"name": "brandID", "label": "品牌标识"},
            "is_builtin": False,
            "created_at": now,
            "updated_at": now,
        }
        with _lock:
            self.schemas[schema_id] = schema
            self._save()
        logger.info(f"创建特征方案: {name} ({schema_id}), {len(features)} 个特征")
        return schema

    def update_schema(self, schema_id: str, **kwargs) -> Optional[dict]:
        with _lock:
            schema = self.schemas.get(schema_id)
            if not schema:
                return None
            if schema.get("is_builtin"):
                raise ValueError("内置方案不可修改，可复制后修改")
            for key in ("name", "description", "features", "target", "brand_column"):
                if key in kwargs:
                    schema[key] = kwargs[key]
            schema["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self._save()
        return schema

    def delete_schema(self, schema_id: str) -> bool:
        with _lock:
            schema = self.schemas.get(schema_id)
            if not schema:
                return False
            if schema.get("is_builtin"):
                raise ValueError("内置方案不可删除")
            del self.schemas[schema_id]
            self._save()
        return True

    def copy_schema(self, schema_id: str, new_name: str = None) -> Optional[dict]:
        source = self.schemas.get(schema_id)
        if not source:
            return None
        import copy
        new_schema = copy.deepcopy(source)
        new_schema["id"] = str(uuid.uuid4())[:8]
        new_schema["name"] = new_name or f"{source['name']} (副本)"
        new_schema["is_builtin"] = False
        new_schema["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        new_schema["updated_at"] = new_schema["created_at"]
        with _lock:
            self.schemas[new_schema["id"]] = new_schema
            self._save()
        return new_schema

    def get_weights(self, schema_id: str) -> dict:
        schema = self.schemas.get(schema_id)
        if not schema:
            return {}
        return {f["name"]: f.get("weight", 1.0) for f in schema["features"]}

    def get_feature_names(self, schema_id: str) -> list:
        schema = self.schemas.get(schema_id)
        if not schema:
            return []
        return [f["name"] for f in schema["features"]]

    def get_input_dim(self, schema_id: str) -> int:
        schema = self.schemas.get(schema_id)
        if not schema:
            return 11
        return len(schema["features"])

    def get_column_description(self, schema_id: str) -> dict:
        """获取方案的列结构描述，用于前端提示用户"""
        schema = self.schemas.get(schema_id)
        if not schema:
            return {}
        features = schema["features"]
        target = schema["target"]
        brand = schema["brand_column"]
        return {
            "schema_id": schema_id,
            "schema_name": schema["name"],
            "input_dim": len(features),
            "min_columns": len(features) + 2,
            "features": [{"name": f["name"], "label": f.get("label", "")} for f in features],
            "target": target,
            "brand_column": brand,
            "column_order": [f["name"] for f in features] + [target["name"], brand["name"]],
            "csv_header_example": ",".join(
                [f["name"] for f in features] + [target["name"], brand["name"]]
            ),
        }


feature_schema_manager = FeatureSchemaManager()


def init_menu_on_startup():
    """启动时自动插入特征方案菜单（如果不存在）"""
    try:
        from core.database import SessionLocal
        from models.menu import SysMenu
        db = SessionLocal()
        try:
            # 查找"神经网络预测"父菜单
            parent = db.query(SysMenu).filter(SysMenu.menu_name == "神经网络预测").first()
            if not parent:
                logger.warning("未找到'神经网络预测'父菜单，跳过菜单初始化")
                return

            # 检查是否已存在
            existing = db.query(SysMenu).filter(
                SysMenu.menu_name == "特征方案",
                SysMenu.parent_id == parent.menu_id
            ).first()
            if existing:
                return

            # 获取最大排序号
            max_order = db.query(SysMenu).filter(
                SysMenu.parent_id == parent.menu_id
            ).count()

            menu = SysMenu(
                menu_name="特征方案",
                parent_id=parent.menu_id,
                order_num=max_order + 1,
                path="features",
                component="prediction/features/index",
                menu_type="C",
                visible="0",
                status="0",
                icon="setting",
                remark="自定义特征列方案管理",
            )
            db.add(menu)
            db.commit()
            logger.info("已自动插入'特征方案'菜单")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"菜单初始化跳过: {e}")
