#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repository cleanup tool tests."""

from __future__ import annotations

import json
from pathlib import Path


def test_repo_cleanup_inventory_classifies_known_targets(tmp_path: Path):
    runtime_dir = tmp_path / "agent" / "__pycache__"
    runtime_dir.parent.mkdir()
    runtime_dir.mkdir()
    (runtime_dir / "sample.pyc").write_bytes(b"cache")

    release_dir = tmp_path / "dist"
    release_dir.mkdir()
    (release_dir / "FerrumBot.exe").write_text("bin", encoding="utf-8")

    scratch_file = tmp_path / "makcu_api.html"
    scratch_file.write_text("<html></html>", encoding="utf-8")

    source_dir = tmp_path / "discard"
    source_dir.mkdir()
    (source_dir / "v1.0.0_cleanup").mkdir()

    from tools.repo_cleanup import build_cleanup_plan

    entries = build_cleanup_plan(tmp_path)
    by_source = {entry.source_relpath: entry for entry in entries}

    assert by_source["agent/__pycache__"].category == "runtime"
    assert by_source["dist"].category == "release"
    assert by_source["makcu_api.html"].category == "scratch"
    assert by_source["discard"].category == "source"
    assert "docs" not in by_source


def test_repo_cleanup_execute_moves_targets_and_writes_manifest(tmp_path: Path):
    cache_dir = tmp_path / "agent" / "__pycache__"
    cache_dir.parent.mkdir()
    cache_dir.mkdir()
    (cache_dir / "a.pyc").write_bytes(b"cache")

    release_dir = tmp_path / "release"
    release_dir.mkdir()
    (release_dir / "notes.txt").write_text("release", encoding="utf-8")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "old-plan.md").write_text("legacy", encoding="utf-8")

    from tools.repo_cleanup import execute_cleanup, ARCHIVE_ROOT

    manifest_path = execute_cleanup(tmp_path)
    archive_root = tmp_path / ARCHIVE_ROOT

    assert manifest_path.exists()
    assert not cache_dir.exists()
    assert not release_dir.exists()
    assert (archive_root / "runtime" / "agent" / "__pycache__").exists()
    assert (archive_root / "release" / "release").exists()
    assert docs_dir.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["archive_root"] == str(ARCHIVE_ROOT).replace("\\", "/")
    sources = {entry["source_relpath"]: entry for entry in manifest["entries"]}
    assert sources["agent/__pycache__"]["category"] == "runtime"
    assert sources["release"]["archived_relpath"].startswith("release/")


def test_repo_cleanup_execute_can_resume_when_archive_target_exists(tmp_path: Path):
    release_dir = tmp_path / "release"
    release_dir.mkdir()
    (release_dir / "remaining.txt").write_text("later", encoding="utf-8")

    archive_target = tmp_path / "archive" / "cleanup" / "2026-03-11-repo-reset" / "release" / "release"
    archive_target.mkdir(parents=True)
    (archive_target / "existing.txt").write_text("earlier", encoding="utf-8")

    from tools.repo_cleanup import execute_cleanup

    manifest_path = execute_cleanup(tmp_path)

    assert manifest_path.exists()
    assert not release_dir.exists()
    assert (archive_target / "existing.txt").exists()
    assert (archive_target / "remaining.txt").exists()


def test_repo_cleanup_manifest_rebuilds_existing_archive_contents(tmp_path: Path):
    archive_target = tmp_path / "archive" / "cleanup" / "2026-03-11-repo-reset" / "runtime" / "agent" / "__pycache__"
    archive_target.mkdir(parents=True)
    (archive_target / "a.pyc").write_bytes(b"cache")

    from tools.repo_cleanup import execute_cleanup

    manifest_path = execute_cleanup(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = {entry["source_relpath"]: entry for entry in manifest["entries"]}

    assert sources["agent/__pycache__"]["category"] == "runtime"
    assert sources["agent/__pycache__"]["archived_relpath"] == "runtime/agent/__pycache__"


def test_repo_cleanup_manifest_ignores_runtime_parent_directories(tmp_path: Path):
    archive_root = tmp_path / "archive" / "cleanup" / "2026-03-11-repo-reset" / "runtime"
    (archive_root / "agent" / "__pycache__").mkdir(parents=True)
    ((archive_root / "agent" / "__pycache__") / "a.pyc").write_bytes(b"cache")

    from tools.repo_cleanup import write_manifest

    manifest_path = write_manifest(tmp_path, tmp_path / "archive" / "cleanup" / "2026-03-11-repo-reset")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = {entry["source_relpath"] for entry in manifest["entries"]}

    assert "agent" not in sources
    assert "agent/__pycache__" in sources
