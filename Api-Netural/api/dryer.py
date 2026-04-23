# api/dryer.py
"""
烘丝机出口水分预测 API
提供: 数据分析 / 模型训练 / 预测 / 版本管理 / PLC实时预测
"""
import json
import uuid
import time
import asyncio
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.dryer_model import DryerModel
from schemas.dryer import TrainRequest, PredictRequest, FeatureWeightUpdate

router = APIRouter(prefix="/dryer", tags=["烘丝机预测"])

# ---- 全局状态 ----
FEATURE_NAMES = [
    "proc_steam_vol", "proc_air_temp", "input_moist", "input_moist_SP",
    "moist_remove", "out_moist_SP", "out_temp", "mat_flow_PV",
    "total_mat_flow", "env_temp", "env_moist", "brandID"
]
TARGET_NAME = "out_moist"
ALL_COLUMNS = FEATURE_NAMES + [TARGET_NAME]

# 模型存储路径
MODEL_DIR = Path(__file__).parent.parent / "saved_models" / "dryer"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
REGISTRY_FILE = MODEL_DIR / "registry.json"


def _load_registry() -> dict:
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text())
    return {"versions": {}, "active_version": None}


def _save_registry(reg: dict):
    REGISTRY_FILE.write_text(json.dumps(reg, ensure_ascii=False, indent=2))


def _normalize(data: np.ndarray, stats: dict = None):
    """Z-Score 标准化"""
    if stats is None:
        mean = data.mean(axis=0)
        std = data.std(axis=0) + 1e-8
        stats = {"mean": mean.tolist(), "std": std.tolist()}
    else:
        mean = np.array(stats["mean"])
        std = np.array(stats["std"])
    return (data - mean) / std, stats


def _create_sequences(data: np.ndarray, targets: np.ndarray, window_size: int):
    """创建滑动窗口序列"""
    X, y = [], []
    for i in range(len(data) - window_size):
        X.append(data[i:i + window_size])
        y.append(targets[i + window_size])
    return np.array(X), np.array(y)


# ========== 1. 数据上传与分析 ==========

@router.post("/upload")
async def upload_data(file: UploadFile = File(...)):
    """上传训练数据 (Excel/CSV)"""
    import pandas as pd
    import io

    content = await file.read()
    filename = file.filename.lower()

    try:
        if filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(content))
        elif filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        else:
            raise HTTPException(400, "仅支持 .xlsx / .xls / .csv 格式")
    except Exception as e:
        raise HTTPException(400, f"文件解析失败: {str(e)}")

    # 列名映射 (支持中文或英文)
    col_map = {
        "加工蒸汽量": "proc_steam_vol", "蒸汽量": "proc_steam_vol",
        "加工热风温度": "proc_air_temp", "热风温度": "proc_air_temp",
        "入口含水率": "input_moist",
        "入口含水率设定值": "input_moist_SP", "入口水分设定": "input_moist_SP",
        "湿基去除量": "moist_remove",
        "出口含水率": "out_moist", "出口水分": "out_moist",
        "出口含水率设定值": "out_moist_SP", "出口水分设定": "out_moist_SP",
        "出口温度": "out_temp",
        "物料流量": "mat_flow_PV",
        "累计物料流量": "total_mat_flow",
        "环境温度": "env_temp",
        "环境湿度": "env_moist",
        "牌号ID": "brandID", "牌号": "brandID",
    }
    df = df.rename(columns=col_map)

    # 检查必需列
    required = FEATURE_NAMES + [TARGET_NAME]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise HTTPException(400, f"缺少必需列: {missing}")

    df = df[required].dropna()

    if len(df) < 20:
        raise HTTPException(400, f"数据量不足: {len(df)} 行 (最少20行)")

    # 保存到内存 (持久化到临时文件)
    data_file = MODEL_DIR / "training_data.npy"
    np.save(data_file, df.values.astype(np.float32))

    # 数据统计
    stats = {}
    for col in required:
        vals = df[col].values.astype(np.float64)
        def sf(v):
            f = float(v)
            return 0.0 if (np.isnan(f) or np.isinf(f)) else round(f, 4)
        stats[col] = {
            "mean": sf(vals.mean()),
            "std": sf(vals.std()),
            "min": sf(vals.min()),
            "max": sf(vals.max()),
            "count": int(len(vals))
        }

    return {
        "code": 200,
        "msg": f"上传成功: {len(df)} 行数据",
        "data": {
            "rows": len(df),
            "columns": list(df.columns),
            "stats": stats
        }
    }


