---
phase: 02-configuration-system
plan: 03
subsystem: configuration
milestone: v1.0

requirements:
  - CFG-01
  - CFG-02
  - CFG-03
  - CFG-04

dependency_graph:
  requires:
    - 02-01
    - 02-02
  provides:
    - workflow-bootstrap
    - launcher-integration
  affects:
    - gui_launcher.py

tech_stack:
  added:
    - workflow_bootstrap.py
    - guild_donation.yaml
  patterns:
    - bootstrap-pattern
    - config-driven-automation

key_files:
  created:
    - core/workflow_bootstrap.py
    - config/workflows/guild_donation.yaml
    - tests/config_system/test_workflow_integration.py
  modified:
    - gui_launcher.py

decisions:
  - Bootstrap module provides single entrypoint create_workflow_executor()
  - Launcher uses workflow path config/workflows/guild_donation.yaml
  - StoppableController checks stop_event during wait operations
  - MockVisionEngine simulates detection for testing
  - Fallback simulation mode when config file missing

metrics:
  duration: 3 minutes
  completed_date: "2026-03-07"
  tests_added: 16
  total_tests: 54
---

# Phase 02 Plan 03: Workflow Bootstrap and Launcher Integration Summary

**One-liner:** Workflow bootstrap module with config-driven automation integration into GUI launcher.

## What Was Built

### 1. Workflow Bootstrap Module (`core/workflow_bootstrap.py`)

A bootstrap entrypoint that wires together the configuration system components:

- **`create_workflow_executor(path, controller, vision_engine)`**: Single public API that:
  - Loads workflow config from YAML file
  - Compiles for semantic validation
  - Creates ActionDispatcher with controller
  - Creates ConditionEvaluator with vision engine
  - Returns configured WorkflowExecutor

- **Re-exports**: `ConfigLoadError` for convenient error handling

### 2. Sample Guild Donation Workflow (`config/workflows/guild_donation.yaml`)

A complete 18-step workflow demonstrating:

- **All action types**: click, wait, press, scroll
- **Conditional branching**: `on_true`/`on_false` with image conditions
- **Loop path**: Character iteration with scroll and login
- **Explicit step IDs**: Every step has unique identifier
- **Retry policies**: Per-step retry configuration
- **ROI-based detection**: Guild flag, quick switch button detection

Key workflow sections:
- Open guild menu (Alt+U)
- Wait and check for menu open
- Navigate to donation tab
- Execute silver donation
- Close menu
- Loop to next character if available

### 3. Launcher Integration (`gui_launcher.py`)

Updated automation path to use config-driven workflow:

- **Imports**: `create_workflow_executor` and `ConfigLoadError`
- **`_automation_worker()`**: Now uses workflow bootstrap instead of simulation
- **`_create_controller()`**: Stoppable controller with stop_event checking
- **`_create_vision_engine()`**: Mock vision engine for testing
- **`_simulate_automation()`**: Fallback when config file missing
- **Error handling**: Clear log messages for config load failures

### 4. Integration Tests (`tests/config_system/test_workflow_integration.py`)

16 comprehensive tests covering:

**WorkflowBootstrap (4 tests)**:
- Loads YAML and creates executor
- Invalid YAML raises ConfigLoadError
- Missing file raises FileNotFoundError
- Creates dispatcher and evaluator correctly

**GuildDonationWorkflow (5 tests)**:
- YAML loads and compiles
- Has all required action types (click, wait, press, scroll)
- Has conditional branch
- Has loop path for character iteration
- Uses explicit step IDs

**BootstrapExecutorIntegration (1 test)**:
- Executor runs through mocked dependencies with loop

**WorkflowValidation (1 test)**:
- Bootstrap fails on dangling reference

**LauncherIntegration (5 tests)**:
- Imports bootstrap correctly
- Has workflow path config
- Creates controller with stop event
- Handles ConfigLoadError
- Handles missing workflow file

## Test Results

```
pytest tests/config_system/ -v
============================= 54 passed in 0.70s =============================
```

All 54 config_system tests pass, including:
- 38 from previous plans (02-01, 02-02)
- 16 new from this plan

## Commits

| Hash | Message |
|------|---------|
| 5e23e19 | test(02-03): add workflow bootstrap and integration tests |
| 9080333 | feat(02-03): integrate workflow bootstrap into launcher automation path |

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- [x] Integration test verifies full parse->validate->compile->execute wiring from sample YAML
- [x] Launcher path uses workflow bootstrap
- [x] Launcher does not bypass strict startup validation
- [x] All 16 new tests pass
- [x] All 54 config_system tests pass

## Self-Check: PASSED

- [x] `core/workflow_bootstrap.py` exists
- [x] `config/workflows/guild_donation.yaml` exists
- [x] `tests/config_system/test_workflow_integration.py` exists
- [x] `gui_launcher.py` modified with bootstrap integration
- [x] Commit 5e23e19 exists
- [x] Commit 9080333 exists
