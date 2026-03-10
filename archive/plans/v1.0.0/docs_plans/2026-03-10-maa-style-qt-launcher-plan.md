# MAA-Style Qt Launcher Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild the FerrumBot launcher UI in `PySide6` with high visual fidelity to the local MAA client while preserving the existing Python launcher service layer.

**Architecture:** Keep `launcher/service.py`, `launcher/settings.py`, and `launcher/trigger_service.py` as the business layer, then add a new `gui_qt` package that owns Qt widgets, theme assets, and thread-safe service bridging. Preserve the current launcher entry during migration so the new Qt launcher can be verified in parallel before cutover.

**Tech Stack:** Python, PySide6, Qt stylesheets, threading, existing launcher services, pytest

---

### Task 1: Inventory current launcher behavior and MAA reference assets

**Files:**
- Review: `gui_launcher.py`
- Review: `launcher/service.py`
- Review: `launcher/settings.py`
- Review: `launcher/trigger_service.py`
- Review external reference: `E:\MAA`
- Document in: `docs/plans/2026-03-10-maa-style-qt-launcher-design.md`

**Step 1: Write the failing test**

No code test yet. Instead, define a parity checklist covering:
- title bar controls
- top tabs
- left task panel
- center checklist content
- runtime/status strip
- trigger/log page coverage

**Step 2: Verify the gap exists**

Run the current launcher manually:

`python gui_launcher.py`

Expected: current `tkinter` UI is functionally usable but visibly far from the MAA client.

**Step 3: Write minimal implementation**

Capture the exact assets and UI elements needed from `E:\MAA` into a local launcher asset inventory.

**Step 4: Verify the result**

Expected: a concrete asset list and parity checklist exist before UI implementation starts.

### Task 2: Add failing tests for a Qt-friendly launcher bridge

**Files:**
- Modify: `tests/test_gui_launcher.py`
- Create: `gui_qt/adapters/launcher_bridge.py`

**Step 1: Write the failing test**

Add focused tests for:
- loading and saving settings through the bridge
- probing controller state through the bridge
- emitting task start/completion/log events through bridge callbacks or signals
- trigger start/stop state transitions

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: FAIL because the Qt bridge module does not exist yet.

**Step 3: Write minimal implementation**

Create `gui_qt/adapters/launcher_bridge.py` with the thinnest layer needed to adapt the existing launcher services for Qt-safe background execution.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: PASS for the bridge-focused tests.

### Task 3: Create the new Qt launcher package skeleton

**Files:**
- Create: `gui_qt/__init__.py`
- Create: `gui_qt/main.py`
- Create: `gui_qt/window.py`
- Create: `gui_qt/theme/__init__.py`
- Create: `gui_qt/theme/palette.py`
- Create: `gui_qt/theme/style.qss`
- Create: `gui_qt/widgets/__init__.py`
- Create: `gui_qt/views/__init__.py`

**Step 1: Write the failing test**

Add a smoke-level import/initialization test that verifies the Qt launcher package can build the main window without starting task execution.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: FAIL because the Qt launcher package does not exist.

**Step 3: Write minimal implementation**

Build the package skeleton with:
- Qt application bootstrap
- theme loader
- empty but valid main window shell

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: PASS for the smoke-level package test.

### Task 4: Build the MAA-style main shell and navigation

**Files:**
- Modify: `gui_qt/window.py`
- Create: `gui_qt/titlebar.py`
- Create: `gui_qt/views/home_view.py`
- Create: `gui_qt/widgets/navigation.py`
- Create: `gui_qt/widgets/titlebar_buttons.py`
- Modify: `gui_qt/theme/style.qss`

**Step 1: Write the failing test**

Add focused tests for:
- main tabs exist with expected labels
- title bar control actions are wired
- primary sections render in the window hierarchy

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: FAIL because the main shell layout is not implemented yet.

**Step 3: Write minimal implementation**

Implement:
- custom title bar
- top navigation tabs
- left/center content shell
- page switching between main, trigger, and logs views

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: PASS for structure-level tests.

### Task 5: Recreate the left task panel and runtime controls