@router.get("/debug")
async def debug_info():
    """调试: 检查数据文件和模型目录状态"""
    data_file = MODEL_DIR / "training_data.npy"
    info = {
        "model_dir": str(MODEL_DIR),
        "model_dir_exists": MODEL_DIR.exists(),
        "data_file": str(data_file),
        "data_file_exists": data_file.exists(),
    }
    if data_file.exists():
        try:
            data = np.load(data_file, allow_pickle=True)
            info["data_shape"] = list(data.shape)
            info["data_dtype"] = str(data.dtype)
            info["data_file_size"] = data_file.stat().st_size
        except Exception as e:
            info["load_error"] = str(e)

    registry = _load_registry()
    info["registry"] = registry
    info["saved_models"] = [f.name for f in MODEL_DIR.glob("*.pth")]

    return {"code": 200, "data": info}


@router.get("/analyze")
async def analyze_data():
    """数据分析 — 统计 + 相关性 + 分布"""
    data_file = MODEL_DIR / "training_data.npy"
    if not data_file.exists():
        raise HTTPException(400, "请先上传训练数据")

    try:
        data = np.load(data_file, allow_pickle=True)
    except Exception as e:
        raise HTTPException(500, f"加载数据文件失败: {str(e)}")

    if data.ndim != 2 or data.shape[1] != len(FEATURE_NAMES) + 1:
        raise HTTPException(400, f"数据维度异常: {data.shape}，期望 (N, {len(FEATURE_NAMES) + 1})")

    def safe_float(v):
        """将 numpy 值转为安全的 Python float (处理 NaN/Inf)"""
        f = float(v)
        if np.isnan(f) or np.isinf(f):
            return 0.0
        return f

    def safe_round(v, n=4):
        return round(safe_float(v), n)

    n_features = len(FEATURE_NAMES)
    features = data[:, :n_features].astype(np.float64)
    target = data[:, n_features].astype(np.float64)

    # 1. 基本统计
    stats = {}
    all_names = FEATURE_NAMES + [TARGET_NAME]
    for i, name in enumerate(all_names):
        col = data[:, i].astype(np.float64)
        stats[name] = {
            "mean": safe_round(col.mean()),
            "std": safe_round(col.std()),
            "min": safe_round(col.min()),
            "max": safe_round(col.max()),
            "median": safe_round(np.median(col))
        }

    # 2. 相关性矩阵 (与 target 的相关性)
    correlations = {}
    target_std = target.std()
    for i, name in enumerate(FEATURE_NAMES):
        feat_std = features[:, i].std()
        if feat_std < 1e-10 or target_std < 1e-10:
            correlations[name] = 0.0
        else:
            corr = np.corrcoef(features[:, i], target)[0, 1]
            correlations[name] = safe_round(corr)

    # 3. 时间序列趋势 (target 随时间变化)
    trend = [safe_float(v) for v in target]

    # 4. 特征重要性 (基于方差贡献)
    variances = features.var(axis=0)
    var_sum = variances.sum()
    if var_sum < 1e-10:
        importance = {name: 0.0 for name in FEATURE_NAMES}
    else:
        importance = {name: safe_round(v / var_sum) for name, v in zip(FEATURE_NAMES, variances)}

    # 5. 目标值分布 (直方图)
    hist, bin_edges = np.histogram(target, bins=20)
    distribution = {
        "counts": [int(v) for v in hist],
        "bins": [safe_round(float(e), 2) for e in bin_edges]
    }

    return {
        "code": 200,
        "data": {
            "stats": stats,
            "correlations": correlations,
            "trend": trend,
            "importance": importance,
            "distribution": distribution,
            "total_rows": int(len(data))
        }
    }


# ========== 2. 模型训练 ==========

