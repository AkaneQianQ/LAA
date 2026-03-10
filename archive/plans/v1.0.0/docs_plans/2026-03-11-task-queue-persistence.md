# Task Queue Persistence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Persist task queue checked state, visible state, and order in the existing launcher settings file so the next launch restores the last session state.

**Architecture:** Extend `LauncherSettings` with a small task queue state payload and continue using `LauncherSettingsStore` as the single persistence entry point. Restore task state during `FerrumMainWindow` initialization, then save immediately after checkbox toggles, visibility changes, and reorder operations.

**Tech Stack:** Python, PySide6, pytest

---

### Task 1: Extend launcher settings schema

**Files:**
- Modify: `launcher/settings.py`
- Test: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add a settings round-trip test asserting task checked state, visibility state, and order are loaded from `ui_settings.json`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gui_launcher.py -q -k "persist_task_queue_state"`
Expected: FAIL because `LauncherSettings` does not carry task queue state.

**Step 3: Write minimal implementation**

Add `task_checked`, `task_visibility`, and `task_order` fields to `LauncherSettings`. Teach `LauncherSettingsStore.load()` to parse them with safe defaults and `save()` to serialize them.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gui_launcher.py -q -k "persist_task_queue_state"`
Expected: PASS

### Task 2: Restore task queue state in the Qt window

**Files:**
- Modify: `gui_qt/window.py`
- Test: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add a window initialization test asserting saved order, checked state, and visible state are restored from settings.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gui_launcher.py -q -k "restores_saved_task_queue_state"`
Expected: FAIL because the window always uses hardcoded defaults.

**Step 3: Write minimal implementation**

Apply saved task state onto `self.task_items` before the task list is built. Fall back to existing defaults for unknown or missing entries.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gui_launcher.py -q -k "restores_saved_task_queue_state"`
Expected: PASS

### Task 3: Save task queue changes immediately

**Files:**
- Modify: `gui_qt/window.py`
- Modify: `gui_qt/adapters/launcher_bridge.py`
- Test: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add tests asserting checkbox toggles, visibility menu changes, and drag reorder updates call `save_settings()` with the current task queue state.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gui_launcher.py -q -k "persists_task_queue"`
Expected: FAIL because only backend and port changes are saved.

**Step 3: Write minimal implementation**

Add a helper that snapshots task queue state and persists it through the bridge. Call it after checkbox toggles, visibility changes, and final drag completion.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gui_launcher.py -q -k "persists_task_queue"`
Expected: PASS

### Task 4: Full verification

**Files:**
- Test: `tests/test_gui_launcher.py`

**Step 1: Run focused tests**

Run: `pytest tests/test_gui_launcher.py -q -k "task_queue or persist_task_queue_state or restores_saved_task_queue_state"`

**Step 2: Run full launcher regression**

Run: `pytest tests/test_gui_launcher.py -q`
Expected: PASS
