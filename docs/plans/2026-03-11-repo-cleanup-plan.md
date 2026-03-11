# Repository Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Archive obsolete repository contents into a dated cleanup area while keeping the current launcher, task execution, and update path runnable.

**Architecture:** Build a scripted cleanup flow that classifies repository items into archive buckets, moves them without deletion, emits a manifest, and then verifies the retained product path with targeted tests. Keep the first pass conservative around active source paths and explicit about every archived item.

**Tech Stack:** Python, PowerShell, pytest, git status inspection, JSON manifest generation

---

### Task 1: Inventory and classify cleanup targets

**Files:**
- Create: `tools/repo_cleanup.py`
- Test: `tests/test_repo_cleanup.py`
- Reference: `docs/plans/2026-03-11-repo-cleanup-design.md`

**Step 1: Write the failing test**

Add a test that builds a temporary repository tree and asserts the cleanup tool classifies:
- caches into `runtime`
- build and release directories into `release`
- scratch files into `scratch`
- explicit obsolete files into `source`

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_repo_cleanup.py -q`
Expected: FAIL because `tools.repo_cleanup` does not exist yet

**Step 3: Write minimal implementation**

Create `tools/repo_cleanup.py` with:
- cleanup root constants
- a dataclass describing archive entries
- classification helpers for runtime, release, scratch, docs, and source
- inventory logic that returns planned archive moves

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_repo_cleanup.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_repo_cleanup.py tools/repo_cleanup.py docs/plans/2026-03-11-repo-cleanup-design.md docs/plans/2026-03-11-repo-cleanup-plan.md
git commit -m "test: add repository cleanup inventory coverage"
```

### Task 2: Execute archive moves and emit manifest

**Files:**
- Modify: `tools/repo_cleanup.py`
- Test: `tests/test_repo_cleanup.py`

**Step 1: Write the failing test**

Add a test that creates sample files, runs the cleanup tool, and asserts:
- files moved into `archive/cleanup/2026-03-11-repo-reset/<category>/...`
- original paths removed
- `manifest.json` created with source path, archived path, category, and tracked flag fields

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_repo_cleanup.py -q`
Expected: FAIL because move/manifest behavior is incomplete

**Step 3: Write minimal implementation**

Extend `tools/repo_cleanup.py` to:
- create archive directories
- move files and directories
- preserve relative paths inside archive buckets
- write `manifest.json`
- support dry-run and execute modes

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_repo_cleanup.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_repo_cleanup.py tools/repo_cleanup.py
git commit -m "feat: archive cleanup targets with manifest generation"
```

### Task 3: Define repository-specific target sets and verify retained path

**Files:**
- Modify: `tools/repo_cleanup.py`
- Modify: `tests/test_repo_cleanup.py`
- Verify: `tests/test_update_service.py`
- Verify: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add a test covering repository-specific rules for:
- `__pycache__`, `.pytest_cache`, `build`, `dist`, `release`, `logs`, `data`
- `makcu_api.html`, `RELEASE_README.txt`
- explicit obsolete launcher entry files or deprecated source paths

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_repo_cleanup.py -q`
Expected: FAIL because repository-specific rules are incomplete

**Step 3: Write minimal implementation**

Add repository cleanup rules and CLI entry points:
- `--plan` to print intended moves
- `--execute` to perform moves
- protection rules for retained launcher/update path

**Step 4: Run cleanup in plan mode**

Run: `python tools/repo_cleanup.py --plan`
Expected: printed archive plan with category assignments and no filesystem changes

**Step 5: Run cleanup in execute mode**

Run: `python tools/repo_cleanup.py --execute`
Expected: archive tree created and selected files moved

**Step 6: Verify retained product path**

Run: `python -m pytest tests/test_update_service.py tests/test_gui_launcher.py -q`
Expected: PASS

**Step 7: Commit**

```bash
git add tools/repo_cleanup.py tests/test_repo_cleanup.py archive/cleanup docs/plans/2026-03-11-repo-cleanup-design.md docs/plans/2026-03-11-repo-cleanup-plan.md
git commit -m "chore: archive obsolete repository contents"
```