@router.get("/train")
async def train_model(
    epochs: int = Query(100, ge=10, le=500),
    batch_size: int = Query(32, ge=8, le=128),
    learning_rate: float = Query(0.001, gt=0, le=0.1),
    window_size: int = Query(10, ge=3, le=50),
    hidden_dim: int = Query(128, ge=32, le=512),
    num_layers: int = Query(2, ge=1, le=4),
    dropout: float = Query(0.2, ge=0, le=0.5),
    test_ratio: float = Query(0.2, ge=0.1, le=0.4),
    feature_weights: str = Query("", description="逗号分隔的12个特征权重"),
    target_range: str = Query("14.0,15.0", description="目标水分范围"),
    base_version: str = Query("", description="基于已有模型继续训练(微调)")
):
    """训练模型 — SSE 流式输出训练进度"""

    async def event_generator():
        try:
            # ---- 解析参数 ----
            parsed_fw = [float(w.strip()) for w in feature_weights.split(',') if w.strip()] if feature_weights else None
            parsed_tr = [float(x.strip()) for x in target_range.split(',')] if target_range else [14.0, 15.0]

            data_file = MODEL_DIR / "training_data.npy"
            if not data_file.exists():
                yield f"data: {json.dumps({'type': 'error', 'msg': '请先上传训练数据'})}\n\n"
                return

            data = np.load(data_file, allow_pickle=True)
            n_features = len(FEATURE_NAMES)
            features = data[:, :n_features].astype(np.float32)
            target = data[:, n_features].astype(np.float32)

            # 标准化
            features_norm, feat_stats = _normalize(features)
            target_norm, tgt_stats = _normalize(target.reshape(-1, 1))

            # 创建序列
            X, y = _create_sequences(features_norm, target_norm.squeeze(), window_size)

            if len(X) < 10:
                yield f"data: {json.dumps({'type': 'error', 'msg': f'数据量不足: 仅 {len(X)} 个序列，请减小窗口大小或增加数据量'})}\n\n"
                return

            # 训练/测试划分
            split = int(len(X) * (1 - test_ratio))
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]

            # 转 Tensor
            train_ds = TensorDataset(
                torch.tensor(X_train), torch.tensor(y_train).unsqueeze(-1)
            )
            test_ds = TensorDataset(
                torch.tensor(X_test), torch.tensor(y_test).unsqueeze(-1)
            )
            train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
            test_loader = DataLoader(test_ds, batch_size=batch_size)

            # 构建模型
            model = DryerModel(
                input_dim=n_features,
                hidden_dim=hidden_dim,
                num_layers=num_layers,
                dropout=dropout
            )

            # 如果指定了基础模型，加载已有权重继续训练
            if base_version:
                base_path = MODEL_DIR / f"{base_version}.pth"
                if base_path.exists():
                    checkpoint = torch.load(base_path, map_location="cpu", weights_only=False)
                    try:
                        model.load_state_dict(checkpoint['model_state'], strict=False)
                        yield f"data: {json.dumps({'type': 'progress', 'epoch': 0, 'total_epochs': epochs, 'train_loss': 0, 'test_loss': 0, 'r2': 0, 'lr': learning_rate, 'best_loss': 0, 'feature_weights': model.get_feature_weights(), 'msg': f'已加载基础模型: {base_version}，继续训练中...'}, ensure_ascii=False)}\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'type': 'progress', 'epoch': 0, 'total_epochs': epochs, 'train_loss': 0, 'test_loss': 0, 'r2': 0, 'lr': learning_rate, 'best_loss': 0, 'feature_weights': [1.0]*n_features, 'msg': f'基础模型权重不匹配({str(e)})，从头训练'}, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'progress', 'epoch': 0, 'total_epochs': epochs, 'train_loss': 0, 'test_loss': 0, 'r2': 0, 'lr': learning_rate, 'best_loss': 0, 'feature_weights': [1.0]*n_features, 'msg': f'基础模型 {base_version} 不存在，从头训练'}, ensure_ascii=False)}\n\n"

            # 设置初始特征权重
            if parsed_fw and len(parsed_fw) == n_features:
                with torch.no_grad():
                    model.feature_weights.data = torch.tensor(
                        [max(0.01, min(0.99, w)) for w in parsed_fw],
                        dtype=torch.float32
                    )
                    model.feature_weights.data = torch.log(
                        model.feature_weights.data / (1 - model.feature_weights.data)
                    )

            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model = model.to(device)

            optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
            mse_loss = nn.MSELoss()

            # 版本号
            version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

            best_loss = float('inf')
            train_losses = []
            test_losses = []

            for epoch in range(1, epochs + 1):
                # ---- Train ----
                model.train()
                train_loss = 0
                for xb, yb in train_loader:
                    xb, yb = xb.to(device), yb.to(device)
                    pred, unc = model(xb)
                    loss = mse_loss(pred, yb) + 0.1 * torch.mean(unc)
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                    optimizer.step()
                    train_loss += loss.item() * len(xb)
                train_loss /= len(train_ds)
                train_losses.append(train_loss)

                # ---- Eval ----
                model.eval()
                test_loss = 0
                preds_all, targets_all = [], []
                with torch.no_grad():
                    for xb, yb in test_loader:
                        xb, yb = xb.to(device), yb.to(device)
                        pred, unc = model(xb)
                        test_loss += mse_loss(pred, yb).item() * len(xb)
                        preds_all.append(pred.cpu().numpy())
                        targets_all.append(yb.cpu().numpy())
                test_loss /= len(test_ds)
                test_losses.append(test_loss)

                scheduler.step()

                # R² 计算
                preds_np = np.concatenate(preds_all).flatten()
                targets_np = np.concatenate(targets_all).flatten()
                ss_res = np.sum((targets_np - preds_np) ** 2)
                ss_tot = np.sum((targets_np - targets_np.mean()) ** 2)
                r2 = float(1 - ss_res / (ss_tot + 1e-8))

                # 保存最优
                if test_loss < best_loss:
                    best_loss = test_loss
                    save_path = MODEL_DIR / f"{version}.pth"
                    torch.save({
                        'model_state': model.state_dict(),
                        'config': {
                            'input_dim': n_features,
                            'hidden_dim': hidden_dim,
                            'num_layers': num_layers,
                            'dropout': dropout,
                            'window_size': window_size
                        },
                        'normalize_stats': {'features': feat_stats, 'target': tgt_stats},
                        'feature_names': FEATURE_NAMES,
                        'target_name': TARGET_NAME,
                        'metrics': {
                            'best_test_loss': best_loss,
                            'r2': r2,
                            'epoch': epoch
                        }
                    }, save_path)

                # 进度推送
                progress = {
                    "type": "progress",
                    "epoch": epoch,
                    "total_epochs": epochs,
                    "train_loss": round(train_loss, 6),
                    "test_loss": round(test_loss, 6),
                    "r2": round(r2, 4),
                    "lr": round(scheduler.get_last_lr()[0], 7),
                    "best_loss": round(best_loss, 6),
                    "feature_weights": model.get_feature_weights()
                }
                yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"

            # 训练完成 — 注册版本
            registry = _load_registry()
            registry["versions"][version] = {
                "created_at": datetime.now().isoformat(),
                "metrics": {
                    "best_test_loss": round(best_loss, 6),
                    "final_r2": round(r2, 4),
                    "epochs": epochs
                },
                "config": {
                    "hidden_dim": hidden_dim,
                    "num_layers": num_layers,
                    "dropout": dropout,
                    "window_size": window_size,
                    "learning_rate": learning_rate,
                    "batch_size": batch_size,
                    "target_range": parsed_tr
                },
                "feature_weights": model.get_feature_weights(),
                "normalize_stats": {'features': feat_stats, 'target': tgt_stats}
            }
            registry["active_version"] = version
            _save_registry(registry)

            done = {
                "type": "done",
                "version": version,
                "best_test_loss": round(best_loss, 6),
                "final_r2": round(r2, 4),
                "train_losses": [round(l, 6) for l in train_losses],
                "test_losses": [round(l, 6) for l in test_losses],
                "feature_weights": model.get_feature_weights(),
                "msg": f"训练完成! 版本: {version}, R²={round(r2, 4)}"
            }
            yield f"data: {json.dumps(done, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"训练错误: {tb}")
            yield f"data: {json.dumps({'type': 'error', 'msg': f'训练失败: {str(e)}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


