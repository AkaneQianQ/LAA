#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hybrid Makcu mouse + Python keyboard controller."""

from __future__ import annotations

from agent.py_service.pkg.makcu.controller import MakcuController

from .python_keyboard import PythonKeyboardController


class HybridMakcuController:
    """Keep Makcu mouse path while routing keyboard to Python."""

    def __init__(self, port: str = "COM3", baudrate: int = 115200, timeout: float = 1.0):
        self._mouse = MakcuController(port=port, baudrate=baudrate, timeout=timeout)
        self._keyboard = PythonKeyboardController()

    def wait(self, seconds: float) -> None:
        self._mouse.wait(seconds)

    def is_connected(self) -> bool:
        return self._mouse.is_connected() and self._keyboard.is_connected()

    def handshake(self) -> bool:
        return self._mouse.handshake() and self._keyboard.handshake()

    def move_absolute(self, x: int, y: int) -> None:
        self._mouse.move_absolute(x, y)

    def click(self, x: int, y: int) -> None:
        self._mouse.click(x, y)

    def click_current(self) -> None:
        self._mouse.click_current()

    def move_and_click(self, x: int, y: int) -> None:
        self._mouse.move_and_click(x, y)

    def click_right(self, x: int, y: int) -> None:
        self._mouse.click_right(x, y)

    def scroll(self, direction: str, ticks: int) -> None:
        self._mouse.scroll(direction, ticks)

    def press(self, key_name: str) -> None:
        self._keyboard.press(key_name)

    def key_down(self, key_name: str) -> None:
        self._keyboard.key_down(key_name)

    def key_up(self, key_name: str) -> None:
        self._keyboard.key_up(key_name)

    def close(self) -> None:
        try:
            self._keyboard.close()
        finally:
            self._mouse.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
