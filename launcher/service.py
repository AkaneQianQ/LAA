#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Launcher-facing service helpers."""

from __future__ import annotations

import copy
import ctypes
import ctypes.wintypes
import io
import os
import json
import shutil
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from agent.py_service import main as service_main
from agent.py_service.pkg.common.database import (
    find_account_by_hash,
    get_or_create_account,
    init_database,
    list_characters_by_account,
    update_account_tag,
    upsert_character,
)

try:
    import win32con
    import win32gui
    import win32process

    WIN32_WINDOW_API_AVAILABLE = True
except ImportError:
    win32con = None
    win32gui = None
    win32process = None
    WIN32_WINDOW_API_AVAILABLE = False


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "assets" / "interface.json"
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROBE_LOG_PATH = PROJECT_ROOT / "logs" / "makcu_probe.log"


@dataclass(frozen=True)
class ProbeResult:
    ok: bool
    message: str


@dataclass(frozen=True)
class FocusWindowResult:
    ok: bool
    message: str
    hwnd: Optional[int] = None


class _LineWriter(io.TextIOBase):
    def __init__(self, callback: Callable[[str], None]):
        self._callback = callback
        self._buffer = ""

    def write(self, s: str) -> int:
        self._buffer += s
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line:
                self._callback(line)
        return len(s)

    def flush(self) -> None:
        if self._buffer:
            self._callback(self._buffer)
            self._buffer = ""


def append_probe_log(message: str) -> None:
    PROBE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with PROBE_LOG_PATH.open("a", encoding="utf-8") as fp:
        fp.write(f"[{timestamp}] {message}\n")


def load_interface_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    return service_main.load_interface_config(str(config_path or DEFAULT_CONFIG_PATH))


def _iter_top_level_windows() -> list[int]:
    if not WIN32_WINDOW_API_AVAILABLE or win32gui is None:
        return []

    hwnds: list[int] = []

    def callback(hwnd, _extra) -> bool:
        hwnds.append(hwnd)
        return True

    win32gui.EnumWindows(callback, None)
    return hwnds


def _get_process_basename(pid: int) -> str:
    if pid <= 0:
        return ""

    try:
        kernel32 = ctypes.windll.kernel32
        process_handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not process_handle:
            return ""
        try:
            buffer_size = ctypes.wintypes.DWORD(260)
            buffer = ctypes.create_unicode_buffer(buffer_size.value)
            success = kernel32.QueryFullProcessImageNameW(
                process_handle,
                0,
                buffer,
                ctypes.byref(buffer_size),
            )
            if not success:
                return ""
            return os.path.basename(buffer.value)
        finally:
            kernel32.CloseHandle(process_handle)
    except Exception:
        return ""


def focus_lostark_window(process_name: str = "LOSTARK.exe") -> FocusWindowResult:
    if not WIN32_WINDOW_API_AVAILABLE or win32gui is None or win32process is None or win32con is None:
        return FocusWindowResult(False, "win32 window api unavailable")

    target_name = str(process_name).lower()
    for hwnd in _iter_top_level_windows():
        try:
            if not win32gui.IsWindowVisible(hwnd):
                continue
            _thread_id, pid = win32process.GetWindowThreadProcessId(hwnd)
            if _get_process_basename(pid).lower() != target_name:
                continue
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return FocusWindowResult(True, f"focused {process_name}", hwnd=hwnd)
        except Exception as exc:
            return FocusWindowResult(False, f"failed to focus {process_name}: {exc}")

    return FocusWindowResult(False, f"no visible window found for {process_name}")


def resolve_controller_name(interface_config: Dict[str, Any], driver_backend: str) -> str:
    backend = str(driver_backend).lower()
    controllers = interface_config.get("controller", [])

    for controller in controllers:
        driver = str(controller.get("driver", "ferrum")).lower()
        if driver == backend:
            return str(controller["name"])

    raise ValueError(f"no controller found for backend: {driver_backend}")


def build_controller_override(
    port: str,
    baudrate: Optional[int] = None,
    keyboard_via_python: bool = False,
) -> Dict[str, Any]:
    serial = {"port": str(port)}
    if baudrate is not None:
        serial["baudrate"] = int(baudrate)
    override = {"serial": serial}
    if keyboard_via_python:
        override["input"] = {"keyboard_via_python": True}
    return override


def resolve_controller_config(interface_config: Dict[str, Any], controller_name: str) -> Dict[str, Any]:
    for controller in interface_config.get("controller", []):
        if str(controller.get("name")) == controller_name:
            return copy.deepcopy(controller)
    raise ValueError(f"controller not found: {controller_name}")


