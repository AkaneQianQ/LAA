"""
FerrumController - Serial communication layer for Ferrum hardware device.

提供与Ferrum设备的串口通信，实现硬件输入控制的基础接口。
"""

import serial
import time
import logging
from typing import Optional, List, Dict

try:
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    win32api = None

# 配置日志
logger = logging.getLogger(__name__)

# HID Key Code Mapping (HID Usage Table 1.5)
# Letters a-z: codes 4-29, Numbers 0-9: codes 30-39
KEY_MAP: Dict[str, int] = {
    # Letters a-z
    "a": 4, "b": 5, "c": 6, "d": 7, "e": 8, "f": 9,
    "g": 10, "h": 11, "i": 12, "j": 13, "k": 14, "l": 15,
    "m": 16, "n": 17, "o": 18, "p": 19, "q": 20, "r": 21,
    "s": 22, "t": 23, "u": 24, "v": 25, "w": 26, "x": 27,
    "y": 28, "z": 29,
    # Numbers 0-9
    "0": 30, "1": 31, "2": 32, "3": 33, "4": 34,
    "5": 35, "6": 36, "7": 37, "8": 38, "9": 39,
    # Special keys
    "enter": 40, "return": 40,
    "esc": 41, "escape": 41,
    "backspace": 42, "bs": 42,
    "tab": 43,
    "space": 44, "spacebar": 44,
    # Arrow keys
    "up": 38, "arrowup": 38,
    "down": 40, "arrowdown": 40,
    "left": 37, "arrowleft": 37,
    "right": 39, "arrowright": 39,
    # Modifier keys
    "alt": 226, "lalt": 226, "leftalt": 226,
    "ralt": 230, "rightalt": 230,
    "ctrl": 224, "lctrl": 224, "leftctrl": 224, "control": 224,
    "rctrl": 228, "rightctrl": 228,
    "shift": 225, "lshift": 225, "leftshift": 225,
    "rshift": 229, "rightshift": 229,
    # Function keys F1-F12
    "f1": 58, "f2": 59, "f3": 60, "f4": 61,
    "f5": 62, "f6": 63, "f7": 64, "f8": 65,
    "f9": 66, "f10": 67, "f11": 68, "f12": 69,
}

