#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Background task execution for the launcher."""

from __future__ import annotations

import threading
from typing import Callable, Optional


class LauncherTaskRunner:
    """Run a selected task in a background thread."""

    def __init__(self, task_func: Callable[..., bool]):
        self._task_func = task_func
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._busy = False

    def is_busy(self) -> bool:
        with self._lock:
            return self._busy

    def start(
        self,
        task_name: str,
        controller_name: str,
        log_writer: Callable[[str], None],
        on_complete: Callable[[bool], None],
        port: Optional[str] = None,
    ) -> None:
        with self._lock:
            if self._busy:
                raise RuntimeError("task runner is already busy")
            self._busy = True

        def worker() -> None:
            success = False
            try:
                if port is None:
                    success = bool(self._task_func(task_name, controller_name, log_writer))
                else:
                    success = bool(self._task_func(task_name, controller_name, port=port, log_writer=log_writer))
            except Exception as exc:
                log_writer(f"[ERROR] {exc}")
                success = False
            finally:
                with self._lock:
                    self._busy = False
                on_complete(success)

        self._thread = threading.Thread(target=worker, name="launcher-task-runner", daemon=True)
        self._thread.start()

    def join(self, timeout: Optional[float] = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout=timeout)