def apply_controller_override(controller_config: Dict[str, Any], controller_override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged = copy.deepcopy(controller_config)
    if controller_override and "serial" in controller_override:
        merged.setdefault("serial", {})
        merged["serial"].update(controller_override["serial"])
    if controller_override and "input" in controller_override:
        merged.setdefault("input", {})
        merged["input"].update(controller_override["input"])
    return merged


def probe_controller(
    interface_config: Dict[str, Any],
    driver_backend: str,
    port: str,
    baudrate: Optional[int] = None,
    keyboard_via_python: bool = False,
) -> ProbeResult:
    controller_name = resolve_controller_name(interface_config, driver_backend)
    controller_config = resolve_controller_config(interface_config, controller_name)
    merged_config = apply_controller_override(
        controller_config,
        build_controller_override(port, baudrate, keyboard_via_python=keyboard_via_python),
    )
    # Probe should validate serial/hardware reachability only.
    # Avoid initializing PYDD during MAKCU probe to prevent false failures.
    if str(driver_backend).lower() == "makcu":
        merged_config.setdefault("input", {})
        merged_config["input"]["keyboard_via_python"] = False
    controller = None
    try:
        controller = service_main.create_hardware_controller(merged_config)
        if not controller.is_connected():
            append_probe_log(f"{driver_backend.upper()} port={port} result=not_connected")
            return ProbeResult(False, f"{driver_backend.upper()} 未连接")
        if not controller.handshake():
            append_probe_log(f"{driver_backend.upper()} port={port} result=handshake_failed")
            return ProbeResult(False, f"{driver_backend.upper()} 握手失败")
        append_probe_log(f"{driver_backend.upper()} port={port} result=connected")
        return ProbeResult(True, f"{driver_backend.upper()} 已连接: {port}")
    except Exception as exc:
        append_probe_log(f"{driver_backend.upper()} port={port} result=exception detail={exc}")
        return ProbeResult(False, f"{driver_backend.upper()} 检测失败: {exc}")
    finally:
        if controller is not None:
            try:
                controller.close()
            except Exception:
                pass


def run_selected_task(
    task_name: str,
    controller_name: str,
    port: Optional[str] = None,
    baudrate: Optional[int] = None,
    keyboard_via_python: bool = False,
    config_path: Optional[Path] = None,
    log_writer: Optional[Callable[[str], None]] = None,
    stop_event: Any = None,
) -> bool:
    controller_override = build_controller_override(port, baudrate, keyboard_via_python=keyboard_via_python) if port else None
    if log_writer is None:
        return bool(
            service_main.run_task(
                task_name,
                config_path=str(config_path or DEFAULT_CONFIG_PATH),
                controller_name=controller_name,
                controller_override=controller_override,
                stop_event=stop_event,
            )
        )

    writer = _LineWriter(log_writer)
    with redirect_stdout(writer), redirect_stderr(writer):
        result = service_main.run_task(
            task_name,
            config_path=str(config_path or DEFAULT_CONFIG_PATH),
            controller_name=controller_name,
            controller_override=controller_override,
            stop_event=stop_event,
        )
        writer.flush()
        return bool(result)


def _load_account_indexing_staging_summary(data_dir: str, session_id: str) -> dict[str, Any]:
    session_dir = Path(data_dir) / "staging" / "account_indexing" / str(session_id)
    summary_path = session_dir / "summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"staging summary not found: {summary_path}")
    return json.loads(summary_path.read_text(encoding="utf-8"))


def load_latest_account_indexing_staging_summary(data_dir: str) -> Optional[dict[str, Any]]:
    staging_root = Path(data_dir) / "staging" / "account_indexing"
    if not staging_root.exists():
        return None

    latest_summary: Optional[Path] = None
    latest_mtime = -1.0
    for summary_path in staging_root.glob("*/summary.json"):
        try:
            mtime = summary_path.stat().st_mtime
        except OSError:
            continue
        if mtime > latest_mtime:
            latest_mtime = mtime
            latest_summary = summary_path

    if latest_summary is None:
        return None
    return json.loads(latest_summary.read_text(encoding="utf-8"))


def save_account_indexing_staging(db_path: str, data_dir: str, session_id: str) -> dict[str, Any]:
    summary = _load_account_indexing_staging_summary(data_dir, session_id)
    init_database(db_path)

    account_hash = str(summary["account_hash"])
    account_id = get_or_create_account(db_path, account_hash)
    account_row = find_account_by_hash(db_path, account_hash)
    if account_row is None:
        raise RuntimeError(f"failed to resolve account after create: {account_hash}")
    account_id = int(account_row["id"])

    account_dir = Path(data_dir) / "accounts" / account_hash
    characters_dir = account_dir / "characters"
    characters_dir.mkdir(parents=True, exist_ok=True)

    tag_src = Path(str(summary["tag_path"]))
    tag_dst = account_dir / "tag.png"
    if tag_src.exists():
        shutil.copy2(tag_src, tag_dst)
        update_account_tag(db_path, account_id, str(tag_dst))

    for idx, src_path in enumerate(summary.get("character_paths", []), start=1):
        src = Path(str(src_path))
        if not src.exists():
            continue
        dst = characters_dir / f"{idx}.png"
        shutil.copy2(src, dst)
        upsert_character(db_path, account_id, idx, str(dst))

    character_count_switchable = len(list_characters_by_account(db_path, account_id))
    character_count_total = int(summary.get("character_count_total", character_count_switchable + 1))
    info = {
        "account_id": account_id,
        "account_hash": account_hash,
        "character_count": character_count_total,
    }
    (account_dir / "account_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    session_dir = Path(str(summary["staging_dir"]))
    if session_dir.exists():
        shutil.rmtree(session_dir)

    return {
        "account_id": account_id,
        "account_hash": account_hash,
        "character_count_total": character_count_total,
        "character_count_switchable": int(summary.get("character_count_switchable", character_count_switchable)),
    }


def discard_account_indexing_staging(data_dir: str, session_id: str) -> dict[str, Any]:
    summary = _load_account_indexing_staging_summary(data_dir, session_id)
    session_dir = Path(str(summary["staging_dir"]))
    if session_dir.exists():
        shutil.rmtree(session_dir)
    return {"discarded": True, "session_id": str(session_id)}
