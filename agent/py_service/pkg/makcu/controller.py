#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MakcuController - Legacy API serial communication layer for MAKCU hardware.
"""

import logging
import time
from dataclasses import dataclass
from typing import List, Optional

import serial
try:
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    win32api = None
    WIN32_AVAILABLE = False


logger = logging.getLogger(__name__)

BUTTON_LEFT = 1
BUTTON_RIGHT = 2
BUTTON_MIDDLE = 3
CLICK_POST_DELAY_S = 0.1
CLICK_DELAY_MS = 50
PRE_CLICK_SETTLE_S = 0.03
PRE_CLICK_DELAY_S = 0.1
KEY_DOWN_DELAY_S = 0.012
KEY_HOLD_MS = 50
KEY_UP_DELAY_S = 0.008

MAKCU_KEY_ALIASES = {
    "return": "enter",
    "escape": "esc",
    "back": "backspace",
    "bs": "backspace",
    "spacebar": "space",
    "dash": "minus",
    "hyphen": "minus",
    "equal": "equals",
    "lbracket": "leftbracket",
    "openbracket": "leftbracket",
    "rbracket": "rightbracket",
    "closebracket": "rightbracket",
    "bslash": "backslash",
    "semi": "semicolon",
    "apostrophe": "quote",
    "singlequote": "quote",
    "backtick": "grave",
    "tilde": "grave",
    "dot": "period",
    "forwardslash": "slash",
    "fslash": "slash",
    "caps": "capslock",
    "prtsc": "printscreen",
    "print": "printscreen",
    "scroll": "scrolllock",
    "break": "pause",
    "ins": "insert",
    "pgup": "pageup",
    "del": "delete",
    "pgdown": "pagedown",
    "pgdn": "pagedown",
    "arrowup": "up",
    "arrowdown": "down",
    "arrowleft": "left",
    "arrowright": "right",
    "control": "ctrl",
    "leftctrl": "ctrl",
    "lctrl": "ctrl",
    "leftshift": "shift",
    "lshift": "shift",
    "leftalt": "alt",
    "lalt": "alt",
    "rightctrl": "rctrl",
    "rctrl": "rctrl",
    "rightshift": "rshift",
    "rshift": "rshift",
    "rightalt": "ralt",
    "ralt": "ralt",
}

MAKCU_MODIFIER_KEYS = {"ctrl", "shift", "alt", "gui", "rctrl", "rshift", "ralt", "rgui"}
NO_RESPONSE_PREFIXES = (
    "km.moveto(",
    "km.move(",
    "km.silent(",
    "km.click(",
    "km.left(",
    "km.right(",
    "km.middle(",
    "km.wheel(",
    "km.press(",
    "km.down(",
    "km.up(",
)


@dataclass
class ControllerConfig:
    name: str = "MAKCU-Default"
    port: str = "COM3"
    baudrate: int = 115200
    timeout: float = 1.0


class MakcuConnectionError(Exception):
    """MAKCU device connection error."""


def _format_raw_response(buffer: bytearray) -> str:
    if not buffer:
        return "<empty>"
    text = buffer.decode("utf-8", errors="replace").replace("\r", "\\r").replace("\n", "\\n")
    if len(text) > 160:
        text = text[:157] + "..."
    return text


class MakcuController:
    """
    MAKCU hardware controller using the documented Legacy ASCII API over serial.

    Command shapes are aligned with the official MAKCU API and cross-checked
    against the working Makcu-main serial sample.
    """

    def __init__(self, port: str = "COM3", baudrate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: Optional[serial.Serial] = None
        self._connected = False
        self._firmware_version = ""

        self._connect()
        self._initialize_device()

    def _connect(self) -> None:
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
            self._connected = True
        except serial.SerialException as exc:
            raise MakcuConnectionError(f"Unable to connect to MAKCU device {self.port}: {exc}") from exc

    def _disconnect(self) -> None:
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None
        self._connected = False

    def _validate_connection(self) -> None:
        if not self._connected or not self._serial or not self._serial.is_open:
            raise MakcuConnectionError("Serial connection is not available")

    def _read_response(self) -> str:
        response_buffer = bytearray()
        start_time = time.monotonic()

        while True:
            if time.monotonic() - start_time > self.timeout:
                raise TimeoutError(f"Timed out waiting for MAKCU response; raw={_format_raw_response(response_buffer)}")

            if self._serial.in_waiting:
                chunk = self._serial.read(self._serial.in_waiting)
                response_buffer.extend(chunk)
                if b">>>" in response_buffer:
                    break
            else:
                time.sleep(0.001)

        lines = [line.strip() for line in response_buffer.decode("utf-8", errors="ignore").splitlines() if line.strip()]
        if not lines:
            return ""
        payload_lines = [line for line in lines if line != ">>>"]
        return "\n".join(payload_lines)

    def _send_command(self, command: str, retry: bool = True, wait_response: bool = True) -> str:
        self._validate_connection()
        try:
            logger.info("[Hardware] MAKCU send: %s", command)
            self._serial.write(f"{command}\r\n".encode("utf-8"))
            # Fire-and-forget commands on some firmware never emit prompt;
            # skip response wait to avoid 1s timeout penalty per action.
            if self._is_no_response_command(command):
                logger.info("[Hardware] MAKCU ack: %s -> <no-wait-no-response-cmd>", command)
                return ""
            if not wait_response:
                logger.info("[Hardware] MAKCU ack: %s -> <no-wait>", command)
                return ""
            response = self._read_response()
            logger.info("[Hardware] MAKCU ack: %s -> %s", command, response or "<empty>")
            return response
        except (serial.SerialException, TimeoutError) as exc:
            if isinstance(exc, TimeoutError) and self._is_no_response_command(command):
                logger.info("[Hardware] MAKCU ack: %s -> <allowed-empty-timeout>", command)
                return ""
            if retry:
                time.sleep(0.05)
                return self._send_command(command, retry=False, wait_response=wait_response)
            raise MakcuConnectionError(f"Command failed '{command}': {exc}") from exc

    def _is_no_response_command(self, command: str) -> bool:
        stripped = str(command).strip().lower()
        return any(stripped.startswith(prefix) for prefix in NO_RESPONSE_PREFIXES)

    def _initialize_device(self) -> None:
        if self._serial and self._serial.is_open:
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
        result = self._send_command("km.version()")
        if result:
            lines = [line for line in result.splitlines() if line != "km.version()"]
            if lines:
                self._firmware_version = lines[-1]

    def wait(self, seconds: float) -> None:
        time.sleep(seconds)

    def is_connected(self) -> bool:
        return self._connected and self._serial is not None and self._serial.is_open

    def handshake(self) -> bool:
        try:
            self._validate_connection()
            result = self._send_command("km.version()")
            if result:
                lines = [line for line in result.splitlines() if line != "km.version()"]
                if lines:
                    self._firmware_version = lines[-1]
            return True
        except Exception as exc:
            logger.warning("[MAKCU] Handshake failed: %s", exc)
            return False

    def _move(self, x: int, y: int) -> None:
        self._send_command(f"km.move({int(x)},{int(y)})")

    def move_absolute(self, x: int, y: int) -> None:
        self._validate_connection()
        target_x = int(x)
        target_y = int(y)
        # Some MAKCU firmware builds are unreliable with moveto().
        # Prefer relative move derived from current cursor position when possible.
        if WIN32_AVAILABLE:
            try:
                cur_x, cur_y = win32api.GetCursorPos()
                dx = int(target_x - cur_x)
                dy = int(target_y - cur_y)
                self._send_command(f"km.move({dx},{dy})")
                return
            except Exception:
                pass
        self._send_command(f"km.moveto({target_x},{target_y})")

    def _click_button(self, button: int) -> None:
        self._validate_connection()
        if button not in {BUTTON_LEFT, BUTTON_RIGHT, BUTTON_MIDDLE}:
            raise ValueError(f"unsupported mouse button: {button}")
        time.sleep(PRE_CLICK_DELAY_S)
        # Align with the proven minimal smoke test command shape:
        # km.click(button, count, interval_ms)
        self._send_command(f"km.click({button},1,{CLICK_DELAY_MS})")
        time.sleep(CLICK_POST_DELAY_S)

    def click(self, x: int, y: int) -> None:
        self.move_and_click(x, y)

    def click_current(self) -> None:
        self._click_button(BUTTON_LEFT)

    def move_and_click(self, x: int, y: int) -> None:
        self._validate_connection()
        # Keep the same stable absolute move path used elsewhere, then click.
        self.move_absolute(int(x), int(y))
        time.sleep(PRE_CLICK_SETTLE_S)
        self._click_button(BUTTON_LEFT)

    def click_right(self, x: int, y: int) -> None:
        self.move_absolute(x, y)
        self._click_button(BUTTON_RIGHT)

    def scroll(self, direction: str, ticks: int) -> None:
        self._validate_connection()
        normalized = direction.lower()
        if normalized not in ("up", "down"):
            raise ValueError(f"scroll direction must be 'up' or 'down', got: {direction}")
        delta = 1 if normalized == "up" else -1
        for _ in range(ticks):
            self._send_command(f"km.wheel({delta})")
            time.sleep(0.005)

    def _normalize_key_part(self, key_name: str) -> str:
        token = str(key_name).strip()
        if len(token) == 1:
            return token
        lowered = token.lower()
        return MAKCU_KEY_ALIASES.get(lowered, lowered)

    def _parse_key_parts(self, key_name: str) -> List[str]:
        parts = str(key_name).split("+")
        normalized = [self._normalize_key_part(part) for part in parts if str(part).strip()]
        if not normalized:
            raise ValueError("empty key name")
        return normalized

    def _order_key_parts(self, parts: List[str]) -> List[str]:
        modifiers = [part for part in parts if part.lower() in MAKCU_MODIFIER_KEYS]
        main_keys = [part for part in parts if part.lower() not in MAKCU_MODIFIER_KEYS]
        return modifiers + main_keys

    def press(self, key_name: str) -> None:
        self._validate_connection()
        parts = self._order_key_parts(self._parse_key_parts(key_name))
        if len(parts) == 1:
            key = parts[0]
            quote = '"' if '"' not in key else "'"
            self._send_command(f"km.press({quote}{key}{quote},{KEY_HOLD_MS},0)")
            return

        for key in parts:
            quote = '"' if '"' not in key else "'"
            self._send_command(f"km.down({quote}{key}{quote})")
            time.sleep(KEY_DOWN_DELAY_S)
        time.sleep(KEY_HOLD_MS / 1000.0)
        for key in reversed(parts):
            quote = '"' if '"' not in key else "'"
            self._send_command(f"km.up({quote}{key}{quote})")
            time.sleep(KEY_UP_DELAY_S)

    def key_down(self, key_name: str) -> None:
        self._validate_connection()
        for key in self._order_key_parts(self._parse_key_parts(key_name)):
            quote = '"' if '"' not in key else "'"
            self._send_command(f"km.down({quote}{key}{quote})")

    def key_up(self, key_name: str) -> None:
        self._validate_connection()
        for key in reversed(self._order_key_parts(self._parse_key_parts(key_name))):
            quote = '"' if '"' not in key else "'"
            self._send_command(f"km.up({quote}{key}{quote})")

    def close(self) -> None:
        self._disconnect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._disconnect()
        return False
