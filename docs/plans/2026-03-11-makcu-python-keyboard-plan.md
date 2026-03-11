# Makcu Python Keyboard Path Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Makcu launcher option that routes keyboard input through Python while keeping mouse input on Makcu hardware, and ship the change as version 1.0.03.

**Architecture:** Persist a `keyboard_via_python` launcher setting, pass it through launcher runtime overrides, and let service-side controller creation return either the existing Makcu controller or a new hybrid controller that delegates keyboard methods to a Python keyboard adapter. Extend Makcu serial logging so every command/ack is visible in runtime logs, then rebuild release artifacts and refresh the portable folders.

**Tech Stack:** Python, PySide6, pytest, pyserial, keyboard, PyInstaller, PowerShell zip packaging

---

### Task 1: Lock behavior with failing tests

**Files:**
- Modify: `tests/test_gui_launcher.py`
- Modify: `tests/test_makcu_controller.py`

**Steps:**
1. Add a launcher settings test for `keyboard_via_python`.
2. Add a Qt window test for the Makcu-only checkbox persistence.
3. Add a service test that expects a hybrid controller when Makcu + Python keyboard is enabled.
4. Add a Makcu controller logging test that expects hardware ack logs.
5. Run the focused pytest selection and confirm failures.

### Task 2: Implement runtime settings and controller path

**Files:**
- Modify: `launcher/settings.py`
- Modify: `launcher/service.py`
- Modify: `launcher/trigger_service.py`
- Modify: `agent/py_service/main.py`
- Create: `agent/py_service/pkg/input/__init__.py`
- Create: `agent/py_service/pkg/input/python_keyboard.py`
- Create: `agent/py_service/pkg/input/hybrid_makcu.py`

**Steps:**
1. Add the persisted boolean setting and backward-compatible load/save behavior.
2. Extend runtime controller overrides to carry the keyboard routing choice.
3. Implement a small Python keyboard adapter with `press`, `key_down`, `key_up`, `wait`, `handshake`, and `close`.
4. Implement a hybrid Makcu controller that proxies mouse/connection behavior to Makcu and keyboard behavior to Python.
5. Update service controller creation to instantiate the hybrid controller when requested.

### Task 3: Wire the Qt setting

**Files:**
- Modify: `gui_qt/adapters/launcher_bridge.py`
- Modify: `gui_qt/window.py`
- Modify: `tests/test_gui_launcher.py`

**Steps:**
1. Add the checkbox to the settings page and only show it when backend is `makcu`.
2. Persist and restore the checkbox state through the bridge.
3. Pass the setting into task and trigger launches.
4. Run the relevant GUI tests and confirm they pass.

### Task 4: Update versions and release outputs

**Files:**
- Modify: `agent/py_service/__init__.py`
- Modify: `agent/py_service/main.py`
- Modify: `assets/interface.json`
- Modify: `gui_qt/window.py`
- Modify: `RELEASE_README.txt`
- Refresh: `release/FerrumBot-v1.0.03-portable`
- Refresh: `release/FerrumBot-v1.0.03-portable.zip`
- Refresh: `release/FerrumBot-v1.0.0-portable`

**Steps:**
1. Update source version strings to 1.0.03.
2. Build the launcher.
3. Copy/package the fresh portable output into the 1.0.03 folder and zip.
4. Replace the local `release/FerrumBot-v1.0.0-portable` contents with the same fresh build.

### Task 5: Verify before completion

**Files:**
- Modify: none

**Steps:**
1. Run focused tests for launcher + Makcu behavior.
2. Run the full relevant pytest command if feasible.
3. Build/package and verify the release outputs exist.
4. Report exact commands and observed results.
