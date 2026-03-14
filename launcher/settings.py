#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persistent settings for the desktop launcher."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from launcher.update_service import DEFAULT_UPDATE_REPO, LEGACY_UPDATE_REPOS, ProxyConfig


DEFAULT_DRIVER_BACKEND = "ferrum"
DEFAULT_BAUDRATE = 115200


@dataclass(frozen=True)
class LauncherSettings:
    driver_backend: str = DEFAULT_DRIVER_BACKEND
    ports: dict[str, str] = field(default_factory=lambda: {"ferrum": "COM2", "makcu": "COM3"})
    baudrates: dict[str, int] = field(default_factory=lambda: {"ferrum": DEFAULT_BAUDRATE, "makcu": DEFAULT_BAUDRATE})
    keyboard_via_python: bool = True
    force_pydd: bool = True
    update_repo: str = DEFAULT_UPDATE_REPO
    update_proxy: ProxyConfig = field(default_factory=ProxyConfig)
    task_checked: dict[str, bool] = field(default_factory=dict)
    task_visibility: dict[str, bool] = field(default_factory=dict)
    task_order: list[str] = field(default_factory=list)


class LauncherSettingsStore:
    """Read and write small launcher settings JSON files."""

    def __init__(self, settings_path: Path):
        self.settings_path = Path(settings_path)

    def load(self) -> LauncherSettings:
        if not self.settings_path.exists():
            return LauncherSettings()

        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return LauncherSettings()

        driver_backend = str(payload.get("driver_backend", DEFAULT_DRIVER_BACKEND)).lower()
        if driver_backend not in {"ferrum", "makcu"}:
            driver_backend = DEFAULT_DRIVER_BACKEND
        ports_raw = payload.get("ports", {})
        ports = {
            "ferrum": str(ports_raw.get("ferrum", "COM2")),
            "makcu": str(ports_raw.get("makcu", "COM3")),
        }
        baudrates_raw = payload.get("baudrates", {})
        baudrates = {
            "ferrum": self._normalize_baudrate(
                baudrates_raw.get("ferrum", DEFAULT_BAUDRATE),
                default=DEFAULT_BAUDRATE,
            ),
            "makcu": self._normalize_baudrate(
                baudrates_raw.get("makcu", DEFAULT_BAUDRATE),
                default=DEFAULT_BAUDRATE,
            ),
        }
        task_checked_raw = payload.get("task_checked", {})
        task_visibility_raw = payload.get("task_visibility", {})
        task_order_raw = payload.get("task_order", [])
        keyboard_via_python = bool(payload.get("keyboard_via_python", True))
        force_pydd = bool(payload.get("force_pydd", True))
        update_repo = str(payload.get("update_repo", DEFAULT_UPDATE_REPO)).strip() or DEFAULT_UPDATE_REPO
        if update_repo in LEGACY_UPDATE_REPOS:
            update_repo = DEFAULT_UPDATE_REPO
        update_proxy_raw = payload.get("update_proxy", {})
        task_checked = {
            str(name): bool(value)
            for name, value in task_checked_raw.items()
        } if isinstance(task_checked_raw, dict) else {}
        task_visibility = {
            str(name): bool(value)
            for name, value in task_visibility_raw.items()
        } if isinstance(task_visibility_raw, dict) else {}
        task_order = [str(name) for name in task_order_raw] if isinstance(task_order_raw, list) else []
        return LauncherSettings(
            driver_backend=driver_backend,
            ports=ports,
            baudrates=baudrates,
            keyboard_via_python=keyboard_via_python,
            force_pydd=force_pydd,
            update_repo=update_repo,
            update_proxy=self._load_proxy_config(update_proxy_raw),
            task_checked=task_checked,
            task_visibility=task_visibility,
            task_order=task_order,
        )

    def save(self, settings: LauncherSettings) -> None:
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            json.dumps(asdict(settings), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _normalize_baudrate(value: object, default: int = DEFAULT_BAUDRATE) -> int:
        try:
            baudrate = int(value)
        except (TypeError, ValueError):
            return int(default)
        if baudrate <= 0:
            return int(default)
        return baudrate

    @staticmethod
    def _load_proxy_config(payload: object) -> ProxyConfig:
        if not isinstance(payload, dict):
            return ProxyConfig()
        scheme = str(payload.get("scheme", "http")).strip().lower()
        if scheme not in {"http", "socks5"}:
            scheme = "http"
        return ProxyConfig(
            enabled=bool(payload.get("enabled", False)),
            scheme=scheme,
            host=str(payload.get("host", "")).strip(),
            port=LauncherSettingsStore._normalize_baudrate(payload.get("port", 0), default=0),
            username=str(payload.get("username", "")),
            password=str(payload.get("password", "")),
        )
