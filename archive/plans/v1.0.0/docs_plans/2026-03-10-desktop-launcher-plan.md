# Desktop Launcher Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a minimal desktop launcher with persistent Ferrum/Makcu selection, two task buttons, and one-folder packaging.

**Architecture:** Add a small `launcher` package for settings, controller resolution, and threaded task execution, then add a `ttkbootstrap` GUI entry file that reuses the existing service and workflow executor layers. Package the launcher with PyInstaller in `--onedir` mode so users can extract a folder and run it directly.

**Tech Stack:** Python, tkinter, ttkbootstrap, threading, queue, PyInstaller, pytest

---

### Task 1: Add failing tests for launcher settings and controller resolution

**Files:**
- Create: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add tests for:
- default settings fallback when no file exists
- saving and reloading `driver_backend`
- resolving `ferrum` to the Ferrum controller entry
- resolving `makcu` to the Makcu controller entry

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: FAIL because launcher helpers do not exist yet

**Step 3: Write minimal implementation**

Create launcher helper modules with only the functions required by the tests.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: PASS

### Task 2: Add failing tests for background task runner behavior

**Files:**
- Modify: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add tests for:
- runner marks itself busy during execution
- runner forwards log lines
- runner emits success/failure completion state

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: FAIL because the task runner does not exist or is incomplete

**Step 3: Write minimal implementation**

Add the threaded runner and its callback/log plumbing.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: PASS

### Task 3: Extend the service entry points to accept explicit controller selection

**Files:**
- Modify: `agent/py_service/main.py`
- Modify: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add a test that verifies launcher code can choose a controller from `assets/interface.json` and pass it into service initialization/execution.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: FAIL because service entry points ignore explicit controller selection

**Step 3: Write minimal implementation**

Thread `controller_name` through service APIs without changing task semantics.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: PASS

### Task 4: Build the GUI launcher

**Files:**
- Create: `gui_launcher.py`
- Create: `launcher/__init__.py`
- Create: `launcher/settings.py`
- Create: `launcher/service.py`
- Create: `launcher/task_runner.py`
- Modify: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add focused tests around the launcher-facing service wrapper where possible without opening real windows.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: FAIL because launcher modules are incomplete

**Step 3: Write minimal implementation**

Implement the actual GUI with:
- driver radio buttons
- task buttons
- busy-state guarding
- log area
- automatic settings persistence

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: PASS

### Task 5: Add packaging assets for one-folder distribution

**Files:**
- Create: `requirements-gui.txt`
- Create: `build_launcher.ps1`
- Optionally create: `FerrumBotLauncher.spec`
- Modify: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add a smoke test that asserts expected packaging files exist and reference the launcher entry point.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: FAIL because packaging files do not exist yet

**Step 3: Write minimal implementation**

Add the dependency file and build script/spec needed to produce `dist/FerrumBot/`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: PASS

### Task 6: Build and verify the distributable folder

**Files:**
- Output: `dist/FerrumBot/`

**Step 1: Run the packaging command**

Run: `powershell -ExecutionPolicy Bypass -File .\\build_launcher.ps1`
Expected: successful PyInstaller build and populated `dist/FerrumBot/`

**Step 2: Verify the folder contents**

Check that `dist/FerrumBot/` includes the executable plus dependent libraries and required assets.

**Step 3: Run focused verification**

Run:
- `python -m pytest tests/test_gui_launcher.py -v`
- the packaging command above

Expected: tests pass and the distributable folder exists

Plan complete and saved to `docs/plans/2026-03-10-desktop-launcher-plan.md`.
