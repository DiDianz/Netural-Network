# core/plc_service.py
"""
PLC 连接服务 — 基于 python-snap7 实现 S7 协议通信
管理多个 PLC 设备连接，提供读取 DB 数据的功能
"""
import struct
import logging
import threading
from typing import Dict, Optional, Any, List

logger = logging.getLogger("plc_service")


class PlcConnectionManager:
    """PLC 连接管理器 — 管理所有 PLC 设备的连接"""

    def __init__(self):
        # device_id -> { "client": snap7.client.Client, "lock": threading.Lock }
        self._connections: Dict[int, dict] = {}
        self._snap7_available = False
        try:
            import snap7
            self._snap7 = snap7
            self._snap7_available = True
            logger.info("snap7 库加载成功")
        except ImportError:
            logger.warning("snap7 库未安装，请执行: pip install python-snap7")

    @property
    def available(self) -> bool:
        return self._snap7_available

    def connect(self, device_id: int, ip: str, port: int = 102,
                rack: int = 0, slot: int = 1) -> dict:
        """连接 PLC 设备"""
        if not self._snap7_available:
            return {"success": False, "msg": "snap7 库未安装，请执行: pip install python-snap7"}

        # 断开已有连接
        self.disconnect(device_id)

        client = self._snap7.client.Client()
        lock = threading.Lock()
        try:
            client.connect(ip, rack, slot, port)
            if client.get_connected():
                self._connections[device_id] = {"client": client, "lock": lock}
                logger.info(f"PLC 连接成功: device_id={device_id}, ip={ip}:{port}")
                return {"success": True, "msg": "连接成功"}
            else:
                return {"success": False, "msg": "连接失败，无法建立通信"}
        except Exception as e:
            logger.error(f"PLC 连接异常: device_id={device_id}, error={e}")
            try:
                client.destroy()
            except Exception:
                pass
            return {"success": False, "msg": f"连接异常: {str(e)}"}

    def disconnect(self, device_id: int) -> bool:
        """断开 PLC 连接"""
        conn = self._connections.pop(device_id, None)
        if conn:
            try:
                conn["client"].disconnect()
                conn["client"].destroy()
            except Exception as e:
                logger.warning(f"断开 PLC 连接异常: {e}")
            return True
        return False

    def is_connected(self, device_id: int) -> bool:
        """检查设备是否已连接"""
        conn = self._connections.get(device_id)
        if not conn:
            return False
        try:
            return conn["client"].get_connected()
        except Exception:
            return False

    def read_value(self, device_id: int, db_number: int, start_address: int,
                   data_type: str, bit_index: int = 0) -> dict:
        """读取 PLC 数据点的值"""
        if not self._snap7_available:
            return {"success": False, "msg": "snap7 库未安装"}

        conn = self._connections.get(device_id)
        if not conn:
            return {"success": False, "msg": "设备未连接"}

        # 根据数据类型确定读取字节数
        type_sizes = {"REAL": 4, "INT": 2, "DINT": 4, "WORD": 2, "BOOL": 1}
        size = type_sizes.get(data_type.upper(), 4)

        try:
            with conn["lock"]:
                client = conn["client"]
                data = client.db_read(db_number, start_address, size)
                value = self._parse_data(data, data_type, bit_index)
            return {"success": True, "value": value, "raw": list(data)}
        except Exception as e:
            logger.error(f"读取 PLC 数据失败: device_id={device_id}, db={db_number}, addr={start_address}, error={e}")
            return {"success": False, "msg": f"读取失败: {str(e)}"}

    def read_multiple(self, device_id: int, points: List[dict]) -> dict:
        """批量读取多个 DB 点位"""
        if not self._snap7_available:
            return {"success": False, "msg": "snap7 库未安装"}

        conn = self._connections.get(device_id)
        if not conn:
            return {"success": False, "msg": "设备未连接"}

        results = []
        try:
            with conn["lock"]:
                client = conn["client"]
                for pt in points:
                    db_number = pt["db_number"]
                    start_address = pt["start_address"]
                    data_type = pt.get("data_type", "REAL")
                    bit_index = pt.get("bit_index", 0)
                    type_sizes = {"REAL": 4, "INT": 2, "DINT": 4, "WORD": 2, "BOOL": 1}
                    size = type_sizes.get(data_type.upper(), 4)
                    try:
                        data = client.db_read(db_number, start_address, size)
                        value = self._parse_data(data, data_type, bit_index)
                        results.append({
                            "point_id": pt.get("id"),
                            "point_name": pt.get("point_name"),
                            "value": value,
                            "success": True
                        })
                    except Exception as e:
                        results.append({
                            "point_id": pt.get("id"),
                            "point_name": pt.get("point_name"),
                            "value": None,
                            "success": False,
                            "msg": str(e)
                        })
            return {"success": True, "data": results}
        except Exception as e:
            return {"success": False, "msg": f"批量读取失败: {str(e)}"}

    def _parse_data(self, data: bytes, data_type: str, bit_index: int = 0) -> Any:
        """解析 PLC 返回的字节数据"""
        dtype = data_type.upper()
        if dtype == "REAL":
            return round(struct.unpack('>f', data)[0], 4)
        elif dtype == "INT":
            return struct.unpack('>h', data)[0]
        elif dtype == "DINT":
            return struct.unpack('>i', data)[0]
        elif dtype == "WORD":
            return struct.unpack('>H', data)[0]
        elif dtype == "BOOL":
            byte_val = data[0]
            return bool((byte_val >> bit_index) & 1)
        else:
            return struct.unpack('>f', data)[0]

    def get_connected_devices(self) -> List[int]:
        """获取所有已连接的设备 ID 列表"""
        connected = []
        for did, conn in self._connections.items():
            try:
                if conn["client"].get_connected():
                    connected.append(did)
            except Exception:
                pass
        return connected

    def disconnect_all(self):
        """断开所有连接"""
        for did in list(self._connections.keys()):
            self.disconnect(did)


# 全局单例
plc_manager = PlcConnectionManager()
