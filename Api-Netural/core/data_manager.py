# core/data_manager.py
from typing import Dict, List, Optional
import logging

logger = logging.getLogger("data_manager")

INPUT_DIM = 11


class UploadedDataManager:
    """管理用户上传的训练数据，支持按 brandID 分组"""

    def __init__(self):
        self.files: Dict[str, dict] = {}
        self.data_index = 0

    def add_file(self, file_id: str, data: List[list], metadata: dict):
        self.files[file_id] = {"data": data, "metadata": metadata}

    def get_file(self, file_id: str) -> Optional[dict]:
        return self.files.get(file_id)

    def remove_file(self, file_id: str):
        self.files.pop(file_id, None)

    def list_files(self) -> List[dict]:
        result = []
        for fid, f in self.files.items():
            meta = f["metadata"]
            result.append({
                "file_id": fid,
                "filename": meta.get("filename", ""),
                "num_rows": meta.get("num_rows", 0),
                "num_cols": meta.get("num_cols", 0),
                "brand_count": meta.get("brand_count", 0),
                "brands": meta.get("brands", [])
            })
        return result

    def has_data(self) -> bool:
        return len(self.files) > 0

    def get_combined_data(self, file_ids: Optional[List[str]] = None) -> List[list]:
        """
        合并多个文件的数据，返回 [特征11列, out_moist]（12列，不含brandID）
        供训练函数使用
        """
        all_data = []
        targets = file_ids if file_ids else list(self.files.keys())
        for fid in targets:
            f = self.files.get(fid)
            if not f:
                logger.warning(f"文件不存在: {fid}")
                continue
            rows = f["data"]
            for row in rows:
                if len(row) >= INPUT_DIM + 1:
                    # 取前12列：特征11 + out_moist，丢弃 brandID
                    all_data.append(row[:INPUT_DIM + 1])
        logger.info(f"get_combined_data: file_ids={targets}, 返回 {len(all_data)} 行")
        return all_data

    def get_grouped_data(self, file_ids: Optional[List[str]] = None) -> Dict[int, list]:
        """获取按 brandID 分组的数据"""
        combined = {}
        targets = file_ids if file_ids else list(self.files.keys())
        for fid in targets:
            f = self.files.get(fid)
            if f and "grouped_data" in f["metadata"]:
                for brand, rows in f["metadata"]["grouped_data"].items():
                    if brand not in combined:
                        combined[brand] = []
                    combined[brand].extend(rows)
        return combined

    def get_next_window(self, window_size: int, file_ids: Optional[List[str]] = None) -> Optional[list]:
        data = self.get_combined_data(file_ids)
        if not data or self.data_index >= len(data):
            return None
        start = max(0, self.data_index - window_size + 1)
        window = data[start:self.data_index + 1]
        while len(window) < window_size:
            window.insert(0, data[0] if data else [0.0] * (INPUT_DIM + 1))
        self.data_index += 1
        return window

    def get_actual_value(self, index: int, file_ids: Optional[List[str]] = None) -> Optional[float]:
        data = self.get_combined_data(file_ids)
        if 0 <= index < len(data):
            return float(data[index][-1])
        return None

    def get_all_actual_values(self, limit: int = 500, file_ids: Optional[List[str]] = None) -> List[dict]:
        data = self.get_combined_data(file_ids)
        result = []
        for i, row in enumerate(data[:limit]):
            result.append({"index": i, "actual": float(row[-1])})
        return result

    def reset_index(self):
        self.data_index = 0

    def clear(self):
        self.files.clear()
        self.data_index = 0


class TrainingJobManager:
    """管理多个并发训练任务"""

    def __init__(self):
        self.jobs: Dict[str, dict] = {}

    def add_job(self, job_id: str, job_info: dict):
        self.jobs[job_id] = job_info

    def get_job(self, job_id: str) -> Optional[dict]:
        return self.jobs.get(job_id)

    def remove_job(self, job_id: str):
        self.jobs.pop(job_id, None)

    def is_model_training(self, model_key: str) -> bool:
        return any(
            j.get("model_key") == model_key and j.get("is_training", False)
            for j in self.jobs.values()
        )

    def get_model_job(self, model_key: str) -> Optional[dict]:
        for jid, j in self.jobs.items():
            if j.get("model_key") == model_key and j.get("is_training", False):
                return j
        return None

    def has_active_training(self) -> bool:
        return any(j.get("is_training", False) for j in self.jobs.values())


data_manager = UploadedDataManager()
training_job_manager = TrainingJobManager()
