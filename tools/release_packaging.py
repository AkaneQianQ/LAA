#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build release assets that match updater expectations."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from launcher.update_service import RELEASE_PRODUCT_NAME, SHA256SUMS_NAME, expected_release_asset_name


def read_project_version(project_root: str | Path) -> str:
    root = Path(project_root)
    package_init = root / "agent" / "py_service" / "__init__.py"
    interface_json = root / "assets" / "interface.json"

    package_version = _read_package_version(package_init)
    interface_payload = json.loads(interface_json.read_text(encoding="utf-8"))
    interface_version = str(interface_payload.get("version", "")).strip()
    normalized_package = f"v{package_version.lstrip('vV')}"
    if interface_version != normalized_package:
        raise ValueError(f"version mismatch: package={normalized_package} interface={interface_version}")
    return interface_version


def _read_package_version(init_path: Path) -> str:
    module = ast.parse(init_path.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    return str(ast.literal_eval(node.value))
    raise ValueError("__version__ not found")


def build_release_names(version_tag: str) -> dict[str, str]:
    return {
        "release_dir": f"{RELEASE_PRODUCT_NAME}-{version_tag}-portable",
        "portable_zip": expected_release_asset_name(version_tag),
        "sha256sums": SHA256SUMS_NAME,
    }


def package_portable_release(
    project_root: str | Path,
    version_tag: str,
    dist_dir: str | Path,
    output_root: str | Path,
) -> dict[str, str]:
    root = Path(project_root)
    dist_path = Path(dist_dir)
    if not dist_path.exists():
        raise FileNotFoundError(f"dist directory not found: {dist_path}")

    names = build_release_names(version_tag)
    output_path = Path(output_root)
    output_path.mkdir(parents=True, exist_ok=True)

    stage_dir = output_path / names["release_dir"]
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    shutil.copytree(dist_path, stage_dir)

    zip_path = output_path / names["portable_zip"]
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(stage_dir.rglob("*")):
            if file_path.is_dir():
                continue
            archive.write(file_path, arcname=(Path(names["release_dir"]) / file_path.relative_to(stage_dir)).as_posix())

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    sha256_path = output_path / names["sha256sums"]
    sha256_path.write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")

    return {
        "release_dir": str(stage_dir),
        "zip_path": str(zip_path),
        "sha256_path": str(sha256_path),
        "sha256": digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a portable release zip and SHA256SUMS.txt")
    parser.add_argument("--project-root", default=".", help="Project root path")
    parser.add_argument("--dist-dir", default="dist/LAA", help="PyInstaller dist directory")
    parser.add_argument("--output-root", default="release", help="Release output directory")
    parser.add_argument("--version-tag", default="", help="Release version tag, e.g. v1.0.04")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    version_tag = args.version_tag.strip() or read_project_version(project_root)
    result = package_portable_release(
        project_root=project_root,
        version_tag=version_tag,
        dist_dir=project_root / args.dist_dir,
        output_root=project_root / args.output_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
