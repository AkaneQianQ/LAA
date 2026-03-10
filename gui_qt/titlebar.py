#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Custom title bar for the Qt launcher."""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from gui_qt.theme import load_icon
from gui_qt.widgets import AnimatedButton


class LauncherTitleBar(QWidget):
    """Simple draggable title bar with window controls."""

    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOACTIVATE = 0x0010
    SWP_SHOWWINDOW = 0x0040

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("titleBar")
        self._drag_offset: QPoint | None = None
        self._always_on_top = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(8)

        self.icon_label = QLabel("", self)
        self.icon_label.setObjectName("titleIcon")
        self.icon_label.setPixmap(load_icon("app.svg").pixmap(18, 18))
        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("titleCaption")

        self.pin_button = AnimatedButton("", self)
        self.pin_button.setObjectName("titleButton")
        self.pin_button.setIcon(load_icon("pin.svg"))
        self.pin_button.setCheckable(True)
        self.minimize_button = AnimatedButton("", self)
        self.minimize_button.setObjectName("titleButton")
        self.minimize_button.setIcon(load_icon("minimize.svg"))
        self.maximize_button = AnimatedButton("", self)
        self.maximize_button.setObjectName("titleButton")
        self.maximize_button.setIcon(load_icon("maximize.svg"))
        self.close_button = AnimatedButton("", self)
        self.close_button.setObjectName("titleCloseButton")
        self.close_button.setIcon(load_icon("close.svg"))

        layout.addWidget(self.icon_label, 0)
        layout.addWidget(self.title_label, 1)
        layout.addWidget(self.pin_button, 0)
        layout.addWidget(self.minimize_button, 0)
        layout.addWidget(self.maximize_button, 0)
        layout.addWidget(self.close_button, 0)

        self.minimize_button.clicked.connect(self._minimize)
        self.maximize_button.clicked.connect(self._toggle_maximize)
        self.close_button.clicked.connect(self._close_window)
        self.pin_button.clicked.connect(self._toggle_always_on_top)
        self.setFixedHeight(36)

    def _window(self):
        return self.window()

    def _minimize(self) -> None:
        self._window().showMinimized()

    def _toggle_maximize(self) -> None:
        window = self._window()
        if window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()

    def _close_window(self) -> None:
        self._window().close()

    def is_always_on_top(self) -> bool:
        return self._always_on_top

    def _toggle_always_on_top(self, checked: bool) -> None:
        window = self._window()
        self._always_on_top = bool(checked)
        if sys.platform.startswith("win"):
            if self._set_windows_topmost(window, checked):
                return

        window.setWindowFlag(Qt.WindowStaysOnTopHint, checked)
        window.show()

    def _set_windows_topmost(self, window: QWidget, checked: bool) -> bool:
        hwnd = int(window.winId())
        if hwnd == 0:
            return False

        user32 = ctypes.windll.user32
        user32.SetWindowPos.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.SetWindowPos.restype = ctypes.c_int
        insert_after = ctypes.c_void_p(self.HWND_TOPMOST if checked else self.HWND_NOTOPMOST)
        result = user32.SetWindowPos(
            ctypes.c_void_p(hwnd),
            insert_after,
            0,
            0,
            0,
            0,
            self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_NOACTIVATE | self.SWP_SHOWWINDOW,
        )
        return bool(result)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._window().frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton and not self._window().isMaximized():
            self._window().move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)
