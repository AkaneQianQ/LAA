# Task Cancel And F10 Hotkey Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add cancellable task execution from the home page and a global F10 stop hotkey.

**Architecture:** Use a single shared cancellation path based on `threading.Event` so button and hotkey behavior stay consistent. Propagate the event from the Qt bridge into the service and workflow executor so task shutdown is cooperative instead of force-killing threads.

**Tech Stack:** Python, PySide6, keyboard, pytest, threading.Event

---

### Task 1: Add failing tests for UI state and bridge stop path

**Files:**
- Modify: `tests/test_gui_launcher.py`
- Test: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add tests for:
- start button text changes to `运行中...` during task execution
- second click while running calls task stop
- global `F10` hotkey callback routes to the same stop method

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gui_launcher.py -k "task_stop or hotkey or running_button" -v`

Expected: FAIL because the launcher has no task cancellation or global hotkey registration.

**Step 3: Write minimal implementation**

Add bridge stop support, button text toggling, and hotkey registration.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gui_launcher.py -k "task_stop or hotkey or running_button" -v`

Expected: PASS

### Task 2: Add failing tests for cooperative workflow cancellation

**Files:**
- Modify: `tests/test_gui_launcher.py`
- Modify: `agent/py_service/main.py`
- Modify: `agent/py_service/pkg/workflow/pipeline_executor.py`
- Test: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add a service-level test proving a `stop_event` is propagated and causes workflow execution to stop early.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gui_launcher.py -k "stop_event or cancellation" -v`

Expected: FAIL because task execution ignores cancellation.

**Step 3: Write minimal implementation**

Thread the stop event through launcher service and workflow executor, with periodic checks before nodes and during wait actions.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gui_launcher.py -k "stop_event or cancellation" -v`

Expected: PASS

### Task 3: Verify related launcher tests

**Files:**
- Test: `tests/test_gui_launcher.py`

**Step 1: Run focused verification**

Run: `pytest tests/test_gui_launcher.py -k "task or trigger or hotkey or cancellation" -v`

Expected: PASS
