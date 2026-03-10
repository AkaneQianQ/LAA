#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local asset resolution for the Qt launcher."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon


ASSET_ROOT = Path(__file__).resolve().parent / "assets"


def asset_path(name: str) -> str:
    return str(ASSET_ROOT / name)


def load_icon(name: str) -> QIcon:
    return QIcon(asset_path(name))
