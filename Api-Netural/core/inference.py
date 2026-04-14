# core/inference.py
import torch
import numpy as np
import asyncio
import time
from collections import deque
from core.model import PredictionNet

class InferenceEngine:
    """持续推理引擎 — 维护滑动窗口，持续输出预测"""

    def __init__(self, model_path: str = None): # type: ignore
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = PredictionNet(input_dim=5, hidden_dim=128, output_dim=1).to(self.device)

        if model_path:
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()

        # 滑动窗口缓存
        self.window_size = 60  # 用最近60个时间步预测
        self.buffer = deque(maxlen=self.window_size)
        self._running = False
        self._interval = 1.0   # 推理间隔(秒)

        # 用模拟数据预填充窗口
        self._prefill_buffer()

    def _prefill_buffer(self):
        """预填充历史数据窗口"""
        for _ in range(self.window_size):
            self.buffer.append(np.random.randn(5).astype(np.float32))

    def update_config(self, interval: float = None, window_size: int = None): # type: ignore
        """运行时更新配置"""
        if interval is not None:
            self._interval = max(0.1, interval)
        if window_size is not None:
            old_buffer = list(self.buffer)
            self.window_size = window_size
            self.buffer = deque(old_buffer[-window_size:], maxlen=window_size)

    @torch.no_grad()
    def predict_once(self) -> dict:
        """单次推理"""
        # 构建输入张量
        input_seq = np.array(list(self.buffer))           # (window, features)
        input_tensor = torch.tensor(input_seq).unsqueeze(0).to(self.device)  # (1, window, features)

        # 模型推理
        prediction = self.model(input_tensor).cpu().numpy()[0]

        # 计算置信区间（简化版：用 dropout Monte Carlo）
        self.model.train()
        preds_mc = []
        for _ in range(10):
            p = self.model(input_tensor).cpu().numpy()[0]
            preds_mc.append(p)
        self.model.eval()

        preds_mc = np.array(preds_mc)
        mean_pred = float(preds_mc.mean())
        std_pred = float(preds_mc.std())

        # 模拟新数据流入（实际场景替换为真实数据源）
        new_data = np.random.randn(5).astype(np.float32)
        self.buffer.append(new_data)

        return {
            "timestamp": time.time(),
            "prediction": round(mean_pred, 6),
            "confidence_upper": round(mean_pred + 2 * std_pred, 6),
            "confidence_lower": round(mean_pred - 2 * std_pred, 6),
            "uncertainty": round(std_pred, 6),
            "input_window_size": len(self.buffer)
        }

    async def stream_predictions(self):
        """异步生成器 — 持续产出预测结果"""
        self._running = True
        while self._running:
            result = self.predict_once()
            yield result
            await asyncio.sleep(self._interval)

    def stop(self):
        self._running = False


# 全局单例
engine = InferenceEngine()
