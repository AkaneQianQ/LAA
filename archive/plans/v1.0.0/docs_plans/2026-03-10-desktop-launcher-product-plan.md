# Desktop Launcher Product Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add product-style GUI polish, editable per-driver COM ports, automatic/manual hardware detection, and hidden-console packaging to the FerrumBot launcher.

**Architecture:** Extend launcher settings and service helpers so the launcher can override controller serial ports at runtime and probe connectivity with existing controller APIs. Update the `ttkbootstrap` GUI to surface driver configuration and status cleanly, then switch PyInstaller to a windowed build while preserving one-folder distribution.

**Tech Stack:** Python, tkinter, ttkbootstrap, threading, queue, PyInstaller, pytest

---

### Task 1: Add failing tests for per-driver COM persistence and runtime overrides

**Files:**
- Modify: `tests/test_gui_launcher.py`
- Modify: `launcher/settings.py`
- Modify: `launcher/service.py`

**Step 1: Write the failing test**

Add tests for:
- per-driver port persistence
- resolving the active port for the selected backend
- overriding the controller serial port for a runtime task

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: FAIL because settings and service helpers do not support port overrides yet

**Step 3: Write minimal implementation**

Implement per-backend port storage and runtime config override helpers.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: PASS

### Task 2: Add failing tests for hardware probe behavior

**Files:**
- Modify: `tests/test_gui_launcher.py`
- Modify: `launcher/service.py`

**Step 1: Write the failing test**

Add tests for:
- successful handshake probe
- failed handshake probe
- probe closes the controller

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: FAIL because no probe helper exists

**Step 3: Write minimal implementation**

Add a probe helper that constructs a controller from overridden config and returns a structured status result.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: PASS

### Task 3: Productize the GUI

**Files:**
- Modify: `gui_launcher.py`
- Modify: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add focused non-visual tests around launcher-facing state handling where practical.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: FAIL because the launcher state flow does not support detection/ports yet

**Step 3: Write minimal implementation**

Add:
- polished layout
- COM input
- detect button
- auto detect on startup and backend switch
- busy-state lockout for task and detect actions

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: PASS

### Task 4: Switch packaging to hidden-console mode and rebuild

**Files:**
- Modify: `FerrumBotLauncher.spec`
- Modify: `build_launcher.ps1`

**Step 1: Write the failing test**

Add a packaging smoke assertion if needed for the spec flags.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: FAIL if the windowed packaging expectation is not encoded yet

**Step 3: Write minimal implementation**

Switch PyInstaller spec to GUI mode and keep one-folder output.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`
Expected: PASS

### Task 5: Verify and rebuild distributable

**Files:**
- Output: `dist/FerrumBot/`

**Step 1: Run verification**

Run: `python -m pytest tests/test_gui_launcher.py -v`

**Step 2: Rebuild**

Run: `powershell -ExecutionPolicy Bypass -File .\\build_launcher.ps1`

**Step 3: Check folder contents**

Confirm the output remains a one-folder distribution with bundled dependencies.
