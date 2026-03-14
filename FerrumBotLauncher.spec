# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys
import site

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_root = Path.cwd()
assets_datas = [(str(project_root / "assets"), "assets")]
data_datas = [(str(project_root / "data"), "data")] if (project_root / "data").exists() else []
agent_datas = collect_data_files("agent", include_py_files=True)
gui_qt_datas = [(str(project_root / "gui_qt" / "theme" / "assets"), "gui_qt/theme/assets")]
dd_driver_path = project_root / "agent" / "py_service" / "pkg" / "input" / "drivers" / "dd.54900.dll"
dd_driver_datas = [(str(dd_driver_path), "agent/py_service/pkg/input/drivers")] if dd_driver_path.exists() else []


def _find_site_package_file(*relative_parts: str) -> Path:
    candidates = []
    for root in site.getsitepackages():
        candidates.append(Path(root, *relative_parts))
    usersite = site.getusersitepackages()
    if usersite:
        candidates.append(Path(usersite, *relative_parts))

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"required bundled dependency not found: {'/'.join(relative_parts)}")


pywin32_binaries = [
    (str(_find_site_package_file("win32", "win32api.pyd")), "win32"),
    (str(_find_site_package_file("win32", "win32gui.pyd")), "win32"),
    (str(_find_site_package_file("win32", "win32process.pyd")), "win32"),
    (str(_find_site_package_file("pywin32_system32", f"pywintypes{sys.version_info.major}{sys.version_info.minor}.dll")), "pywin32_system32"),
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
    datas=assets_datas + data_datas + agent_datas + gui_qt_datas + dd_driver_datas,
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
    name="LAA",
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
    name="LAA",
)
