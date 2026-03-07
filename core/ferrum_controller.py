"""
FerrumController - Serial communication layer for Ferrum hardware device.

提供与Ferrum设备的串口通信，实现硬件输入控制的基础接口。
"""

import serial
import time
import logging
from typing import Optional, List, Dict

# 配置日志
logger = logging.getLogger(__name__)

# HID Key Code Mapping (HID Usage Table 1.5)
KEY_MAP: Dict[str, int] = {
    "esc": 41,
    "u": 24,
    "up": 38,
    "down": 40,
    "left": 37,
    "right": 39,
    "enter": 40,
    "alt": 226,  # Left Alt
    "space": 44,
    "tab": 43,
}

# Mouse Button Constants (per Ferrum documentation)
BUTTON_LEFT = 0
BUTTON_RIGHT = 1
BUTTON_MIDDLE = 2
BUTTON_SIDE_REAR = 3
BUTTON_SIDE_FRONT = 4


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
        self._initialize_device()

    def _connect(self) -> None:
        """建立串口连接"""
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            self._connected = True
            logger.debug(f"[Ferrum] 串口已打开: {self.port} @ {self.baudrate}")
        except serial.SerialException as e:
            raise FerrumConnectionError(f"无法连接到Ferrum设备 {self.port}: {e}")

    def _disconnect(self) -> None:
        """关闭串口连接并清理资源"""
        if self._serial and self._serial.is_open:
            self._serial.close()
            logger.debug(f"[Ferrum] 串口已关闭: {self.port}")
        self._connected = False
        self._serial = None

    def _validate_connection(self) -> None:
        """
        验证串口连接状态

        Raises:
            FerrumConnectionError: 串口未连接或已关闭
        """
        if not self._connected or not self._serial or not self._serial.is_open:
            raise FerrumConnectionError("串口未连接")

    def _send_command(self, command: str, retry: bool = True) -> str:
        """
        发送命令到Ferrum设备并读取响应

        协议格式:
        - 输入: command + \r\n
        - 输出: command\r\n (echo) + result + \r\n>>>

        Args:
            command: 要发送的命令字符串
            retry: 失败时是否重试一次

        Returns:
            命令执行结果字符串（不含echo和prompt）

        Raises:
            FerrumConnectionError: 串口未连接或通信失败
        """
        self._validate_connection()

        try:
            # 发送命令，添加\r\n终止符
            full_command = command + "\r\n"
            self._serial.write(full_command.encode('utf-8'))
            logger.debug(f"[Ferrum] 发送命令: {command}")

            # 读取响应直到遇到prompt
            response_lines = []
            start_time = time.monotonic()

            while True:
                if time.monotonic() - start_time > self.timeout:
                    raise TimeoutError(f"命令超时: {command}")

                if self._serial.in_waiting:
                    line = self._serial.readline().decode('utf-8', errors='ignore')
                    response_lines.append(line)

                    # 检查是否收到prompt
                    if ">>> " in line:
                        break
                else:
                    time.sleep(0.001)  # 短暂等待避免CPU占用

            # 解析响应：第一行是echo，最后一行是prompt，中间是结果
            result = self._parse_response(response_lines, command)
            logger.debug(f"[Ferrum] 响应结果: {result!r}")
            return result

        except (TimeoutError, serial.SerialException) as e:
            if retry:
                logger.warning(f"[Ferrum] 命令失败，重试一次: {command}")
                time.sleep(0.1)
                return self._send_command(command, retry=False)
            raise FerrumConnectionError(f"命令执行失败 '{command}': {e}")

    def _parse_response(self, lines: list[str], expected_command: str) -> str:
        """
        解析Ferrum设备响应

        Args:
            lines: 从串口读取的所有行
            expected_command: 期望的命令echo

        Returns:
            命令执行结果（echo和prompt之间的内容）
        """
        if not lines:
            return ""

        # 过滤空行
        lines = [line.rstrip('\r\n') for line in lines if line.strip()]

        # 查找包含prompt的行
        prompt_idx = -1
        for i, line in enumerate(lines):
            if ">>>" in line:
                prompt_idx = i
                break

        if prompt_idx == -1:
            # 没有找到prompt，返回所有非空内容
            return "\n".join(lines)

        # prompt前的最后一行是结果（如果有的话）
        if prompt_idx > 0:
            # 检查是否有echo行
            first_line = lines[0].strip()
            if first_line == expected_command.strip():
                # 有echo，结果是echo和prompt之间的内容
                if prompt_idx > 1:
                    return "\n".join(lines[1:prompt_idx])
                return ""  # echo后直接是prompt，无结果
            else:
                # 无echo或格式异常，返回prompt前的所有内容
                return "\n".join(lines[:prompt_idx])

        return ""  # prompt是第一行，无结果

    def _initialize_device(self) -> None:
        """
        初始化Ferrum设备

        发送km.init()命令清除设备状态，确保设备处于就绪状态。
        """
        try:
            # 清除串口缓冲区
            if self._serial and self._serial.is_open:
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()

            # 发送初始化命令
            result = self._send_command("km.init()")
            logger.info(f"[Ferrum] 设备已初始化")

        except FerrumConnectionError as e:
            logger.error(f"[错误] Ferrum设备初始化失败: {e}")
            raise
        except Exception as e:
            logger.error(f"[错误] 初始化过程中发生未知错误: {e}")
            raise FerrumConnectionError(f"设备初始化失败: {e}")

    def wait(self, seconds: float) -> None:
        """
        等待指定时间

        供ActionDispatcher调用的基础等待方法。

        Args:
            seconds: 等待时间（秒）
        """
        time.sleep(seconds)

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口，确保资源清理"""
        self._disconnect()
        return False
