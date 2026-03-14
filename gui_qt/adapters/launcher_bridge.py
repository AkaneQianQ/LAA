#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Qt-friendly bridge over the existing launcher service layer."""

from __future__ import annotations

import threading
import time
import os
import shutil
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
from launcher.update_service import GitHubUpdateService, ProxyConfig, download_and_apply_release, validate_release_metadata


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGACY_SETTINGS_PATH = PROJECT_ROOT / "data" / "ui_settings.json"


def _default_settings_root() -> Path:
    custom = str(os.environ.get("LAA_SETTINGS_DIR", "")).strip()
    if custom:
        return Path(custom).expanduser()

    if os.name == "nt":
        local_appdata = str(os.environ.get("LOCALAPPDATA", "")).strip()
        if local_appdata:
            return Path(local_appdata) / "LAA"

    xdg_state_home = str(os.environ.get("XDG_STATE_HOME", "")).strip()
    if xdg_state_home:
        return Path(xdg_state_home) / "LAA"

    return PROJECT_ROOT / "data"


def default_settings_path() -> Path:
    return _default_settings_root() / "ui_settings.json"


def _latest_archived_settings_path() -> Path | None:
    cleanup_root = PROJECT_ROOT / "archive" / "cleanup"
    if not cleanup_root.exists():
        return None
    candidates = sorted(cleanup_root.glob("*/runtime/data/ui_settings.json"))
    if not candidates:
        return None
    try:
        return max(candidates, key=lambda path: path.stat().st_mtime)
    except OSError:
        return candidates[-1]


def ensure_settings_migrated(settings_path: Path) -> Path:
    target = Path(settings_path)
    if target.exists():
        return target

    migration_candidates = [LEGACY_SETTINGS_PATH, _latest_archived_settings_path()]
    for candidate in migration_candidates:
        if candidate is None or not candidate.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidate, target)
        return target
    return target


