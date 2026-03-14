#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Qt launcher bootstrap."""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from gui_qt.theme import build_stylesheet, load_icon


def build_application() -> QApplication:
    if "PYTEST_CURRENT_TEST" in os.environ:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is not None:
        return app

    app = QApplication(sys.argv)
    app.setApplicationName("LAA")
    app.setOrganizationName("LAA")
    # Guard against invalid platform font metadata (pointSize == -1) on some hosts.
    default_font = app.font()
    if default_font.pointSize() <= 0:
        default_font.setPointSize(10)
        app.setFont(default_font)
    app.setWindowIcon(load_icon("app.svg"))
    app.setStyleSheet(build_stylesheet())
    return app


def main() -> int:
    from gui_qt.window import FerrumMainWindow

    app = build_application()
    window = FerrumMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
