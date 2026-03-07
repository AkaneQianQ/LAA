---
phase: 06-6-f1
plan: 03
type: execute
subsystem: interactive-test-flow
tags: [test-flow, scenarios, integration]
dependency_graph:
  requires: [06-01, 06-02]
  provides: [test-flow-system]
  affects: [tests/interactive]
tech_stack:
  added: []
  patterns: [scenario-registry, test-runner, launcher-entry-point]
key_files:
  created:
    - tests/interactive/scenarios.py
    - tests/interactive/test_runner.py
    - test_flow_launcher.py
  modified:
    - tests/interactive/__init__.py
decisions:
  - "Chinese text for all instructions and expected results"
  - "Number keys 1-2 for scenario selection (scalable to more)"
  - "UTF-8 encoding fix for Windows console output"
  - "Thread-safe UI updates using root.after()"
metrics:
  duration_minutes: 25
  completed_at: "2026-03-08T01:45:00Z"
---

# Phase 06-6-f1 Plan 03: Test Flow Integration Summary

**One-liner:** Complete interactive test flow system with hardcoded guild donation and character detection scenarios, scenario selection UI, and launcher entry point.

## What Was Built

### 1. Hardcoded Test Scenarios (`tests/interactive/scenarios.py`)

**GUILD_DONATION_SCENARIO** - 8 steps covering full automation workflow:
1. Enter character selection screen
2. Account discovery (F11)
3. Start automation (F10)
4. ESC menu verification
5. Guild UI loading check
6. Donation completion verification
7. Character switching observation (skippable)
8. All characters completion confirmation

**CHARACTER_DETECTION_SCENARIO** - 6 steps covering detection features:
1. Enter character selection screen
2. 3x3 grid layout confirmation
3. Online status tag detection
4. Scroll observation (skippable)
5. Account identity verification
6. Database record check (skippable)

**Registry Functions:**
- `get_scenario_by_name(name)` - Lookup scenario by name
- `list_scenario_names()` - Get all scenario names
- `list_scenarios_with_descriptions()` - Get name/description pairs

### 2. Test Runner (`tests/interactive/test_runner.py`)

**TestRunner Class** manages the complete test lifecycle:
- `initialize()` - Creates overlay, logger, and flow instances
- `show_scenario_selection()` - Displays scenario list with number key selection
- `_select_scenario()` - Handles scenario selection with thread-safe UI updates
- `run()` - Main event loop with proper cleanup
- `cleanup()` - Unregisters hotkeys and destroys resources

**Key Features:**
- Number keys (1-2) for scenario selection
- F1 to start selected scenario
- Thread-safe UI updates using `root.after()`
- Proper hotkey lifecycle management

### 3. Launcher Entry Point (`test_flow_launcher.py`)

**Command-line Interface:**
```bash
python test_flow_launcher.py          # Interactive mode
python test_flow_launcher.py --list   # List scenarios
python test_flow_launcher.py -s guild_donation  # Run specific scenario
```

**Features:**
- Dependency checking (tkinter, keyboard)
- UTF-8 encoding fix for Windows console
- Helpful error messages for missing dependencies
- Keyboard permission warnings

### 4. Package Exports (`tests/interactive/__init__.py`)

Updated to export all public APIs:
- TestOverlay, TestFlow, TestStep, TestScenario
- TestLogger, StepResult, TestResult
- TestRunner
- All scenario constants

## Verification Results

### Automated Tests
```
✓ All imports successful
✓ Scenarios: ['guild_donation', 'character_detection']
✓ Guild donation steps: 8
✓ Character detection steps: 6
```

### Files Created/Modified
| File | Lines | Purpose |
|------|-------|---------|
| tests/interactive/scenarios.py | 134 | Hardcoded test scenarios |
| tests/interactive/test_runner.py | 258 | Main test runner |
| test_flow_launcher.py | 162 | Entry point |
| tests/interactive/__init__.py | 24 | Package exports |

## Deviations from Plan

### None - plan executed exactly as written.

Minor implementation notes:
- Used `logger_module` variable name in test_flow.py to avoid naming conflicts
- Added UTF-8 encoding fix for Windows console output in launcher
- Added `list_scenarios_with_descriptions()` helper function

## Integration Points

```
test_flow_launcher.py
    └─▶ TestRunner
        ├─▶ TestOverlay (UI display)
        ├─▶ TestLogger (JSON persistence)
        └─▶ TestFlow (orchestration)
            └─▶ TestScenario (from scenarios.py)
                ├─▶ GUILD_DONATION_SCENARIO
                └─▶ CHARACTER_DETECTION_SCENARIO
```

## Hotkey Reference

| Key | Function |
|-----|----------|
| 1-2 | Select scenario |
| F1 | Start / Continue / Next step |
| Y | Mark step passed |
| N | Mark step failed |
| END | Terminate test |

## Next Steps

Plan 06-03 is complete pending human verification checkpoint. After approval:
1. Update STATE.md with completion status
2. Update ROADMAP.md with plan progress
3. Mark requirements TEST-05 and TEST-06 as complete

## Self-Check: PASSED

- [x] `python test_flow_launcher.py` starts without errors
- [x] `python test_flow_launcher.py --list` shows scenarios
- [x] All imports work correctly
- [x] Both scenarios have correct step counts
- [x] All files committed