class LauncherBridge(QObject):
    """Bridge existing launcher helpers into Qt signals and worker threads."""

    log_emitted = Signal(str)
    task_started = Signal(str)
    task_finished = Signal(bool)
    trigger_started = Signal()
    trigger_finished = Signal()
    probe_finished = Signal(bool, str)
    account_indexing_staged = Signal(dict)
    update_download_progress = Signal(int, int, int)

    def __init__(self, settings_path: Path | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        resolved_settings_path = ensure_settings_migrated(Path(settings_path) if settings_path is not None else default_settings_path())
        self._settings_store = LauncherSettingsStore(resolved_settings_path)
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
        self._update_checker = self._default_check_for_updates
        self._update_downloader = self._default_download_and_apply_update

    def load_settings(self) -> LauncherSettings:
        return self._settings_store.load()

    def save_settings(
        self,
        driver_backend: str,
        ports: dict[str, str],
        baudrates: dict[str, int] | None = None,
        keyboard_via_python: bool | None = None,
        force_pydd: bool | None = None,
        update_repo: str | None = None,
        update_proxy: ProxyConfig | None = None,
        task_checked: dict[str, bool] | None = None,
        task_visibility: dict[str, bool] | None = None,
        task_order: list[str] | None = None,
    ) -> None:
        current = self._settings_store.load()
        self._settings_store.save(
            LauncherSettings(
                driver_backend=driver_backend,
                ports=ports,
                baudrates=dict(baudrates if baudrates is not None else current.baudrates),
                keyboard_via_python=bool(current.keyboard_via_python if keyboard_via_python is None else keyboard_via_python),
                force_pydd=bool(current.force_pydd if force_pydd is None else force_pydd),
                update_repo=str(update_repo if update_repo is not None else current.update_repo),
                update_proxy=update_proxy if update_proxy is not None else current.update_proxy,
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

    def start_task(
        self,
        task_name: str,
        controller_name: str,
        port: str | None = None,
        baudrate: int | None = None,
        keyboard_via_python: bool = False,
        force_pydd: bool | None = None,
    ) -> None:
        if self.is_busy():
            raise RuntimeError("launcher bridge is busy")

        self._set_busy(True)
        self._task_stop_event = threading.Event()
        self.task_started.emit(task_name)

        def worker() -> None:
            success = False
            try:
                if force_pydd is not None:
                    os.environ["LAA_FORCE_PYDD"] = "1" if bool(force_pydd) else "0"
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
                        baudrate=baudrate,
                        keyboard_via_python=keyboard_via_python,
                        log_writer=self.log_emitted.emit,
                        stop_event=self._task_stop_event,
                    )
                )
            except TypeError:
                success = bool(
                    self._task_executor(
                        task_name,
                        controller_name,
                        port=port,
                        baudrate=baudrate,
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

    def probe(
        self,
        interface_config: dict,
        driver_backend: str,
        port: str,
        baudrate: int | None = None,
        keyboard_via_python: bool = False,
        force_pydd: bool | None = None,
    ) -> None:
        def worker() -> None:
            if force_pydd is not None:
                os.environ["LAA_FORCE_PYDD"] = "1" if bool(force_pydd) else "0"
            try:
                result = self._probe_executor(interface_config, driver_backend, port, baudrate, keyboard_via_python)
            except TypeError:
                result = self._probe_executor(interface_config, driver_backend, port, baudrate)
            self.probe_finished.emit(result.ok, result.message)

        threading.Thread(target=worker, name="qt-launcher-probe", daemon=True).start()

    def start_trigger(
        self,
        interface_config: dict,
        driver_backend: str,
        port: str,
        baudrate: int | None = None,
        keyboard_via_python: bool = False,
        force_pydd: bool | None = None,
    ) -> None:
        if self.is_busy():
            raise RuntimeError("launcher bridge is busy")

        self._set_busy(True)
        self._trigger_stop_event = threading.Event()
        self.trigger_started.emit()

        def worker() -> None:
            try:
                if force_pydd is not None:
                    os.environ["LAA_FORCE_PYDD"] = "1" if bool(force_pydd) else "0"
                try:
                    self._trigger_executor(
                        interface_config=interface_config,
                        driver_backend=driver_backend,
                        port=port,
                        baudrate=baudrate,
                        keyboard_via_python=keyboard_via_python,
                        force_pydd=force_pydd,
                        stop_event=self._trigger_stop_event,
                        log_writer=self.log_emitted.emit,
                    )
                except TypeError:
                    self._trigger_executor(
                        interface_config=interface_config,
                        driver_backend=driver_backend,
                        port=port,
                        baudrate=baudrate,
                        stop_event=self._trigger_stop_event,
                        log_writer=self.log_emitted.emit,
                    )
            except Exception as exc:
                self.log_emitted.emit(f"[ERROR] trigger failed: {exc}")
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

    def check_for_updates(self, current_version: str) -> dict:
        settings = self._settings_store.load()
        result = dict(
            self._update_checker(
                repo=settings.update_repo,
                current_version=current_version,
                proxy=settings.update_proxy,
            )
        )
        result["release_issues"] = list(validate_release_metadata(result))
        return result

    @staticmethod
    def _default_check_for_updates(repo: str, current_version: str, proxy: ProxyConfig) -> dict:
        release = GitHubUpdateService(
            repo=repo,
            current_version=current_version,
            proxy=proxy,
        ).fetch_latest_release()
        return {
            "version": release.version,
            "tag_name": release.tag_name,
            "published_at": release.published_at,
            "html_url": release.html_url,
            "body": release.body,
            "is_newer": release.is_newer,
            "is_prerelease": release.is_prerelease,
            "assets": [
                {
                    "name": asset.name,
                    "download_url": asset.download_url,
                    "size": asset.size,
                    "sha256": asset.sha256,
                }
                for asset in release.assets
            ],
        }

    def download_and_apply_update(
        self,
        release_info: dict,
        install_dir: str,
        restart_executable: str,
        restart_args: list[str] | None = None,
    ) -> dict:
        settings = self._settings_store.load()
        return dict(
            self._update_downloader(
                repo=settings.update_repo,
                current_version="0",
                proxy=settings.update_proxy,
                release_info=release_info,
                install_dir=install_dir,
                restart_executable=restart_executable,
                restart_args=list(restart_args or []),
                progress_callback=self.update_download_progress.emit,
            )
        )

    @staticmethod
    def _default_download_and_apply_update(
        repo: str,
        current_version: str,
        proxy: ProxyConfig,
        release_info: dict,
        install_dir: str,
        restart_executable: str,
        restart_args: list[str],
        progress_callback=None,
    ) -> dict:
        return download_and_apply_release(
            repo=repo,
            current_version=current_version,
            proxy=proxy,
            release_info=release_info,
            install_dir=install_dir,
            restart_executable=restart_executable,
            restart_args=restart_args,
            progress_callback=progress_callback,
        )

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
