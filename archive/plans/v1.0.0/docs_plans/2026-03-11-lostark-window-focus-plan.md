# Lost Ark Window Focus Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Focus the running Lost Ark game window before starting a Qt launcher task.

**Architecture:** Keep process and window lookup in `launcher/service.py` so the Qt layer only triggers the behavior. Make focus best-effort and non-blocking so launcher task execution remains stable even when the game window is missing or cannot be activated.

**Tech Stack:** Python, PySide6, pytest, monkeypatch, Win32 API via `pywin32`

---

### Task 1: Add failing tests for launcher service focus behavior

**Files:**
- Modify: `tests/test_gui_launcher.py`
- Test: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add tests covering:
- selecting a visible top-level window for `LOSTARK.exe`
- returning a failure result when no matching process/window exists

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gui_launcher.py -k "lostark or focus" -v`

Expected: FAIL because the focus helper does not exist yet.

**Step 3: Write minimal implementation**

Add the process/window focus helper and a small result object in `launcher/service.py`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gui_launcher.py -k "lostark or focus" -v`

Expected: PASS

### Task 2: Add failing test for bridge startup integration

**Files:**
- Modify: `tests/test_gui_launcher.py`
- Modify: `gui_qt/adapters/launcher_bridge.py`
- Test: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add a bridge test asserting `start_task()` attempts focus before calling the task executor.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gui_launcher.py::test_qt_launcher_bridge_focuses_lostark_before_running_task -v`

Expected: FAIL because the bridge does not call the focus helper yet.

**Step 3: Write minimal implementation**

Inject a focus executor into `LauncherBridge` and call it in the worker before `run_selected_task()`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gui_launcher.py::test_qt_launcher_bridge_focuses_lostark_before_running_task -v`

Expected: PASS

### Task 3: Verify targeted launcher tests

**Files:**
- Test: `tests/test_gui_launcher.py`

**Step 1: Run focused verification**

Run: `pytest tests/test_gui_launcher.py -k "launcher_service or bridge or lostark or focus" -v`

Expected: PASS
