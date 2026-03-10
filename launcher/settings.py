#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persistent settings for the desktop launcher."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


DEFAULT_DRIVER_BACKEND = "ferrum"


@dataclass(frozen=True)
class LauncherSettings:
    driver_backend: str = DEFAULT_DRIVER_BACKEND
    ports: dict[str, str] = field(default_factory=lambda: {"ferrum": "COM2", "makcu": "COM3"})
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
        task_checked_raw = payload.get("task_checked", {})
        task_visibility_raw = payload.get("task_visibility", {})
        task_order_raw = payload.get("task_order", [])
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
