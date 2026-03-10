#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Launcher helper tests.
"""

import queue
import threading
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QPoint, Qt, Signal
from PySide6.QtWidgets import QApplication, QPushButton


def test_launcher_settings_default_to_ferrum_when_file_missing(tmp_path):
    from launcher.settings import LauncherSettingsStore

    settings_path = tmp_path / "ui_settings.json"
    store = LauncherSettingsStore(settings_path)

    settings = store.load()
    assert settings.driver_backend == "ferrum"


def test_launcher_settings_persist_driver_backend(tmp_path):
    from launcher.settings import LauncherSettings, LauncherSettingsStore

    settings_path = tmp_path / "ui_settings.json"
    store = LauncherSettingsStore(settings_path)
    store.save(LauncherSettings(driver_backend="makcu"))

    loaded = store.load()
    assert loaded.driver_backend == "makcu"


def test_launcher_settings_persist_ports_per_backend(tmp_path):
    from launcher.settings import LauncherSettings, LauncherSettingsStore

    settings_path = tmp_path / "ui_settings.json"
    store = LauncherSettingsStore(settings_path)
    store.save(
        LauncherSettings(
            driver_backend="makcu",
            ports={"ferrum": "COM2", "makcu": "COM7"},
        )
    )

    loaded = store.load()
    assert loaded.ports["ferrum"] == "COM2"
    assert loaded.ports["makcu"] == "COM7"


def test_launcher_settings_persist_task_queue_state(tmp_path):
    from launcher.settings import LauncherSettings, LauncherSettingsStore

    settings_path = tmp_path / "ui_settings.json"
    store = LauncherSettingsStore(settings_path)
    store.save(
        LauncherSettings(
            driver_backend="ferrum",
            ports={"ferrum": "COM2", "makcu": "COM3"},
            task_checked={"AccountIndexing": False, "CharacterSwitch": True},
            task_visibility={"AccountIndexing": True, "CharacterSwitch": False},
            task_order=["CharacterSwitch", "AccountIndexing"],
        )
    )

    loaded = store.load()
    assert loaded.task_checked == {"AccountIndexing": False, "CharacterSwitch": True}
    assert loaded.task_visibility == {"AccountIndexing": True, "CharacterSwitch": False}
    assert loaded.task_order == ["CharacterSwitch", "AccountIndexing"]


def test_resolve_controller_name_maps_backend_to_interface_entry():
    from launcher.service import resolve_controller_name

    interface_config = {
        "controller": [
            {"name": "KMBox-Default", "driver": "ferrum"},
            {"name": "MAKCU-Default", "driver": "makcu"},
        ]
    }

    assert resolve_controller_name(interface_config, "ferrum") == "KMBox-Default"
    assert resolve_controller_name(interface_config, "makcu") == "MAKCU-Default"


def test_task_runner_emits_logs_and_completion_status():
    from launcher.task_runner import LauncherTaskRunner

    log_queue = queue.Queue()
    completions = []
    started = threading.Event()
    release = threading.Event()

    def fake_task(task_name, controller_name, log_writer):
        started.set()
        log_writer("worker started")
        release.wait(timeout=2)
        log_writer(f"finished:{task_name}:{controller_name}")
        return True

    runner = LauncherTaskRunner(fake_task)
    runner.start(
        task_name="CharacterSwitch",
        controller_name="MAKCU-Default",
        log_writer=log_queue.put,
        on_complete=completions.append,
    )

    assert runner.is_busy() is True
    assert started.wait(timeout=2) is True
    release.set()
    runner.join(timeout=2)

    logs = []
    while not log_queue.empty():
        logs.append(log_queue.get())

    assert "worker started" in logs
    assert "finished:CharacterSwitch:MAKCU-Default" in logs
    assert completions == [True]
    assert runner.is_busy() is False


def test_launcher_service_run_task_passes_controller_name(monkeypatch):
    from launcher.service import run_selected_task

    captured = {}

    def fake_run_task(task_name, config_path=None, test_mode=False, debug_mode=False, controller_name=None, controller_override=None, stop_event=None):
        captured["task_name"] = task_name
        captured["controller_name"] = controller_name
        captured["controller_override"] = controller_override
        return True

    monkeypatch.setattr("launcher.service.service_main.run_task", fake_run_task)

    result = run_selected_task("AccountIndexing", "KMBox-Default", port="COM9")
    assert result is True
    assert captured == {
        "task_name": "AccountIndexing",
        "controller_name": "KMBox-Default",
        "controller_override": {"serial": {"port": "COM9"}},
    }


def test_focus_lostark_window_activates_visible_window_for_lostark_process(monkeypatch):
    from launcher import service

    monkeypatch.setattr(service, "WIN32_WINDOW_API_AVAILABLE", True, raising=False)

    class FakeWin32Gui:
        def IsWindowVisible(self, hwnd):
            return hwnd == 100

        def GetWindowText(self, hwnd):
            return "LOST ARK"

        def IsIconic(self, hwnd):
            return True

        def ShowWindow(self, hwnd, cmd):
            events.append(("show", hwnd, cmd))

        def SetForegroundWindow(self, hwnd):
            events.append(("foreground", hwnd))

    class FakeWin32Process:
        def GetWindowThreadProcessId(self, hwnd):
            return (1, 4321 if hwnd == 100 else 9999)

    class FakeWin32Con:
        SW_RESTORE = 9

    events = []
    monkeypatch.setattr(service, "win32gui", FakeWin32Gui(), raising=False)
    monkeypatch.setattr(service, "win32process", FakeWin32Process(), raising=False)
    monkeypatch.setattr(service, "win32con", FakeWin32Con(), raising=False)
    monkeypatch.setattr(service, "_iter_top_level_windows", lambda: [200, 100], raising=False)
    monkeypatch.setattr(service, "_get_process_basename", lambda pid: "LOSTARK.exe" if pid == 4321 else "other.exe", raising=False)

    result = service.focus_lostark_window()

    assert result.ok is True
    assert result.hwnd == 100
    assert ("show", 100, 9) in events
    assert ("foreground", 100) in events


def test_focus_lostark_window_reports_missing_window(monkeypatch):
    from launcher import service

    monkeypatch.setattr(service, "WIN32_WINDOW_API_AVAILABLE", True, raising=False)
    monkeypatch.setattr(service, "_iter_top_level_windows", lambda: [100], raising=False)

    class FakeWin32Gui:
        def IsWindowVisible(self, hwnd):
            return True

        def GetWindowText(self, hwnd):
            return "Some Other App"

    class FakeWin32Process:
        def GetWindowThreadProcessId(self, hwnd):
            return (1, 9999)

    monkeypatch.setattr(service, "win32gui", FakeWin32Gui(), raising=False)
    monkeypatch.setattr(service, "win32process", FakeWin32Process(), raising=False)
    monkeypatch.setattr(service, "_get_process_basename", lambda pid: "not_lostark.exe", raising=False)

    result = service.focus_lostark_window()

    assert result.ok is False
    assert "LOSTARK.exe" in result.message


def test_probe_controller_reports_success_and_closes_controller(monkeypatch):
    from launcher.service import probe_controller

    closed = {"value": False}

    class FakeController:
        def __init__(self, port, baudrate, timeout):
            assert port == "COM8"

        def is_connected(self):
            return True

        def handshake(self):
            return True

        def close(self):
            closed["value"] = True

    monkeypatch.setattr("launcher.service.service_main.create_hardware_controller", lambda config: FakeController(**config["serial"]))

    result = probe_controller(
        interface_config={
            "controller": [
                {"name": "KMBox-Default", "driver": "ferrum", "serial": {"port": "COM2", "baudrate": 115200, "timeout": 1.0}}
            ]
        },
        driver_backend="ferrum",
        port="COM8",
    )
    assert result.ok is True
    assert "已连接" in result.message
    assert closed["value"] is True


def test_probe_controller_reports_handshake_failure(monkeypatch):
    from launcher.service import probe_controller

    class FakeController:
        def __init__(self, port, baudrate, timeout):
            pass

        def is_connected(self):
            return True

        def handshake(self):
            return False

        def close(self):
            return None

    monkeypatch.setattr("launcher.service.service_main.create_hardware_controller", lambda config: FakeController(**config["serial"]))

    result = probe_controller(
        interface_config={
            "controller": [
                {"name": "MAKCU-Default", "driver": "makcu", "serial": {"port": "COM3", "baudrate": 115200, "timeout": 1.0}}
            ]
        },
        driver_backend="makcu",
        port="COM10",
    )
    assert result.ok is False
    assert "握手失败" in result.message


def test_packaging_files_exist():
    assert Path("requirements-gui.txt").exists()
    assert Path("build_launcher.ps1").exists()
    assert "console=False" in Path("FerrumBotLauncher.spec").read_text(encoding="utf-8")
    assert Path("gui_qt/theme/assets/app.svg").exists()
    assert Path("gui_qt/theme/assets/close.svg").exists()
    assert Path("gui_qt/theme/assets/checkbox_checked.svg").exists()
    assert Path("gui_qt/theme/assets/checkbox_unchecked.svg").exists()


def test_qt_launcher_bridge_loads_and_saves_settings(tmp_path):
    from gui_qt.adapters.launcher_bridge import LauncherBridge

    bridge = LauncherBridge(settings_path=tmp_path / "ui_settings.json")

    settings = bridge.load_settings()
    assert settings.driver_backend == "ferrum"

    bridge.save_settings("makcu", {"ferrum": "COM2", "makcu": "COM8"})
    updated = bridge.load_settings()
    assert updated.driver_backend == "makcu"
    assert updated.ports["makcu"] == "COM8"


def test_qt_launcher_bridge_runs_task_and_emits_events():
    from gui_qt.adapters.launcher_bridge import LauncherBridge

    app = QApplication.instance() or QApplication([])
    _ = app
    bridge = LauncherBridge()
    captured = {"log": [], "started": [], "finished": []}
    release = threading.Event()

    def fake_runner(task_name, controller_name, port=None, log_writer=None, stop_event=None):
        captured["started"].append((task_name, controller_name, port))
        if log_writer is not None:
            log_writer("bridge worker started")
        release.wait(timeout=2)
        if log_writer is not None:
            log_writer("bridge worker finished")
        return True

    bridge._task_executor = fake_runner
    bridge.log_emitted.connect(captured["log"].append)
    bridge.task_started.connect(lambda task_name: captured["started"].append(("signal", task_name)))
    bridge.task_finished.connect(lambda success: captured["finished"].append(success))

    bridge.start_task("CharacterSwitch", "KMBox-Default", "COM9")
    assert bridge.is_busy() is True
    release.set()
    bridge.wait_for_idle(timeout=2)

    assert ("CharacterSwitch", "KMBox-Default", "COM9") in captured["started"]
    assert ("signal", "CharacterSwitch") in captured["started"]
    assert "bridge worker started" in captured["log"]
    assert "bridge worker finished" in captured["log"]
    assert captured["finished"] == [True]
    assert bridge.is_busy() is False


def test_qt_launcher_bridge_stop_task_requests_cancellation():
    from gui_qt.adapters.launcher_bridge import LauncherBridge

    bridge = LauncherBridge()
    seen = {"stopped": False}

    def fake_is_alive():
        return True

    class FakeThread:
        is_alive = staticmethod(fake_is_alive)

    bridge._task_thread = FakeThread()
    bridge._task_stop_event.set()
    bridge._task_stop_event.clear()

    bridge.stop_task()

    assert bridge._task_stop_event.is_set() is True


def test_qt_launcher_bridge_focuses_lostark_before_running_task():
    from gui_qt.adapters.launcher_bridge import LauncherBridge

    app = QApplication.instance() or QApplication([])
    _ = app
    bridge = LauncherBridge()
    calls = []
    release = threading.Event()

    class FocusResult:
        ok = True
        message = "focused"
        hwnd = 100

    def fake_focus():
        calls.append("focus")
        return FocusResult()

    def fake_runner(task_name, controller_name, port=None, log_writer=None, stop_event=None):
        calls.append(("task", task_name, controller_name, port))
        release.wait(timeout=2)
        return True

    bridge._focus_executor = fake_focus
    bridge._task_executor = fake_runner

    bridge.start_task("CharacterSwitch", "KMBox-Default", "COM9")
    release.set()
    bridge.wait_for_idle(timeout=2)

    assert calls[0] == "focus"
    assert calls[1] == ("task", "CharacterSwitch", "KMBox-Default", "COM9")


def test_qt_launcher_bridge_waits_one_second_after_focus_before_running_task():
    from gui_qt.adapters.launcher_bridge import LauncherBridge

    app = QApplication.instance() or QApplication([])
    _ = app
    bridge = LauncherBridge()
    calls = []
    release = threading.Event()

    class FocusResult:
        ok = True
        message = "focused"
        hwnd = 100

    def fake_focus():
        calls.append("focus")
        return FocusResult()

    def fake_sleep(seconds):
        calls.append(("sleep", seconds))

    def fake_runner(task_name, controller_name, port=None, log_writer=None, stop_event=None):
        calls.append(("task", task_name, controller_name, port))
        release.wait(timeout=2)
        return True

    bridge._focus_executor = fake_focus
    bridge._sleep = fake_sleep
    bridge._task_executor = fake_runner

    bridge.start_task("CharacterSwitch", "KMBox-Default", "COM9")
    release.set()
    bridge.wait_for_idle(timeout=2)

    assert calls == [
        "focus",
        ("sleep", 1.0),
        ("task", "CharacterSwitch", "KMBox-Default", "COM9"),
    ]


def test_qt_launcher_window_builds_expected_tabs():
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()

    tab_labels = [window.tab_widget.tabText(index) for index in range(window.tab_widget.count())]

    assert "一键长草" in tab_labels
    assert "小工具" in tab_labels
    assert "日志" in tab_labels
    assert "自动战斗" not in tab_labels

    window.close()
    app.quit()


def test_qt_launcher_window_builds_main_shell_sections():
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()

    assert window.findChild(type(window.tab_widget), "mainTabs") is not None
    assert window.findChild(object, "appShell") is not None
    assert window.findChild(object, "titleBar") is not None
    assert window.findChild(object, "taskPanel") is not None
    assert window.findChild(object, "taskListContainer") is not None
    assert window.findChild(object, "contentPanel") is not None
    assert window.findChild(object, "statusStrip") is not None
    assert window.findChild(object, "topStatusPanel") is not None
    assert window.findChild(object, "taskListActions") is not None
    assert window.findChild(object, "contentFooter") is None
    assert not window.findChildren(type(window.current_task_value), "taskDescription")

    window.close()
    app.quit()


def test_qt_launcher_window_hides_task_config_panel_by_default():
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()

    assert window.config_title_label.isHidden() is True
    assert window.config_group.isHidden() is True

    window.close()
    app.quit()


def test_qt_launcher_window_clicking_task_gear_shows_named_config_panel():
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()

    row = window.task_rows["CharacterSwitch"]
    row.gear_button.click()
    app.processEvents()

    assert window.config_title_label.isHidden() is False
    assert window.config_group.isHidden() is False
    assert window.config_title_label.text() == "全自动捐献配置"

    window.close()
    app.quit()


def test_qt_launcher_window_uses_compact_outer_margins():
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()

    margins = window.centralWidget().layout().contentsMargins()
    assert margins.left() <= 10
    assert margins.top() <= 8
    assert margins.right() <= 10
    assert margins.bottom() <= 10

    window.close()
    app.quit()


def test_qt_launcher_window_restores_saved_task_queue_state():
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)

        def load_settings(self):
            return LauncherSettings(
                driver_backend="ferrum",
                ports={"ferrum": "COM2", "makcu": "COM3"},
                task_checked={"AccountIndexing": False, "CharacterSwitch": True},
                task_visibility={"AccountIndexing": False, "CharacterSwitch": True},
                task_order=["CharacterSwitch", "AccountIndexing"],
            )

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved = (driver_backend, ports)

        def load_interface(self):
            return {}

        def is_busy(self):
            return False

    app = build_application()
    window = FerrumMainWindow(bridge=FakeBridge())

    assert window.visible_task_names() == ["CharacterSwitch"]
    assert window.task_items[0]["task_name"] == "CharacterSwitch"
    assert window.task_rows["CharacterSwitch"].checkbox.isChecked() is True

    window.close()
    app.quit()


def test_qt_launcher_window_starts_selected_task_and_updates_runtime():
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)

        def __init__(self):
            super().__init__()
            self.started = []
            self.stops = 0

        def load_settings(self):
            return LauncherSettings(driver_backend="makcu", ports={"ferrum": "COM2", "makcu": "COM9"})

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved = (driver_backend, ports)

        def load_interface(self):
            return {}

        def start_task(self, task_name, controller_name, port=None):
            self.started.append((task_name, controller_name, port))
            self.task_started.emit(task_name)

        def stop_task(self):
            self.stops += 1

        def is_busy(self):
            return False

    app = build_application()
    bridge = FakeBridge()
    window = FerrumMainWindow(bridge=bridge)

    window.start_button.click()

    assert bridge.started == [("AccountIndexing", "MAKCU-Default", "COM9")]
    assert window.runtime_state_value.text() == "运行中"
    assert window.current_task_value.text() == "账号读取"
    assert window.start_button.text() == "运行中..."

    bridge.task_finished.emit(True)
    app.processEvents()

    assert window.runtime_state_value.text() == "空闲"
    assert window.current_task_value.text() == "-"
    assert window.start_button.text() == "Link Start!"

    window.close()
    app.quit()


def test_qt_launcher_window_second_start_click_stops_running_task():
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)

        def __init__(self):
            super().__init__()
            self.started = []
            self.stops = 0
            self._busy = False

        def load_settings(self):
            return LauncherSettings(driver_backend="makcu", ports={"ferrum": "COM2", "makcu": "COM9"})

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved = (driver_backend, ports)

        def load_interface(self):
            return {}

        def start_task(self, task_name, controller_name, port=None):
            self.started.append((task_name, controller_name, port))
            self._busy = True
            self.task_started.emit(task_name)

        def stop_task(self):
            self.stops += 1

        def is_busy(self):
            return self._busy

    app = build_application()
    bridge = FakeBridge()
    window = FerrumMainWindow(bridge=bridge)

    window.start_button.click()
    window.start_button.click()

    assert bridge.started == [("AccountIndexing", "MAKCU-Default", "COM9")]
    assert bridge.stops == 1

    window.close()
    app.quit()


def test_qt_launcher_window_registers_global_f10_hotkey(monkeypatch):
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    registered = {}

    class FakeKeyboardModule:
        def add_hotkey(self, key, callback):
            registered["key"] = key
            registered["callback"] = callback
            return "hotkey-handle"

        def remove_hotkey(self, handle):
            registered["removed"] = handle

    monkeypatch.setattr("gui_qt.window.keyboard", FakeKeyboardModule(), raising=False)

    app = build_application()
    window = FerrumMainWindow()

    assert registered["key"] == "f10"
    assert callable(registered["callback"])

    window.close()
    app.quit()


def test_qt_launcher_window_probes_selected_driver_and_updates_status():
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)

        def __init__(self):
            super().__init__()
            self.probes = []

        def load_settings(self):
            return LauncherSettings(driver_backend="ferrum", ports={"ferrum": "COM6", "makcu": "COM9"})

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved = (driver_backend, ports)

        def load_interface(self):
            return {"controller": []}

        def start_task(self, task_name, controller_name, port=None):
            raise AssertionError("start_task should not be called in probe test")

        def probe(self, interface_config, driver_backend, port):
            self.probes.append((interface_config, driver_backend, port))

        def is_busy(self):
            return False

    app = build_application()
    bridge = FakeBridge()
    window = FerrumMainWindow(bridge=bridge)

    ferrum_button = next(button for button in window.findChildren(QPushButton, "backendToggle") if button.text() == "Ferrum")
    ferrum_button.click()
    window.detect_button.click()

    assert bridge.probes == [({"controller": []}, "ferrum", "COM6")]

    bridge.probe_finished.emit(True, "FERRUM 已连接: COM6")
    app.processEvents()

    assert window.connection_value.text() == "COM6"
    assert bridge.saved == ("ferrum", {"ferrum": "COM6", "makcu": "COM9"})

    bridge.probe_finished.emit(False, "FERRUM 握手失败")
    app.processEvents()
    assert window.connection_value.text() == "未连接"

    window.close()
    app.quit()


def test_qt_launcher_home_status_actions_probe_and_open_settings():
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)

        def __init__(self):
            super().__init__()
            self.probes = []

        def load_settings(self):
            return LauncherSettings(driver_backend="makcu", ports={"ferrum": "COM2", "makcu": "COM8"})

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved = (driver_backend, ports)

        def load_interface(self):
            return {"controller": []}

        def probe(self, interface_config, driver_backend, port):
            self.probes.append((interface_config, driver_backend, port))

        def is_busy(self):
            return False

    app = build_application()
    bridge = FakeBridge()
    window = FerrumMainWindow(bridge=bridge)

    assert window.status_probe_button.text() == ""
    assert window.status_probe_button.icon().isNull() is False

    window.status_probe_button.click()
    assert bridge.probes == [({"controller": []}, "makcu", "COM8")]

    window.status_settings_button.click()
    app.processEvents()
    assert window.tab_widget.tabText(window.tab_widget.currentIndex()) == "设置"

    assert window.findChild(type(window.runtime_state_value), "statusDriverLabel") is not None
    assert window.findChild(type(window.runtime_state_value), "statusConnectionLabel") is not None
    assert not hasattr(window, "clock_label")

    window.close()
    app.quit()


def test_qt_launcher_window_appends_bridge_logs_to_log_view():
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)

        def __init__(self):
            super().__init__()

        def load_settings(self):
            return LauncherSettings(driver_backend="ferrum", ports={"ferrum": "COM2", "makcu": "COM3"})

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved = (driver_backend, ports)

        def load_interface(self):
            return {"controller": []}

        def is_busy(self):
            return False

    app = build_application()
    bridge = FakeBridge()
    window = FerrumMainWindow(bridge=bridge)

    bridge.log_emitted.emit("[Launcher] hello qt")
    app.processEvents()

    assert "[Launcher] hello qt" in window.log_view.toPlainText()

    window.close()
    app.quit()


def test_qt_launcher_window_toggles_trigger_runtime_state():
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)

        def __init__(self):
            super().__init__()
            self.trigger_starts = []
            self.trigger_stops = 0
            self._busy = False

        def load_settings(self):
            return LauncherSettings(driver_backend="makcu", ports={"ferrum": "COM2", "makcu": "COM8"})

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved = (driver_backend, ports)

        def load_interface(self):
            return {"controller": []}

        def start_trigger(self, interface_config, driver_backend, port):
            self.trigger_starts.append((interface_config, driver_backend, port))
            self._busy = True
            self.trigger_started.emit()

        def stop_trigger(self):
            self.trigger_stops += 1
            self._busy = False
            self.trigger_finished.emit()

        def is_busy(self):
            return self._busy

    app = build_application()
    bridge = FakeBridge()
    window = FerrumMainWindow(bridge=bridge)

    window.tab_widget.setCurrentIndex(2)
    app.processEvents()
    window.trigger_toggle_button.click()

    assert bridge.trigger_starts == [({"controller": []}, "makcu", "COM8")]
    assert window.runtime_state_value.text() == "触发中"
    assert window.current_task_value.text() == "图像触发"

    window.trigger_toggle_button.click()
    app.processEvents()

    assert bridge.trigger_stops == 1
    assert window.runtime_state_value.text() == "空闲"
    assert window.current_task_value.text() == "-"

    window.close()
    app.quit()


def test_service_run_task_executes_pipeline(monkeypatch):
    from agent.py_service import main as service_main

    fake_components = service_main.InitializedComponents(
        config={
            "task": [
                {
                    "name": "AccountIndexing",
                    "entry": "AccountIndexingMain",
                    "pipeline": "assets/resource/pipeline/account_indexing.json",
                }
            ]
        },
        controller_config={"name": "KMBox-Default", "serial": {"port": "COM2"}},
        resource_config={"name": "LostArk-KR-2560x1440"},
        hardware_controller=object(),
        vision_engine=object(),
        frame_cache=None,
    )

    captured = {}

    monkeypatch.setattr(service_main, "initialize", lambda **kwargs: fake_components)
    monkeypatch.setattr(service_main, "get_task_config", lambda config, task_name: config["task"][0])
    monkeypatch.setattr(service_main, "load_pipeline", lambda path: {"AccountIndexingMain": {}})

    def fake_execute_pipeline(pipeline_path, entry_node, hardware_controller, vision_engine, timeout_seconds=300.0, stop_event=None):
        captured["pipeline_path"] = str(pipeline_path)
        captured["entry_node"] = entry_node
        captured["hardware_controller"] = hardware_controller
        captured["vision_engine"] = vision_engine
        return True

    monkeypatch.setattr("agent.py_service.modules.workflow_executor.executor.execute_pipeline", fake_execute_pipeline)

    result = service_main.run_task("AccountIndexing")

    assert result is True
    assert captured["pipeline_path"].endswith("assets\\resource\\pipeline\\account_indexing.json")
    assert captured["entry_node"] == "AccountIndexingMain"


def test_launcher_service_run_task_passes_stop_event(monkeypatch):
    from launcher.service import run_selected_task
    import threading

    captured = {}
    stop_event = threading.Event()

    def fake_run_task(task_name, config_path=None, test_mode=False, debug_mode=False, controller_name=None, controller_override=None, stop_event=None):
        captured["stop_event"] = stop_event
        return True

    monkeypatch.setattr("launcher.service.service_main.run_task", fake_run_task)

    result = run_selected_task("AccountIndexing", "KMBox-Default", port="COM9", stop_event=stop_event)

    assert result is True
    assert captured["stop_event"] is stop_event


def test_service_run_task_resolves_pipeline_entry_name_mismatch(monkeypatch):
    from agent.py_service import main as service_main

    fake_components = service_main.InitializedComponents(
        config={
            "task": [
                {
                    "name": "AccountIndexing",
                    "entry": "AccountIndexingMain",
                    "pipeline": "assets/resource/pipeline/account_indexing.json",
                }
            ]
        },
        controller_config={"name": "KMBox-Default", "serial": {"port": "COM2"}},
        resource_config={"name": "LostArk-KR-2560x1440"},
        hardware_controller=object(),
        vision_engine=object(),
        frame_cache=None,
    )

    captured = {}

    monkeypatch.setattr(service_main, "initialize", lambda **kwargs: fake_components)
    monkeypatch.setattr(service_main, "get_task_config", lambda config, task_name: config["task"][0])
    monkeypatch.setattr(service_main, "load_pipeline", lambda path: {"account_indexingMain": {}, "press_esc_first": {}})

    def fake_execute_pipeline(pipeline_path, entry_node, hardware_controller, vision_engine, timeout_seconds=300.0, stop_event=None):
        captured["entry_node"] = entry_node
        captured["hardware_controller"] = hardware_controller
        captured["vision_engine"] = vision_engine
        return True

    monkeypatch.setattr("agent.py_service.modules.workflow_executor.executor.execute_pipeline", fake_execute_pipeline)

    result = service_main.run_task("AccountIndexing")

    assert result is True
    assert captured["entry_node"] == "account_indexingMain"
    assert captured["hardware_controller"] is fake_components.hardware_controller
    assert captured["vision_engine"] is fake_components.vision_engine


def test_gui_launcher_entry_delegates_to_qt_main(monkeypatch):
    import gui_launcher

    captured = {"called": False}

    def fake_main():
        captured["called"] = True
        return 123

    monkeypatch.setattr("gui_launcher.qt_main", fake_main)

    result = gui_launcher.main()

    assert result == 123
    assert captured["called"] is True


def test_qt_launcher_window_uses_laa_title_and_empty_config_panel():
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()

    assert window.title_bar.title_label.text() == "LAA 1.0.0"
    assert window.config_placeholder_label.text() == "暂无配置项"
    assert "主界面迁移中" not in window.config_placeholder_label.text()

    window.close()
    app.quit()


def test_qt_launcher_shows_account_indexing_pending_result_controls():
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)
        account_indexing_staged = Signal(dict)

        def load_settings(self):
            return LauncherSettings(driver_backend="ferrum", ports={"ferrum": "COM2", "makcu": "COM3"})

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved = (driver_backend, ports)

        def load_interface(self):
            return {"controller": []}

        def is_busy(self):
            return False

    app = build_application()
    bridge = FakeBridge()
    window = FerrumMainWindow(bridge=bridge)

    bridge.account_indexing_staged.emit({
        "session_id": "session-1",
        "character_count_total": 8,
        "characters_dir": "C:\\temp\\chars",
    })
    app.processEvents()
    window.task_rows["AccountIndexing"].gear_button.click()
    app.processEvents()

    assert window.config_placeholder_label.isHidden() is True
    assert window.account_indexing_result_card.isHidden() is False
    assert window.account_indexing_count_label.text() == "本次角色总数：8"
    assert window.account_indexing_open_button.isHidden() is False
    assert window.account_indexing_save_button.isHidden() is False
    assert window.account_indexing_discard_button.isHidden() is False

    window.close()
    app.quit()


def test_qt_launcher_staged_account_indexing_summary_waits_for_config_view():
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)
        account_indexing_staged = Signal(dict)

        def load_settings(self):
            return LauncherSettings(driver_backend="ferrum", ports={"ferrum": "COM2", "makcu": "COM3"})

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved = (driver_backend, ports)

        def load_interface(self):
            return {"controller": []}

        def is_busy(self):
            return False

    app = build_application()
    bridge = FakeBridge()
    window = FerrumMainWindow(bridge=bridge)

    bridge.account_indexing_staged.emit({
        "session_id": "session-1",
        "character_count_total": 8,
        "characters_dir": "C:\\temp\\chars",
    })
    app.processEvents()

    assert window.config_group.isHidden() is True
    assert window.account_indexing_result_card.isHidden() is True

    window.task_rows["AccountIndexing"].gear_button.click()
    app.processEvents()

    assert window.config_title_label.text() == "账号读取配置"
    assert window.account_indexing_result_card.isHidden() is False

    window.close()
    app.quit()


def test_qt_launcher_save_account_indexing_staging_clears_pending_panel():
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)
        account_indexing_staged = Signal(dict)

        def __init__(self):
            super().__init__()
            self.saved_calls = []

        def load_settings(self):
            return LauncherSettings(driver_backend="ferrum", ports={"ferrum": "COM2", "makcu": "COM3"})

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved = (driver_backend, ports)

        def load_interface(self):
            return {"controller": []}

        def is_busy(self):
            return False

        def save_account_indexing_staging(self, session_id):
            self.saved_calls.append(session_id)
            return {"character_count_total": 8}

    app = build_application()
    bridge = FakeBridge()
    window = FerrumMainWindow(bridge=bridge)

    bridge.account_indexing_staged.emit({
        "session_id": "session-save",
        "character_count_total": 8,
        "characters_dir": "C:\\temp\\chars",
    })
    app.processEvents()
    window.account_indexing_save_button.click()
    app.processEvents()

    assert bridge.saved_calls == ["session-save"]
    assert window.pending_account_indexing_result is None
    assert window.account_indexing_result_card.isHidden() is True
    assert window.config_placeholder_label.isHidden() is False

    window.close()
    app.quit()


def test_qt_launcher_discard_account_indexing_staging_clears_pending_panel():
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)
        account_indexing_staged = Signal(dict)

        def __init__(self):
            super().__init__()
            self.discard_calls = []

        def load_settings(self):
            return LauncherSettings(driver_backend="ferrum", ports={"ferrum": "COM2", "makcu": "COM3"})

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved = (driver_backend, ports)

        def load_interface(self):
            return {"controller": []}

        def is_busy(self):
            return False

        def discard_account_indexing_staging(self, session_id):
            self.discard_calls.append(session_id)
            return {"discarded": True}

    app = build_application()
    bridge = FakeBridge()
    window = FerrumMainWindow(bridge=bridge)

    bridge.account_indexing_staged.emit({
        "session_id": "session-discard",
        "character_count_total": 8,
        "characters_dir": "C:\\temp\\chars",
    })
    app.processEvents()
    window.account_indexing_discard_button.click()
    app.processEvents()

    assert bridge.discard_calls == ["session-discard"]
    assert window.pending_account_indexing_result is None
    assert window.account_indexing_result_card.isHidden() is True
    assert window.config_placeholder_label.isHidden() is False

    window.close()
    app.quit()


def test_qt_launcher_save_account_indexing_staging_clears_pending_panel():
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)
        account_indexing_staged = Signal(dict)

        def __init__(self):
            super().__init__()
            self.saved_calls = []

        def load_settings(self):
            return LauncherSettings(driver_backend="ferrum", ports={"ferrum": "COM2", "makcu": "COM3"})

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved = (driver_backend, ports)

        def load_interface(self):
            return {"controller": []}

        def save_account_indexing_staging(self, session_id):
            self.saved_calls.append(session_id)
            return {"character_count_total": 8}

        def is_busy(self):
            return False

    app = build_application()
    bridge = FakeBridge()
    window = FerrumMainWindow(bridge=bridge)
    bridge.account_indexing_staged.emit({
        "session_id": "session-save",
        "character_count_total": 8,
        "characters_dir": "C:\\temp\\chars",
    })
    app.processEvents()
    window.task_rows["AccountIndexing"].gear_button.click()
    app.processEvents()

    window.account_indexing_save_button.click()
    app.processEvents()

    assert bridge.saved_calls == ["session-save"]
    assert window.account_indexing_result_card.isHidden() is True
    assert window.config_placeholder_label.isHidden() is False

    window.close()
    app.quit()


def test_qt_launcher_discard_account_indexing_staging_clears_pending_panel():
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)
        account_indexing_staged = Signal(dict)

        def __init__(self):
            super().__init__()
            self.discard_calls = []

        def load_settings(self):
            return LauncherSettings(driver_backend="ferrum", ports={"ferrum": "COM2", "makcu": "COM3"})

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved = (driver_backend, ports)

        def load_interface(self):
            return {"controller": []}

        def discard_account_indexing_staging(self, session_id):
            self.discard_calls.append(session_id)
            return {"discarded": True}

        def is_busy(self):
            return False

    app = build_application()
    bridge = FakeBridge()
    window = FerrumMainWindow(bridge=bridge)
    bridge.account_indexing_staged.emit({
        "session_id": "session-discard",
        "character_count_total": 8,
        "characters_dir": "C:\\temp\\chars",
    })
    app.processEvents()
    window.task_rows["AccountIndexing"].gear_button.click()
    app.processEvents()

    window.account_indexing_discard_button.click()
    app.processEvents()

    assert bridge.discard_calls == ["session-discard"]
    assert window.account_indexing_result_card.isHidden() is True
    assert window.config_placeholder_label.isHidden() is False

    window.close()
    app.quit()


def test_qt_launcher_open_account_indexing_characters_dir(monkeypatch):
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)
        account_indexing_staged = Signal(dict)

        def load_settings(self):
            return LauncherSettings(driver_backend="ferrum", ports={"ferrum": "COM2", "makcu": "COM3"})

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved = (driver_backend, ports)

        def load_interface(self):
            return {"controller": []}

        def is_busy(self):
            return False

    opened = {}
    monkeypatch.setattr("gui_qt.window.os.startfile", lambda path: opened.setdefault("path", path), raising=False)

    app = build_application()
    bridge = FakeBridge()
    window = FerrumMainWindow(bridge=bridge)
    bridge.account_indexing_staged.emit({
        "session_id": "session-open",
        "character_count_total": 8,
        "characters_dir": "C:\\temp\\chars",
    })
    app.processEvents()

    window.account_indexing_open_button.click()

    assert opened["path"] == "C:\\temp\\chars"

    window.close()
    app.quit()


def test_qt_bridge_emits_staged_result_after_account_indexing_success(monkeypatch, tmp_path):
    from gui_qt.adapters.launcher_bridge import LauncherBridge

    emitted = []
    bridge = LauncherBridge(settings_path=tmp_path / "ui_settings.json")
    bridge.account_indexing_staged.connect(lambda summary: emitted.append(summary))

    bridge._focus_executor = lambda: type("FocusResult", (), {"ok": True})()
    bridge._task_executor = lambda *args, **kwargs: True
    monkeypatch.setattr(
        "gui_qt.adapters.launcher_bridge.load_latest_account_indexing_staging_summary",
        lambda data_dir: {"session_id": "bridge-session", "character_count_total": 6, "characters_dir": "C:\\temp\\chars"},
    )

    bridge.start_task("AccountIndexing", "KMBox-Default", "COM2")
    bridge.wait_for_idle(timeout=2.0)

    assert emitted == [{"session_id": "bridge-session", "character_count_total": 6, "characters_dir": "C:\\temp\\chars"}]


def test_qt_stylesheet_does_not_force_background_on_all_qwidgets():
    from gui_qt.theme.style import build_stylesheet

    stylesheet = build_stylesheet()

    assert "QWidget {\n        background:" not in stylesheet
    assert "QWidget#appRoot {\n        background: transparent;" in stylesheet
    assert "QWidget#appShell {" in stylesheet
    assert "QTabWidget#mainTabs::tab-bar {\n        left: 18px;" in stylesheet


def test_qt_launcher_task_visibility_and_order_management(tmp_path):
    from gui_qt.adapters.launcher_bridge import LauncherBridge
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow(bridge=LauncherBridge(settings_path=tmp_path / "ui_settings.json"))

    assert window.visible_task_names() == ["AccountIndexing", "CharacterSwitch"]

    window.set_task_visibility("CharacterSwitch", False)
    assert window.visible_task_names() == ["AccountIndexing"]

    window.set_task_visibility("CharacterSwitch", True)
    window.set_task_order(["CharacterSwitch", "AccountIndexing"])
    assert window.visible_task_names() == ["CharacterSwitch", "AccountIndexing"]
    assert window.findChild(type(window.current_task_value), "taskDescription") is None

    window.close()
    app.quit()


def test_qt_launcher_persists_task_queue_checkbox_state():
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)

        def __init__(self):
            super().__init__()
            self.saved_calls = []

        def load_settings(self):
            return LauncherSettings(driver_backend="ferrum", ports={"ferrum": "COM2", "makcu": "COM3"})

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved_calls.append((driver_backend, ports, task_checked, task_visibility, task_order))

        def load_interface(self):
            return {}

        def is_busy(self):
            return False

    app = build_application()
    bridge = FakeBridge()
    window = FerrumMainWindow(bridge=bridge)

    window.task_rows["AccountIndexing"].checkbox.setChecked(False)
    app.processEvents()

    last_call = bridge.saved_calls[-1]
    assert last_call[2]["AccountIndexing"] is False
    assert last_call[3]["AccountIndexing"] is True
    assert last_call[4] == ["AccountIndexing", "CharacterSwitch"]

    window.close()
    app.quit()


def test_qt_launcher_persists_task_queue_visibility_and_order():
    from launcher.settings import LauncherSettings
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    class FakeBridge(QObject):
        log_emitted = Signal(str)
        task_started = Signal(str)
        task_finished = Signal(bool)
        trigger_started = Signal()
        trigger_finished = Signal()
        probe_finished = Signal(bool, str)

        def __init__(self):
            super().__init__()
            self.saved_calls = []

        def load_settings(self):
            return LauncherSettings(driver_backend="ferrum", ports={"ferrum": "COM2", "makcu": "COM3"})

        def save_settings(self, driver_backend, ports, task_checked=None, task_visibility=None, task_order=None):
            self.saved_calls.append((driver_backend, ports, task_checked, task_visibility, task_order))

        def load_interface(self):
            return {}

        def is_busy(self):
            return False

    app = build_application()
    bridge = FakeBridge()
    window = FerrumMainWindow(bridge=bridge)

    window.set_task_visibility("CharacterSwitch", False)
    last_visibility_call = bridge.saved_calls[-1]
    assert last_visibility_call[3]["CharacterSwitch"] is False

    window.set_task_visibility("CharacterSwitch", True)
    window.set_task_order(["CharacterSwitch", "AccountIndexing"])
    last_order_call = bridge.saved_calls[-1]
    assert last_order_call[4] == ["CharacterSwitch", "AccountIndexing"]

    window.close()
    app.quit()


def test_qt_launcher_titlebar_pin_toggles_always_on_top():
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()

    assert window.title_bar.is_always_on_top() is False
    window.title_bar.pin_button.click()
    assert window.title_bar.is_always_on_top() is True
    window.title_bar.pin_button.click()
    assert window.title_bar.is_always_on_top() is False

    window.close()
    app.quit()


def test_qt_launcher_task_drag_prefers_live_reorder_feedback():
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()

    first_task_row = next(iter(window.task_rows.values()))
    assert first_task_row.drag_activation_distance == 4
    assert window.findChild(object, "taskDropIndicator") is None

    window.close()
    app.quit()


def test_qt_launcher_live_drag_reorder_keeps_same_row_instances():
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()
    window.show()
    app.processEvents()

    original_row = window.task_rows["AccountIndexing"]
    target_row = window.task_rows["CharacterSwitch"]
    target_point = target_row.rect().bottomLeft()
    target_point.setY(target_point.y() + 6)
    target_global = target_row.mapToGlobal(target_point)

    source_row = window.task_rows["AccountIndexing"]
    source_global = source_row.mapToGlobal(source_row.rect().center())
    window._begin_task_drag("AccountIndexing", source_global, source_row.rect().center())
    window._drag_task(target_global)

    assert window.visible_task_names() == ["CharacterSwitch", "AccountIndexing"]
    assert window.task_rows["AccountIndexing"] is original_row

    window.close()
    app.quit()


def test_qt_launcher_drag_preview_stays_on_task_rail():
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()
    window.show()
    app.processEvents()

    source_row = window.task_rows["AccountIndexing"]
    source_global = source_row.mapToGlobal(source_row.rect().center())
    rail_global_x = window.task_list_container.mapToGlobal(QPoint(0, 0)).x()

    window._begin_task_drag("AccountIndexing", source_global, source_row.rect().center())
    window._drag_task(source_global + QPoint(120, 18))

    assert window.task_drag_preview.x() == window.mapFromGlobal(QPoint(rail_global_x, source_global.y())).x()
    rail_top = window.mapFromGlobal(window.task_list_container.mapToGlobal(QPoint(0, 0))).y()
    rail_bottom = rail_top + window.task_list_container.height() - window.task_drag_preview.height()
    assert rail_top <= window.task_drag_preview.y() <= rail_bottom

    window.close()
    app.quit()


def test_qt_launcher_drag_preview_clamps_to_task_rail_extremes():
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()
    window.show()
    app.processEvents()

    source_row = window.task_rows["AccountIndexing"]
    source_global = source_row.mapToGlobal(source_row.rect().center())
    rail_origin = window.task_list_container.mapToGlobal(QPoint(0, 0))
    rail_top = window.mapFromGlobal(rail_origin).y()

    window._begin_task_drag("AccountIndexing", source_global, source_row.rect().center())
    rail_bottom = rail_top + window.task_list_container.height() - window.task_drag_preview.height()
    window._drag_task(source_global + QPoint(0, -400))
    assert window.task_drag_preview.y() == rail_top

    window._drag_task(source_global + QPoint(0, 2000))
    assert window.task_drag_preview.y() == rail_bottom

    window.close()
    app.quit()


def test_qt_launcher_global_mouse_release_always_ends_drag():
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QMouseEvent
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()
    window.show()
    app.processEvents()

    source_row = window.task_rows["AccountIndexing"]
    source_global = source_row.mapToGlobal(source_row.rect().center())
    window._begin_task_drag("AccountIndexing", source_global, source_row.rect().center())

    release_event = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPoint(10, 10),
        QPoint(10, 10),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.eventFilter(app, release_event)

    assert window.dragging_task_name is None
    assert window.task_drag_preview.isHidden() is True

    window.close()
    app.quit()


def test_qt_launcher_task_row_allows_drag_on_text_but_not_checkbox_indicator():
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QMouseEvent
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()

    row = window.task_rows["AccountIndexing"]
    checkbox_center = row._checkbox_indicator_rect().center()
    text_point = QPoint(row.checkbox.geometry().x() + 34, row.checkbox.geometry().center().y())

    assert row._drag_allowed_from_pos(checkbox_center) is False
    assert row._drag_allowed_from_pos(text_point) is True

    checkbox_local_text_point = QPoint(34, row.checkbox.rect().center().y())
    press_event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        checkbox_local_text_point,
        checkbox_local_text_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    assert row.eventFilter(row.checkbox, press_event) is True
    assert row._drag_candidate is True

    window.close()
    app.quit()


def test_qt_launcher_task_row_height_fits_gear_button_without_clipping():
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()
    window.show()
    app.processEvents()

    row = window.task_rows["AccountIndexing"]
    assert row.height() >= row.gear_button.height() + 8
    assert row.gear_button.geometry().bottom() <= row.rect().bottom()

    window.close()
    app.quit()


def test_qt_launcher_window_reports_resize_hit_test_regions():
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()

    assert window._hit_test_resize_region(QPoint(1, 1)) == window.HTTOPLEFT
    assert window._hit_test_resize_region(QPoint(window.width() - 2, window.height() // 2)) == window.HTRIGHT
    assert window._hit_test_resize_region(QPoint(window.width() // 2, window.height() // 2)) is None

    window.close()
    app.quit()


def test_qt_launcher_buttons_and_tabs_use_motion_primitives():
    from gui_qt.main import build_application
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()

    assert hasattr(window.start_button, "hover_animation")
    assert window.start_button.hover_animation.duration() == 140
    assert hasattr(window.start_button, "press_animation")
    assert window.start_button.press_animation.duration() == 90
    assert hasattr(window.tab_widget, "page_fade_animation")
    assert window.tab_widget.page_fade_animation.duration() == 180

    first_task_row = next(iter(window.task_rows.values()))
    assert hasattr(first_task_row, "hover_animation")
    assert first_task_row.hover_animation.duration() == 140

    window.close()
    app.quit()


def test_qt_stylesheet_emphasizes_checked_backend_toggle():
    from gui_qt.theme.style import build_stylesheet

    stylesheet = build_stylesheet()

    assert 'QPushButton#backendToggle:checked {' in stylesheet
    assert 'border-color: ' in stylesheet
    assert 'text-align: center;' in stylesheet
    assert 'padding-left: 0px;' in stylesheet
