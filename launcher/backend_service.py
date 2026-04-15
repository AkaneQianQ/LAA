#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ferrum backend-service process lifecycle helpers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class BackendServiceState:
    """Track whether the backend was already running before our launch."""

    existed_before: bool = False
    started_by_us: bool = False
    pid: Optional[int] = None
    started: bool = False
    error: Optional[str] = None


class BackendServiceManager:
    """Best-effort controller for Ferrum backend-service.exe."""

    def __init__(self, executable_path: Path = Path(r"C:\Program Files\Ferrum\ferrum-backend-service.exe")):
        self.executable_path = Path(executable_path)
        self._state = BackendServiceState()

    def is_available(self) -> bool:
        return self.executable_path.exists()

    def _find_running_process(self) -> Optional[dict]:
        try:
            completed = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            return None

        target_name = "ferrum-backend-service.exe"
        for line in completed.stdout.splitlines():
            line = line.strip().strip('"')
            if not line:
                continue
            parts = [part.strip('"') for part in line.split('","')]
            if len(parts) < 2:
                continue
            name = parts[0].lower()
            if name != target_name:
                continue
            try:
                pid = int(parts[1])
            except ValueError:
                pid = 0
            return {"pid": pid, "name": name, "exe": str(self.executable_path)}
        return None

    def ensure_running(self) -> BackendServiceState:
        existing = self._find_running_process()
        if existing is not None:
            self._state = BackendServiceState(
                existed_before=True,
                started_by_us=False,
                pid=int(existing.get("pid") or 0) or None,
                started=False,
            )
            return self._state

        if not self.is_available():
            self._state = BackendServiceState(error=f"backend-service not found: {self.executable_path}")
            return self._state

        creation_flags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            creation_flags |= subprocess.CREATE_NO_WINDOW

        try:
            proc = subprocess.Popen(
                [str(self.executable_path)],
                creationflags=creation_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            self._state = BackendServiceState(
                existed_before=False,
                started_by_us=True,
                pid=int(proc.pid),
                started=True,
            )
            return self._state
        except OSError as exc:
            if getattr(exc, "winerror", None) == 740:
                self._state = BackendServiceState(
                    existed_before=False,
                    started_by_us=False,
                    pid=None,
                    started=False,
                    error="backend-service requires elevation",
                )
                return self._state
            self._state = BackendServiceState(
                existed_before=False,
                started_by_us=False,
                pid=None,
                started=False,
                error=str(exc),
            )
            return self._state
        except Exception as exc:
            self._state = BackendServiceState(
                existed_before=False,
                started_by_us=False,
                pid=None,
                started=False,
                error=str(exc),
            )
            return self._state

    def stop_if_started_by_us(self) -> bool:
        if not self._state.started_by_us or self._state.pid is None:
            return False
        try:
            subprocess.run(
                ["taskkill", "/PID", str(self._state.pid), "/T", "/F"],
                capture_output=True,
                text=True,
                check=False,
            )
            return True
        except Exception:
            return False
        finally:
            self._state = BackendServiceState()

    @property
    def state(self) -> BackendServiceState:
        return self._state