**Files:**
- Modify: `gui_qt/views/home_view.py`
- Create: `gui_qt/widgets/task_panel.py`
- Create: `gui_qt/widgets/task_row.py`
- Modify: `gui_qt/theme/style.qss`
- Modify: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add tests for:
- task rows render from launcher metadata
- task selection state updates correctly
- start button busy-state logic matches existing behavior
- runtime labels update when a task starts and finishes

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: FAIL because the task panel and state wiring are incomplete.

**Step 3: Write minimal implementation**

Implement:
- task list card
- task row widgets with checkbox and gear affordance
- start button and bottom action area
- runtime state display bound to the bridge

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: PASS for task panel behavior tests.

### Task 6: Recreate the center configuration content and secondary controls

**Files:**
- Modify: `gui_qt/views/home_view.py`
- Create: `gui_qt/widgets/checklist_group.py`
- Create: `gui_qt/widgets/segmented_buttons.py`
- Modify: `gui_qt/theme/style.qss`
- Modify: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add tests for:
- configuration groups render with expected labels
- secondary buttons switch visible state correctly
- status/info text regions populate predictably

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: FAIL because the content area widgets do not exist yet.

**Step 3: Write minimal implementation**

Implement the center content area with static and launcher-driven content arranged to match the target MAA composition.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: PASS for content-area tests.

### Task 7: Connect trigger and logs pages to the new shell

**Files:**
- Create: `gui_qt/views/trigger_view.py`
- Create: `gui_qt/views/logs_view.py`
- Modify: `gui_qt/window.py`
- Modify: `gui_qt/adapters/launcher_bridge.py`
- Modify: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add tests for:
- trigger page start/stop wiring
- log view appends incoming log lines
- busy state blocks conflicting actions across pages

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: FAIL because the secondary views are not connected.

**Step 3: Write minimal implementation**

Implement and wire the trigger and logs pages using the same bridge/runtime state model as the home view.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: PASS for trigger/log view tests.

### Task 8: Import and localize MAA-style assets

**Files:**
- Create: `gui_qt/theme/assets/`
- Modify: `gui_qt/theme/style.qss`
- Optionally create: `gui_qt/theme/fonts.py`
- Modify: `gui_qt/theme/palette.py`

**Step 1: Write the failing test**

Add smoke checks that required local asset paths exist and the theme loader can resolve them.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: FAIL because the local asset bundle is not present yet.

**Step 3: Write minimal implementation**

Copy/select the required icon and optional font assets into the project-local Qt theme asset directory and wire them through the theme loader.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: PASS for theme asset resolution checks.

### Task 9: Add the Qt launcher entry point and preserve the current launcher during migration

**Files:**
- Create: `gui_launcher_qt.py`
- Optionally modify: `gui_launcher.py`
- Modify: `requirements-gui.txt`
- Modify: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

Add tests that assert:
- the Qt entry point imports successfully
- launcher startup paths are unambiguous
- required GUI dependencies are declared

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: FAIL because the Qt launcher entry point and dependency declarations are incomplete.

**Step 3: Write minimal implementation**

Create `gui_launcher_qt.py` as the new Qt entry point and preserve the current launcher path until parity verification is complete.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: PASS for entry-point and dependency tests.

### Task 10: Verify functionality and parity

**Files:**
- Verify: `gui_launcher_qt.py`
- Verify visually against: `E:\MAA`

**Step 1: Run automated verification**

Run: `python -m pytest tests/test_gui_launcher.py -v`

Expected: PASS

**Step 2: Run the Qt launcher manually**

Run: `python gui_launcher_qt.py`

Expected:
- window opens successfully
- task selection and start flow work
- detection flow works
- trigger start/stop works
- logs update in real time

**Step 3: Run visual parity review**

Compare the new launcher against the local `E:\MAA` client for:
- tabs
- title bar
- left task list
- center controls
- status strip
- icons and spacing

Expected: the launcher is clearly MAA-style and materially closer to the reference than the current `tkinter` launcher.

Plan complete and saved to `docs/plans/2026-03-10-maa-style-qt-launcher-plan.md`.
