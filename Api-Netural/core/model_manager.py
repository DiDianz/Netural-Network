# core/model_manager.py
"""
模型管理器 — 支持动态特征维度 + 特征权重
"""
import torch
import torch.nn as nn
import numpy as np
import asyncio
import json
import time
import os
import uuid
from collections import deque
from datetime import datetime
from core.model import PredictionNet
from core.model_gru import GRUNet
from core.model_transformer import TransformerNet
from core.data_manager import data_manager

# 默认特征维度（可通过 rebuild_models 动态修改）
DEFAULT_INPUT_DIM = 11


class ModelManager:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.window_size = 60
        self.input_dim = DEFAULT_INPUT_DIM
        self._schema_id = "default"  # 当前模型对应的特征方案

        self.models = self._create_models(self.input_dim)

        self.current_model_key = "lstm"
        self.buffers = {}
        for key in self.models:
            self.buffers[key] = deque(maxlen=self.window_size)
        for key in self.buffers:
            self._prefill_buffer(key)

        self.training_state = {
            "is_training": False, "model_key": None, "epoch": 0, "total_epochs": 0,
            "loss": 0, "val_loss": 0, "best_val_loss": 0, "progress": 0,
            "lr": 0, "elapsed": 0, "logs": [], "loss_history": [],
            "val_loss_history": [], "done": False, "message": "", "error": "",
            "predictions": [], "actuals": [], "train_id": "",
            "brand_predictions": {},
            "schema_id": "default", "input_dim": DEFAULT_INPUT_DIM,
        }

        self._running = False
        self._interval = 1.0
        self.save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'saved_models')
        os.makedirs(self.save_dir, exist_ok=True)
        self._registry_path = os.path.join(self.save_dir, 'registry.json')
        self.saved_models = {}
        self._load_registry()
        self._load_saved_models()

    def _create_models(self, input_dim):
        """根据特征维度创建三个模型"""
        return {
            "lstm": {
                "name": "LSTM", "display_name": "LSTM + Attention",
                "model": PredictionNet(input_dim=input_dim, hidden_dim=128, output_dim=1),
                "status": "idle", "accuracy": None, "trained_at": None,
                "total_predictions": 0,
                "description": "长短期记忆网络 + 注意力机制，适合短序列时序预测"
            },
            "gru": {
                "name": "GRU", "display_name": "GRU",
                "model": GRUNet(input_dim=input_dim, hidden_dim=128, output_dim=1),
                "status": "idle", "accuracy": None, "trained_at": None,
                "total_predictions": 0,
                "description": "门控循环单元，比 LSTM 更快更轻，适合资源受限场景"
            },
            "transformer": {
                "name": "Transformer", "display_name": "Transformer",
                "model": TransformerNet(input_dim=input_dim, d_model=128, output_dim=1),
                "status": "idle", "accuracy": None, "trained_at": None,
                "total_predictions": 0,
                "description": "Transformer 编码器，并行计算快，擅长长距离依赖"
            }
        }

    def rebuild_models(self, input_dim, schema_id=None):
        """
        用新的特征维度重建所有模型。
        当上传数据的特征列数与当前模型不同时自动调用。
        """
        old_dim = self.input_dim
        self.input_dim = input_dim
        self._schema_id = schema_id or "default"

        # 重建模型
        self.models = self._create_models(input_dim)

        # 重建 buffer
        self.buffers = {}
        for key in self.models:
            self.buffers[key] = deque(maxlen=self.window_size)
            self._prefill_buffer(key)

        # 加载已有最佳权重（如果维度匹配）
        self._load_saved_models()

        print(f"[ModelManager] 模型已重建: input_dim {old_dim} → {input_dim}, schema={self._schema_id}")

    @property
    def current_model(self):
        return self.models[self.current_model_key]["model"]

    @property
    def current_buffer(self):
        return self.buffers[self.current_model_key]

    def _prefill_buffer(self, model_key):
        for _ in range(self.window_size):
            self.buffers[model_key].append(np.random.randn(self.input_dim).astype(np.float32))

    # ========== 模型版本注册表 ==========

    def _load_registry(self):
        if os.path.exists(self._registry_path):
            try:
                with open(self._registry_path, 'r', encoding='utf-8') as f:
                    self.saved_models = json.load(f)
            except Exception as e:
                print(f"加载模型注册表失败: {e}")
                self.saved_models = {}

    def _save_registry(self):
        try:
            with open(self._registry_path, 'w', encoding='utf-8') as f:
                json.dump(self.saved_models, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存模型注册表失败: {e}")

    def _register_saved_model(self, model_key, epochs, best_val_loss, remark=None, custom_name=None,
                               schema_id=None, input_dim=None, db=None):
        """训练完成后注册一个保存的模型版本"""
        model_id = str(uuid.uuid4())[:8]
        filename = f"{model_key}_{model_id}.pth"
        filepath = os.path.join(self.save_dir, filename)
        best_path = os.path.join(self.save_dir, f"{model_key}_best.pth")
        if os.path.exists(best_path):
            import shutil
            shutil.copy2(best_path, filepath)

        if not custom_name:
            date_str = datetime.now().strftime("%Y%m%d")
            custom_name = f"{self.models[model_key]['display_name']}_{date_str}_{epochs}轮_val{best_val_loss:.4f}"

        entry = {
            "model_id": model_id,
            "model_key": model_key,
            "display_name": self.models[model_key]["display_name"],
            "name": custom_name,
            "filename": filename,
            "epochs": epochs,
            "best_val_loss": round(best_val_loss, 6),
            "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "remark": remark or "",
            "file_size_kb": round(os.path.getsize(filepath) / 1024, 1) if os.path.exists(filepath) else 0,
            "schema_id": schema_id or self._schema_id,
            "input_dim": input_dim or self.input_dim,
        }
        self.saved_models[model_id] = entry
        self._save_registry()

        # 同步到数据库（使用独立 session，避免异步训练时原 session 已关闭）
        self._save_model_to_db(model_id, model_key, custom_name, filename,
                               epochs, best_val_loss, remark, schema_id, input_dim, filepath)

        return entry

    def _save_model_to_db(self, model_id, model_key, custom_name, filename,
                          epochs, best_val_loss, remark=None, schema_id=None,
                          input_dim=None, filepath=None):
        """使用独立 session 将模型保存到数据库"""
        from core.database import SessionLocal
        from models.saved_model import SavedModel
        _db = SessionLocal()
        try:
            record = SavedModel(
                model_id=model_id,
                model_type="general",
                model_key=model_key,
                display_name=self.models[model_key]["display_name"],
                name=custom_name,
                filename=filename,
                epochs=epochs,
                best_val_loss=round(best_val_loss, 6),
                trained_at=datetime.now(),
                remark=remark or "",
                file_size_kb=round(os.path.getsize(filepath) / 1024, 1) if filepath and os.path.exists(filepath) else 0,
                schema_id=schema_id or self._schema_id,
                input_dim=input_dim or self.input_dim,
            )
            _db.add(record)
            _db.commit()
            print(f"模型已保存到数据库: {model_id} ({model_key})")
        except Exception as e:
            print(f"保存模型到数据库失败: {e}")
            _db.rollback()
        finally:
            _db.close()

    def rename_saved_model(self, model_id, new_name):
        if model_id not in self.saved_models:
            raise ValueError(f"模型版本不存在: {model_id}")
        if not new_name or not new_name.strip():
            raise ValueError("名称不能为空")
        self.saved_models[model_id]["name"] = new_name.strip()
        self._save_registry()

        # 同步到数据库
        try:
            from models.saved_model import SavedModel
            from core.database import SessionLocal
            _db = SessionLocal()
            record = _db.query(SavedModel).filter(SavedModel.model_id == model_id).first()
            if record:
                record.name = new_name.strip()
                _db.commit()
            _db.close()
        except Exception as e:
            print(f"重命名模型数据库同步失败: {e}")

        return self.saved_models[model_id]

    def list_saved_models(self, model_key=None):
        result = []
        to_remove = []
        for mid, entry in self.saved_models.items():
            filepath = os.path.join(self.save_dir, entry["filename"])
            if not os.path.exists(filepath):
                to_remove.append(mid)
            else:
                if model_key is None or entry["model_key"] == model_key:
                    result.append(dict(entry))
        for mid in to_remove:
            del self.saved_models[mid]
        if to_remove:
            self._save_registry()
        result.sort(key=lambda x: x.get("trained_at", ""), reverse=True)
        return result

    def delete_saved_model(self, model_id, delete_local=False):
        if model_id not in self.saved_models:
            raise ValueError(f"模型版本不存在: {model_id}")
        entry = self.saved_models[model_id]
        filepath = os.path.join(self.save_dir, entry["filename"])
        if os.path.exists(filepath) and delete_local:
            os.remove(filepath)
        del self.saved_models[model_id]
        self._save_registry()

        # 从数据库删除
        try:
            from models.saved_model import SavedModel
            from core.database import SessionLocal
            _db = SessionLocal()
            _db.query(SavedModel).filter(SavedModel.model_id == model_id).delete()
            _db.commit()
            _db.close()
        except Exception as e:
            print(f"从数据库删除模型失败: {e}")

        return {"deleted": model_id, "model_key": entry["model_key"]}

    def load_model_weights(self, model_key, model_id):
        if model_id not in self.saved_models:
            raise ValueError(f"模型版本不存在: {model_id}")
        entry = self.saved_models[model_id]
        if entry["model_key"] != model_key:
            raise ValueError(f"模型类型不匹配: 期望 {entry['model_key']}, 实际 {model_key}")

        # 如果保存模型的 input_dim 与当前不同，先重建
        saved_dim = entry.get("input_dim", DEFAULT_INPUT_DIM)
        if saved_dim != self.input_dim:
            self.rebuild_models(saved_dim, entry.get("schema_id"))

        filepath = os.path.join(self.save_dir, entry["filename"])
        if not os.path.exists(filepath):
            raise ValueError(f"模型文件不存在: {filepath}")
        model = self.models[model_key]["model"]
        model.load_state_dict(torch.load(filepath, map_location=self.device))
        model.to(self.device)
        return entry

    def _load_saved_models(self):
        for key in self.models:
            path = os.path.join(self.save_dir, f"{key}_best.pth")
            if os.path.exists(path):
                try:
                    state_dict = torch.load(path, map_location=self.device)
                    # 检查维度是否匹配
                    model = self.models[key]["model"]
                    first_key = list(state_dict.keys())[0]
                    saved_dim = state_dict[first_key].shape[-1] if len(state_dict[first_key].shape) > 1 else None
                    if saved_dim and saved_dim != self.input_dim:
                        print(f"[ModelManager] 跳过加载 {key}: 维度不匹配 (saved={saved_dim}, current={self.input_dim})")
                        continue
                    model.load_state_dict(state_dict)
                    self.models[key]["status"] = "ready"
                    self.models[key]["trained_at"] = datetime.fromtimestamp(
                        os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    print(f"加载 {key} 模型失败: {e}")

    # ========== 模型管理 ==========

    def list_models(self):
        result = []
        for key, info in self.models.items():
            result.append({
                "key": key, "name": info["name"], "display_name": info["display_name"],
                "description": info["description"], "status": info["status"],
                "is_current": key == self.current_model_key,
                "accuracy": info["accuracy"], "trained_at": info["trained_at"],
                "total_predictions": info["total_predictions"],
                "params_count": sum(p.numel() for p in info["model"].parameters()),
                "device": str(self.device),
                "input_dim": self.input_dim,
                "schema_id": self._schema_id,
            })
        return result

    def switch_model(self, model_key):
        if model_key not in self.models:
            raise ValueError(f"模型不存在: {model_key}")
        self.current_model_key = model_key
        self.current_model.eval()
        return {"current_model": model_key, "display_name": self.models[model_key]["display_name"],
                "status": self.models[model_key]["status"]}

    def get_status(self):
        return {
            "current_model": self.current_model_key, "is_running": self._running,
            "interval": self._interval, "buffer_size": len(self.current_buffer),
            "is_training": self.training_state["is_training"],
            "training_model": self.training_state["model_key"],
            "input_dim": self.input_dim,
            "schema_id": self._schema_id,
        }

    # ========== 推理 ==========

    @torch.no_grad()
    def predict_once(self, model_key=None):
        key = model_key or self.current_model_key
        model = self.models[key]["model"]
        buffer = self.buffers[key]
        model.eval()

        input_seq = np.array(list(buffer))
        input_tensor = torch.tensor(input_seq).unsqueeze(0).to(self.device)
        prediction = model(input_tensor).cpu().numpy()[0]

        model.train()
        preds_mc = [model(input_tensor).cpu().numpy()[0] for _ in range(10)]
        model.eval()
        preds_mc = np.array(preds_mc)
        mean_pred = float(preds_mc.mean())
        std_pred = float(preds_mc.std())

        buffer.append(np.random.randn(self.input_dim).astype(np.float32))
        self.models[key]["total_predictions"] += 1

        return {
            "timestamp": time.time(), "model_key": key,
            "model_name": self.models[key]["display_name"],
            "prediction": round(mean_pred, 6),
            "confidence_upper": round(mean_pred + 2 * std_pred, 6),
            "confidence_lower": round(mean_pred - 2 * std_pred, 6),
            "uncertainty": round(std_pred, 6), "input_window_size": len(buffer),
            "input_dim": self.input_dim, "schema_id": self._schema_id,
        }

    async def stream_predictions(self, model_key=None, use_uploaded=False):
        self._running = True
        while self._running:
            if use_uploaded and data_manager.has_data():
                result = self.predict_with_uploaded_data(model_key)
            else:
                result = self.predict_once(model_key)
            if result:
                yield result
            await asyncio.sleep(self._interval)

    def stop(self):
        self._running = False

    def stop_training(self):
        self.training_state["is_training"] = False

    def get_training_state(self):
        return dict(self.training_state)

    # ========== 数据库保存 ==========

    def _save_train_log(self, model_key, epochs, best_val_loss, elapsed, status, db=None, remark=None):
        from core.database import SessionLocal
        from models.train_log import TrainLog
        _db = SessionLocal()
        try:
            record = TrainLog(
                model_key=model_key, model_name=self.models[model_key]["display_name"],
                epoch=epochs, total_epochs=epochs,
                train_loss=self.training_state.get("loss", 0),
                val_loss=self.training_state.get("val_loss", 0),
                learning_rate=self.training_state.get("lr", 0),
                status=status, best_val_loss=best_val_loss,
                duration_seconds=round(elapsed, 1),
                remark=remark or self.training_state.get("message", "")
            )
            _db.add(record)
            _db.commit()
        except Exception as e:
            print(f"保存训练日志失败: {e}")
            _db.rollback()
        finally:
            _db.close()

    def _save_train_trend(self, train_id, model_key, epoch, total_epochs,
                          train_loss, val_loss, best_val_loss, lr, elapsed,
                          predictions, actuals, db=None):
        from core.database import SessionLocal
        from models.train_trend import TrainTrend
        _db = SessionLocal()
        try:
            record = TrainTrend(
                train_id=train_id, model_key=model_key,
                model_name=self.models[model_key]["display_name"],
                epoch=epoch, total_epochs=total_epochs,
                train_loss=train_loss, val_loss=val_loss,
                best_val_loss=best_val_loss, learning_rate=lr,
                elapsed_seconds=round(elapsed, 1),
                predictions_json=json.dumps(predictions) if predictions else None,
                actuals_json=json.dumps(actuals) if actuals else None
            )
            _db.add(record)
            _db.commit()
        except Exception as e:
            print(f"保存趋势失败 epoch {epoch}: {e}")
            _db.rollback()
        finally:
            _db.close()

    # ========== 训练（随机数据） ==========

    async def train_model(self, model_key, epochs=50, lr=0.001, batch_size=32,
                          db=None, base_model_id=None, model_name=None):
        if self.training_state["is_training"]:
            raise RuntimeError("已有训练任务在进行中")
        if model_key not in self.models:
            raise ValueError(f"模型不存在: {model_key}")

        if base_model_id:
            self.load_model_weights(model_key, base_model_id)

        train_id = str(uuid.uuid4())[:8]
        self.training_state = {
            "is_training": True, "model_key": model_key, "epoch": 0, "total_epochs": epochs,
            "loss": 0, "val_loss": 0, "best_val_loss": float('inf'), "progress": 0,
            "lr": lr, "elapsed": 0, "logs": [], "loss_history": [],
            "val_loss_history": [], "done": False, "message": "", "error": "",
            "predictions": [], "actuals": [], "train_id": train_id,
            "brand_predictions": {},
            "schema_id": self._schema_id, "input_dim": self.input_dim,
        }

        model = self.models[model_key]["model"]
        model.train()
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        criterion = nn.MSELoss()
        start_time = time.time()
        best_val_loss = float('inf')

        try:
            for epoch in range(1, epochs + 1):
                # 生成随机训练数据
                train_x = np.random.randn(batch_size * 10, self.window_size, self.input_dim).astype(np.float32)
                train_y = np.random.randn(batch_size * 10, 1).astype(np.float32)
                val_x = np.random.randn(batch_size * 2, self.window_size, self.input_dim).astype(np.float32)
                val_y = np.random.randn(batch_size * 2, 1).astype(np.float32)

                # 训练
                total_loss = 0
                n_batches = 0
                for i in range(0, len(train_x), batch_size):
                    bx = torch.tensor(train_x[i:i+batch_size]).to(self.device)
                    by = torch.tensor(train_y[i:i+batch_size]).to(self.device)
                    optimizer.zero_grad()
                    pred = model(bx)
                    loss = criterion(pred, by)
                    loss.backward()
                    optimizer.step()
                    total_loss += loss.item()
                    n_batches += 1

                avg_loss = total_loss / max(n_batches, 1)

                # 验证
                model.eval()
                with torch.no_grad():
                    vx = torch.tensor(val_x).to(self.device)
                    vy = torch.tensor(val_y).to(self.device)
                    val_pred = model(vx)
                    val_loss = criterion(val_pred, vy).item()
                model.train()

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    torch.save(model.state_dict(),
                              os.path.join(self.save_dir, f"{model_key}_best.pth"))

                elapsed = time.time() - start_time
                progress = int(epoch / epochs * 100)

                self.training_state.update({
                    "epoch": epoch, "loss": avg_loss, "val_loss": val_loss,
                    "best_val_loss": best_val_loss, "progress": progress,
                    "elapsed": round(elapsed, 1),
                })

                log_entry = {"epoch": epoch, "loss": avg_loss, "val_loss": val_loss, "lr": lr}
                self.training_state["logs"].append(log_entry)
                self.training_state["loss_history"].append(avg_loss)
                self.training_state["val_loss_history"].append(val_loss)

                await asyncio.sleep(0.01)

                if not self.training_state["is_training"]:
                    self.training_state["message"] = "训练已手动停止"
                    break

            # 注册模型
            self._register_saved_model(model_key, epochs, best_val_loss,
                                        schema_id=self._schema_id, input_dim=self.input_dim, db=db)
            self.models[model_key]["status"] = "ready"
            self.models[model_key]["trained_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if db:
                self._save_train_log(model_key, epochs, best_val_loss,
                                     time.time() - start_time, "completed", db)

            self.training_state["done"] = True
            self.training_state["message"] = f"训练完成，最优 Val Loss: {best_val_loss:.6f}"

        except Exception as e:
            self.training_state["error"] = str(e)
            self.training_state["message"] = f"训练异常: {e}"
            if db:
                self._save_train_log(model_key, epochs, best_val_loss,
                                     time.time() - start_time, "failed", db, str(e))
        finally:
            self.training_state["is_training"] = False

    # ========== 上传数据训练（支持特征权重） ==========

    async def train_model_with_data1(self, model_key, data, job_id, epochs=50, lr=0.001,
                                      batch_size=32, db=None, base_model_id=None, model_name=None,
                                      feature_weights=None, schema_id="default"):
        """
        用上传的真实数据训练模型
        data: [[feature1, feature2, ..., featureN, out_moist, brandID], ...]
        feature_weights: {feature_name: weight} 可选
        """
        try:
            if base_model_id:
                self.load_model_weights(model_key, base_model_id)

            train_id = str(uuid.uuid4())[:8]
            self.training_state = {
                "is_training": True, "model_key": model_key, "epoch": 0, "total_epochs": epochs,
                "loss": 0, "val_loss": 0, "best_val_loss": float('inf'), "progress": 0,
                "lr": lr, "elapsed": 0, "logs": [], "loss_history": [],
                "val_loss_history": [], "done": False, "message": "", "error": "",
                "predictions": [], "actuals": [], "train_id": train_id,
                "brand_predictions": {},
                "schema_id": schema_id, "input_dim": self.input_dim,
            }

            model = self.models[model_key]["model"]
            model.train()
            optimizer = torch.optim.Adam(model.parameters(), lr=lr)
            criterion = nn.MSELoss()
            start_time = time.time()
            best_val_loss = float('inf')

            # 解析数据：分离特征和目标
            arr = np.array(data, dtype=np.float32)
            input_dim = self.input_dim
            features = arr[:, :input_dim]   # (N, input_dim)
            targets = arr[:, input_dim]     # (N,)

            # ===== 应用特征权重 =====
            if feature_weights:
                from core.feature_schema import feature_schema_manager
                schema = feature_schema_manager.get_schema(schema_id)
                if schema:
                    weight_vec = np.ones(input_dim, dtype=np.float32)
                    for i, feat in enumerate(schema["features"]):
                        w = feature_weights.get(feat["name"], feat.get("weight", 1.0))
                        weight_vec[i] = w
                    features = features * weight_vec  # 广播加权

            # 构建滑动窗口序列
            window_size = self.window_size
            n_samples = len(features) - window_size
            if n_samples < 10:
                raise ValueError(f"数据量不足，需要至少 {window_size + 10} 行")

            X, y = [], []
            for i in range(n_samples):
                X.append(features[i:i + window_size])
                y.append(targets[i + window_size])
            X = np.array(X, dtype=np.float32)
            y = np.array(y, dtype=np.float32).reshape(-1, 1)

            # 划分训练/验证集 (80/20)
            split = int(len(X) * 0.8)
            train_X, val_X = X[:split], X[split:]
            train_y, val_y = y[:split], y[split:]

            # 按品牌收集实际值用于趋势图
            brand_actuals = {}
            for row in data:
                brand = int(row[-1])
                target_val = float(row[input_dim])
                if brand not in brand_actuals:
                    brand_actuals[brand] = []
                brand_actuals[brand].append(target_val)

            for epoch in range(1, epochs + 1):
                # 训练
                total_loss = 0
                n_batches = 0
                indices = np.random.permutation(len(train_X))
                for i in range(0, len(train_X), batch_size):
                    batch_idx = indices[i:i + batch_size]
                    bx = torch.tensor(train_X[batch_idx]).to(self.device)
                    by = torch.tensor(train_y[batch_idx]).to(self.device)
                    optimizer.zero_grad()
                    pred = model(bx)
                    loss = criterion(pred, by)
                    loss.backward()
                    optimizer.step()
                    total_loss += loss.item()
                    n_batches += 1

                avg_loss = total_loss / max(n_batches, 1)

                # 验证
                model.eval()
                with torch.no_grad():
                    vx = torch.tensor(val_X).to(self.device)
                    vy = torch.tensor(val_y).to(self.device)
                    val_pred = model(vx)
                    val_loss = criterion(val_pred, vy).item()

                    # 收集预测值用于趋势图
                    all_pred = model(torch.tensor(X[:200]).to(self.device)).cpu().numpy().flatten().tolist()
                    all_actual = y[:200].flatten().tolist()
                model.train()

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    torch.save(model.state_dict(),
                              os.path.join(self.save_dir, f"{model_key}_best.pth"))

                elapsed = time.time() - start_time
                progress = int(epoch / epochs * 100)

                self.training_state.update({
                    "epoch": epoch, "loss": avg_loss, "val_loss": val_loss,
                    "best_val_loss": best_val_loss, "progress": progress,
                    "elapsed": round(elapsed, 1),
                    "predictions": all_pred,
                    "actuals": all_actual,
                })

                log_entry = {"epoch": epoch, "loss": avg_loss, "val_loss": val_loss, "lr": lr}
                self.training_state["logs"].append(log_entry)
                self.training_state["loss_history"].append(avg_loss)
                self.training_state["val_loss_history"].append(val_loss)

                # 更新训练任务状态
                job = training_job_manager.get_job(job_id)
                if job:
                    job["epoch"] = epoch
                    job["loss"] = avg_loss
                    job["val_loss"] = val_loss
                    job["best_val_loss"] = best_val_loss
                    job["progress"] = progress

                # 保存趋势
                if db and epoch % 5 == 0:
                    self._save_train_trend(train_id, model_key, epoch, epochs,
                                          avg_loss, val_loss, best_val_loss, lr,
                                          elapsed, all_pred, all_actual, db)

                await asyncio.sleep(0.01)

                if not self.training_state["is_training"]:
                    self.training_state["message"] = "训练已手动停止"
                    break

            # 注册模型
            custom_name = model_name or None
            self._register_saved_model(model_key, epochs, best_val_loss,
                                        custom_name=custom_name,
                                        schema_id=schema_id, input_dim=input_dim, db=db)
            self.models[model_key]["status"] = "ready"
            self.models[model_key]["trained_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if db:
                self._save_train_log(model_key, epochs, best_val_loss,
                                     time.time() - start_time, "completed", db,
                                     f"schema={schema_id}, dim={input_dim}")

            self.training_state["done"] = True
            self.training_state["message"] = f"训练完成，最优 Val Loss: {best_val_loss:.6f}"

        except Exception as e:
            self.training_state["error"] = str(e)
            self.training_state["message"] = f"训练异常: {e}"
            if db:
                self._save_train_log(model_key, epochs, 0,
                                     time.time() - start_time, "failed", db, str(e))
        finally:
            self.training_state["is_training"] = False
            job = training_job_manager.get_job(job_id)
            if job:
                job["is_training"] = False


# 全局单例
model_manager = ModelManager()
