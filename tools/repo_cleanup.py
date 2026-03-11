#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Archive repository cleanup targets into a dated archive root."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


ARCHIVE_ROOT = Path("archive/cleanup/2026-03-11-repo-reset")
TOP_LEVEL_RUNTIME_NAMES = {".pytest_cache", "logs", "data"}
TOP_LEVEL_RELEASE_NAMES = {"build", "dist", "release"}
SCRATCH_FILES = {"makcu_api.html", "RELEASE_README.txt"}
SOURCE_NAMES = {"discard"}
SKIP_NAMES = {".git", ".claude", "archive"}


@dataclass(frozen=True)
class CleanupEntry:
    source_relpath: str
    archived_relpath: str
    category: str
    reason: str
    tracked: bool


def build_cleanup_plan(repo_root: str | Path) -> list[CleanupEntry]:
    root = Path(repo_root)
    entries: list[CleanupEntry] = []
    seen: set[str] = set()
    for path in iter_cleanup_targets(root):
        relpath = path.relative_to(root).as_posix()
        if relpath in seen:
            continue
        seen.add(relpath)
        category, reason = classify_path(path, root)
        if category is None:
            continue
        archived_relpath = (Path(category) / relpath).as_posix()
        entries.append(
            CleanupEntry(
                source_relpath=relpath,
                archived_relpath=archived_relpath,
                category=category,
                reason=reason,
                tracked=is_git_tracked(root, relpath),
            )
        )
    return entries


def iter_cleanup_targets(root: Path):
    for path in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if path.name in SKIP_NAMES:
            continue
        if path.name in TOP_LEVEL_RUNTIME_NAMES or path.name in TOP_LEVEL_RELEASE_NAMES or path.name in SCRATCH_FILES or path.name in SOURCE_NAMES:
            yield path
            continue
        if path.is_dir():
            for nested in sorted(path.rglob("*"), key=lambda item: item.as_posix().lower()):
                if nested.is_dir() and nested.name == "__pycache__":
                    yield nested


def classify_path(path: Path, repo_root: Path) -> tuple[str | None, str]:
    name = path.name
    if name == "__pycache__" or name == ".pytest_cache" or name in TOP_LEVEL_RUNTIME_NAMES:
        return "runtime", "generated runtime outputs or cache"
    if name in TOP_LEVEL_RELEASE_NAMES:
        return "release", "packaging or release artifact"
    if name in SCRATCH_FILES:
        return "scratch", "temporary reference or release note"
    if name in SOURCE_NAMES:
        return "source", "legacy cleanup staging directory"
    return None, ""


def execute_cleanup(repo_root: str | Path) -> Path:
    root = Path(repo_root)
    entries = build_cleanup_plan(root)
    archive_root = root / ARCHIVE_ROOT
    archive_root.mkdir(parents=True, exist_ok=True)

    for entry in entries:
        source_path = root / entry.source_relpath
        if not source_path.exists():
            continue
        target_path = archive_root / entry.archived_relpath
        target_path.parent.mkdir(parents=True, exist_ok=True)
        move_to_archive(source_path, target_path)

    manifest_path = write_manifest(root, archive_root)
    return manifest_path


def move_to_archive(source_path: Path, target_path: Path) -> None:
    if source_path.is_dir():
        if target_path.exists():
            for child in source_path.iterdir():
                move_to_archive(child, target_path / child.name)
            source_path.rmdir()
            return
        shutil.move(str(source_path), str(target_path))
        return
    if target_path.exists():
        target_path.unlink()
    shutil.move(str(source_path), str(target_path))


def write_manifest(repo_root: Path, archive_root: Path) -> Path:
    entries = sorted(rebuild_manifest_entries(repo_root, archive_root), key=lambda item: (item.category, item.source_relpath))
    manifest_path = archive_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "archive_root": ARCHIVE_ROOT.as_posix(),
                "entries": [asdict(entry) for entry in entries],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest_path


def rebuild_manifest_entries(repo_root: Path, archive_root: Path) -> list[CleanupEntry]:
    entries: list[CleanupEntry] = []
    for category_dir in sorted(archive_root.iterdir(), key=lambda item: item.name.lower()):
        if not category_dir.is_dir():
            continue
        category = category_dir.name
        for archived_path in sorted(category_dir.rglob("*"), key=lambda item: item.as_posix().lower()):
            if not should_manifest_entry(category_dir, archived_path):
                continue
            rel_under_category = archived_path.relative_to(category_dir).as_posix()
            reason = manifest_reason_for_category(category)
            entries.append(
                CleanupEntry(
                    source_relpath=rel_under_category,
                    archived_relpath=f"{category}/{rel_under_category}",
                    category=category,
                    reason=reason,
                    tracked=is_git_tracked(repo_root, rel_under_category),
                )
            )
    return entries


def should_manifest_entry(category_dir: Path, archived_path: Path) -> bool:
    category = category_dir.name
    if category == "runtime":
        return archived_path.is_dir() and (
            archived_path.name == "__pycache__"
            or (archived_path.parent == category_dir and archived_path.name in TOP_LEVEL_RUNTIME_NAMES)
        )
    if category == "release":
        return archived_path.parent == category_dir and archived_path.name in TOP_LEVEL_RELEASE_NAMES
    if category == "scratch":
        return archived_path.is_file() and archived_path.parent == category_dir
    if category == "source":
        return archived_path.parent == category_dir or archived_path.name == "__pycache__"
    if category == "docs":
        return archived_path.parent == category_dir
    return False


def manifest_reason_for_category(category: str) -> str:
    reasons = {
        "runtime": "generated runtime outputs or cache",
        "release": "packaging or release artifact",
        "scratch": "temporary reference or release note",
        "source": "legacy cleanup staging directory",
        "docs": "documentation archive",
    }
    return reasons.get(category, "archived cleanup target")


def is_git_tracked(repo_root: Path, relpath: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", relpath],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive repository cleanup targets.")
    parser.add_argument("--plan", action="store_true", help="Print cleanup plan without moving files.")
    parser.add_argument("--execute", action="store_true", help="Execute cleanup plan.")
    args = parser.parse_args()

    repo_root = Path.cwd()
    entries = build_cleanup_plan(repo_root)
    if args.plan or not args.execute:
        for entry in entries:
            print(f"{entry.category}: {entry.source_relpath} -> {entry.archived_relpath}")
        return 0
    manifest_path = execute_cleanup(repo_root)
    print(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
