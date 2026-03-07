"""
FerrumController - Serial communication layer for Ferrum hardware device.

提供与Ferrum设备的串口通信，实现硬件输入控制的基础接口。
"""

import serial
import time
from typing import Optional


class FerrumConnectionError(Exception):
    """Ferrum设备连接错误"""
    pass


class FerrumController:
    """
    Ferrum硬件控制器

    通过串口与Ferrum设备通信，发送鼠标和键盘命令。
    实现ActionDispatcher期望的基础接口。
    """

    def __init__(
        self,
        port: str = "COM2",
        baudrate: int = 115200,
        timeout: float = 1.0
    ):
        """
        初始化Ferrum控制器

        Args:
            port: 串口名称，默认COM2
            baudrate: 波特率，默认115200
            timeout: 超时时间（秒），默认1.0
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: Optional[serial.Serial] = None
        self._connected = False

        self._connect()

    def _connect(self) -> None:
        """建立串口连接"""
        pass  # TODO: Implement in Task 2

    def _disconnect(self) -> None:
        """关闭串口连接并清理资源"""
        pass  # TODO: Implement in Task 2

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口，确保资源清理"""
        self._disconnect()
        return False
