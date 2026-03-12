#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local Python keyboard input adapter."""

from __future__ import annotations

import logging
import time
from typing import List

try:
    import keyboard as keyboard_lib
except ImportError:
    keyboard_lib = None

from agent.py_service.pkg.ferrum.controller import KEY_MAP, MODIFIER_CODES


logger = logging.getLogger(__name__)

KEY_DOWN_DELAY_S = 0.012
KEY_HOLD_DELAY_S = 0.06
KEY_UP_DELAY_S = 0.008

FERRUM_TO_PYTHON_KEY = {
    "return": "enter",
    "escape": "esc",
    "bs": "backspace",
    "spacebar": "space",
    "arrowup": "up",
    "arrowdown": "down",
    "arrowleft": "left",
    "arrowright": "right",
    "control": "ctrl",
    "leftctrl": "left ctrl",
    "rightctrl": "right ctrl",
    "leftshift": "left shift",
    "rightshift": "right shift",
    "leftalt": "left alt",
    "rightalt": "right alt",
    "lctrl": "left ctrl",
    "rctrl": "right ctrl",
    "lshift": "left shift",
    "rshift": "right shift",
    "lalt": "left alt",
    "ralt": "right alt",
}


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

    def _parse_key_parts(self, key_name: str) -> List[str]:
        parts = str(key_name).lower().split("+")
        normalized_parts: List[str] = []
        for part in parts:
            token = part.strip()
            if token not in KEY_MAP:
                raise ValueError(f"unknown Ferrum key name: {token}")
            normalized_parts.append(token)
        return normalized_parts

    def _order_parts(self, parts: List[str]) -> List[str]:
        modifiers = [part for part in parts if KEY_MAP[part] in MODIFIER_CODES]
        main_keys = [part for part in parts if KEY_MAP[part] not in MODIFIER_CODES]
        return modifiers + main_keys

    def _to_python_key(self, ferrum_key_name: str) -> str:
        return FERRUM_TO_PYTHON_KEY.get(ferrum_key_name, ferrum_key_name)

    def press(self, key_name: str) -> None:
        parts = self._order_parts(self._parse_key_parts(key_name))
        logger.info("[Hardware] Python keyboard press: %s -> %s", key_name, parts)
        for part in parts:
            keyboard_lib.press(self._to_python_key(part))
            time.sleep(KEY_DOWN_DELAY_S)
        time.sleep(KEY_HOLD_DELAY_S)
        for part in reversed(parts):
            keyboard_lib.release(self._to_python_key(part))
            time.sleep(KEY_UP_DELAY_S)

    def key_down(self, key_name: str) -> None:
        parts = self._order_parts(self._parse_key_parts(key_name))
        logger.info("[Hardware] Python keyboard down: %s -> %s", key_name, parts)
        for part in parts:
            keyboard_lib.press(self._to_python_key(part))

    def key_up(self, key_name: str) -> None:
        parts = self._order_parts(self._parse_key_parts(key_name))
        logger.info("[Hardware] Python keyboard up: %s -> %s", key_name, parts)
        for part in reversed(parts):
            keyboard_lib.release(self._to_python_key(part))

    def close(self) -> None:
        return None