# ========== 3. 预测 ==========

@router.post("/predict")
async def predict(req: PredictRequest):
    """使用训练好的模型预测出口水分"""
    registry = _load_registry()
    version = req.model_version or registry.get("active_version")
    if not version or version not in registry["versions"]:
        raise HTTPException(400, "没有可用的训练模型，请先训练")

    model_path = MODEL_DIR / f"{version}.pth"
    if not model_path.exists():
        raise HTTPException(400, f"模型文件不存在: {version}")

    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    config = checkpoint['config']
    norm_stats = checkpoint['normalize_stats']

    model = DryerModel(
        input_dim=config['input_dim'],
        hidden_dim=config['hidden_dim'],
        num_layers=config['num_layers'],
        dropout=config['dropout']
    )
    model.load_state_dict(checkpoint['model_state'])
    model.eval()

    # 预处理
    input_data = np.array(req.data, dtype=np.float32)
    if input_data.shape[1] != config['input_dim']:
        raise HTTPException(400, f"输入维度不匹配: 期望 {config['input_dim']}, 实际 {input_data.shape[1]}")

    features_norm, _ = _normalize(input_data, norm_stats['features'])
    input_tensor = torch.tensor(features_norm).unsqueeze(0)

    with torch.no_grad():
        pred_norm, unc_norm = model(input_tensor)

    # 反标准化
    tgt_mean = np.array(norm_stats['target']['mean'])
    tgt_std = np.array(norm_stats['target']['std'])
    pred_val = float(pred_norm.numpy()[0, 0] * tgt_std[0] + tgt_mean[0])
    unc_val = float(unc_norm.numpy()[0, 0] * tgt_std[0])

    return {
        "code": 200,
        "data": {
            "prediction": round(pred_val, 4),
            "uncertainty": round(unc_val, 4),
            "confidence_upper": round(pred_val + 2 * unc_val, 4),
            "confidence_lower": round(pred_val - 2 * unc_val, 4),
            "version": version,
            "in_target": 14.0 <= pred_val <= 15.0
        }
    }


