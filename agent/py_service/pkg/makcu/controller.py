#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MakcuController - Legacy API serial communication layer for MAKCU hardware.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

import serial

try:
    import win32api

    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    win32api = None


logger = logging.getLogger(__name__)

BUTTON_LEFT = 0
BUTTON_RIGHT = 1
BUTTON_MIDDLE = 2
CLICK_POST_DELAY_S = 0.1

BUTTON_PRESS_COMMANDS = {
    BUTTON_LEFT: "km.left(1)",
    BUTTON_RIGHT: "km.right(1)",
    BUTTON_MIDDLE: "km.middle(1)",
}

BUTTON_RELEASE_COMMANDS = {
    BUTTON_LEFT: "km.left(0)",
    BUTTON_RIGHT: "km.right(0)",
    BUTTON_MIDDLE: "km.middle(0)",
}


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
            if not wait_response:
                logger.info("[Hardware] MAKCU ack: %s -> <no-wait>", command)
                return ""
            response = self._read_response()
            logger.info("[Hardware] MAKCU ack: %s -> %s", command, response or "<empty>")
            return response
        except (serial.SerialException, TimeoutError) as exc:
            if retry:
                time.sleep(0.05)
                return self._send_command(command, retry=False, wait_response=wait_response)
            raise MakcuConnectionError(f"Command failed '{command}': {exc}") from exc

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
        if not WIN32_AVAILABLE:
            raise MakcuConnectionError("Absolute cursor movement requires win32api on Windows")
        try:
            win32api.SetCursorPos((int(x), int(y)))
        except Exception as exc:
            logger.warning("[Hardware] MAKCU absolute move fallback: %s", exc)

    def _click_button(self, button: int) -> None:
        self._validate_connection()
        press_command = BUTTON_PRESS_COMMANDS.get(button)
        release_command = BUTTON_RELEASE_COMMANDS.get(button)
        if press_command is None or release_command is None:
            raise ValueError(f"unsupported mouse button: {button}")
        self._send_command(press_command)
        self._send_command(release_command)
        time.sleep(CLICK_POST_DELAY_S)

    def click(self, x: int, y: int) -> None:
        self.move_absolute(x, y)
        self.click_current()

    def click_current(self) -> None:
        self._click_button(BUTTON_LEFT)

    def move_and_click(self, x: int, y: int) -> None:
        self.move_absolute(x, y)
        self.click_current()

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

    def press(self, key_name: str) -> None:
        self._validate_connection()
        self._send_command(f"km.press('{str(key_name).lower()}')")

    def key_down(self, key_name: str) -> None:
        self._validate_connection()
        self._send_command(f"km.down('{str(key_name).lower()}')")

    def key_up(self, key_name: str) -> None:
        self._validate_connection()
        self._send_command(f"km.up('{str(key_name).lower()}')")

    def close(self) -> None:
        self._disconnect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._disconnect()
        return False
