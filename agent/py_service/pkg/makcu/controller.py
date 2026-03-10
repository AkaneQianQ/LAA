#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MakcuController - Serial communication layer for MAKCU hardware device.
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


@dataclass
class ControllerConfig:
    name: str = "MAKCU-Default"
    port: str = "COM3"
    baudrate: int = 115200
    timeout: float = 1.0


class MakcuConnectionError(Exception):
    """MAKCU device connection error."""


class MakcuController:
    """
    MAKCU hardware controller.

    The public surface matches the controller methods already consumed by the
    workflow runtime so users can switch backends from configuration.
    """

    def __init__(self, port: str = "COM3", baudrate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: Optional[serial.Serial] = None
        self._connected = False

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
                raise TimeoutError("Timed out waiting for MAKCU response")

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
        prompt_index = next((idx for idx, line in enumerate(lines) if ">>>" in line), -1)
        if prompt_index == -1:
            return "\n".join(lines)
        return "\n".join(lines[:prompt_index])

    def _send_command(self, command: str, retry: bool = True, wait_response: bool = True) -> str:
        self._validate_connection()
        try:
            self._serial.write(f"{command}\r\n".encode("utf-8"))
            if not wait_response:
                return ""
            return self._read_response()
        except (serial.SerialException, TimeoutError) as exc:
            if retry:
                time.sleep(0.1)
                return self._send_command(command, retry=False, wait_response=wait_response)
            raise MakcuConnectionError(f"Command failed '{command}': {exc}") from exc

    def _initialize_device(self) -> None:
        if self._serial and self._serial.is_open:
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
        self._send_command("km.init()")

    def wait(self, seconds: float) -> None:
        time.sleep(seconds)

    def is_connected(self) -> bool:
        return self._connected and self._serial is not None and self._serial.is_open

    def handshake(self) -> bool:
        try:
            self._validate_connection()
            self._send_command("km.init()")
            return True
        except Exception as exc:
            logger.warning("[MAKCU] Handshake failed: %s", exc)
            return False

    def _move(self, x: int, y: int) -> None:
        self._send_command(f"km.move({x}, {y})")

    def move_absolute(self, x: int, y: int) -> None:
        if not WIN32_AVAILABLE or win32api is None:
            raise RuntimeError("win32api not available, cannot get current cursor position")

        current_x, current_y = win32api.GetCursorPos()
        self._move(x - current_x, y - current_y)

    def click(self, x: int, y: int) -> None:
        self._validate_connection()
        self._move(x, y)
        self._send_command(f"km.click({BUTTON_LEFT})")
        time.sleep(CLICK_POST_DELAY_S)

    def click_current(self) -> None:
        self._validate_connection()
        self._send_command(f"km.click({BUTTON_LEFT})")
        time.sleep(CLICK_POST_DELAY_S)

    def move_and_click(self, x: int, y: int) -> None:
        if not WIN32_AVAILABLE or win32api is None:
            raise RuntimeError("win32api not available")

        self._validate_connection()
        current_x, current_y = win32api.GetCursorPos()
        dx = x - current_x
        dy = y - current_y

        self._serial.reset_input_buffer()
        self._serial.write(f"km.move({dx}, {dy})\r\n".encode("utf-8"))
        time.sleep(0.005)
        self._send_command(f"km.click({BUTTON_LEFT})")
        time.sleep(CLICK_POST_DELAY_S)

    def click_right(self, x: int, y: int) -> None:
        self._validate_connection()
        self._move(x, y)
        self._send_command(f"km.click({BUTTON_RIGHT})")
        time.sleep(CLICK_POST_DELAY_S)

    def scroll(self, direction: str, ticks: int) -> None:
        self._validate_connection()
        direction = direction.lower()
        if direction not in ("up", "down"):
            raise ValueError(f"scroll direction must be 'up' or 'down', got: {direction}")

        amount = 1 if direction == "up" else -1
        for _ in range(ticks):
            self._send_command(f"km.wheel({amount})")
            time.sleep(0.005)

    def press(self, key_name: str) -> None:
        self._validate_connection()
        self._send_command(f"km.press('{key_name.lower()}')")

    def key_down(self, key_name: str) -> None:
        self._validate_connection()
        self._send_command(f"km.down('{key_name.lower()}')")

    def key_up(self, key_name: str) -> None:
        self._validate_connection()
        self._send_command(f"km.up('{key_name.lower()}')")

    def close(self) -> None:
        self._disconnect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._disconnect()
        return False
