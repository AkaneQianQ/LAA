#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DD-driver keyboard input adapter for Hybrid MAKCU path."""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import List
from threading import Lock

try:
    from .third_party.pydd import PyDD
except ImportError:
    PyDD = None

try:
    import keyboard as keyboard_lib
except ImportError:
    keyboard_lib = None

from agent.py_service.pkg.ferrum.controller import KEY_MAP, MODIFIER_CODES


logger = logging.getLogger(__name__)
_PYDD_SINGLETON = None
_PYDD_SINGLETON_DLL = ""
_PYDD_LOCK = Lock()

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
    """Route keyboard actions through DD driver (pydd), with optional fallback."""

    def __init__(self) -> None:
        self._backend = "pydd"
        self._dd = None
        self._force_pydd = str(os.environ.get("LAA_FORCE_PYDD", "1")).strip().lower() not in {"0", "false", "no", "off"}
        dll_path = self._resolve_dd_dll_path()

        if PyDD is None:
            if self._force_pydd:
                raise RuntimeError("pydd module is unavailable")
            if keyboard_lib is None:
                raise RuntimeError("pydd module is unavailable and keyboard fallback is unavailable")
            self._backend = "keyboard"
            logger.warning("[Hardware] pydd unavailable, fallback to keyboard backend")
            return

        try:
            self._register_dll_search_dir(dll_path)
            self._dd = self._init_pydd_with_retry(dll_path=dll_path)
            logger.info("[Hardware] Keyboard backend selected: pydd (%s)", dll_path)
        except Exception as exc:
            if self._force_pydd:
                raise RuntimeError(f"pydd init failed: {exc}") from exc
            if keyboard_lib is None:
                raise RuntimeError(f"pydd init failed and keyboard fallback unavailable: {exc}") from exc
            self._backend = "keyboard"
            logger.warning("[Hardware] pydd init failed, fallback to keyboard backend: %s", exc)

    def _init_pydd_with_retry(self, dll_path: str, attempts: int = 3, delay_s: float = 0.35):
        global _PYDD_SINGLETON, _PYDD_SINGLETON_DLL
        with _PYDD_LOCK:
            if _PYDD_SINGLETON is not None:
                logger.info("[Hardware] Reuse existing pydd instance (%s)", _PYDD_SINGLETON_DLL or dll_path)
                return _PYDD_SINGLETON

        last_exc: Exception | None = None
        for idx in range(max(1, int(attempts))):
            try:
                instance = PyDD(dll_path=dll_path)
                with _PYDD_LOCK:
                    _PYDD_SINGLETON = instance
                    _PYDD_SINGLETON_DLL = dll_path
                return instance
            except Exception as exc:
                last_exc = exc
                if idx < attempts - 1:
                    logger.warning(
                        "[Hardware] pydd init attempt %d/%d failed, retrying in %.2fs: %s",
                        idx + 1,
                        attempts,
                        delay_s,
                        exc,
                    )
                    time.sleep(delay_s)
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("pydd init failed with unknown error")

    def _resolve_dd_dll_path(self) -> str:
        module_dir = Path(__file__).resolve().parent
        env_path = str(os.environ.get("LAA_DD_DLL_PATH", "")).strip()
        candidates: List[Path] = []

        if env_path:
            candidates.append(Path(env_path).expanduser())

        # Source tree default.
        candidates.append(module_dir / "drivers" / "dd.54900.dll")

        # Dist layout candidates.
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "agent" / "py_service" / "pkg" / "input" / "drivers" / "dd.54900.dll")
        candidates.append(exe_dir / "_internal" / "agent" / "py_service" / "pkg" / "input" / "drivers" / "dd.54900.dll")

        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "agent" / "py_service" / "pkg" / "input" / "drivers" / "dd.54900.dll")

        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved.exists():
                return str(resolved)

        fallback = module_dir / "drivers" / "dd.54900.dll"
        return str(fallback)

    def _register_dll_search_dir(self, dll_path: str) -> None:
        """Help Windows resolve dependent DLLs alongside DD driver."""
        dll_dir = Path(dll_path).resolve().parent
        try:
            os.add_dll_directory(str(dll_dir))
        except Exception:
            # Best effort only; older Python/Windows may not support this.
            return

    def wait(self, seconds: float) -> None:
        time.sleep(seconds)

    def is_connected(self) -> bool:
        if self._backend == "pydd":
            return self._dd is not None
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

    def _to_dd_key(self, ferrum_key_name: str) -> str:
        normalized = self._to_python_key(ferrum_key_name).lower().strip()
        # pydd does not expose left/right modifier variants in key_name_map.
        if normalized in {"left ctrl", "right ctrl"}:
            return "ctrl"
        if normalized in {"left shift", "right shift"}:
            return "shift"
        if normalized in {"left alt", "right alt"}:
            return "alt"
        return normalized

    def press(self, key_name: str) -> None:
        parts = self._order_parts(self._parse_key_parts(key_name))
        logger.info("[Hardware] Keyboard press (%s): %s -> %s", self._backend, key_name, parts)
        if self._backend == "pydd":
            for part in parts:
                self._dd.key_down(self._to_dd_key(part))
                time.sleep(KEY_DOWN_DELAY_S)
            time.sleep(KEY_HOLD_DELAY_S)
            for part in reversed(parts):
                self._dd.key_up(self._to_dd_key(part))
                time.sleep(KEY_UP_DELAY_S)
            return
        for part in parts:
            keyboard_lib.press(self._to_python_key(part))
            time.sleep(KEY_DOWN_DELAY_S)
        time.sleep(KEY_HOLD_DELAY_S)
        for part in reversed(parts):
            keyboard_lib.release(self._to_python_key(part))
            time.sleep(KEY_UP_DELAY_S)

    def key_down(self, key_name: str) -> None:
        parts = self._order_parts(self._parse_key_parts(key_name))
        logger.info("[Hardware] Keyboard down (%s): %s -> %s", self._backend, key_name, parts)
        if self._backend == "pydd":
            for part in parts:
                self._dd.key_down(self._to_dd_key(part))
            return
        for part in parts:
            keyboard_lib.press(self._to_python_key(part))

    def key_up(self, key_name: str) -> None:
        parts = self._order_parts(self._parse_key_parts(key_name))
        logger.info("[Hardware] Keyboard up (%s): %s -> %s", self._backend, key_name, parts)
        if self._backend == "pydd":
            for part in reversed(parts):
                self._dd.key_up(self._to_dd_key(part))
            return
        for part in reversed(parts):
            keyboard_lib.release(self._to_python_key(part))

    def close(self) -> None:
        # Keep pydd singleton alive for process lifetime to avoid re-init flapping.
        return None
