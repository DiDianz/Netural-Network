"""
一次性同步脚本：将 saved_models/ 下所有 *_best.pth 文件注册到 registry.json 和数据库
用法: cd Api-Netural && python sync_best_models.py
"""
import os
import json
import uuid
from pathlib import Path
from datetime import datetime

SAVE_DIR = Path(__file__).parent / "saved_models"
REGISTRY_PATH = SAVE_DIR / "registry.json"

MODEL_META = {
    "lstm_best.pth": {
        "model_key": "lstm",
        "display_name": "LSTM + Attention",
        "input_dim": 11,
    },
    "gru_best.pth": {
        "model_key": "gru",
        "display_name": "GRU",
        "input_dim": 11,
    },
    "transformer_best.pth": {
        "model_key": "transformer",
        "display_name": "Transformer",
        "input_dim": 11,
    },
}


def sync_registry():
    """将 *_best.pth 注册到 registry.json"""
    if REGISTRY_PATH.exists():
        registry = json.loads(REGISTRY_PATH.read_text())
    else:
        registry = {}

    added = 0
    for fname, meta in MODEL_META.items():
        fpath = SAVE_DIR / fname
        if not fpath.exists():
            print(f"  跳过 {fname}: 文件不存在")
            continue

        model_key = meta["model_key"]
        # 检查是否已有该类型的 _best 条目
        best_key = f"{model_key}_best"
        already_registered = any(
            v.get("filename") == fname or v.get("model_id") == best_key
            for v in registry.values()
        )
        if already_registered:
            print(f"  跳过 {fname}: 已在 registry 中")
            continue

        model_id = best_key
        file_size_kb = round(fpath.stat().st_size / 1024, 1)
        mtime = datetime.fromtimestamp(fpath.stat().st_mtime)
        trained_at = mtime.strftime("%Y-%m-%d %H:%M:%S")
        date_str = mtime.strftime("%Y%m%d")

        entry = {
            "model_id": model_id,
            "model_key": model_key,
            "display_name": meta["display_name"],
            "name": f"{meta['display_name']}_{date_str}_best",
            "filename": fname,
            "epochs": 0,
            "best_val_loss": 0,
            "trained_at": trained_at,
            "remark": "从 best 权重文件同步",
            "file_size_kb": file_size_kb,
            "schema_id": "default",
            "input_dim": meta["input_dim"],
        }
        registry[model_id] = entry
        added += 1
        print(f"  已注册 {fname} → model_id={model_id}")

    if added > 0:
        REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2))
        print(f"\nregistry.json 已更新，共 {len(registry)} 个条目")
    else:
        print("\nregistry.json 无需更新")

    return registry


def sync_database(registry):
    """将 registry 中的条目同步到数据库"""
    try:
        from core.database import SessionLocal, Base, engine
        from models.saved_model import SavedModel
    except ImportError as e:
        print(f"\n无法导入数据库模块: {e}")
        print("请确保已安装依赖: pip install -r requirements.txt")
        return

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    added = 0
    try:
        for model_id, info in registry.items():
            existing = db.query(SavedModel).filter(SavedModel.model_id == model_id).first()
            if existing:
                continue

            trained_at = None
            if info.get("trained_at"):
                try:
                    trained_at = datetime.strptime(info["trained_at"], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    trained_at = datetime.now()

            record = SavedModel(
                model_id=model_id,
                model_type="general",
                model_key=info.get("model_key", ""),
                display_name=info.get("display_name", ""),
                name=info.get("name", ""),
                filename=info.get("filename", ""),
                epochs=info.get("epochs", 0),
                best_val_loss=info.get("best_val_loss", 0),
                trained_at=trained_at,
                remark=info.get("remark", ""),
                file_size_kb=info.get("file_size_kb", 0),
                schema_id=info.get("schema_id", "default"),
                input_dim=info.get("input_dim", 0),
            )
            db.add(record)
            added += 1
            print(f"  已写入数据库: {model_id} ({info.get('model_key')})")

        if added > 0:
            db.commit()
            print(f"\n数据库同步完成，新增 {added} 条记录")
        else:
            print("\n数据库无需更新")
    except Exception as e:
        db.rollback()
        print(f"\n数据库同步失败: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("同步 saved_models/_best.pth → registry.json + 数据库")
    print("=" * 50)

    print("\n[1/2] 同步 registry.json ...")
    registry = sync_registry()

    print("\n[2/2] 同步数据库 ...")
    sync_database(registry)

    print("\n完成!")
