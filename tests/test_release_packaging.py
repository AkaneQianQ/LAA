#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Release packaging tool tests."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


def test_release_packaging_reads_consistent_versions(tmp_path: Path):
    package_root = tmp_path / "repo"
    package_root.mkdir()
    (package_root / "agent").mkdir()
    (package_root / "agent" / "py_service").mkdir(parents=True)
    (package_root / "agent" / "py_service" / "__init__.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
    (package_root / "assets").mkdir()
    (package_root / "assets" / "interface.json").write_text(
        json.dumps({"version": "v1.2.3"}),
        encoding="utf-8",
    )

    from tools.release_packaging import read_project_version

    assert read_project_version(package_root) == "v1.2.3"


def test_release_packaging_builds_expected_asset_names():
    from tools.release_packaging import build_release_names

    names = build_release_names("v1.2.3")

    assert names["portable_zip"] == "FerrumBot-v1.2.3-portable.zip"
    assert names["sha256sums"] == "SHA256SUMS.txt"
    assert names["release_dir"] == "FerrumBot-v1.2.3-portable"


def test_release_packaging_creates_zip_and_sha256sum(tmp_path: Path):
    dist_root = tmp_path / "dist" / "FerrumBot"
    dist_root.mkdir(parents=True)
    (dist_root / "FerrumBot.exe").write_text("binary", encoding="utf-8")
    (dist_root / "README.txt").write_text("notes", encoding="utf-8")

    output_root = tmp_path / "release"

    from tools.release_packaging import package_portable_release

    result = package_portable_release(
        project_root=tmp_path,
        version_tag="v1.2.3",
        dist_dir=dist_root,
        output_root=output_root,
    )

    zip_path = Path(result["zip_path"])
    sha_path = Path(result["sha256_path"])

    assert zip_path.name == "FerrumBot-v1.2.3-portable.zip"
    assert sha_path.name == "SHA256SUMS.txt"
    assert zip_path.exists()
    assert sha_path.exists()

    with zipfile.ZipFile(zip_path) as archive:
        assert sorted(archive.namelist()) == [
            "FerrumBot-v1.2.3-portable/FerrumBot.exe",
            "FerrumBot-v1.2.3-portable/README.txt",
        ]

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    assert sha_path.read_text(encoding="utf-8").strip() == f"{digest}  FerrumBot-v1.2.3-portable.zip"
