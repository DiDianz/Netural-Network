# core/model_manager.py
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

# 特征列数（不含 out_moist 和 brandID）
INPUT_DIM = 11


class ModelManager:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.window_size = 60
        self.input_dim = INPUT_DIM

        self.models = {
            "lstm": {
                "name": "LSTM", "display_name": "LSTM + Attention",
                "model": PredictionNet(input_dim=self.input_dim, hidden_dim=128, output_dim=1),
                "status": "idle", "accuracy": None, "trained_at": None,
                "total_predictions": 0,
                "description": "长短期记忆网络 + 注意力机制，适合短序列时序预测"
            },
            "gru": {
                "name": "GRU", "display_name": "GRU",
                "model": GRUNet(input_dim=self.input_dim, hidden_dim=128, output_dim=1),
                "status": "idle", "accuracy": None, "trained_at": None,
                "total_predictions": 0,
                "description": "门控循环单元，比 LSTM 更快更轻，适合资源受限场景"
            },
            "transformer": {
                "name": "Transformer", "display_name": "Transformer",
                "model": TransformerNet(input_dim=self.input_dim, d_model=128, output_dim=1),
                "status": "idle", "accuracy": None, "trained_at": None,
                "total_predictions": 0,
                "description": "Transformer 编码器，并行计算快，擅长长距离依赖"
            }
        }

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
            "brand_predictions": {}  # {brand_id: {"predictions": [...], "actuals": [...]}}
        }

        self._running = False
        self._interval = 1.0
        self.save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'saved_models')
        os.makedirs(self.save_dir, exist_ok=True)
        self._registry_path = os.path.join(self.save_dir, 'registry.json')
        self.saved_models = {}  # {model_id: {model_id, model_key, display_name, filename, epochs, best_val_loss, trained_at, remark}}
        self._load_registry()
        self._load_saved_models()

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

    def _register_saved_model(self, model_key, epochs, best_val_loss, remark=None, custom_name=None):
        """训练完成后注册一个保存的模型版本"""
        model_id = str(uuid.uuid4())[:8]
        filename = f"{model_key}_{model_id}.pth"
        filepath = os.path.join(self.save_dir, filename)
        # 同时保存到 _best.pth 和带ID的文件
        best_path = os.path.join(self.save_dir, f"{model_key}_best.pth")
        if os.path.exists(best_path):
            import shutil
            shutil.copy2(best_path, filepath)

        # 默认命名: 模型类型_日期_轮次_最优损失
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
            "file_size_kb": round(os.path.getsize(filepath) / 1024, 1) if os.path.exists(filepath) else 0
        }
        self.saved_models[model_id] = entry
        self._save_registry()
        return entry

    def rename_saved_model(self, model_id, new_name):
        """重命名一个已保存的模型版本"""
        if model_id not in self.saved_models:
            raise ValueError(f"模型版本不存在: {model_id}")
        if not new_name or not new_name.strip():
            raise ValueError("名称不能为空")
        self.saved_models[model_id]["name"] = new_name.strip()
        self._save_registry()
        return self.saved_models[model_id]

    def list_saved_models(self, model_key=None):
        """列出所有保存的模型版本，可按model_key过滤"""
        result = []
        # 清理不存在的文件
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
        """删除一个保存的模型版本"""
        if model_id not in self.saved_models:
            raise ValueError(f"模型版本不存在: {model_id}")
        entry = self.saved_models[model_id]
        filepath = os.path.join(self.save_dir, entry["filename"])
        if os.path.exists(filepath) and delete_local:
            os.remove(filepath)
        # 始终从注册表中移除
        del self.saved_models[model_id]
        self._save_registry()
        return {"deleted": model_id, "model_key": entry["model_key"], "local_file_deleted": delete_local and os.path.exists(filepath) is False}

    def load_model_weights(self, model_key, model_id):
        """从已保存的版本加载权重到当前模型"""
        if model_id not in self.saved_models:
            raise ValueError(f"模型版本不存在: {model_id}")
        entry = self.saved_models[model_id]
        if entry["model_key"] != model_key:
            raise ValueError(f"模型类型不匹配: 期望 {entry['model_key']}, 实际 {model_key}")
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
                    self.models[key]["model"].load_state_dict(torch.load(path, map_location=self.device))
                    self.models[key]["status"] = "ready"
                    self.models[key]["trained_at"] = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
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
                "device": str(self.device)
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
            "training_model": self.training_state["model_key"]
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
            "uncertainty": round(std_pred, 6), "input_window_size": len(buffer)
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

    # ========== 数据库保存 ==========

    def _save_train_log(self, model_key, epochs, best_val_loss, elapsed, status, db, remark=None):
        try:
            from models.train_log import TrainLog
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
            db.add(record)
            db.commit()
        except Exception as e:
            print(f"保存训练日志失败: {e}")
            db.rollback()

    def _save_train_trend(self, train_id, model_key, epoch, total_epochs,
                          train_loss, val_loss, best_val_loss, lr, elapsed,
                          predictions, actuals, db):
        try:
            from models.train_trend import TrainTrend
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
            db.add(record)
            db.commit()
        except Exception as e:
            print(f"保存趋势失败 epoch {epoch}: {e}")
            db.rollback()

    # ========== 训练（随机数据） ==========

    async def train_model(self, model_key, epochs=50, lr=0.001, batch_size=32, db=None, base_model_id=None, model_name=None):
        if self.training_state["is_training"]:
            raise RuntimeError("已有训练任务在进行中")
        if model_key not in self.models:
            raise ValueError(f"模型不存在: {model_key}")

        # 如果指定了基础模型，先加载权重
        if base_model_id:
            self.load_model_weights(model_key, base_model_id)

        train_id = str(uuid.uuid4())[:8]
        self.training_state = {
            "is_training": True, "model_key": model_key, "epoch": 0, "total_epochs": epochs,
            "loss": 0, "val_loss": 0, "best_val_loss": 0, "progress": 0,
            "lr": lr, "elapsed": 0, "logs": [], "loss_history": [],
            "val_loss_history": [], "done": False, "message": "", "error": "",
            "predictions": [], "actuals": [], "train_id": train_id,
            "brand_predictions": {}, "base_model_id": base_model_id or ""
        }

        model = self.models[model_key]["model"]
        model.train()
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        criterion = nn.MSELoss()
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5)

        X_train, y_train, X_val, y_val = self._generate_training_data()
        best_val_loss = float('inf')
        start_time = time.time()

        try:
            for epoch in range(epochs):
                if not self.training_state["is_training"]:
                    break
                model.train()
                train_loss, num_batches = 0, 0
                perm = torch.randperm(len(X_train))
                for i in range(0, len(X_train), batch_size):
                    idx = perm[i:i + batch_size]
                    bx = X_train[idx].to(self.device)
                    by = y_train[idx].to(self.device)
                    pred = model(bx)
                    loss = criterion(pred, by)
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                    optimizer.step()
                    train_loss += loss.item()
                    num_batches += 1

                avg_train_loss = train_loss / max(num_batches, 1)
                model.eval()
                with torch.no_grad():
                    val_pred = model(X_val.to(self.device))
                    val_loss = criterion(val_pred, y_val.to(self.device)).item()

                scheduler.step(val_loss)
                current_lr = optimizer.param_groups[0]['lr']

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    torch.save(model.state_dict(), os.path.join(self.save_dir, f"{model_key}_best.pth"))

                elapsed = time.time() - start_time
                self.training_state.update({
                    "epoch": epoch + 1, "loss": round(avg_train_loss, 6),
                    "val_loss": round(val_loss, 6), "best_val_loss": round(best_val_loss, 6),
                    "progress": round((epoch + 1) / epochs * 100, 1),
                    "lr": current_lr, "elapsed": round(elapsed, 1)
                })
                self.training_state["loss_history"].append(round(avg_train_loss, 6))
                self.training_state["val_loss_history"].append(round(val_loss, 6))
                self.training_state["logs"].append({
                    "epoch": epoch + 1, "loss": round(avg_train_loss, 6),
                    "val_loss": round(val_loss, 6), "lr": round(current_lr, 8),
                    "time": round(elapsed, 1)
                })
                if len(self.training_state["logs"]) > 500:
                    self.training_state["logs"] = self.training_state["logs"][-500:]

                if db:
                    self._save_train_trend(train_id, model_key, epoch + 1, epochs,
                                           avg_train_loss, val_loss, best_val_loss,
                                           current_lr, elapsed, None, None, db)
                await asyncio.sleep(0.01)

            self.models[model_key]["status"] = "ready"
            self.models[model_key]["trained_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.models[model_key]["accuracy"] = round(1 - best_val_loss, 6) if best_val_loss < 1 else None

            # 注册保存的模型版本
            remark = f"随机数据训练 {epochs}轮"
            if base_model_id:
                remark += f" (基于 {base_model_id})"
            saved = self._register_saved_model(model_key, epochs, best_val_loss, remark, custom_name=model_name)

            self.training_state.update({"is_training": False, "progress": 100, "done": True,
                                        "message": f"训练完成！最优验证损失: {best_val_loss:.6f}",
                                        "saved_model_id": saved["model_id"]})
            if db:
                self._save_train_log(model_key, epochs, best_val_loss, elapsed, "completed", db) # type: ignore

        except Exception as e:
            self.training_state.update({"is_training": False, "done": True,
                                        "error": str(e), "message": f"训练出错: {str(e)}"})
            if db:
                self._save_train_log(model_key, epochs, best_val_loss, time.time() - start_time,
                                     "failed", db, str(e))
            raise

    def _generate_training_data(self):
        num_samples = 500
        X = np.random.randn(num_samples, self.window_size, self.input_dim).astype(np.float32)
        y = np.random.randn(num_samples, 1).astype(np.float32)
        split = int(num_samples * 0.8)
        return torch.tensor(X[:split]), torch.tensor(y[:split]), torch.tensor(X[split:]), torch.tensor(y[split:])

    def stop_training(self):
        self.training_state["is_training"] = False
        self.training_state["message"] = "训练已手动停止"

    def get_training_state(self):
        return dict(self.training_state)

    # ========== 用上传数据训练（按 brandID 分组） ==========

    def _create_model(self, model_key, input_dim):
        if model_key == "lstm":
            return PredictionNet(input_dim=input_dim, hidden_dim=128, output_dim=1)
        elif model_key == "gru":
            return GRUNet(input_dim=input_dim, hidden_dim=128, output_dim=1)
        elif model_key == "transformer":
            return TransformerNet(input_dim=input_dim, d_model=128, output_dim=1)
        else:
            raise ValueError(f"未知模型: {model_key}")


    # core/model_manager.py 中 train_model_with_data 方法完整替换

    async def train_model_with_data(self, model_key, data, job_id, epochs=50, lr=0.001, batch_size=32, db=None):
        """
        用上传数据训练
        data 格式: [特征11列, out_moist] 共12列
        每个 epoch 结束后对全量数据推理，收集预测趋势
        """
        from core.data_manager import training_job_manager

        if model_key not in self.models:
            raise ValueError(f"模型不存在: {model_key}")

        self.training_state["is_training"] = True
        train_id = str(uuid.uuid4())[:8]

        job = training_job_manager.get_job(job_id)
        if not job:
            self.training_state["is_training"] = False
            return

        # ===== 数据校验 =====
        if not data or len(data) == 0:
            msg = "训练数据为空"
            job.update({"is_training": False, "done": True, "error": msg})
            self.training_state.update({"is_training": False, "done": True, "error": msg})
            return

        actual_cols = len(data[0])
        print(f"训练数据: {len(data)} 行, {actual_cols} 列")

        if actual_cols != INPUT_DIM + 1:
            msg = f"数据列数错误: 期望 {INPUT_DIM + 1} 列，实际 {actual_cols} 列"
            job.update({"is_training": False, "done": True, "error": msg})
            self.training_state.update({"is_training": False, "done": True, "error": msg})
            return

        # ===== 构建滑动窗口 =====
        # X[i] = data[i : i+window_size] 的前11列（特征）
        # y[i] = data[i+window_size] 的第12列（out_moist）
        X_all, y_all = [], []
        for i in range(len(data) - self.window_size):
            window = [row[:INPUT_DIM] for row in data[i:i + self.window_size]]
            target = [data[i + self.window_size][INPUT_DIM]]
            X_all.append(window)
            y_all.append(target)

        total = len(X_all)
        if total < 20:
            msg = f"窗口化后样本不足（仅 {total} 个），原始数据需要至少 {self.window_size + 20} 行"
            job.update({"is_training": False, "done": True, "error": msg})
            self.training_state.update({"is_training": False, "done": True, "error": msg})
            return

        split = int(total * 0.8)
        X_tensor = torch.tensor(X_all, dtype=torch.float32)
        y_tensor = torch.tensor(y_all, dtype=torch.float32)
        X_train, y_train = X_tensor[:split], y_tensor[:split]
        X_val, y_val = X_tensor[split:], y_tensor[split:]

        # ===== 趋势图数据：用全部样本 =====
        trend_n = total
        X_trend = X_tensor
        y_trend = y_tensor.numpy().flatten().tolist()
        y_trend_round = [round(v, 6) for v in y_trend]

        # 统计实际值范围，用于调试
        y_min = min(y_trend)
        y_max = max(y_trend)
        y_mean = sum(y_trend) / len(y_trend)
        print(f"训练集: {len(X_train)}, 验证集: {len(X_val)}, 趋势样本: {trend_n}")
        print(f"out_moist 范围: min={y_min:.4f}, max={y_max:.4f}, mean={y_mean:.4f}")

        if y_min == y_max:
            msg = f"目标列 out_moist 全部相同（值={y_min}），无法训练。请检查数据。"
            job.update({"is_training": False, "done": True, "error": msg})
            self.training_state.update({"is_training": False, "done": True, "error": msg})
            return

        # ===== 创建模型 =====
        model = self._create_model(model_key, INPUT_DIM).to(self.device)
        self.models[model_key]["model"] = model
        model.train()

        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        criterion = nn.MSELoss()
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5)

        best_val_loss = float('inf')
        start_time = time.time()

        # ===== 初始状态 =====
        init_state = {
            "is_training": True, "model_key": model_key, "epoch": 0, "total_epochs": epochs,
            "loss": 0, "val_loss": 0, "best_val_loss": 0, "progress": 0,
            "lr": lr, "elapsed": 0, "logs": [], "loss_history": [],
            "val_loss_history": [], "done": False, "message": "", "error": "",
            "predictions": [], "actuals": [], "train_id": train_id,
            "brand_predictions": {},
            "trend_predictions": [],
            "trend_actuals": y_trend_round,
            "trend_epoch": 0
        }
        job.update(init_state)
        self.training_state.update(init_state)

        try:
            for epoch in range(epochs):
                if not job.get("is_training", False):
                    break

                # ===== 训练 =====
                model.train()
                train_loss, num_batches = 0, 0
                perm = torch.randperm(len(X_train))

                for i in range(0, len(X_train), batch_size):
                    idx = perm[i:i + batch_size]
                    bx = X_train[idx].to(self.device)
                    by = y_train[idx].to(self.device)
                    pred = model(bx)
                    loss = criterion(pred, by)
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                    optimizer.step()
                    train_loss += loss.item()
                    num_batches += 1

                avg_train_loss = train_loss / max(num_batches, 1)

                # ===== 验证 =====
                model.eval()
                with torch.no_grad():
                    vp = model(X_val.to(self.device))
                    val_loss = criterion(vp, y_val.to(self.device)).item()

                scheduler.step(val_loss)
                current_lr = optimizer.param_groups[0]['lr']

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    torch.save(model.state_dict(), os.path.join(self.save_dir, f"{model_key}_best.pth"))

                elapsed = time.time() - start_time

                # ===== 趋势预测（全量推理）=====
                model.eval()
                with torch.no_grad():
                    trend_preds = model(X_trend.to(self.device)).cpu().numpy().flatten().tolist()
                trend_preds_round = [round(p, 6) for p in trend_preds]

                # 验证集预测
                with torch.no_grad():
                    sample_n = min(200, len(X_val))
                    sample_preds = model(X_val[:sample_n].to(self.device)).cpu().numpy().flatten().tolist()
                    sample_actuals = y_val[:sample_n].cpu().numpy().flatten().tolist()

                preds_round = [round(p, 6) for p in sample_preds]
                actuals_round = [round(a, 6) for a in sample_actuals]

                # ===== 更新状态 =====
                update_data = {
                    "epoch": epoch + 1, "loss": round(avg_train_loss, 6),
                    "val_loss": round(val_loss, 6), "best_val_loss": round(best_val_loss, 6),
                    "progress": round((epoch + 1) / epochs * 100, 1),
                    "lr": current_lr, "elapsed": round(elapsed, 1),
                    "predictions": preds_round, "actuals": actuals_round,
                    "trend_predictions": trend_preds_round,
                    "trend_actuals": y_trend_round,
                    "trend_epoch": epoch + 1
                }

                job.update(update_data)
                job["loss_history"].append(round(avg_train_loss, 6))
                job["val_loss_history"].append(round(val_loss, 6))
                job["logs"].append({
                    "epoch": epoch + 1, "loss": round(avg_train_loss, 6),
                    "val_loss": round(val_loss, 6), "lr": round(current_lr, 8),
                    "time": round(elapsed, 1)
                })
                if len(job["logs"]) > 500:
                    job["logs"] = job["logs"][-500:]

                self.training_state.update({
                    "epoch": epoch + 1, "total_epochs": epochs,
                    "loss": round(avg_train_loss, 6), "val_loss": round(val_loss, 6),
                    "best_val_loss": round(best_val_loss, 6),
                    "progress": round((epoch + 1) / epochs * 100, 1),
                    "lr": current_lr, "elapsed": round(elapsed, 1),
                    "logs": list(job["logs"]),
                    "loss_history": list(job["loss_history"]),
                    "val_loss_history": list(job["val_loss_history"]),
                    "predictions": preds_round, "actuals": actuals_round,
                    "trend_predictions": trend_preds_round,
                    "trend_actuals": y_trend_round,
                    "trend_epoch": epoch + 1
                })

                if db:
                    self._save_train_trend(train_id, model_key, epoch + 1, epochs,
                                        avg_train_loss, val_loss, best_val_loss,
                                        current_lr, elapsed, preds_round, actuals_round, db)

                await asyncio.sleep(0.01)

            # ===== 完成 =====
            self.models[model_key]["status"] = "ready"
            self.models[model_key]["trained_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.models[model_key]["accuracy"] = round(1 - best_val_loss, 6) if best_val_loss < 1 else None

            job.update({"is_training": False, "progress": 100, "done": True,
                        "message": f"训练完成！最优验证损失: {best_val_loss:.6f}"})
            self.training_state.update({"is_training": False, "progress": 100, "done": True,
                                        "message": f"训练完成！最优验证损失: {best_val_loss:.6f}"})

            if db:
                self._save_train_log(model_key, epochs, best_val_loss, elapsed, "completed", db, # type: ignore
                                    f"样本数={total}, train_id={train_id}")

        except Exception as e:
            job.update({"is_training": False, "done": True,
                        "error": str(e), "message": f"训练出错: {str(e)}"})
            self.training_state.update({"is_training": False, "done": True,
                                        "error": str(e), "message": f"训练出错: {str(e)}"})
            if db:
                self._save_train_log(model_key, epochs, best_val_loss, time.time() - start_time,
                                    "failed", db, str(e))





    # core/model_manager.py 中 train_model_with_data 方法完整替换

    async def train_model_with_data3(self, model_key, data, job_id, epochs=50, lr=0.001, batch_size=32, db=None):
        """
        用上传数据训练
        data 格式: [特征11列, out_moist] 共12列
        每个 epoch 结束后对全量数据推理，收集预测趋势
        """
        from core.data_manager import training_job_manager

        if model_key not in self.models:
            raise ValueError(f"模型不存在: {model_key}")

        self.training_state["is_training"] = True
        train_id = str(uuid.uuid4())[:8]

        job = training_job_manager.get_job(job_id)
        if not job:
            self.training_state["is_training"] = False
            return

        # ===== 数据校验 =====
        if not data or len(data) == 0:
            msg = "训练数据为空"
            job.update({"is_training": False, "done": True, "error": msg})
            self.training_state.update({"is_training": False, "done": True, "error": msg})
            return

        actual_cols = len(data[0])
        print(f"训练数据: {len(data)} 行, {actual_cols} 列")

        if actual_cols != INPUT_DIM + 1:
            msg = f"数据列数错误: 期望 {INPUT_DIM + 1} 列，实际 {actual_cols} 列"
            job.update({"is_training": False, "done": True, "error": msg})
            self.training_state.update({"is_training": False, "done": True, "error": msg})
            return

        # ===== 构建滑动窗口 =====
        X_all, y_all = [], []
        for i in range(len(data) - self.window_size):
            window = [row[:INPUT_DIM] for row in data[i:i + self.window_size]]
            target = [data[i + self.window_size][INPUT_DIM]]
            X_all.append(window)
            y_all.append(target)

        total = len(X_all)
        if total < 20:
            msg = f"窗口化后样本不足（仅 {total} 个），原始数据需要至少 {self.window_size + 20} 行"
            job.update({"is_training": False, "done": True, "error": msg})
            self.training_state.update({"is_training": False, "done": True, "error": msg})
            return

        split = int(total * 0.8)
        X_tensor = torch.tensor(X_all, dtype=torch.float32)
        y_tensor = torch.tensor(y_all, dtype=torch.float32)
        X_train, y_train = X_tensor[:split], y_tensor[:split]
        X_val, y_val = X_tensor[split:], y_tensor[split:]

        # ===== 全量趋势数据（用于预测趋势图）=====
        trend_n = min(300, total)
        X_trend = X_tensor[:trend_n]
        y_trend = y_tensor[:trend_n].numpy().flatten().tolist()
        y_trend_round = [round(v, 6) for v in y_trend]

        print(f"训练集: {len(X_train)}, 验证集: {len(X_val)}, 趋势样本: {trend_n}")

        # ===== 创建模型 =====
        model = self._create_model(model_key, INPUT_DIM).to(self.device)
        self.models[model_key]["model"] = model
        model.train()

        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        criterion = nn.MSELoss()
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5)

        best_val_loss = float('inf')
        start_time = time.time()

        # ===== 初始状态 =====
        init_state = {
            "is_training": True, "model_key": model_key, "epoch": 0, "total_epochs": epochs,
            "loss": 0, "val_loss": 0, "best_val_loss": 0, "progress": 0,
            "lr": lr, "elapsed": 0, "logs": [], "loss_history": [],
            "val_loss_history": [], "done": False, "message": "", "error": "",
            "predictions": [], "actuals": [], "train_id": train_id,
            "brand_predictions": {},
            # ===== 新增：趋势图数据 =====
            "trend_predictions": [],
            "trend_actuals": y_trend_round,
            "trend_epoch": 0
        }
        job.update(init_state)
        self.training_state.update(init_state)

        try:
            for epoch in range(epochs):
                if not job.get("is_training", False):
                    break

                # ===== 训练 =====
                model.train()
                train_loss, num_batches = 0, 0
                perm = torch.randperm(len(X_train))

                for i in range(0, len(X_train), batch_size):
                    idx = perm[i:i + batch_size]
                    bx = X_train[idx].to(self.device)
                    by = y_train[idx].to(self.device)
                    pred = model(bx)
                    loss = criterion(pred, by)
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                    optimizer.step()
                    train_loss += loss.item()
                    num_batches += 1

                avg_train_loss = train_loss / max(num_batches, 1)

                # ===== 验证 =====
                model.eval()
                with torch.no_grad():
                    vp = model(X_val.to(self.device))
                    val_loss = criterion(vp, y_val.to(self.device)).item()

                scheduler.step(val_loss)
                current_lr = optimizer.param_groups[0]['lr']

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    torch.save(model.state_dict(), os.path.join(self.save_dir, f"{model_key}_best.pth"))

                elapsed = time.time() - start_time

                # ===== 全量趋势预测（核心新增）=====
                model.eval()
                with torch.no_grad():
                    trend_preds = model(X_trend.to(self.device)).cpu().numpy().flatten().tolist()
                trend_preds_round = [round(p, 6) for p in trend_preds]

                # 验证集预测（用于 loss 图旁边的对比）
                with torch.no_grad():
                    sample_n = min(200, len(X_val))
                    sample_preds = model(X_val[:sample_n].to(self.device)).cpu().numpy().flatten().tolist()
                    sample_actuals = y_val[:sample_n].cpu().numpy().flatten().tolist()

                preds_round = [round(p, 6) for p in sample_preds]
                actuals_round = [round(a, 6) for a in sample_actuals]

                # ===== 更新状态 =====
                update_data = {
                    "epoch": epoch + 1, "loss": round(avg_train_loss, 6),
                    "val_loss": round(val_loss, 6), "best_val_loss": round(best_val_loss, 6),
                    "progress": round((epoch + 1) / epochs * 100, 1),
                    "lr": current_lr, "elapsed": round(elapsed, 1),
                    "predictions": preds_round, "actuals": actuals_round,
                    "trend_predictions": trend_preds_round,
                    "trend_actuals": y_trend_round,
                    "trend_epoch": epoch + 1
                }

                job.update(update_data)
                job["loss_history"].append(round(avg_train_loss, 6))
                job["val_loss_history"].append(round(val_loss, 6))
                job["logs"].append({
                    "epoch": epoch + 1, "loss": round(avg_train_loss, 6),
                    "val_loss": round(val_loss, 6), "lr": round(current_lr, 8),
                    "time": round(elapsed, 1)
                })
                if len(job["logs"]) > 500:
                    job["logs"] = job["logs"][-500:]

                self.training_state.update({
                    "epoch": epoch + 1, "total_epochs": epochs,
                    "loss": round(avg_train_loss, 6), "val_loss": round(val_loss, 6),
                    "best_val_loss": round(best_val_loss, 6),
                    "progress": round((epoch + 1) / epochs * 100, 1),
                    "lr": current_lr, "elapsed": round(elapsed, 1),
                    "logs": list(job["logs"]),
                    "loss_history": list(job["loss_history"]),
                    "val_loss_history": list(job["val_loss_history"]),
                    "predictions": preds_round, "actuals": actuals_round,
                    "trend_predictions": trend_preds_round,
                    "trend_actuals": y_trend_round,
                    "trend_epoch": epoch + 1
                })

                if db:
                    self._save_train_trend(train_id, model_key, epoch + 1, epochs,
                                        avg_train_loss, val_loss, best_val_loss,
                                        current_lr, elapsed, preds_round, actuals_round, db)

                await asyncio.sleep(0.01)

            # ===== 完成 =====
            self.models[model_key]["status"] = "ready"
            self.models[model_key]["trained_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.models[model_key]["accuracy"] = round(1 - best_val_loss, 6) if best_val_loss < 1 else None

            job.update({"is_training": False, "progress": 100, "done": True,
                        "message": f"训练完成！最优验证损失: {best_val_loss:.6f}"})
            self.training_state.update({"is_training": False, "progress": 100, "done": True,
                                        "message": f"训练完成！最优验证损失: {best_val_loss:.6f}"})

            if db:
                self._save_train_log(model_key, epochs, best_val_loss, elapsed, "completed", db, # type: ignore
                                    f"样本数={total}, train_id={train_id}")

        except Exception as e:
            job.update({"is_training": False, "done": True,
                        "error": str(e), "message": f"训练出错: {str(e)}"})
            self.training_state.update({"is_training": False, "done": True,
                                        "error": str(e), "message": f"训练出错: {str(e)}"})
            if db:
                self._save_train_log(model_key, epochs, best_val_loss, time.time() - start_time,
                                    "failed", db, str(e))


    # core/model_manager.py 中 train_model_with_data 方法的改动
    # 数据现在是 12 列: [特征11列, out_moist]

    async def train_model_with_data2(self, model_key, data, job_id, epochs=50, lr=0.001, batch_size=32, db=None):
        """
        用上传数据训练
        data 格式: [特征11列, out_moist] 共12列（brandID 已在 data_manager 中剥离）
        """
        from core.data_manager import training_job_manager

        if model_key not in self.models:
            raise ValueError(f"模型不存在: {model_key}")

        self.training_state["is_training"] = True
        train_id = str(uuid.uuid4())[:8]

        job = training_job_manager.get_job(job_id)
        if not job:
            self.training_state["is_training"] = False
            return

        # ===== 数据校验 =====
        if not data or len(data) == 0:
            msg = "训练数据为空"
            job.update({"is_training": False, "done": True, "error": msg})
            self.training_state.update({"is_training": False, "done": True, "error": msg})
            return

        actual_cols = len(data[0])
        print(f"训练数据: {len(data)} 行, {actual_cols} 列")

        if actual_cols != INPUT_DIM + 1:
            msg = f"数据列数错误: 期望 {INPUT_DIM + 1} 列（特征{INPUT_DIM} + 目标1），实际 {actual_cols} 列"
            job.update({"is_training": False, "done": True, "error": msg})
            self.training_state.update({"is_training": False, "done": True, "error": msg})
            return

        # ===== 构建滑动窗口 =====
        X_all, y_all = [], []
        for i in range(len(data) - self.window_size):
            window = [row[:INPUT_DIM] for row in data[i:i + self.window_size]]
            target = [data[i + self.window_size][INPUT_DIM]]  # out_moist
            X_all.append(window)
            y_all.append(target)

        total = len(X_all)
        if total < 20:
            msg = f"窗口化后样本不足（仅 {total} 个），原始数据需要至少 {self.window_size + 20} 行"
            job.update({"is_training": False, "done": True, "error": msg})
            self.training_state.update({"is_training": False, "done": True, "error": msg})
            return

        split = int(total * 0.8)
        X_tensor = torch.tensor(X_all, dtype=torch.float32)
        y_tensor = torch.tensor(y_all, dtype=torch.float32)
        X_train, y_train = X_tensor[:split], y_tensor[:split]
        X_val, y_val = X_tensor[split:], y_tensor[split:]

        print(f"训练集: {len(X_train)}, 验证集: {len(X_val)}, 特征维度: {INPUT_DIM}")

        # ===== 创建模型 =====
        model = self._create_model(model_key, INPUT_DIM).to(self.device)
        self.models[model_key]["model"] = model
        model.train()

        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        criterion = nn.MSELoss()
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5)

        best_val_loss = float('inf')
        start_time = time.time()

        job.update({
            "epoch": 0, "loss": 0, "val_loss": 0, "best_val_loss": 0,
            "progress": 0, "lr": lr, "elapsed": 0,
            "loss_history": [], "val_loss_history": [],
            "logs": [], "done": False, "message": "", "error": "",
            "predictions": [], "actuals": [], "train_id": train_id,
            "brand_predictions": {}
        })

        self.training_state.update({
            "is_training": True, "model_key": model_key, "epoch": 0, "total_epochs": epochs,
            "loss": 0, "val_loss": 0, "best_val_loss": 0, "progress": 0,
            "lr": lr, "elapsed": 0, "logs": [], "loss_history": [],
            "val_loss_history": [], "done": False, "message": "", "error": "",
            "predictions": [], "actuals": [], "train_id": train_id,
            "brand_predictions": {}
        })

        try:
            for epoch in range(epochs):
                if not job.get("is_training", False):
                    break

                model.train()
                train_loss, num_batches = 0, 0
                perm = torch.randperm(len(X_train))

                for i in range(0, len(X_train), batch_size):
                    idx = perm[i:i + batch_size]
                    bx = X_train[idx].to(self.device)
                    by = y_train[idx].to(self.device)
                    pred = model(bx)
                    loss = criterion(pred, by)
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                    optimizer.step()
                    train_loss += loss.item()
                    num_batches += 1

                avg_train_loss = train_loss / max(num_batches, 1)
                model.eval()
                with torch.no_grad():
                    vp = model(X_val.to(self.device))
                    val_loss = criterion(vp, y_val.to(self.device)).item()

                scheduler.step(val_loss)
                current_lr = optimizer.param_groups[0]['lr']

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    torch.save(model.state_dict(), os.path.join(self.save_dir, f"{model_key}_best.pth"))

                elapsed = time.time() - start_time

                # 预测值 vs 实际值
                model.eval()
                with torch.no_grad():
                    sample_n = min(200, len(X_val))
                    sample_x = X_val[:sample_n].to(self.device)
                    sample_preds = model(sample_x).cpu().numpy().flatten().tolist()
                    sample_actuals = y_val[:sample_n].cpu().numpy().flatten().tolist()

                preds_round = [round(p, 6) for p in sample_preds]
                actuals_round = [round(a, 6) for a in sample_actuals]

                job.update({
                    "epoch": epoch + 1, "loss": round(avg_train_loss, 6),
                    "val_loss": round(val_loss, 6), "best_val_loss": round(best_val_loss, 6),
                    "progress": round((epoch + 1) / epochs * 100, 1),
                    "lr": current_lr, "elapsed": round(elapsed, 1),
                    "predictions": preds_round, "actuals": actuals_round
                })

                job["loss_history"].append(round(avg_train_loss, 6))
                job["val_loss_history"].append(round(val_loss, 6))
                job["logs"].append({
                    "epoch": epoch + 1, "loss": round(avg_train_loss, 6),
                    "val_loss": round(val_loss, 6), "lr": round(current_lr, 8),
                    "time": round(elapsed, 1)
                })
                if len(job["logs"]) > 500:
                    job["logs"] = job["logs"][-500:]

                self.training_state.update({
                    "epoch": epoch + 1, "total_epochs": epochs,
                    "loss": round(avg_train_loss, 6), "val_loss": round(val_loss, 6),
                    "best_val_loss": round(best_val_loss, 6),
                    "progress": round((epoch + 1) / epochs * 100, 1),
                    "lr": current_lr, "elapsed": round(elapsed, 1),
                    "logs": list(job["logs"]),
                    "loss_history": list(job["loss_history"]),
                    "val_loss_history": list(job["val_loss_history"]),
                    "predictions": preds_round, "actuals": actuals_round
                })

                if db:
                    self._save_train_trend(train_id, model_key, epoch + 1, epochs,
                                        avg_train_loss, val_loss, best_val_loss,
                                        current_lr, elapsed, preds_round, actuals_round, db)

                await asyncio.sleep(0.01)

            self.models[model_key]["status"] = "ready"
            self.models[model_key]["trained_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.models[model_key]["accuracy"] = round(1 - best_val_loss, 6) if best_val_loss < 1 else None

            job.update({"is_training": False, "progress": 100, "done": True,
                        "message": f"训练完成！最优验证损失: {best_val_loss:.6f}"})
            self.training_state.update({"is_training": False, "progress": 100, "done": True,
                                        "message": f"训练完成！最优验证损失: {best_val_loss:.6f}"})

            if db:
                self._save_train_log(model_key, epochs, best_val_loss, elapsed, "completed", db, # type: ignore
                                    f"样本数={total}, train_id={train_id}")

        except Exception as e:
            job.update({"is_training": False, "done": True,
                        "error": str(e), "message": f"训练出错: {str(e)}"})
            self.training_state.update({"is_training": False, "done": True,
                                        "error": str(e), "message": f"训练出错: {str(e)}"})
            if db:
                self._save_train_log(model_key, epochs, best_val_loss, time.time() - start_time,
                                    "failed", db, str(e))



    async def train_model_with_data1(self, model_key, data, job_id, epochs=50, lr=0.001, batch_size=32, db=None, base_model_id=None, model_name=None):
        """
        用上传数据训练，数据格式: [特征11列, out_moist, brandID]
        按 brandID 分组，每组内构建滑动窗口
        """
        from core.data_manager import training_job_manager

        if model_key not in self.models:
            raise ValueError(f"模型不存在: {model_key}")

        # 如果指定了基础模型，先加载权重
        if base_model_id:
            self.load_model_weights(model_key, base_model_id)

        self.training_state["is_training"] = True
        train_id = str(uuid.uuid4())[:8]

        job = training_job_manager.get_job(job_id)
        if not job:
            self.training_state["is_training"] = False
            return

        # ===== 按 brandID 分组 =====
        brand_groups = {}
        for row in data:
            features = row[:INPUT_DIM]          # 前11列 = 特征
            target = row[INPUT_DIM]             # 第12列 = out_moist
            brand = int(row[INPUT_DIM + 1])     # 第13列 = brandID
            if brand not in brand_groups:
                brand_groups[brand] = {"features": [], "targets": []}
            brand_groups[brand]["features"].append(features)
            brand_groups[brand]["targets"].append(target)

        print(f"上传数据: {len(data)} 行, {len(brand_groups)} 个品牌, 特征维度={INPUT_DIM}")

        # ===== 构建滑动窗口训练集 =====
        X_all, y_all = [], []
        brand_windows = {}  # {brand: (X_tensor, y_tensor)}

        for brand, group in brand_groups.items():
            feats = group["features"]
            targs = group["targets"]
            brand_x, brand_y = [], []

            for i in range(len(feats) - self.window_size):
                window = feats[i:i + self.window_size]
                brand_x.append(window)
                brand_y.append([targs[i + self.window_size]])

            if brand_x:
                brand_windows[brand] = (
                    torch.tensor(brand_x, dtype=torch.float32),
                    torch.tensor(brand_y, dtype=torch.float32)
                )
                X_all.extend(brand_x)
                y_all.extend(brand_y)

        total = len(X_all)
        if total < 20:
            msg = f"数据量不足（仅{total}个样本），每个品牌至少需要{self.window_size + 10}行"
            job.update({"is_training": False, "done": True, "error": msg})
            self.training_state.update({"is_training": False, "done": True, "error": msg})
            return

        # 合并所有品牌数据
        X_tensor = torch.tensor(X_all, dtype=torch.float32)
        y_tensor = torch.tensor(y_all, dtype=torch.float32)

        split = int(total * 0.8)
        X_train, y_train = X_tensor[:split], y_tensor[:split]
        X_val, y_val = X_tensor[split:], y_tensor[split:]

        print(f"训练集: {len(X_train)} 样本, 验证集: {len(X_val)} 样本")

        # ===== 创建模型 =====
        model = self._create_model(model_key, INPUT_DIM).to(self.device)
        self.models[model_key]["model"] = model
        model.train()

        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        criterion = nn.MSELoss()
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5)

        best_val_loss = float('inf')
        start_time = time.time()

        job.update({
            "epoch": 0, "loss": 0, "val_loss": 0, "best_val_loss": 0,
            "progress": 0, "lr": lr, "elapsed": 0,
            "loss_history": [], "val_loss_history": [],
            "logs": [], "done": False, "message": "", "error": "",
            "predictions": [], "actuals": [], "train_id": train_id,
            "brand_predictions": {},
            "trend_predictions": [], "trend_actuals": [], "trend_epoch": 0
        })

        self.training_state.update({
            "is_training": True, "model_key": model_key, "epoch": 0, "total_epochs": epochs,
            "loss": 0, "val_loss": 0, "best_val_loss": 0, "progress": 0,
            "lr": lr, "elapsed": 0, "logs": [], "loss_history": [],
            "val_loss_history": [], "done": False, "message": "", "error": "",
            "predictions": [], "actuals": [], "train_id": train_id,
            "brand_predictions": {},
            "trend_predictions": [], "trend_actuals": [], "trend_epoch": 0
        })

        try:
            for epoch in range(epochs):
                if not job.get("is_training", False):
                    break

                model.train()
                train_loss, num_batches = 0, 0
                perm = torch.randperm(len(X_train))

                for i in range(0, len(X_train), batch_size):
                    idx = perm[i:i + batch_size]
                    bx = X_train[idx].to(self.device)
                    by = y_train[idx].to(self.device)
                    pred = model(bx)
                    loss = criterion(pred, by)
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                    optimizer.step()
                    train_loss += loss.item()
                    num_batches += 1

                avg_train_loss = train_loss / max(num_batches, 1)
                model.eval()
                with torch.no_grad():
                    vp = model(X_val.to(self.device))
                    val_loss = criterion(vp, y_val.to(self.device)).item()

                scheduler.step(val_loss)
                current_lr = optimizer.param_groups[0]['lr']

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    torch.save(model.state_dict(), os.path.join(self.save_dir, f"{model_key}_best.pth"))

                elapsed = time.time() - start_time

                # ===== 按品牌收集预测值 vs 实际值 =====
                model.eval()
                brand_preds = {}
                all_preds, all_actuals = [], []

                with torch.no_grad():
                    for brand, (bx_brand, by_brand) in brand_windows.items():
                        sample_n = min(100, len(bx_brand))
                        preds = model(bx_brand[:sample_n].to(self.device)).cpu().numpy().flatten().tolist()
                        actuals = by_brand[:sample_n].cpu().numpy().flatten().tolist()
                        brand_preds[str(brand)] = {
                            "predictions": [round(p, 6) for p in preds],
                            "actuals": [round(a, 6) for a in actuals]
                        }
                        all_preds.extend(preds)
                        all_actuals.extend(actuals)

                preds_round = [round(p, 6) for p in all_preds[:200]]
                actuals_round = [round(a, 6) for a in all_actuals[:200]]
                trend_preds_round = preds_round
                trend_actuals_round = actuals_round

                job.update({
                    "epoch": epoch + 1, "loss": round(avg_train_loss, 6),
                    "val_loss": round(val_loss, 6), "best_val_loss": round(best_val_loss, 6),
                    "progress": round((epoch + 1) / epochs * 100, 1),
                    "lr": current_lr, "elapsed": round(elapsed, 1),
                    "predictions": preds_round, "actuals": actuals_round,
                    "brand_predictions": brand_preds,
                    "trend_predictions": trend_preds_round,
                    "trend_actuals": trend_actuals_round,
                    "trend_epoch": epoch + 1
                })

                job["loss_history"].append(round(avg_train_loss, 6))
                job["val_loss_history"].append(round(val_loss, 6))
                job["logs"].append({
                    "epoch": epoch + 1, "loss": round(avg_train_loss, 6),
                    "val_loss": round(val_loss, 6), "lr": round(current_lr, 8),
                    "time": round(elapsed, 1)
                })
                if len(job["logs"]) > 500:
                    job["logs"] = job["logs"][-500:]

                self.training_state.update({
                    "epoch": epoch + 1, "total_epochs": epochs,
                    "loss": round(avg_train_loss, 6), "val_loss": round(val_loss, 6),
                    "best_val_loss": round(best_val_loss, 6),
                    "progress": round((epoch + 1) / epochs * 100, 1),
                    "lr": current_lr, "elapsed": round(elapsed, 1),
                    "logs": list(job["logs"]),
                    "loss_history": list(job["loss_history"]),
                    "val_loss_history": list(job["val_loss_history"]),
                    "predictions": preds_round, "actuals": actuals_round,
                    "brand_predictions": brand_preds,
                    "trend_predictions": trend_preds_round,
                    "trend_actuals": trend_actuals_round,
                    "trend_epoch": epoch + 1
                })

                if db:
                    self._save_train_trend(train_id, model_key, epoch + 1, epochs,
                                           avg_train_loss, val_loss, best_val_loss,
                                           current_lr, elapsed, preds_round, actuals_round, db)

                await asyncio.sleep(0.01)

            # 完成
            self.models[model_key]["status"] = "ready"
            self.models[model_key]["trained_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.models[model_key]["accuracy"] = round(1 - best_val_loss, 6) if best_val_loss < 1 else None

            # 注册保存的模型版本
            remark = f"品牌数={len(brand_groups)}, 样本数={total}"
            if base_model_id:
                remark += f" (基于 {base_model_id})"
            saved = self._register_saved_model(model_key, epochs, best_val_loss, remark, custom_name=model_name)

            job.update({"is_training": False, "progress": 100, "done": True,
                        "message": f"训练完成！最优验证损失: {best_val_loss:.6f}",
                        "saved_model_id": saved["model_id"]})
            self.training_state.update({"is_training": False, "progress": 100, "done": True,
                                        "message": f"训练完成！最优验证损失: {best_val_loss:.6f}",
                                        "saved_model_id": saved["model_id"]})

            if db:
                self._save_train_log(model_key, epochs, best_val_loss, elapsed, "completed", db, # type: ignore
                                     f"品牌数={len(brand_groups)}, 样本数={total}, train_id={train_id}")

        except Exception as e:
            job.update({"is_training": False, "done": True,
                        "error": str(e), "message": f"训练出错: {str(e)}"})
            self.training_state.update({"is_training": False, "done": True,
                                        "error": str(e), "message": f"训练出错: {str(e)}"})
            if db:
                self._save_train_log(model_key, epochs, best_val_loss, time.time() - start_time,
                                     "failed", db, str(e))

    def predict_with_uploaded_data(self, model_key=None):
        """用上传数据预测，按品牌分组返回"""
        key = model_key or self.current_model_key
        model = self.models[key]["model"]
        model.eval()

        window = data_manager.get_next_window(self.window_size)
        if window is None:
            data_manager.reset_index()
            window = data_manager.get_next_window(self.window_size)
        if window is None:
            return None

        # 只取前11列作为特征
        features = [row[:INPUT_DIM] for row in window]
        input_tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(self.device)

        with torch.no_grad():
            prediction = model(input_tensor).cpu().numpy()[0]

        model.train()
        mc = [model(input_tensor).cpu().numpy()[0] for _ in range(10)]
        model.eval()
        mc = np.array(mc)
        mean_pred = float(mc.mean())
        std_pred = float(mc.std())

        actual = window[-1][INPUT_DIM] if len(window[-1]) > INPUT_DIM else None
        self.models[key]["total_predictions"] += 1

        return {
            "timestamp": time.time(), "model_key": key,
            "model_name": self.models[key]["display_name"],
            "prediction": round(mean_pred, 6),
            "confidence_upper": round(mean_pred + 2 * std_pred, 6),
            "confidence_lower": round(mean_pred - 2 * std_pred, 6),
            "uncertainty": round(std_pred, 6), "input_window_size": len(window),
            "actual_value": actual, "has_actual": actual is not None
        }


model_manager = ModelManager()