# ========== 4. 特征权重管理 ==========

@router.get("/weights")
async def get_weights():
    """获取当前模型的特征权重"""
    registry = _load_registry()
    version = registry.get("active_version")
    if not version or version not in registry["versions"]:
        return {"code": 200, "data": {"weights": {name: 1.0 for name in FEATURE_NAMES}}}

    weights = registry["versions"][version].get("feature_weights", [1.0] * len(FEATURE_NAMES))
    return {
        "code": 200,
        "data": {
            "weights": {name: round(w, 4) for name, w in zip(FEATURE_NAMES, weights)},
            "version": version
        }
    }


@router.post("/weights")
async def update_weights(req: FeatureWeightUpdate):
    """更新特征权重 (将在下次训练时生效)"""
    registry = _load_registry()
    version = registry.get("active_version")

    if version and version in registry["versions"]:
        registry["versions"][version]["feature_weights"] = req.weights
        _save_registry(registry)

    return {
        "code": 200,
        "msg": "特征权重已更新",
        "data": {name: round(w, 4) for name, w in zip(FEATURE_NAMES, req.weights)}
    }


# ========== 5. 模型版本管理 ==========

@router.get("/versions")
async def list_versions():
    """列出所有模型版本"""
    registry = _load_registry()
    versions = []
    for v, info in registry.get("versions", {}).items():
        versions.append({
            "version": v,
            "created_at": info.get("created_at", ""),
            "metrics": info.get("metrics", {}),
            "config": info.get("config", {}),
            "feature_weights": info.get("feature_weights", []),
            "is_active": v == registry.get("active_version")
        })
    versions.sort(key=lambda x: x["created_at"], reverse=True)
    return {"code": 200, "data": versions}


@router.post("/versions/{version}/activate")
async def activate_version(version: str):
    """激活指定版本"""
    registry = _load_registry()
    if version not in registry.get("versions", {}):
        raise HTTPException(404, f"版本不存在: {version}")
    registry["active_version"] = version
    _save_registry(registry)
    return {"code": 200, "msg": f"已激活版本: {version}"}


