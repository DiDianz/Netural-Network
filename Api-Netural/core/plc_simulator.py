# core/plc_simulator.py
"""
PLC 模拟器 — 为无真实 PLC 环境提供模拟数据生成
支持多种波动模式：random / sine / step / sawtooth
"""
import math
import random
import time
import threading
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("plc_simulator")


class PlcSimulator:
    """单个 PLC 设备的模拟器"""

    def __init__(self, device_id: int, config: dict):
        self.device_id = device_id
        self.interval = config.get("interval", 1.0)
        self.min_val = config.get("min_val", 0)
        self.max_val = config.get("max_val", 100)
        self.pattern = config.get("pattern", "random")
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._values: Dict[int, float] = {}  # point_id -> current value
        self._tick = 0

    def start(self, points: List[dict]):
        """启动模拟数据生成"""
        if self._running:
            return
        self._running = True
        self._tick = 0
        for pt in points:
            pid = pt.get("id", 0)
            self._values[pid] = random.uniform(self.min_val, self.max_val)

        self._thread = threading.Thread(
            target=self._run, args=(points,), daemon=True
        )
        self._thread.start()
        logger.info(f"模拟PLC启动: device_id={self.device_id}, pattern={self.pattern}")

    def stop(self):
        """停止模拟"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        self._values.clear()
        logger.info(f"模拟PLC停止: device_id={self.device_id}")

    @property
    def is_running(self) -> bool:
        return self._running

    def get_value(self, point_id: int) -> Optional[float]:
        """获取指定点位的当前模拟值"""
        with self._lock:
            return self._values.get(point_id)

    def get_all_values(self) -> Dict[int, float]:
        """获取所有点位的当前模拟值"""
        with self._lock:
            return dict(self._values)

    def _run(self, points: List[dict]):
        """后台线程：按间隔更新模拟数据"""
        mid = (self.min_val + self.max_val) / 2
        amp = (self.max_val - self.min_val) / 2

        while self._running:
            self._tick += 1
            with self._lock:
                for pt in points:
                    pid = pt.get("id", 0)
                    old_val = self._values.get(pid, mid)
                    new_val = self._generate_value(old_val, mid, amp)
                    self._values[pid] = round(new_val, 4)

            time.sleep(self.interval)

    def _generate_value(self, old_val: float, mid: float, amp: float) -> float:
        """根据波动模式生成下一个值"""
        t = self._tick

        if self.pattern == "sine":
            return mid + amp * math.sin(t * 0.15)

        elif self.pattern == "step":
            level = (t // 10) % 3
            return mid + amp * (level - 1) * 0.6

        elif self.pattern == "sawtooth":
            period = 30
            phase = t % period
            return self.min_val + (self.max_val - self.min_val) * (phase / period)

        else:
            drift = random.gauss(0, amp * 0.08)
            new_val = old_val + drift
            if new_val > self.max_val:
                new_val = self.max_val - abs(random.gauss(0, amp * 0.1))
            elif new_val < self.min_val:
                new_val = self.min_val + abs(random.gauss(0, amp * 0.1))
            return max(self.min_val, min(self.max_val, new_val))


class PlcSimulatorManager:
    """管理所有模拟 PLC 实例"""

    def __init__(self):
        self._simulators: Dict[int, PlcSimulator] = {}

    def start_simulate(self, device_id: int, points: List[dict], config: dict) -> dict:
        """启动设备的模拟"""
        self.stop_simulate(device_id)

        sim = PlcSimulator(device_id, config)
        sim.start(points)
        self._simulators[device_id] = sim
        return {"success": True, "msg": "模拟启动成功"}

    def stop_simulate(self, device_id: int) -> bool:
        """停止设备的模拟"""
        sim = self._simulators.pop(device_id, None)
        if sim:
            sim.stop()
            return True
        return False

    def is_simulating(self, device_id: int) -> bool:
        """检查设备是否在模拟中"""
        sim = self._simulators.get(device_id)
        return sim is not None and sim.is_running

    def read_value(self, device_id: int, point_id: int) -> dict:
        """读取模拟数据"""
        sim = self._simulators.get(device_id)
        if not sim or not sim.is_running:
            return {"success": False, "msg": "设备未处于模拟状态"}
        value = sim.get_value(point_id)
        if value is None:
            return {"success": False, "msg": "点位无模拟数据"}
        return {"success": True, "value": value}

    def read_multiple(self, device_id: int, points: List[dict]) -> dict:
        """批量读取模拟数据"""
        sim = self._simulators.get(device_id)
        if not sim or not sim.is_running:
            return {"success": False, "msg": "设备未处于模拟状态"}

        all_vals = sim.get_all_values()
        results = []
        for pt in points:
            pid = pt.get("id", 0)
            val = all_vals.get(pid)
            results.append({
                "point_id": pid,
                "point_name": pt.get("point_name"),
                "value": val,
                "success": val is not None
            })
        return {"success": True, "data": results}

    def stop_all(self):
        """停止所有模拟"""
        for did in list(self._simulators.keys()):
            self.stop_simulate(did)

    def get_simulated_devices(self) -> List[int]:
        """获取所有正在模拟的设备 ID"""
        return [did for did, sim in self._simulators.items() if sim.is_running]


# 全局单例
plc_simulator = PlcSimulatorManager()
