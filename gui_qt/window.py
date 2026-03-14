#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Qt main window shell for the MAA-style launcher."""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, Property, QEasingCurve, QPropertyAnimation, QRect, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QEnterEvent, QMouseEvent, QPaintEvent, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QApplication,
)

try:
    import keyboard
except ImportError:
    keyboard = None

from gui_qt.adapters.launcher_bridge import LauncherBridge
from gui_qt.theme import load_icon
from gui_qt.titlebar import LauncherTitleBar
from gui_qt.widgets import AnimatedButton, AnimatedTabWidget, BackendToggleButton
from launcher.service import resolve_controller_name
from launcher.update_service import ProxyConfig
from agent.py_service import __version__ as APP_VERSION


TASK_ITEMS = [
    {"task_name": "AccountIndexing", "label": "账号读取", "checked": True, "description": "扫描并索引当前账号角色"},
    {"task_name": "CharacterSwitch", "label": "全自动捐献", "checked": False, "description": "执行角色切换与完整捐献流程"},
]

CHECKLIST_ITEMS = [
    # Configuration widgets will be attached here later.
]


class TaskRowWidget(QWidget):
    """Task row that supports drag sorting outside its controls."""

    def __init__(self, task_item: dict[str, str | bool], parent_window: "FerrumMainWindow", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.parent_window = parent_window
        self.task_item = task_item
        self.setObjectName("taskRow")
        self.setCursor(Qt.OpenHandCursor)
        self.setFixedHeight(40)
        self.drag_activation_distance = 4
        self._drag_candidate = False
        self._drag_started = False
        self._press_global_pos = None
        self._press_offset = None
        self._hover_strength = 0.0
        self.hover_animation = QPropertyAnimation(self, b"hoverStrength", self)
        self.hover_animation.setDuration(140)
        self.hover_animation.setEasingCurve(QEasingCurve.OutCubic)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        self.checkbox = QCheckBox(str(task_item["label"]), self)
        self.checkbox.setChecked(bool(task_item.get("checked", False)))
        self.checkbox.toggled.connect(lambda checked: self.task_item.__setitem__("checked", bool(checked)))
        self.checkbox.toggled.connect(lambda _checked: self.parent_window._persist_task_queue_settings())
        self.checkbox.installEventFilter(self)

        self.gear_button = AnimatedButton("", self)
        self.gear_button.setObjectName("miniButton")
        self.gear_button.setIcon(load_icon("gear.svg"))
        self.gear_button.clicked.connect(lambda: self.parent_window._open_task_config(str(self.task_item["task_name"])))

        layout.addWidget(self.checkbox, 1)
        layout.addWidget(self.gear_button, 0)

    def _drag_allowed_from_pos(self, pos) -> bool:
        if self.gear_button.geometry().contains(pos):
            return False
        if self.checkbox.geometry().contains(pos):
            return not self._checkbox_indicator_rect().contains(pos)
        return True

    def _checkbox_indicator_rect(self):
        indicator_size = 18
        checkbox_rect = self.checkbox.geometry()
        indicator_y = checkbox_rect.y() + max(0, (checkbox_rect.height() - indicator_size) // 2)
        return QRect(checkbox_rect.x(), indicator_y, indicator_size, indicator_size)

    def _drag_allowed(self, event: QMouseEvent) -> bool:
        return self._drag_allowed_from_pos(event.position().toPoint())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._drag_allowed(event):
            self._drag_candidate = True
            self._drag_started = False
            self._press_global_pos = event.globalPosition().toPoint()
            self._press_offset = event.position().toPoint()
        super().mousePressEvent(event)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_candidate:
            if not self._drag_started and self._press_global_pos is not None:
                distance = (event.globalPosition().toPoint() - self._press_global_pos).manhattanLength()
                if distance >= self.drag_activation_distance:
                    self._drag_started = True
                    self.setCursor(Qt.ClosedHandCursor)
                    self.parent_window._begin_task_drag(
                        str(self.task_item["task_name"]),
                        event.globalPosition().toPoint(),
                        self._press_offset or event.position().toPoint(),
                    )
            if self._drag_started:
                self.parent_window._drag_task(event.globalPosition().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_candidate and self._drag_started:
            self.parent_window._end_task_drag(event.globalPosition().toPoint())
        self._drag_candidate = False
        self._drag_started = False
        self._press_global_pos = None
        self._press_offset = None
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.checkbox and isinstance(event, QMouseEvent):
            local_pos = event.position().toPoint()
            translated_pos = local_pos + self.checkbox.geometry().topLeft()
            if self._drag_allowed_from_pos(translated_pos):
                if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.LeftButton:
                    self._drag_candidate = True
                    self._drag_started = False
                    self._press_global_pos = event.globalPosition().toPoint()
                    self._press_offset = translated_pos
                    return True
                if event.type() == QEvent.Type.MouseMove and self._drag_candidate:
                    if not self._drag_started and self._press_global_pos is not None:
                        distance = (event.globalPosition().toPoint() - self._press_global_pos).manhattanLength()
                        if distance >= self.drag_activation_distance:
                            self._drag_started = True
                            self.setCursor(Qt.ClosedHandCursor)
                            self.parent_window._begin_task_drag(
                                str(self.task_item["task_name"]),
                                event.globalPosition().toPoint(),
                                self._press_offset or translated_pos,
                            )
                    if self._drag_started:
                        self.parent_window._drag_task(event.globalPosition().toPoint())
                    return True
                if event.type() == QEvent.Type.MouseButtonRelease and self._drag_candidate:
                    if self._drag_started:
                        self.parent_window._end_task_drag(event.globalPosition().toPoint())
                    self._drag_candidate = False
                    self._drag_started = False
                    self._press_global_pos = None
                    self._press_offset = None
                    self.setCursor(Qt.OpenHandCursor)
                    return True
        return super().eventFilter(watched, event)

    def set_drag_preview(self, active: bool) -> None:
        self.setProperty("dragging", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def get_hover_strength(self) -> float:
        return self._hover_strength

    def set_hover_strength(self, value: float) -> None:
        self._hover_strength = max(0.0, min(1.0, float(value)))
        self.update()

    hoverStrength = Property(float, get_hover_strength, set_hover_strength)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if self._hover_strength <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        overlay = QColor("#ffffff")
        overlay.setAlpha(int(10 * self._hover_strength))
        painter.fillRect(self.rect().adjusted(1, 1, -1, -1), overlay)

    def _animate_hover(self, target: float) -> None:
        self.hover_animation.stop()
        self.hover_animation.setStartValue(self._hover_strength)
        self.hover_animation.setEndValue(target)
        self.hover_animation.start()


class TaskListContainer(QWidget):
    """Absolute-positioned task list area for animated reordering."""

    def __init__(self, parent_window: "FerrumMainWindow", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.parent_window = parent_window

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.parent_window._layout_task_rows(animated=False)


class FerrumMainWindow(QMainWindow):
    """Minimal main window shell for the Qt launcher."""

    update_download_succeeded = Signal(dict)
    update_download_failed = Signal(str)

    WM_NCHITTEST = 0x0084
    HTLEFT = 10
    HTRIGHT = 11
    HTTOP = 12
    HTTOPLEFT = 13
    HTTOPRIGHT = 14
    HTBOTTOM = 15
    HTBOTTOMLEFT = 16
    HTBOTTOMRIGHT = 17

    def __init__(self, bridge: LauncherBridge | None = None) -> None:
        super().__init__()
        self.bridge = bridge or LauncherBridge(parent=self)
        self.settings = self.bridge.load_settings()
        self.interface_config = self.bridge.load_interface()
        self.ports = dict(self.settings.ports)
        self.baudrates = dict(getattr(self.settings, "baudrates", {}) or {"ferrum": 115200, "makcu": 115200})
        self.keyboard_via_python = bool(getattr(self.settings, "keyboard_via_python", True))
        self.force_pydd = bool(getattr(self.settings, "force_pydd", True))
        # Keyboard backend selection is now exclusive: Python keyboard vs PYDD.
        # Default to PYDD when legacy settings are ambiguous.
        if not self.keyboard_via_python and not self.force_pydd:
            self.force_pydd = True
            self.keyboard_via_python = True
        self.update_repo = str(getattr(self.settings, "update_repo", "") or "")
        self.update_proxy = getattr(self.settings, "update_proxy", ProxyConfig())
        self.current_backend = self.settings.driver_backend
        self.latest_update_result: dict | None = None
        self._update_download_thread: threading.Thread | None = None
        self.task_items = [dict(item, visible=True) for item in TASK_ITEMS]
        self._restore_task_queue_state()
        self.task_checkboxes: dict[str, QCheckBox] = {}
        self.task_rows: dict[str, TaskRowWidget] = {}
        self.dragging_task_name: str | None = None
        self.drag_target_index: int | None = None
        self.drag_press_offset = None
        self.task_row_spacing = 4
        self.task_row_animations: dict[str, QPropertyAnimation] = {}
        self.resize_margin = 6
        self.task_labels = {item["task_name"]: str(item["label"]) for item in self.task_items}
        self.active_config_task_name: str | None = None
        self._update_download_in_progress = False
        self._update_progress_animation: QPropertyAnimation | None = None
        self.update_download_succeeded.connect(self._on_update_download_succeeded)
        self.update_download_failed.connect(self._on_update_download_failed)
        self._f10_hotkey_handle = None
        self.setWindowTitle("LAA")
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1280, 760)
        self.setMinimumSize(1180, 720)

        root = QWidget(self)
        root.setObjectName("appRoot")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(0)

        shell = QWidget(root)
        shell.setObjectName("appShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(10, 8, 10, 10)
        shell_layout.setSpacing(8)

        self.title_bar = LauncherTitleBar(
            f"LAA {APP_VERSION}",
            shell,
        )
        shell_layout.addWidget(self.title_bar)

        self.tab_widget = AnimatedTabWidget(shell)
        self.tab_widget.setObjectName("mainTabs")
        self.tab_widget.addTab(self._build_page("主界面迁移中"), "一键长草")
        self.tab_widget.addTab(self._build_page("工具页迁移中"), "小工具")
        self.tab_widget.addTab(self._build_page("设置页迁移中"), "设置")
        self.tab_widget.addTab(self._build_page("日志页迁移中"), "日志")
        shell_layout.addWidget(self.tab_widget)

        layout.addWidget(shell)

        self.setCentralWidget(root)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self._bind_bridge_signals()
        self._register_global_hotkeys()
        self._apply_keyboard_env_flags()

    def _restore_task_queue_state(self) -> None:
        checked_map = dict(getattr(self.settings, "task_checked", {}) or {})
        visibility_map = dict(getattr(self.settings, "task_visibility", {}) or {})
        order = [str(name) for name in getattr(self.settings, "task_order", []) or []]
        order_map = {name: index for index, name in enumerate(order)}

        for item in self.task_items:
            task_name = str(item["task_name"])
            if task_name in checked_map:
                item["checked"] = bool(checked_map[task_name])
            if task_name in visibility_map:
                item["visible"] = bool(visibility_map[task_name])

        self.task_items.sort(key=lambda item: order_map.get(str(item["task_name"]), len(order_map)))

    def _build_page(self, text: str) -> QWidget:
        if text == "主界面迁移中":
            return self._build_home_page()
        if text == "工具页迁移中":
            return self._build_trigger_page()
        if text == "设置页迁移中":
            return self._build_settings_page()
        if text == "日志页迁移中":
            return self._build_logs_page()

        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        label = QLabel(text, page)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        return page

    def _build_home_page(self) -> QWidget:
        page = QWidget(self)
        page.setObjectName("homePage")
        outer = QHBoxLayout(page)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(16)

        outer.addWidget(self._build_task_panel(), 0)
        outer.addWidget(self._build_content_panel(), 1)
        return page

    def _build_task_panel(self) -> QWidget:
        panel = QWidget(self)
        panel.setObjectName("taskPanel")
        panel.setFixedWidth(290)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QLabel("任务队列", panel)
        header.setObjectName("sectionTitle")
        layout.addWidget(header)

        self.task_list_container = TaskListContainer(self, panel)
        self.task_list_container.setObjectName("taskListContainer")
        self.task_drag_preview = QLabel(self)
        self.task_drag_preview.setObjectName("taskDragPreview")
        self.task_drag_preview.hide()
        self.task_drag_preview.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.task_list_container, 1)

        self._rebuild_task_list()

        actions = QHBoxLayout()
        actions.setObjectName("taskListActions")
        actions.setSpacing(6)
        select_button = AnimatedButton("全选", panel)
        select_button.clicked.connect(self._select_all_tasks)
        clear_button = AnimatedButton("清空", panel)
        clear_button.clicked.connect(self._clear_all_tasks)
        add_button = AnimatedButton("", panel)
        add_button.setObjectName("miniButton")
        add_button.setIcon(load_icon("add.svg"))
        add_button.clicked.connect(self._show_task_visibility_menu)
        self.task_visibility_button = add_button
        actions.addWidget(add_button)
        actions.addWidget(select_button)
        actions.addWidget(clear_button)
        layout.addLayout(actions)

        separator = QFrame(panel)
        separator.setFrameShape(QFrame.HLine)
        separator.setObjectName("taskSeparator")
        layout.addWidget(separator)

        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(8)

        done_label = QLabel("完成后", panel)
        done_label.setObjectName("sectionTitle")
        done_action = QLabel("无动作", panel)
        done_action.setObjectName("taskMeta")
        self.start_button = AnimatedButton("Link Start!", panel)
        self.start_button.setObjectName("primaryButton")
        self.start_button.setMinimumHeight(48)
        self.start_button.clicked.connect(self._start_selected_tasks)

        bottom_layout.addWidget(done_label)
        bottom_layout.addWidget(done_action)
        bottom_layout.addWidget(self.start_button)
        layout.addLayout(bottom_layout)
        return panel

    def _build_content_panel(self) -> QWidget:
        panel = QWidget(self)
        panel.setObjectName("contentPanel")
        config_layout = QVBoxLayout(panel)
        config_layout.setContentsMargins(18, 18, 18, 18)
        config_layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)
        header_row.addWidget(self._build_status_strip(), 0, Qt.AlignTop)

        self.config_title_label = QLabel("", panel)
        self.config_title_label.setObjectName("sectionTitle")
        self.config_group = QWidget(panel)
        self.config_group.setObjectName("configGroup")
        config_group_layout = QVBoxLayout(self.config_group)
        config_group_layout.setContentsMargins(0, 0, 0, 0)
        config_group_layout.setSpacing(6)
        self.config_placeholder_label = QLabel("暂无配置项", panel)
        self.config_placeholder_label.setObjectName("contentHint")
        self.account_indexing_result_card = QWidget(panel)
        self.account_indexing_result_card.setObjectName("contentPanel")
        result_layout = QVBoxLayout(self.account_indexing_result_card)
        result_layout.setContentsMargins(12, 12, 12, 12)
        result_layout.setSpacing(10)
        self.account_indexing_count_label = QLabel("本次角色总数：-", self.account_indexing_result_card)
        self.account_indexing_count_label.setObjectName("contentInfo")
        result_actions = QHBoxLayout()
        result_actions.setContentsMargins(0, 0, 0, 0)
        result_actions.setSpacing(8)
        self.account_indexing_open_button = AnimatedButton("打开角色截图目录", self.account_indexing_result_card)
        self.account_indexing_save_button = AnimatedButton("保存", self.account_indexing_result_card)
        self.account_indexing_discard_button = AnimatedButton("丢弃", self.account_indexing_result_card)
        self.account_indexing_open_button.clicked.connect(self._open_account_indexing_characters_dir)
        self.account_indexing_save_button.clicked.connect(self._save_account_indexing_staging)
        self.account_indexing_discard_button.clicked.connect(self._discard_account_indexing_staging)
        result_actions.addWidget(self.account_indexing_open_button)
        result_actions.addWidget(self.account_indexing_save_button)
        result_actions.addWidget(self.account_indexing_discard_button)
        result_layout.addWidget(self.account_indexing_count_label)
        result_layout.addLayout(result_actions)
        self.account_indexing_result_card.hide()
        self.pending_account_indexing_result: dict | None = None

        config_layout.addLayout(header_row)
        config_layout.addWidget(self.config_title_label)
        config_group_layout.addWidget(self.config_placeholder_label)
        config_group_layout.addWidget(self.account_indexing_result_card)
        config_layout.addWidget(self.config_group)
        config_layout.addStretch(1)
        self._update_config_panel()
        return panel

    def _build_status_strip(self) -> QWidget:
        strip = QWidget(self)
        strip.setObjectName("topStatusPanel")
        outer = QHBoxLayout(strip)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        status_card = QWidget(strip)
        status_card.setObjectName("statusStrip")
        layout = QHBoxLayout(status_card)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        driver_group = QWidget(status_card)
        driver_group.setObjectName("statusGroup")
        driver_layout = QVBoxLayout(driver_group)
        driver_layout.setContentsMargins(0, 0, 0, 0)
        driver_layout.setSpacing(1)
        driver_label = QLabel("驱动", driver_group)
        driver_label.setObjectName("statusDriverLabel")
        self.driver_value = QLabel(self.settings.driver_backend.upper(), driver_group)
        self.driver_value.setObjectName("statusGroupValue")
        driver_layout.addWidget(driver_label)
        driver_layout.addWidget(self.driver_value)

        runtime_group = QWidget(status_card)
        runtime_group.setObjectName("statusGroup")
        runtime_layout = QVBoxLayout(runtime_group)
        runtime_layout.setContentsMargins(0, 0, 0, 0)
        runtime_layout.setSpacing(1)
        runtime_label = QLabel("状态", runtime_group)
        runtime_label.setObjectName("statusGroupLabel")
        self.runtime_state_value = QLabel("空闲", runtime_group)
        self.runtime_state_value.setObjectName("statusGroupValue")
        runtime_layout.addWidget(runtime_label)
        runtime_layout.addWidget(self.runtime_state_value)

        task_group = QWidget(status_card)
        task_group.setObjectName("statusGroup")
        task_layout = QVBoxLayout(task_group)
        task_layout.setContentsMargins(0, 0, 0, 0)
        task_layout.setSpacing(1)
        task_label = QLabel("任务", task_group)
        task_label.setObjectName("statusGroupLabel")
        self.current_task_value = QLabel("-", task_group)
        self.current_task_value.setObjectName("statusGroupValue")
        task_layout.addWidget(task_label)
        task_layout.addWidget(self.current_task_value)

        connection_group = QWidget(status_card)
        connection_group.setObjectName("statusGroup")
        connection_layout = QVBoxLayout(connection_group)
        connection_layout.setContentsMargins(0, 0, 0, 0)
        connection_layout.setSpacing(1)
        connection_label = QLabel("连接", connection_group)
        connection_label.setObjectName("statusConnectionLabel")
        self.connection_value = QLabel("未检测", connection_group)
        self.connection_value.setObjectName("statusGroupValue")
        connection_layout.addWidget(connection_label)
        connection_layout.addWidget(self.connection_value)

        self.status_probe_button = AnimatedButton("", status_card)
        self.status_probe_button.setObjectName("miniButton")
        self.status_probe_button.setIcon(load_icon("refresh.svg"))
        self.status_probe_button.clicked.connect(self._probe_current_driver)
        self.status_settings_button = AnimatedButton("", status_card)
        self.status_settings_button.setObjectName("miniButton")
        self.status_settings_button.setIcon(load_icon("settings.svg"))
        self.status_settings_button.clicked.connect(self._open_settings_tab)

        layout.addWidget(driver_group)
        layout.addWidget(connection_group)
        layout.addWidget(runtime_group)
        layout.addWidget(task_group)
        layout.addWidget(self.status_probe_button)
        layout.addWidget(self.status_settings_button)
        outer.addWidget(status_card, 0)
        return strip

    def _build_settings_page(self) -> QWidget:
        page = QWidget(self)
        page.setObjectName("settingsPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("驱动设置", page)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        driver_panel = QWidget(page)
        driver_panel.setObjectName("contentPanel")
        driver_layout = QVBoxLayout(driver_panel)
        driver_layout.setContentsMargins(16, 16, 16, 16)
        driver_layout.setSpacing(12)

        radio_row = QHBoxLayout()
        self.ferrum_button = BackendToggleButton("Ferrum", driver_panel)
        self.makcu_button = BackendToggleButton("Makcu", driver_panel)
        self.ferrum_button.setObjectName("backendToggle")
        self.makcu_button.setObjectName("backendToggle")
        self.ferrum_button.clicked.connect(lambda: self._select_backend("ferrum"))
        self.makcu_button.clicked.connect(lambda: self._select_backend("makcu"))
        radio_row.addWidget(self.ferrum_button)
        radio_row.addWidget(self.makcu_button)
        radio_row.addStretch(1)
        driver_layout.addLayout(radio_row)

        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("COM Port", driver_panel))
        self.port_entry = QLineEdit(self.ports.get(self.current_backend, "COM2"), driver_panel)
        self.port_entry.editingFinished.connect(self._persist_settings)
        self.detect_button = AnimatedButton("检测连接", driver_panel)
        self.detect_button.clicked.connect(self._probe_current_driver)
        port_row.addWidget(self.port_entry, 1)
        port_row.addWidget(self.detect_button)
        driver_layout.addLayout(port_row)

        baudrate_row = QHBoxLayout()
        baudrate_row.addWidget(QLabel("Baudrate", driver_panel))
        self.baudrate_entry = QLineEdit(str(self._baudrate_for_backend(self.current_backend)), driver_panel)
        self.baudrate_entry.editingFinished.connect(self._persist_settings)
        baudrate_row.addWidget(self.baudrate_entry, 1)
        driver_layout.addLayout(baudrate_row)

        keyboard_row = QHBoxLayout()
        self.keyboard_path_checkbox = QCheckBox("Python 键盘", driver_panel)
        self.keyboard_path_checkbox.toggled.connect(self._on_keyboard_path_toggled)
        self.force_pydd_checkbox = QCheckBox("PYDD", driver_panel)
        self.force_pydd_checkbox.toggled.connect(self._on_force_pydd_toggled)
        keyboard_row.addWidget(self.keyboard_path_checkbox)
        keyboard_row.addWidget(self.force_pydd_checkbox)
        keyboard_row.addStretch(1)
        driver_layout.addLayout(keyboard_row)

        self.settings_status_label = QLabel("选择驱动并探测连接状态。", driver_panel)
        self.settings_status_label.setObjectName("contentHint")
        driver_layout.addWidget(self.settings_status_label)
        layout.addWidget(driver_panel, 0)

        update_title = QLabel("模块更新", page)
        update_title.setObjectName("sectionTitle")
        layout.addWidget(update_title)

        update_panel = QWidget(page)
        update_panel.setObjectName("contentPanel")
        update_layout = QVBoxLayout(update_panel)
        update_layout.setContentsMargins(16, 16, 16, 16)
        update_layout.setSpacing(12)

        version_row = QHBoxLayout()
        version_row.addWidget(QLabel("当前版本", update_panel))
        self.current_version_label = QLabel(APP_VERSION, update_panel)
        self.current_version_label.setObjectName("taskMeta")
        version_row.addWidget(self.current_version_label)
        version_row.addStretch(1)
        update_layout.addLayout(version_row)

        repo_row = QHBoxLayout()
        repo_row.addWidget(QLabel("GitHub Repo", update_panel))
        self.update_repo_entry = QLineEdit(self.update_repo, update_panel)
        self.update_repo_entry.editingFinished.connect(self._persist_settings)
        repo_row.addWidget(self.update_repo_entry, 1)
        update_layout.addLayout(repo_row)

        proxy_toggle_row = QHBoxLayout()
        self.update_proxy_checkbox = QCheckBox("启用代理", update_panel)
        self.update_proxy_checkbox.toggled.connect(self._on_update_proxy_toggled)
        proxy_toggle_row.addWidget(self.update_proxy_checkbox)
        proxy_toggle_row.addStretch(1)
        update_layout.addLayout(proxy_toggle_row)

        proxy_row = QHBoxLayout()
        self.update_proxy_scheme_combo = QComboBox(update_panel)
        self.update_proxy_scheme_combo.addItems(["http", "socks5"])
        self.update_proxy_scheme_combo.currentTextChanged.connect(lambda _value: self._persist_settings())
        self.update_proxy_host_entry = QLineEdit(str(self.update_proxy.host or ""), update_panel)
        self.update_proxy_host_entry.setPlaceholderText("127.0.0.1")
        self.update_proxy_host_entry.editingFinished.connect(self._persist_settings)
        self.update_proxy_port_entry = QLineEdit(str(self.update_proxy.port or ""), update_panel)
        self.update_proxy_port_entry.setPlaceholderText("7890")
        self.update_proxy_port_entry.editingFinished.connect(self._persist_settings)
        proxy_row.addWidget(self.update_proxy_scheme_combo, 0)
        proxy_row.addWidget(self.update_proxy_host_entry, 1)
        proxy_row.addWidget(self.update_proxy_port_entry, 0)
        update_layout.addLayout(proxy_row)

        proxy_auth_row = QHBoxLayout()
        self.update_proxy_username_entry = QLineEdit(str(self.update_proxy.username or ""), update_panel)
        self.update_proxy_username_entry.setPlaceholderText("Username")
        self.update_proxy_username_entry.editingFinished.connect(self._persist_settings)
        self.update_proxy_password_entry = QLineEdit(str(self.update_proxy.password or ""), update_panel)
        self.update_proxy_password_entry.setPlaceholderText("Password")
        self.update_proxy_password_entry.setEchoMode(QLineEdit.Password)
        self.update_proxy_password_entry.editingFinished.connect(self._persist_settings)
        proxy_auth_row.addWidget(self.update_proxy_username_entry, 1)
        proxy_auth_row.addWidget(self.update_proxy_password_entry, 1)
        update_layout.addLayout(proxy_auth_row)

        update_action_row = QHBoxLayout()
        self.check_update_button = AnimatedButton("检查更新", update_panel)
        self.check_update_button.clicked.connect(self._check_for_updates)
        self.download_update_button = AnimatedButton("下载更新", update_panel)
        self.download_update_button.setEnabled(False)
        self.download_update_button.clicked.connect(self._download_and_apply_update)
        update_action_row.addWidget(self.check_update_button)
        update_action_row.addWidget(self.download_update_button)
        self.update_progress_bar = QProgressBar(update_panel)
        self.update_progress_bar.setObjectName("updateProgressBar")
        self.update_progress_bar.setRange(0, 100)
        self.update_progress_bar.setValue(0)
        self.update_progress_bar.setTextVisible(True)
        self.update_progress_bar.setFormat("%p%")
        self.update_progress_bar.hide()
        update_action_row.addWidget(self.update_progress_bar, 1)
        update_layout.addLayout(update_action_row)

        self.update_status_label = QLabel("检查 GitHub Release 获取最新版本。", update_panel)
        self.update_status_label.setObjectName("contentHint")
        update_layout.addWidget(self.update_status_label)

        layout.addWidget(update_panel, 0)
        layout.addStretch(1)

        self._select_backend(self.current_backend, persist=False)
        self._apply_update_proxy_state()
        return page

    def _build_logs_page(self) -> QWidget:
        page = QWidget(self)
        page.setObjectName("logsPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("运行日志", page)
        title.setObjectName("sectionTitle")
        self.log_view = QPlainTextEdit(page)
        self.log_view.setReadOnly(True)
        self.log_view.setObjectName("logView")

        layout.addWidget(title)
        layout.addWidget(self.log_view, 1)
        return page

    def _build_trigger_page(self) -> QWidget:
        page = QWidget(self)
        page.setObjectName("triggerPage")
        outer = QHBoxLayout(page)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(16)

        left = QWidget(page)
        left.setObjectName("taskPanel")
        left.setFixedWidth(320)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)

        title = QLabel("图像触发", left)
        title.setObjectName("sectionTitle")
        description = QLabel("点击按钮长期启用，再次点击关闭线程。", left)
        description.setObjectName("contentHint")
        self.trigger_toggle_button = AnimatedButton("启动图像触发", left)
        self.trigger_toggle_button.setObjectName("primaryButton")
        self.trigger_toggle_button.setMinimumHeight(42)
        self.trigger_toggle_button.clicked.connect(self._toggle_trigger)
        self.trigger_state_label = QLabel("未运行", left)
        self.trigger_state_label.setObjectName("taskMeta")

        left_layout.addWidget(title)
        left_layout.addWidget(description)
        left_layout.addWidget(self.trigger_toggle_button)
        left_layout.addWidget(self.trigger_state_label)
        left_layout.addStretch(1)

        right = QWidget(page)
        right.setObjectName("contentPanel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(10)

        right_title = QLabel("功能说明", right)
        right_title.setObjectName("sectionTitle")
        guide = QLabel(
            "用途\n长期轮询屏幕中的特定图像，并在命中后立即执行预设动作。\n\n"
            "任务 A\n检测 target_a.png 后执行 Up -> Up -> Down。\n\n"
            "任务 B\n检测 target_b_1.png 或 target_b_2.png 后执行偏移点击，再按 Enter。",
            right,
        )
        guide.setObjectName("contentInfo")
        guide.setWordWrap(True)

        right_layout.addWidget(right_title)
        right_layout.addWidget(guide, 1)

        outer.addWidget(left, 0)
        outer.addWidget(right, 1)
        return page

    def _bind_bridge_signals(self) -> None:
        self.bridge.task_started.connect(self._on_task_started)
        self.bridge.task_finished.connect(self._on_task_finished)
        self.bridge.log_emitted.connect(self._append_log)
        self.bridge.trigger_started.connect(self._on_trigger_started)
        self.bridge.trigger_finished.connect(self._on_trigger_finished)
        self.bridge.probe_finished.connect(self._on_probe_finished)
        account_indexing_signal = getattr(self.bridge, "account_indexing_staged", None)
        if account_indexing_signal is not None:
            account_indexing_signal.connect(self._on_account_indexing_staged)
        update_progress_signal = getattr(self.bridge, "update_download_progress", None)
        if update_progress_signal is not None:
            update_progress_signal.connect(self._on_update_download_progress)

    def _select_all_tasks(self) -> None:
        for checkbox in self.task_checkboxes.values():
            checkbox.setChecked(True)

    def _clear_all_tasks(self) -> None:
        for checkbox in self.task_checkboxes.values():
            checkbox.setChecked(False)

    def _selected_tasks(self) -> list[dict[str, str | bool]]:
        selected = []
        for item in self.task_items:
            if not item.get("visible", True):
                continue
            checkbox = self.task_checkboxes.get(str(item["task_name"]))
            if checkbox is not None and checkbox.isChecked():
                selected.append(item)
        return selected

    def visible_task_names(self) -> list[str]:
        return [str(item["task_name"]) for item in self.task_items if item.get("visible", True)]

    def _task_checked_state(self) -> dict[str, bool]:
        return {str(item["task_name"]): bool(item.get("checked", False)) for item in self.task_items}

    def _task_visibility_state(self) -> dict[str, bool]:
        return {str(item["task_name"]): bool(item.get("visible", True)) for item in self.task_items}

    def _persist_task_queue_settings(self) -> None:
        self._save_bridge_settings(
            self.current_backend,
            dict(self.ports),
            dict(self.baudrates),
            task_checked=self._task_checked_state(),
            task_visibility=self._task_visibility_state(),
            task_order=[str(item["task_name"]) for item in self.task_items],
        )

    def set_task_visibility(self, task_name: str, visible: bool) -> None:
        for item in self.task_items:
            if str(item["task_name"]) == task_name:
                item["visible"] = bool(visible)
                break
        self._rebuild_task_list()
        self._persist_task_queue_settings()

    def set_task_order(self, order: list[str]) -> None:
        order_map = {name: index for index, name in enumerate(order)}
        self.task_items.sort(key=lambda item: order_map.get(str(item["task_name"]), len(order_map)))
        self._rebuild_task_list()
        self._persist_task_queue_settings()

    def _apply_live_task_order(self, visible_order: list[str]) -> None:
        hidden_names = [str(item["task_name"]) for item in self.task_items if not item.get("visible", True)]
        order_map = {name: index for index, name in enumerate(visible_order + hidden_names)}
        self.task_items.sort(key=lambda item: order_map.get(str(item["task_name"]), len(order_map)))
        self._layout_task_rows(animated=True)

    def _rebuild_task_list(self) -> None:
        for row_widget in self.task_rows.values():
            row_widget.deleteLater()
        self.task_checkboxes.clear()
        self.task_rows.clear()
        for item in self.task_items:
            if not item.get("visible", True):
                continue
            row_widget = TaskRowWidget(item, self, self.task_list_container)
            if self.dragging_task_name == str(item["task_name"]):
                row_widget.set_drag_preview(True)
                row_widget.hide()
            self.task_checkboxes[str(item["task_name"])] = row_widget.checkbox
            self.task_rows[str(item["task_name"])] = row_widget
        self._layout_task_rows(animated=False)

    def _show_task_visibility_menu(self) -> None:
        menu = QMenu(self)
        for item in self.task_items:
            action = menu.addAction(str(item["label"]))
            action.setCheckable(True)
            action.setChecked(bool(item.get("visible", True)))
            action.toggled.connect(lambda checked, name=str(item["task_name"]): self.set_task_visibility(name, checked))

        menu.exec(self.task_visibility_button.mapToGlobal(self.task_visibility_button.rect().bottomLeft()))

    def _resolve_controller_name(self, backend: str) -> str:
        try:
            return resolve_controller_name(self.interface_config, backend)
        except Exception:
            fallback = {"ferrum": "KMBox-Default", "makcu": "MAKCU-Default"}
            return fallback.get(str(backend).lower(), "KMBox-Default")

    def _on_backend_changed(self, backend: str, checked: bool) -> None:
        if not checked:
            return
        self.current_backend = backend
        if hasattr(self, "port_entry"):
            self.port_entry.setText(self.ports.get(backend, "COM2" if backend == "ferrum" else "COM3"))
        if hasattr(self, "baudrate_entry"):
            self.baudrate_entry.setText(str(self._baudrate_for_backend(backend)))
        if hasattr(self, "keyboard_path_checkbox"):
            is_makcu = backend == "makcu"
            self.keyboard_path_checkbox.setHidden(not is_makcu)
        if hasattr(self, "force_pydd_checkbox"):
            is_makcu = backend == "makcu"
            self.force_pydd_checkbox.setHidden(not is_makcu)
        self.driver_value.setText(backend.upper())
        self._persist_settings()

    def _select_backend(self, backend: str, persist: bool = True) -> None:
        self.current_backend = backend
        if hasattr(self, "ferrum_button"):
            self.ferrum_button.setChecked(backend == "ferrum")
        if hasattr(self, "makcu_button"):
            self.makcu_button.setChecked(backend == "makcu")
        if hasattr(self, "port_entry"):
            self.port_entry.setText(self.ports.get(backend, "COM2" if backend == "ferrum" else "COM3"))
        if hasattr(self, "baudrate_entry"):
            self.baudrate_entry.setText(str(self._baudrate_for_backend(backend)))
        if hasattr(self, "keyboard_path_checkbox"):
            self.keyboard_path_checkbox.blockSignals(True)
            self.keyboard_path_checkbox.setChecked(not self.force_pydd)
            self.keyboard_path_checkbox.setHidden(backend != "makcu")
            self.keyboard_path_checkbox.blockSignals(False)
        if hasattr(self, "force_pydd_checkbox"):
            self.force_pydd_checkbox.blockSignals(True)
            self.force_pydd_checkbox.setChecked(self.force_pydd)
            self.force_pydd_checkbox.setHidden(backend != "makcu")
            self.force_pydd_checkbox.blockSignals(False)
        self.driver_value.setText(backend.upper())
        if persist:
            self._persist_settings()

    def _persist_settings(self) -> None:
        if hasattr(self, "port_entry"):
            self.ports[self.current_backend] = self.port_entry.text().strip() or self.ports.get(self.current_backend, "COM2")
        if hasattr(self, "baudrate_entry"):
            self.baudrates[self.current_backend] = self._normalize_baudrate(
                self.baudrate_entry.text(),
                self.baudrates.get(self.current_backend, 115200),
            )
            self.baudrate_entry.setText(str(self.baudrates[self.current_backend]))
        if hasattr(self, "update_repo_entry"):
            self.update_repo = self.update_repo_entry.text().strip()
        if hasattr(self, "update_proxy_checkbox"):
            self.update_proxy = ProxyConfig(
                enabled=self.update_proxy_checkbox.isChecked(),
                scheme=self.update_proxy_scheme_combo.currentText().strip().lower() or "http",
                host=self.update_proxy_host_entry.text().strip(),
                port=self._normalize_positive_int(self.update_proxy_port_entry.text(), 0),
                username=self.update_proxy_username_entry.text().strip(),
                password=self.update_proxy_password_entry.text(),
            )
            self.update_proxy_port_entry.setText("" if self.update_proxy.port <= 0 else str(self.update_proxy.port))
        self._apply_keyboard_env_flags()
        self._save_bridge_settings(
            self.current_backend,
            dict(self.ports),
            dict(self.baudrates),
            keyboard_via_python=self.keyboard_via_python,
            force_pydd=self.force_pydd,
            update_repo=self.update_repo,
            update_proxy=self.update_proxy,
            task_checked=self._task_checked_state(),
            task_visibility=self._task_visibility_state(),
            task_order=[str(item["task_name"]) for item in self.task_items],
        )

    def _probe_current_driver(self) -> None:
        self._persist_settings()
        port = self.ports.get(self.current_backend, "COM2")
        baudrate = self._baudrate_for_backend(self.current_backend)
        self.connection_value.setText("检测中")
        if hasattr(self, "settings_status_label"):
            self.settings_status_label.setText("正在探测控制器连接。")
        self._bridge_probe(
            self.interface_config,
            self.current_backend,
            port,
            baudrate,
            keyboard_via_python=self.keyboard_via_python,
        )

    def _toggle_trigger(self) -> None:
        if self.bridge.is_busy():
            self.bridge.stop_trigger()
            return

        self._persist_settings()
        port = self.ports.get(self.current_backend, "COM2")
        baudrate = self._baudrate_for_backend(self.current_backend)
        self._bridge_start_trigger(
            self.interface_config,
            self.current_backend,
            port,
            baudrate,
            keyboard_via_python=self.keyboard_via_python,
        )

    def _open_settings_tab(self) -> None:
        for index in range(self.tab_widget.count()):
            if self.tab_widget.tabText(index) == "设置":
                self.tab_widget.setCurrentIndex(index)
                return

    def _start_selected_tasks(self) -> None:
        if self.bridge.is_busy():
            self.bridge.stop_task()
            return

        selected = self._selected_tasks()
        if not selected:
            self._append_log("[Launcher] no task selected")
            return

        task = selected[0]
        backend = self.current_backend
        port = self.ports.get(backend, "COM2")
        baudrate = self._baudrate_for_backend(backend)
        controller_name = self._resolve_controller_name(backend)
        self._set_busy(True)
        self._bridge_start_task(
            str(task["task_name"]),
            controller_name,
            port,
            baudrate,
            keyboard_via_python=self.keyboard_via_python,
        )

    def _baudrate_for_backend(self, backend: str) -> int:
        return self._normalize_baudrate(self.baudrates.get(backend, 115200), 115200)

    def _normalize_baudrate(self, value: object, default: int = 115200) -> int:
        try:
            baudrate = int(str(value).strip())
        except (TypeError, ValueError):
            return int(default)
        if baudrate <= 0:
            return int(default)
        return baudrate

    def _normalize_positive_int(self, value: object, default: int = 0) -> int:
        try:
            number = int(str(value).strip())
        except (TypeError, ValueError):
            return int(default)
        if number <= 0:
            return int(default)
        return number

    def _save_bridge_settings(self, driver_backend: str, ports: dict[str, str], baudrates: dict[str, int], **kwargs) -> None:
        reduced_kwargs = dict(kwargs)
        legacy_kwargs = dict(kwargs)
        legacy_kwargs.pop("update_repo", None)
        legacy_kwargs.pop("update_proxy", None)
        bare_kwargs = dict(legacy_kwargs)
        bare_kwargs.pop("keyboard_via_python", None)
        bare_kwargs.pop("force_pydd", None)
        try:
            self.bridge.save_settings(driver_backend, ports, baudrates, **kwargs)
        except TypeError:
            try:
                self.bridge.save_settings(driver_backend, ports, baudrates, **legacy_kwargs)
            except TypeError:
                try:
                    self.bridge.save_settings(driver_backend, ports, baudrates, **bare_kwargs)
                except TypeError:
                    self.bridge.save_settings(driver_backend, ports, **bare_kwargs)

    def _bridge_probe(self, interface_config: dict, driver_backend: str, port: str, baudrate: int, keyboard_via_python: bool = False) -> None:
        try:
            self.bridge.probe(interface_config, driver_backend, port, baudrate, keyboard_via_python)
        except TypeError:
            try:
                self.bridge.probe(interface_config, driver_backend, port, baudrate)
            except TypeError:
                self.bridge.probe(interface_config, driver_backend, port)

    def _bridge_start_trigger(self, interface_config: dict, driver_backend: str, port: str, baudrate: int, keyboard_via_python: bool = False) -> None:
        try:
            self.bridge.start_trigger(interface_config, driver_backend, port, baudrate, keyboard_via_python)
        except TypeError:
            try:
                self.bridge.start_trigger(interface_config, driver_backend, port, baudrate)
            except TypeError:
                self.bridge.start_trigger(interface_config, driver_backend, port)

    def _on_update_proxy_toggled(self, checked: bool) -> None:
        self._apply_update_proxy_state(enabled=bool(checked))
        self._persist_settings()

    def _apply_update_proxy_state(self, enabled: bool | None = None) -> None:
        if not hasattr(self, "update_proxy_checkbox"):
            return
        if enabled is None:
            enabled = bool(self.update_proxy.enabled)
        self.update_proxy_checkbox.blockSignals(True)
        self.update_proxy_checkbox.setChecked(bool(enabled))
        self.update_proxy_checkbox.blockSignals(False)
        if hasattr(self, "update_proxy_scheme_combo"):
            scheme = str(self.update_proxy.scheme or "http").lower()
            index = self.update_proxy_scheme_combo.findText(scheme)
            self.update_proxy_scheme_combo.setCurrentIndex(0 if index < 0 else index)
        for widget in (
            getattr(self, "update_proxy_scheme_combo", None),
            getattr(self, "update_proxy_host_entry", None),
            getattr(self, "update_proxy_port_entry", None),
            getattr(self, "update_proxy_username_entry", None),
            getattr(self, "update_proxy_password_entry", None),
        ):
            if widget is not None:
                widget.setEnabled(bool(enabled))

    def _check_for_updates(self) -> None:
        self._persist_settings()
        self._reset_update_progress()
        try:
            result = self.bridge.check_for_updates(APP_VERSION)
        except Exception as exc:
            self.latest_update_result = None
            self.update_status_label.setText(f"检查失败: {exc}")
            self.download_update_button.setEnabled(False)
            self._append_log(f"[Launcher] update check failed: {exc}")
            return
        self.latest_update_result = dict(result)
        version = str(result.get("version", "")).strip() or str(result.get("tag_name", "")).strip() or "unknown"
        assets = [asset for asset in result.get("assets", []) if isinstance(asset, dict)]
        has_verified_asset = any(str(asset.get("sha256", "")).strip() for asset in assets)
        release_issues = [str(issue).strip() for issue in result.get("release_issues", []) if str(issue).strip()]
        if bool(result.get("is_prerelease", False)):
            self.update_status_label.setText(f"发现预发布版本 {version}，当前仅支持正式版自动更新。")
            self.download_update_button.setEnabled(False)
        elif release_issues:
            self.update_status_label.setText("；".join(release_issues))
            self.download_update_button.setEnabled(False)
        elif bool(result.get("is_newer", False)) and not has_verified_asset:
            self.update_status_label.setText(f"发现新版本 {version}，但缺少 SHA-256 校验信息，已禁用自动更新。")
            self.download_update_button.setEnabled(False)
        elif bool(result.get("is_newer", False)):
            self.update_status_label.setText(f"发现新版本 {version}，可准备下载更新。")
            self.download_update_button.setEnabled(True)
        else:
            self.update_status_label.setText(f"当前已是最新版本 ({version})。")
            self.download_update_button.setEnabled(False)

    def _download_and_apply_update(self) -> None:
        if not self.latest_update_result or not self.latest_update_result.get("assets"):
            self.update_status_label.setText("缺少可下载的更新包，请先检查更新。")
            self.download_update_button.setEnabled(False)
            return
        self._update_download_in_progress = True
        self._show_update_progress()
        self._set_update_progress_value(0, 100, "0%")
        self.update_status_label.setText("正在下载更新包...")
        self.download_update_button.setEnabled(False)
        install_dir, restart_executable, restart_args = self._build_update_restart_context()

        def worker() -> None:
            try:
                result = self.bridge.download_and_apply_update(
                    self.latest_update_result,
                    install_dir=install_dir,
                    restart_executable=restart_executable,
                    restart_args=restart_args,
                )
            except Exception as exc:
                self.update_download_failed.emit(str(exc))
                return
            self.update_download_succeeded.emit(dict(result or {}))

        self._update_download_thread = threading.Thread(target=worker, name="qt-update-download", daemon=True)
        self._update_download_thread.start()

    def _show_update_progress(self) -> None:
        if hasattr(self, "update_progress_bar"):
            self.update_progress_bar.show()

    def _reset_update_progress(self) -> None:
        if not hasattr(self, "update_progress_bar"):
            return
        if self._update_progress_animation is not None:
            self._update_progress_animation.stop()
        self.update_progress_bar.setRange(0, 100)
        self.update_progress_bar.setValue(0)
        self.update_progress_bar.setFormat("%p%")
        self.update_progress_bar.hide()

    def _set_update_progress_value(self, value: int, maximum: int, label: str | None = None) -> None:
        if not hasattr(self, "update_progress_bar"):
            return
        maximum = max(0, int(maximum))
        value = max(0, int(value))
        self.update_progress_bar.setRange(0, maximum if maximum > 0 else 0)
        if label is not None:
            self.update_progress_bar.setFormat(label)
        if self._update_progress_animation is None:
            self._update_progress_animation = QPropertyAnimation(self.update_progress_bar, b"value", self)
            self._update_progress_animation.setDuration(120)
            self._update_progress_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._update_progress_animation.stop()
        if value >= maximum and maximum > 0:
            self.update_progress_bar.setValue(value)
            return
        self._update_progress_animation.setStartValue(self.update_progress_bar.value())
        self._update_progress_animation.setEndValue(value)
        self._update_progress_animation.start()

    def _on_update_download_progress(self, downloaded: int, total: int, percent: int) -> None:
        if not hasattr(self, "update_progress_bar"):
            return
        self._show_update_progress()
        if int(total) > 0:
            clamped_percent = max(0, min(100, int(percent)))
            self._set_update_progress_value(clamped_percent, 100, f"{clamped_percent}%")
            self.update_status_label.setText(f"正在下载更新包... {clamped_percent}%")
            return
        self.update_progress_bar.setRange(0, 0)
        self.update_progress_bar.setFormat("下载中...")
        self.update_status_label.setText("正在下载更新包...")

    def _on_update_download_succeeded(self, result: dict) -> None:
        self._update_download_in_progress = False
        self._set_update_progress_value(100, 100, "100%")
        self.update_status_label.setText("更新包已下载，程序即将退出并应用更新。")
        log_path = str(result.get("log_path", "")).strip()
        if log_path:
            self._append_log(f"[Launcher] update installer log: {log_path}")
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _on_update_download_failed(self, message: str) -> None:
        self._update_download_in_progress = False
        self.update_status_label.setText(f"下载失败: {message}")
        self._append_log(f"[Launcher] update download failed: {message}")
        self._reset_update_progress()

    def _build_update_restart_context(self) -> tuple[str, str, list[str]]:
        if getattr(sys, "frozen", False):
            executable = str(Path(sys.executable).resolve())
            install_dir = str(Path(executable).parent)
            return install_dir, executable, []
        install_dir = str(Path(__file__).resolve().parents[1])
        executable = str(Path(sys.executable).resolve())
        launcher_script = str(Path(__file__).resolve().parents[1] / "gui_launcher.py")
        return install_dir, executable, [launcher_script]

    def _bridge_start_task(
        self,
        task_name: str,
        controller_name: str,
        port: str,
        baudrate: int,
        keyboard_via_python: bool = False,
    ) -> None:
        try:
            self.bridge.start_task(task_name, controller_name, port, baudrate, keyboard_via_python)
        except TypeError:
            try:
                self.bridge.start_task(task_name, controller_name, port, baudrate)
            except TypeError:
                self.bridge.start_task(task_name, controller_name, port)

    def _on_keyboard_path_toggled(self, checked: bool) -> None:
        if not checked:
            # Keep one option always selected; PYDD is default fallback.
            self.force_pydd = True
            if hasattr(self, "force_pydd_checkbox"):
                self.force_pydd_checkbox.blockSignals(True)
                self.force_pydd_checkbox.setChecked(True)
                self.force_pydd_checkbox.blockSignals(False)
        else:
            self.force_pydd = False
            if hasattr(self, "force_pydd_checkbox"):
                self.force_pydd_checkbox.blockSignals(True)
                self.force_pydd_checkbox.setChecked(False)
                self.force_pydd_checkbox.blockSignals(False)
        self.keyboard_via_python = True
        self._persist_settings()

    def _on_force_pydd_toggled(self, checked: bool) -> None:
        if checked:
            self.force_pydd = True
            if hasattr(self, "keyboard_path_checkbox"):
                self.keyboard_path_checkbox.blockSignals(True)
                self.keyboard_path_checkbox.setChecked(False)
                self.keyboard_path_checkbox.blockSignals(False)
        else:
            # Keep one option always selected.
            self.force_pydd = False
            if hasattr(self, "keyboard_path_checkbox"):
                self.keyboard_path_checkbox.blockSignals(True)
                self.keyboard_path_checkbox.setChecked(True)
                self.keyboard_path_checkbox.blockSignals(False)
        self.keyboard_via_python = True
        self._persist_settings()

    def _apply_keyboard_env_flags(self) -> None:
        os.environ["LAA_FORCE_PYDD"] = "1" if self.force_pydd else "0"

    def _set_busy(self, busy: bool) -> None:
        self.start_button.setEnabled(True)
        self.start_button.setText("运行中..." if busy else "Link Start!")
        self.task_list_container.setEnabled(not busy)
        for checkbox in self.task_checkboxes.values():
            checkbox.setEnabled(not busy)

    def _register_global_hotkeys(self) -> None:
        if keyboard is None:
            self._append_log("[Launcher] keyboard hotkey unavailable")
            return
        try:
            self._f10_hotkey_handle = keyboard.add_hotkey("f10", self._request_task_stop)
        except Exception as exc:
            self._append_log(f"[Launcher] failed to register F10 hotkey: {exc}")

    def _unregister_global_hotkeys(self) -> None:
        if keyboard is None or self._f10_hotkey_handle is None:
            return
        try:
            keyboard.remove_hotkey(self._f10_hotkey_handle)
        except Exception:
            pass
        self._f10_hotkey_handle = None

    def _request_task_stop(self) -> None:
        if self.bridge.is_busy():
            self.bridge.stop_task()

    def _begin_task_drag(self, task_name: str, global_pos, press_offset) -> None:
        self.dragging_task_name = task_name
        self.drag_target_index = self.visible_task_names().index(task_name)
        self.drag_press_offset = press_offset
        row = self.task_rows.get(task_name)
        if row is not None:
            row.set_drag_preview(True)
            row.hide()
            self.task_drag_preview.setPixmap(row.grab())
            self.task_drag_preview.resize(row.size())
            self._update_drag_preview_position(global_pos)
            self.task_drag_preview.show()
            self.task_drag_preview.raise_()
        self._layout_task_rows(animated=True)

    def _drag_task(self, global_pos) -> None:
        if not self.dragging_task_name:
            return
        self._update_drag_preview_position(global_pos)

        target_index = self._resolve_drop_index(global_pos)
        if target_index is None or target_index == self.drag_target_index:
            return

        self.drag_target_index = target_index
        visible_names = self.visible_task_names()
        ordered_names = [name for name in visible_names if name != self.dragging_task_name]
        clamped_index = max(0, min(target_index, len(ordered_names)))
        ordered_names.insert(clamped_index, self.dragging_task_name)
        self._apply_live_task_order(ordered_names)

    def _end_task_drag(self, global_pos) -> None:
        if not self.dragging_task_name:
            return

        row = self.task_rows.get(self.dragging_task_name)
        if row is not None:
            row.set_drag_preview(False)
            row.show()
        self.task_drag_preview.hide()
        self.dragging_task_name = None
        self.drag_target_index = None
        self.drag_press_offset = None
        self._layout_task_rows(animated=False)

    def _resolve_drop_index(self, global_pos) -> int | None:
        container_pos = self.task_list_container.mapFromGlobal(global_pos)
        visible_names = [name for name in self.visible_task_names() if name != self.dragging_task_name]
        if not visible_names:
            return 0

        for index, task_name in enumerate(visible_names):
            row = self.task_rows.get(task_name)
            if row is None:
                continue
            midpoint = row.geometry().top() + (row.height() / 2)
            if container_pos.y() < midpoint:
                return index
        return len(visible_names)

    def _layout_task_rows(self, animated: bool) -> None:
        if not hasattr(self, "task_list_container"):
            return

        visible_names = [name for name in self.visible_task_names() if name != self.dragging_task_name]
        width = max(0, self.task_list_container.width())
        y = 0
        gap_index = self.drag_target_index if self.dragging_task_name is not None else None
        gap_height = self._task_row_height() + self.task_row_spacing if self.dragging_task_name else 0

        for index, task_name in enumerate(visible_names):
            if gap_index is not None and index == gap_index:
                y += gap_height
            row = self.task_rows.get(task_name)
            if row is None:
                continue
            target_rect = row.geometry()
            target_rect.setX(0)
            target_rect.setY(y)
            target_rect.setWidth(width)
            target_rect.setHeight(self._task_row_height())
            self._move_task_row(row, target_rect, animated)
            y += self._task_row_height() + self.task_row_spacing

        if gap_index is not None and gap_index >= len(visible_names):
            y += gap_height

        self.task_list_container.setMinimumHeight(max(y, self._task_row_height()))

    def _move_task_row(self, row: TaskRowWidget, target_rect, animated: bool) -> None:
        if row.geometry() == target_rect:
            row.show()
            return

        if not animated:
            row.setGeometry(target_rect)
            row.show()
            return

        animation = self.task_row_animations.get(str(row.task_item["task_name"]))
        if animation is None:
            animation = QPropertyAnimation(row, b"geometry", self)
            animation.setDuration(150)
            animation.setEasingCurve(QEasingCurve.OutCubic)
            self.task_row_animations[str(row.task_item["task_name"])] = animation
        animation.stop()
        animation.setStartValue(row.geometry())
        animation.setEndValue(target_rect)
        row.show()
        animation.start()

    def _task_row_height(self) -> int:
        if self.task_rows:
            return next(iter(self.task_rows.values())).height()
        return 34

    def _update_drag_preview_position(self, global_pos) -> None:
        if self.drag_press_offset is None:
            return
        rail_global = self.task_list_container.mapToGlobal(QPoint(0, 0))
        preview_local = self.mapFromGlobal(global_pos - self.drag_press_offset)
        rail_local = self.mapFromGlobal(rail_global)
        preview_local.setX(rail_local.x())
        min_y = rail_local.y()
        max_y = rail_local.y() + self.task_list_container.height() - self.task_drag_preview.height()
        preview_local.setY(max(min_y, min(preview_local.y(), max_y)))
        self.task_drag_preview.move(preview_local)

    def _hit_test_resize_region(self, pos) -> int | None:
        if self.isMaximized():
            return None

        x = pos.x()
        y = pos.y()
        width = self.width()
        height = self.height()
        left = x <= self.resize_margin
        right = x >= width - self.resize_margin
        top = y <= self.resize_margin
        bottom = y >= height - self.resize_margin

        if top and left:
            return self.HTTOPLEFT
        if top and right:
            return self.HTTOPRIGHT
        if bottom and left:
            return self.HTBOTTOMLEFT
        if bottom and right:
            return self.HTBOTTOMRIGHT
        if left:
            return self.HTLEFT
        if right:
            return self.HTRIGHT
        if top:
            return self.HTTOP
        if bottom:
            return self.HTBOTTOM
        return None

    def nativeEvent(self, event_type, message):
        if sys.platform.startswith("win") and event_type == "windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == self.WM_NCHITTEST:
                point = ctypes.wintypes.POINT()
                point.x = ctypes.c_short(msg.lParam & 0xFFFF).value
                point.y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                hit = self._hit_test_resize_region(self.mapFromGlobal(QPoint(point.x, point.y)))
                if hit is not None:
                    return True, hit
        return super().nativeEvent(event_type, message)

    def eventFilter(self, watched, event):
        if self.dragging_task_name and event.type() == event.Type.MouseButtonRelease:
            global_pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else QCursor.pos()
            self._end_task_drag(global_pos)
        return super().eventFilter(watched, event)

    def _on_task_started(self, task_name: str) -> None:
        self.runtime_state_value.setText("运行中")
        self.current_task_value.setText(self.task_labels.get(task_name, task_name))

    def _on_task_finished(self, success: bool) -> None:
        self.runtime_state_value.setText("空闲" if success else "失败")
        self.current_task_value.setText("-")
        self._set_busy(False)

    def _on_trigger_started(self) -> None:
        self.runtime_state_value.setText("触发中")
        self.current_task_value.setText("图像触发")
        if hasattr(self, "trigger_toggle_button"):
            self.trigger_toggle_button.setText("停止图像触发")
        if hasattr(self, "trigger_state_label"):
            self.trigger_state_label.setText("运行中")
        self._set_busy(True)

    def _on_trigger_finished(self) -> None:
        self.runtime_state_value.setText("空闲")
        self.current_task_value.setText("-")
        if hasattr(self, "trigger_toggle_button"):
            self.trigger_toggle_button.setText("启动图像触发")
        if hasattr(self, "trigger_state_label"):
            self.trigger_state_label.setText("未运行")
        self._set_busy(False)

    def _on_probe_finished(self, ok: bool, message: str) -> None:
        if ok:
            self.connection_value.setText(self.ports.get(self.current_backend, "COM2"))
        else:
            self.connection_value.setText("未连接")
        if hasattr(self, "settings_status_label"):
            self.settings_status_label.setText(message if ok else f"连接失败: {message}")

    def _append_log(self, message: str) -> None:
        if hasattr(self, "log_view"):
            self.log_view.appendPlainText(message)

    def _open_task_config(self, task_name: str) -> None:
        self.active_config_task_name = task_name
        self._update_config_panel()

    def _update_config_panel(self) -> None:
        if not hasattr(self, "config_group") or not hasattr(self, "config_title_label"):
            return

        if not self.active_config_task_name:
            self.config_title_label.hide()
            self.config_group.hide()
            self.config_placeholder_label.hide()
            self.account_indexing_result_card.hide()
            return

        task_label = self.task_labels.get(self.active_config_task_name, self.active_config_task_name)
        self.config_title_label.setText(f"{task_label}配置")
        self.config_title_label.show()
        self.config_group.show()

        show_account_indexing = (
            self.active_config_task_name == "AccountIndexing" and self.pending_account_indexing_result is not None
        )
        self.account_indexing_result_card.setVisible(show_account_indexing)
        self.config_placeholder_label.setVisible(not show_account_indexing)

    def _on_account_indexing_staged(self, summary: dict) -> None:
        self.pending_account_indexing_result = dict(summary)
        total = int(summary.get("character_count_total", 0))
        self.account_indexing_count_label.setText(f"本次角色总数：{total}")
        self._update_config_panel()

    def _clear_account_indexing_staged_result(self) -> None:
        self.pending_account_indexing_result = None
        self.account_indexing_count_label.setText("本次角色总数：-")
        self._update_config_panel()

    def _open_account_indexing_characters_dir(self) -> None:
        summary = self.pending_account_indexing_result or {}
        characters_dir = str(summary.get("characters_dir", "")).strip()
        if not characters_dir:
            self._append_log("[Launcher] missing staged characters directory")
            return
        try:
            os.startfile(characters_dir)  # type: ignore[attr-defined]
        except Exception as exc:
            self._append_log(f"[Launcher] failed to open staged characters directory: {exc}")

    def _save_account_indexing_staging(self) -> None:
        summary = self.pending_account_indexing_result or {}
        session_id = str(summary.get("session_id", "")).strip()
        if not session_id:
            self._append_log("[Launcher] missing staged account indexing session")
            return
        try:
            self.bridge.save_account_indexing_staging(session_id)
        except Exception as exc:
            self._append_log(f"[Launcher] save account indexing staging failed: {exc}")
            return
        self._clear_account_indexing_staged_result()

    def _discard_account_indexing_staging(self) -> None:
        summary = self.pending_account_indexing_result or {}
        session_id = str(summary.get("session_id", "")).strip()
        if not session_id:
            self._append_log("[Launcher] missing staged account indexing session")
            return
        try:
            self.bridge.discard_account_indexing_staging(session_id)
        except Exception as exc:
            self._append_log(f"[Launcher] discard account indexing staging failed: {exc}")
            return
        self._clear_account_indexing_staged_result()

    def closeEvent(self, event) -> None:
        self._unregister_global_hotkeys()
        super().closeEvent(event)