# HID modifier codes for ordering (modifiers should be pressed first)
MODIFIER_CODES = {224, 225, 226, 228, 229, 230}

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
            logger.error(f"[错误] 无法连接到Ferrum设备 {self.port}: {e}")
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
            logger.error("[错误] 串口未连接")
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
            logger.error(f"[错误] 命令执行失败 '{command}': {e}")
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

    def is_connected(self) -> bool:
        """
        检查设备是否已连接

        Returns:
            True如果串口已连接且打开，否则False
        """
        return self._connected and self._serial is not None and self._serial.is_open


    def _move(self, x: int, y: int) -> None:
        """
        发送相对鼠标移动命令

        注意: km.move 使用相对坐标，不是绝对定位。
        对于绝对定位，调用者必须跟踪当前位置并计算增量。

        Args:
            x: X方向相对移动（正数=右，负数=左）
            y: Y方向相对移动（正数=下，负数=上）
        """
        self._send_command(f"km.move({x}, {y})")

    def move_absolute(self, x: int, y: int) -> None:
        """
        移动鼠标到绝对坐标位置

        使用win32api.GetCursorPos()获取当前位置，计算相对位移，
        然后调用km.move()进行移动。

        Args:
            x: 目标X坐标（绝对位置）
            y: 目标Y坐标（绝对位置）

        Raises:
            RuntimeError: 如果win32api不可用
        """
        if not WIN32_AVAILABLE or win32api is None:
            raise RuntimeError("win32api not available, cannot get current cursor position")

        self._validate_connection()

        # 获取当前鼠标位置
        current_x, current_y = win32api.GetCursorPos()

        # 计算相对位移
        dx = x - current_x
        dy = y - current_y

        # 发送相对移动命令
        self._send_command(f"km.move({dx}, {dy})")
        logger.debug(f"[Ferrum] 绝对移动: 当前({current_x}, {current_y}) -> 目标({x}, {y}), 相对({dx}, {dy})")

    def click(self, x: int, y: int) -> None:
        """
        在指定坐标点击鼠标左键

        注意：km.move使用相对坐标，这里假设调用者已计算好相对位移。
        如需绝对坐标，调用者需先获取当前鼠标位置并计算delta。

        Args:
            x: X坐标相对位移（正=右，负=左）
            y: Y坐标相对位移（正=下，负=上）
        """
        self._validate_connection()
        # 移动鼠标（相对移动）
        self._move(x, y)
        # 点击左键
        self._send_command(f"km.click({BUTTON_LEFT})")
        logger.debug(f"[Ferrum] 点击 ({x}, {y})")

    def click_right(self, x: int, y: int) -> None:
        """
        在指定坐标点击鼠标右键

        Args:
            x: X坐标相对位移
            y: Y坐标相对位移
        """
        self._validate_connection()
        self._send_command(f"km.move({x}, {y})")
        self._send_command(f"km.click({BUTTON_RIGHT})")
        logger.debug(f"[Ferrum] 右键点击 ({x}, {y})")

    def scroll(self, direction: str, ticks: int) -> None:
        """
        滚动鼠标滚轮

        Args:
            direction: 滚动方向，"up" 或 "down"
            ticks: 滚动次数

        Raises:
            ValueError: 方向不是"up"或"down"
        """
        self._validate_connection()

        direction = direction.lower()
        if direction not in ("up", "down"):
            raise ValueError(f"滚动方向必须是 'up' 或 'down'，得到: {direction}")

        # up = +1, down = -1 (Ferrum文档规定)
        amount = 1 if direction == "up" else -1

        for _ in range(ticks):
            self._send_command(f"km.wheel({amount})")
            time.sleep(0.005)  # 5ms延迟避免设备过载

        logger.debug(f"[Ferrum] 滚动 {direction} {ticks} 次")

    def _parse_key(self, key_name: str) -> List[int]:
        """
        解析键名为HID代码列表

        Args:
            key_name: 键名或组合（如 "alt+u", "esc"）

        Returns:
            HID代码列表

        Raises:
            ValueError: 未知键名
        """
        parts = key_name.lower().split('+')
        codes = []
        for part in parts:
            part = part.strip()
            if part in KEY_MAP:
                codes.append(KEY_MAP[part])
            else:
                raise ValueError(f"未知键名: {part} (可用: {list(KEY_MAP.keys())})")
        return codes

    def _order_codes(self, codes: List[int]) -> List[int]:
        """
        对HID代码进行排序，确保修饰键先按下

        Args:
            codes: HID代码列表

        Returns:
            排序后的代码列表（修饰键在前）
        """
        modifiers = [c for c in codes if c in MODIFIER_CODES]
        main_keys = [c for c in codes if c not in MODIFIER_CODES]
        return modifiers + main_keys

    def press(self, key_name: str) -> None:
        """
        按下指定键或键组合

        Args:
            key_name: 键名或组合（如 "esc", "alt+u", "enter"）

        Raises:
            ValueError: 未知键名
            FerrumConnectionError: 串口通信失败
        """
        self._validate_connection()

        codes = self._parse_key(key_name)
        ordered_codes = self._order_codes(codes)

        if len(ordered_codes) == 1:
            # 单键使用km.press（自动时序）
            self._send_command(f"km.press({ordered_codes[0]})")
        else:
            # 组合键使用down/up序列，修饰键先按下
            # 按下所有键
            for code in ordered_codes:
                self._send_command(f"km.down({code})")
                time.sleep(0.01)  # 10ms延迟
            # 保持50ms
            time.sleep(0.05)
            # 释放所有键（逆序）
            for code in reversed(ordered_codes):
                self._send_command(f"km.up({code})")

        logger.debug(f"[Ferrum] 按键: {key_name}")

    def key_down(self, key_name: str) -> None:
        """
        按住指定键（不释放）

        Args:
            key_name: 键名
        """
        self._validate_connection()
        codes = self._parse_key(key_name)
        for code in codes:
            self._send_command(f"km.down({code})")
        logger.debug(f"[Ferrum] 按住: {key_name}")

    def key_up(self, key_name: str) -> None:
        """
        释放指定键

        Args:
            key_name: 键名
        """
        self._validate_connection()
        codes = self._parse_key(key_name)
        for code in codes:
            self._send_command(f"km.up({code})")
        logger.debug(f"[Ferrum] 释放: {key_name}")

    def close(self) -> None:
        """
        关闭控制器并释放资源

        关闭串口连接，清理所有状态。
        """
        self._disconnect()
        logger.info("[Ferrum] 控制器已关闭")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口，确保资源清理"""
        self._disconnect()
        return False
