#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility launcher entry point forwarding to the Qt UI."""

from __future__ import annotations

from gui_qt.main import main as qt_main


def main() -> int:
    return qt_main()


if __name__ == "__main__":
    raise SystemExit(main())