@router.delete("/versions/{version}")
async def delete_version(version: str):
    """删除指定版本"""
    registry = _load_registry()
    if version not in registry.get("versions", {}):
        raise HTTPException(404, f"版本不存在: {version}")
    del registry["versions"][version]
    if registry["active_version"] == version:
        registry["active_version"] = next(iter(registry["versions"]), None)
    _save_registry(registry)
    model_path = MODEL_DIR / f"{version}.pth"
    if model_path.exists():
        model_path.unlink()
    return {"code": 200, "msg": f"已删除版本: {version}"}


# ========== 6. PLC 实时预测 (SSE) ==========

@router.get("/plc-stream")
async def plc_predict_stream(
    device_id: int = Query(..., description="PLC设备ID"),
    point_ids: str = Query("", description="逗号分隔的点位ID"),
    interval: float = Query(1.0, ge=0.1, le=30.0),
    model_version: str = Query("", description="指定模型版本"),
    db: Session = Depends(get_db)
):
    """PLC实时数据 → 模型预测 → SSE推送"""
    from core.plc_service import plc_manager
    from core.plc_simulator import plc_simulator
    from models.plc_device import PlcDevice
    from models.plc_db_point import PlcDbPoint

    # 加载模型
    registry = _load_registry()
    version = model_version or registry.get("active_version")
    if not version or version not in registry.get("versions", {}):
        raise HTTPException(400, "没有可用的训练模型")

    model_path = MODEL_DIR / f"{version}.pth"
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    config = checkpoint['config']
    norm_stats = checkpoint['normalize_stats']

    model = DryerModel(**{k: config[k] for k in ['input_dim', 'hidden_dim', 'num_layers', 'dropout']})
    model.load_state_dict(checkpoint['model_state'])
    model.eval()

    # 校验设备
    device = db.query(PlcDevice).filter(PlcDevice.id == device_id).first()
    if not device:
        raise HTTPException(404, "PLC设备不存在")

    is_simulated = plc_simulator.is_simulating(device_id)
    is_connected = plc_manager.is_connected(device_id)
    if not is_simulated and not is_connected:
        raise HTTPException(400, "PLC设备未连接或未启动模拟")

    # 获取点位
    query = db.query(PlcDbPoint).filter(
        PlcDbPoint.device_id == device_id, PlcDbPoint.is_active == 1
    )
    if point_ids:
        pids = [int(x.strip()) for x in point_ids.split(",") if x.strip()]
        query = query.filter(PlcDbPoint.id.in_(pids))
    points = query.all()
    if not points:
        raise HTTPException(400, "没有可用的启用点位")

    point_list = [{
        "id": p.id, "point_name": p.point_name,
        "db_number": p.db_number, "start_address": p.start_address,
        "data_type": p.data_type, "bit_index": p.bit_index
    } for p in points]

    window_size = config['window_size']
    input_dim = config['input_dim']

    # 滑动窗口缓冲
    buffer = []
    for _ in range(window_size):
        buffer.append(list(np.random.randn(input_dim).astype(float)))

    async def event_generator():
        tick = 0
        try:
            while True:
                tick += 1
                timestamp = time.time()

                # 读取 PLC 数据
                if is_simulated:
                    plc_result = plc_simulator.read_multiple(device_id, point_list)
                else:
                    plc_result = plc_manager.read_multiple(device_id, point_list)

                if not plc_result["success"]:
                    yield f"data: {json.dumps({'error': plc_result['msg'], 'tick': tick})}\n\n"
                    await asyncio.sleep(interval)
                    continue

                # 转特征向量
                values = []
                for item in plc_result["data"]:
                    val = float(item["value"]) if item["success"] and item["value"] is not None else 0.0
                    values.append(val)
                padded = values[:input_dim]
                while len(padded) < input_dim:
                    padded.append(0.0)
                buffer.append(padded)
                while len(buffer) > window_size:
                    buffer.pop(0)

                # 推理
                try:
                    input_arr = np.array(buffer, dtype=np.float32)
                    input_norm, _ = _normalize(input_arr, norm_stats['features'])
                    input_tensor = torch.tensor(input_norm).unsqueeze(0)

                    with torch.no_grad():
                        pred_norm, unc_norm = model(input_tensor)

                    tgt_mean = norm_stats['target']['mean'][0] if isinstance(norm_stats['target']['mean'], list) else norm_stats['target']['mean']
                    tgt_std = norm_stats['target']['std'][0] if isinstance(norm_stats['target']['std'], list) else norm_stats['target']['std']

                    pred_val = float(pred_norm.numpy()[0, 0]) * tgt_std + tgt_mean
                    unc_val = float(unc_norm.numpy()[0, 0]) * tgt_std

                    payload = {
                        "timestamp": timestamp,
                        "tick": tick,
                        "prediction": round(pred_val, 4),
                        "uncertainty": round(unc_val, 4),
                        "confidence_upper": round(pred_val + 2 * unc_val, 4),
                        "confidence_lower": round(pred_val - 2 * unc_val, 4),
                        "in_target": 14.0 <= pred_val <= 15.0,
                        "feature_weights": model.get_feature_weights(),
                        "plc_points": plc_result["data"],
                        "simulated": is_simulated
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e), 'tick': tick})}\n\n"

                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


