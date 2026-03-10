# V1 Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidate completed planning artifacts and move clearly unused project files into a single discard area for version `1.0.0`.

**Architecture:** Use the Qt launcher entry chain as the retention baseline, then classify files into keep, archive, and discard buckets. Avoid destructive deletion by moving candidates into versioned archive and discard directories inside the repository.

**Tech Stack:** Python project structure, PowerShell filesystem operations, pytest for regression verification

---

### Task 1: Establish cleanup buckets

**Files:**
- Create: `archive/plans/v1.0.0/.gitkeep`
- Create: `discard/v1.0.0_cleanup/.gitkeep`

**Step 1: Create archive and discard roots**

Create versioned directories for plan consolidation and non-destructive cleanup staging.

**Step 2: Verify directories exist**

Run: `Get-ChildItem archive,discard -Force`
Expected: both versioned roots are present

### Task 2: Consolidate planning artifacts

**Files:**
- Move: `.planning/*`
- Move: `docs/plans/*`

**Step 1: Move planning content into one archive tree**

Move `.planning` and existing `docs/plans` contents under `archive/plans/v1.0.0/`.

**Step 2: Preserve lightweight placeholders**

Recreate empty `.planning/` and `docs/plans/` directories only if needed for future repo hygiene.

### Task 3: Move clear discard candidates

**Files:**
- Move: `__pycache__/`
- Move: `.pytest_cache/`
- Move: `build/`
- Move: `dist/`
- Move: `dist_refresh/`
- Move: all discovered `__pycache__/` subdirectories
- Move: discovered duplicate or obsolete launcher entrypoints only if not referenced by build/runtime

**Step 1: Use GUI-driven dependency baseline**

Keep `gui_launcher.py`, `gui_launcher_qt.py`, `gui_qt/`, `launcher/`, `agent/`, `assets/`, `tools/convert_yaml_to_pipeline.py`, and current tests unless references prove otherwise.

**Step 2: Move only high-confidence unused items**

Move generated caches and build outputs into `discard/v1.0.0_cleanup/`.

### Task 4: Verify cleanup safety

**Files:**
- Verify: `gui_launcher.py`
- Verify: `gui_qt/main.py`
- Verify: `assets/interface.json`
- Verify: moved archive and discard directories

**Step 1: Run focused launcher tests**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: launcher tests pass

**Step 2: Confirm final filesystem layout**

Run: `Get-ChildItem -Force`
Expected: `archive/` and `discard/` exist, removed candidates no longer remain at repo root
