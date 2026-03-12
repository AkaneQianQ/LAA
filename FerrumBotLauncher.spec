# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

import pywintypes
import win32api
import win32gui
import win32process
from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_root = Path.cwd()
assets_datas = [(str(project_root / "assets"), "assets")]
data_datas = [(str(project_root / "data"), "data")] if (project_root / "data").exists() else []
agent_datas = collect_data_files("agent", include_py_files=True)
gui_qt_datas = [(str(project_root / "gui_qt" / "theme" / "assets"), "gui_qt/theme/assets")]
pywin32_binaries = [
    (str(Path(win32api.__file__).resolve()), "win32"),
    (str(Path(win32gui.__file__).resolve()), "win32"),
    (str(Path(win32process.__file__).resolve()), "win32"),
    (str(Path(pywintypes.__file__).resolve()), "pywin32_system32"),
]

hiddenimports = (
    collect_submodules("agent.py_service.modules")
    + collect_submodules("ttkbootstrap")
    + collect_submodules("requests")
    + ["win32api", "win32con", "win32gui", "win32process", "pywintypes"]
)


a = Analysis(
    ["gui_launcher.py"],
    pathex=[str(project_root)],
    binaries=pywin32_binaries,
    datas=assets_datas + data_datas + agent_datas + gui_qt_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FerrumBot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FerrumBot",
)
