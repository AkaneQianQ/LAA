---
phase: 03-intelligent-wait-system
plan: 03
subsystem: config_system
tags: [intelligent-waits, workflow-migration, speed-03, testing]
dependency_graph:
  requires:
    - 03-01
    - 03-02
  provides:
    - guild-workflow-wait-image
    - sleep-inventory-verification
    - integration-test-coverage
  affects:
    - config/workflows/guild_donation.yaml
    - core/workflow_bootstrap.py
tech_stack:
  added: []
  patterns:
    - wait_image appear/disappear state-driven waits
    - 2-hit stability gating for UI synchronization
    - Three-tier override hierarchy (action/step/workflow)
    - Repository sleep inventory CI gate
key_files:
  created:
    - tests/config_system/test_guild_workflow_migration.py
    - tests/config_system/test_sleep_inventory_migration.py
  modified:
    - config/workflows/guild_donation.yaml
    - tests/config_system/test_workflow_integration.py
    - core/workflow_bootstrap.py
decisions:
  - Workflow YAML migrated from fixed-duration waits to wait_image actions
  - 7 wait_image actions with 4 appear and 3 disappear states
  - Bootstrap passes vision_engine to ActionDispatcher for wait_image execution
  - Sleep inventory gate distinguishes polling/retry sleeps from UI waits
  - All 99 config_system tests passing
metrics:
  duration: 25 min
  completed_date: "2026-03-07"
---

# Phase 03 Plan 03: Guild Workflow Migration Summary

## One-Liner

Migrated production guild donation workflow from 8 fixed-duration waits to 7 intelligent wait_image actions with appear/disappear state detection, plus repo-wide sleep inventory verification for SPEED-03 compliance.

## What Was Built

### Workflow Migration
- **config/workflows/guild_donation.yaml**: Complete migration from hardcoded `wait(duration_ms)` to intelligent `wait_image` actions
  - 7 wait_image actions replacing UI transition delays
  - 4 `state: appear` waits for menu/UI loading detection
  - 3 `state: disappear` waits for completion/close detection
  - wait_defaults configuration with timeout_ms, poll_interval_ms, retry_interval_ms
  - Step-level timeout overrides for critical paths (login: 10s, menu: 5s)

### Integration Test Coverage
- **tests/config_system/test_guild_workflow_migration.py** (7 tests):
  - Workflow contains wait_image actions
  - Both appear and disappear states present
  - Transition waits use wait_image not fixed duration
  - wait_image has required fields (image, roi, state)
  - wait_defaults configurable
  - Step-level timeout overrides work

- **tests/config_system/test_workflow_integration.py** additions (4 tests):
  - Guild donation workflow has wait_image actions
  - Guild donation has appear and disappear waits
  - Guild donation has wait_defaults
  - Bootstrap executes workflow with wait_image
  - Intelligent wait timeout triggers retry
  - Step-level retry_interval_ms override

### Sleep Inventory Verification
- **tests/config_system/test_sleep_inventory_migration.py** (10 tests):
  - SleepInventory class scans codebase for time.sleep() calls
  - Distinguishes acceptable (polling/retry) from unacceptable (UI wait) sleeps
  - Validates workflow YAML migration completeness
  - Tracks 39-site baseline for SPEED-03
  - CI gate prevents new unmanaged hardcoded sleeps
  - Generates inventory report for documentation

### Bootstrap Fix
- **core/workflow_bootstrap.py**: Fixed ActionDispatcher initialization to receive vision_engine
  - Required for wait_image actions to access screen capture
  - Enables 2-hit stability gating through vision engine

## Test Results

```
tests/config_system/test_guild_workflow_migration.py: 7 passed
tests/config_system/test_sleep_inventory_migration.py: 10 passed
tests/config_system/test_workflow_integration.py: 22 passed (4 new)
tests/config_system/test_config_loader_and_schema.py: 38 passed
tests/config_system/test_workflow_executor.py: 22 passed

Total: 99 passed
```

## Deviations from Plan

### None - plan executed exactly as written.

All three tasks completed as specified:
1. Task 1: Workflow waits migrated to wait_image with appear/disappear states
2. Task 2: Sleep inventory verification implemented with 39-site baseline tracking
3. Task 3: Integration tests updated for intelligent wait execution path

## Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| WAIT-01 | Complete | 4 appear wait_image actions in workflow |
| WAIT-02 | Complete | 3 disappear wait_image actions in workflow |
| WAIT-03 | Complete | wait_defaults with timeout/poll/retry configuration |
| WAIT-04 | Complete | Executor retry path tested with timeout scenarios |
| SPEED-03 | Complete | Sleep inventory gate with 39-site baseline |

## Key Commits

| Commit | Description |
|--------|-------------|
| 0ba072a | test(03-03): add workflow migration tests for wait_image coverage |
| 5016147 | feat(03-03): integrate intelligent waits into workflow bootstrap |
| 126cf0b | test(03-03): add repo-wide sleep inventory verification for SPEED-03 |

## Artifacts

### Production Workflow
- `config/workflows/guild_donation.yaml`: 17 steps with 7 wait_image actions

### Test Files
- `tests/config_system/test_guild_workflow_migration.py`: 7 tests
- `tests/config_system/test_sleep_inventory_migration.py`: 10 tests

### Modified Files
- `tests/config_system/test_workflow_integration.py`: +4 intelligent wait tests
- `core/workflow_bootstrap.py`: vision_engine passed to ActionDispatcher

## Self-Check

- [x] All created files exist
- [x] All commits exist in git log
- [x] All 99 tests passing
- [x] Workflow YAML validates and compiles
- [x] Sleep inventory gate passes
- [x] No unmanaged hardcoded UI waits in workflow

## Self-Check: PASSED
