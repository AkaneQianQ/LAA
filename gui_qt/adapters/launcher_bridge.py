#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Qt-friendly bridge over the existing launcher service layer."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QObject, Signal

from launcher.service import (
    DEFAULT_CONFIG_PATH,
    discard_account_indexing_staging,
    focus_lostark_window,
    load_latest_account_indexing_staging_summary,
    load_interface_config,
    probe_controller,
    run_selected_task,
    save_account_indexing_staging,
)
from launcher.settings import LauncherSettings, LauncherSettingsStore
from launcher.trigger_service import run_independent_trigger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "data" / "ui_settings.json"


class LauncherBridge(QObject):
    """Bridge existing launcher helpers into Qt signals and worker threads."""

    log_emitted = Signal(str)
    task_started = Signal(str)
    task_finished = Signal(bool)
    trigger_started = Signal()
    trigger_finished = Signal()
    probe_finished = Signal(bool, str)
    account_indexing_staged = Signal(dict)

    def __init__(self, settings_path: Path | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings_store = LauncherSettingsStore(settings_path or DEFAULT_SETTINGS_PATH)
        self._task_thread: threading.Thread | None = None
        self._trigger_thread: threading.Thread | None = None
        self._busy_lock = threading.Lock()
        self._busy = False
        self._task_stop_event = threading.Event()
        self._trigger_stop_event = threading.Event()
        self._sleep = time.sleep
        self._task_executor = run_selected_task
        self._focus_executor = focus_lostark_window
        self._probe_executor = probe_controller
        self._trigger_executor = run_independent_trigger

    def load_settings(self) -> LauncherSettings:
        return self._settings_store.load()

    def save_settings(
        self,
        driver_backend: str,
        ports: dict[str, str],
        task_checked: dict[str, bool] | None = None,
        task_visibility: dict[str, bool] | None = None,
        task_order: list[str] | None = None,
    ) -> None:
        current = self._settings_store.load()
        self._settings_store.save(
            LauncherSettings(
                driver_backend=driver_backend,
                ports=ports,
                task_checked=dict(task_checked if task_checked is not None else current.task_checked),
                task_visibility=dict(task_visibility if task_visibility is not None else current.task_visibility),
                task_order=list(task_order if task_order is not None else current.task_order),
            )
        )

    def load_interface(self):
        return load_interface_config(DEFAULT_CONFIG_PATH)

    def is_busy(self) -> bool:
        with self._busy_lock:
            return self._busy

    def _set_busy(self, busy: bool) -> None:
        with self._busy_lock:
            self._busy = busy

    def start_task(self, task_name: str, controller_name: str, port: str | None = None) -> None:
        if self.is_busy():
            raise RuntimeError("launcher bridge is busy")

        self._set_busy(True)
        self._task_stop_event = threading.Event()
        self.task_started.emit(task_name)

        def worker() -> None:
            success = False
            try:
                focus_result = self._focus_executor()
                if focus_result.ok:
                    self._sleep(1.0)
                else:
                    self.log_emitted.emit(f"[Launcher] {focus_result.message}")
                success = bool(
                    self._task_executor(
                        task_name,
                        controller_name,
                        port=port,
                        log_writer=self.log_emitted.emit,
                        stop_event=self._task_stop_event,
                    )
                )
            except Exception as exc:
                self.log_emitted.emit(f"[ERROR] {exc}")
                success = False
            finally:
                if success and task_name == "AccountIndexing":
                    try:
                        summary = load_latest_account_indexing_staging_summary(str(PROJECT_ROOT / "data"))
                        if summary:
                            self.account_indexing_staged.emit(summary)
                    except Exception as exc:
                        self.log_emitted.emit(f"[Launcher] failed to load staged account indexing summary: {exc}")
                self._set_busy(False)
                self.task_finished.emit(success)

        self._task_thread = threading.Thread(target=worker, name="qt-launcher-task", daemon=True)
        self._task_thread.start()

    def stop_task(self) -> None:
        self._task_stop_event.set()
        self.log_emitted.emit("[Launcher] task stop requested")

    def probe(self, interface_config: dict, driver_backend: str, port: str) -> None:
        def worker() -> None:
            result = self._probe_executor(interface_config, driver_backend, port)
            self.probe_finished.emit(result.ok, result.message)

        threading.Thread(target=worker, name="qt-launcher-probe", daemon=True).start()

    def start_trigger(self, interface_config: dict, driver_backend: str, port: str) -> None:
        if self.is_busy():
            raise RuntimeError("launcher bridge is busy")

        self._set_busy(True)
        self._trigger_stop_event = threading.Event()
        self.trigger_started.emit()

        def worker() -> None:
            try:
                self._trigger_executor(
                    interface_config=interface_config,
                    driver_backend=driver_backend,
                    port=port,
                    stop_event=self._trigger_stop_event,
                    log_writer=self.log_emitted.emit,
                )
            finally:
                self._set_busy(False)
                self.trigger_finished.emit()

        self._trigger_thread = threading.Thread(target=worker, name="qt-launcher-trigger", daemon=True)
        self._trigger_thread.start()

    def stop_trigger(self) -> None:
        self._trigger_stop_event.set()

    def wait_for_idle(self, timeout: float = 2.0) -> None:
        deadline = time.time() + timeout
        app = QCoreApplication.instance()
        while time.time() < deadline:
            if app is not None:
                app.processEvents()
            task_alive = self._task_thread is not None and self._task_thread.is_alive()
            trigger_alive = self._trigger_thread is not None and self._trigger_thread.is_alive()
            if not task_alive and not trigger_alive and not self.is_busy():
                if app is not None:
                    app.processEvents()
                return
            time.sleep(0.01)
        raise TimeoutError("launcher bridge did not become idle before timeout")

    def save_account_indexing_staging(self, session_id: str) -> dict:
        return save_account_indexing_staging(
            db_path=str(PROJECT_ROOT / "data" / "accounts.db"),
            data_dir=str(PROJECT_ROOT / "data"),
            session_id=session_id,
        )

    def discard_account_indexing_staging(self, session_id: str) -> dict:
        return discard_account_indexing_staging(
            data_dir=str(PROJECT_ROOT / "data"),
            session_id=session_id,
        )