# ========== 7. 评估报告 ==========

@router.get("/evaluate")
async def evaluate_model(model_version: str = Query("")):
    """评估模型 — 在完整数据集上计算指标"""
    registry = _load_registry()
    version = model_version or registry.get("active_version")
    if not version or version not in registry.get("versions", {}):
        raise HTTPException(400, "没有可用的训练模型")

    data_file = MODEL_DIR / "training_data.npy"
    if not data_file.exists():
        raise HTTPException(400, "没有训练数据")

    data = np.load(data_file, allow_pickle=True)
    n_features = len(FEATURE_NAMES)
    features = data[:, :n_features].astype(np.float32)
    target = data[:, n_features].astype(np.float32)

    model_path = MODEL_DIR / f"{version}.pth"
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    config = checkpoint['config']
    norm_stats = checkpoint['normalize_stats']

    model = DryerModel(**{k: config[k] for k in ['input_dim', 'hidden_dim', 'num_layers', 'dropout']})
    model.load_state_dict(checkpoint['model_state'])
    model.eval()

    # 标准化
    features_norm, _ = _normalize(features, norm_stats['features'])
    target_norm, _ = _normalize(target.reshape(-1, 1), norm_stats['target'])

    # 创建序列
    X, y = _create_sequences(features_norm, target_norm.squeeze(), config['window_size'])

    # 预测
    preds, uncs = [], []
    with torch.no_grad():
        for i in range(len(X)):
            t = torch.tensor(X[i:i+1])
            p, u = model(t)
            preds.append(float(p.numpy()[0, 0]))
            uncs.append(float(u.numpy()[0, 0]))

    preds = np.array(preds)
    uncs = np.array(uncs)
    targets = y

    # 反标准化
    tgt_mean = norm_stats['target']['mean'][0] if isinstance(norm_stats['target']['mean'], list) else norm_stats['target']['mean']
    tgt_std = norm_stats['target']['std'][0] if isinstance(norm_stats['target']['std'], list) else norm_stats['target']['std']
    preds_real = preds * tgt_std + tgt_mean
    targets_real = targets * tgt_std + tgt_mean
    uncs_real = uncs * tgt_std

    # 指标
    mae = float(np.mean(np.abs(preds_real - targets_real)))
    rmse = float(np.sqrt(np.mean((preds_real - targets_real) ** 2)))
    ss_res = np.sum((targets_real - preds_real) ** 2)
    ss_tot = np.sum((targets_real - targets_real.mean()) ** 2)
    r2 = float(1 - ss_res / (ss_tot + 1e-8))
    mape = float(np.mean(np.abs((targets_real - preds_real) / (targets_real + 1e-8))) * 100)

    # 目标范围命中率
    in_target = float(np.mean((preds_real >= 14.0) & (preds_real <= 15.0)) * 100)

    return {
        "code": 200,
        "data": {
            "version": version,
            "metrics": {
                "mae": round(mae, 4),
                "rmse": round(rmse, 4),
                "r2": round(r2, 4),
                "mape": round(mape, 2),
                "in_target_rate": round(in_target, 2)
            },
            "predictions": preds_real.tolist()[-100:],
            "actuals": targets_real.tolist()[-100:],
            "uncertainties": uncs_real.tolist()[-100:],
            "feature_weights": checkpoint.get('feature_weights', [1.0] * n_features),
            "config": config
        }
    }
