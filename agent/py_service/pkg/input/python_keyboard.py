#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local Python keyboard input adapter."""

from __future__ import annotations

import logging
import time

try:
    import keyboard as keyboard_lib
except ImportError:
    keyboard_lib = None


logger = logging.getLogger(__name__)


class PythonKeyboardController:
    """Route keyboard actions through the local Python keyboard package."""

    def __init__(self) -> None:
        if keyboard_lib is None:
            raise RuntimeError("python keyboard package is unavailable")

    def wait(self, seconds: float) -> None:
        time.sleep(seconds)

    def is_connected(self) -> bool:
        return keyboard_lib is not None

    def handshake(self) -> bool:
        return self.is_connected()

    def press(self, key_name: str) -> None:
        normalized = str(key_name).lower()
        logger.info("[Hardware] Python keyboard press: %s", normalized)
        keyboard_lib.press_and_release(normalized)

    def key_down(self, key_name: str) -> None:
        normalized = str(key_name).lower()
        logger.info("[Hardware] Python keyboard down: %s", normalized)
        keyboard_lib.press(normalized)

    def key_up(self, key_name: str) -> None:
        normalized = str(key_name).lower()
        logger.info("[Hardware] Python keyboard up: %s", normalized)
        keyboard_lib.release(normalized)

    def close(self) -> None:
        return None
