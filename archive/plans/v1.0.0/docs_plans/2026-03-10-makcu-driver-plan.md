# MAKCU Driver Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a MAKCU serial driver alongside Ferrum and allow controller backend selection via config.

**Architecture:** Introduce a new `agent.py_service.pkg.makcu` package that implements the controller methods the workflow runtime already expects. Update service initialization to resolve the backend from controller config while preserving Ferrum as the default path.

**Tech Stack:** Python, pyserial, pytest, monkeypatch, win32api fallback handling

---

### Task 1: Add failing tests for MAKCU controller serial behavior

**Files:**
- Create: `tests/test_makcu_controller.py`
- Reference: `agent/py_service/pkg/ferrum/controller.py`

**Step 1: Write the failing test**

Add tests for:
- `km.init()` during startup
- `km.move(dx, dy)` generation in `move_absolute()`
- `km.click(button)` / `km.wheel(delta)` formatting
- `km.down/up/press('key')` keyboard formatting

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_makcu_controller.py -v`
Expected: FAIL because `agent.py_service.pkg.makcu.controller` does not exist yet.

**Step 3: Write minimal implementation**

Create the MAKCU controller package and controller class with serial command helpers.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_makcu_controller.py -v`
Expected: PASS

### Task 2: Add failing tests for backend selection

**Files:**
- Modify: `tests/test_makcu_controller.py`
- Reference: `agent/py_service/main.py`

**Step 1: Write the failing test**

Add tests that call `initialize()` with patched dependencies and verify:
- default config uses Ferrum when `driver` is missing
- `driver: "makcu"` selects `MakcuController`

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_makcu_controller.py -v`
Expected: FAIL because initialization still hardcodes `FerrumController`.

**Step 3: Write minimal implementation**

Add a controller factory in `agent/py_service/main.py`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_makcu_controller.py -v`
Expected: PASS

### Task 3: Add package exports and config example

**Files:**
- Create: `agent/py_service/pkg/makcu/__init__.py`
- Modify: `assets/interface.json`

**Step 1: Write the failing test**

Add coverage that validates config-driven selection using a MAKCU controller entry.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_makcu_controller.py -v`
Expected: FAIL if MAKCU config is absent or unrecognized.

**Step 3: Write minimal implementation**

Export the new package and add a sample MAKCU controller entry to `assets/interface.json`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_makcu_controller.py -v`
Expected: PASS
