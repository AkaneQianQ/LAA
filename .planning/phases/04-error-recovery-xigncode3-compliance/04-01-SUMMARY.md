---
phase: 04-error-recovery-xigncode3-compliance
plan: 01
subsystem: config-system
tags: [recovery, schema, compiler, err-02, err-04, ace-02]
dependency_graph:
  requires: [03-03]
  provides: [04-02, 04-03]
  affects: [core/workflow_schema.py, core/workflow_compiler.py, config/workflows/guild_donation.yaml]
tech_stack:
  added: []
  patterns: [pydantic-v2, discriminated-unions, recovery-anchors]
key_files:
  created:
    - tests/config_system/test_error_recovery_schema.py
  modified:
    - core/workflow_schema.py
    - core/workflow_compiler.py
    - config/workflows/guild_donation.yaml
    - tests/config_system/test_guild_workflow_migration.py
decisions:
  - RecoveryConfig model with anchor/on_timeout/max_escalations/audit_context
  - Compiler validates recovery graph safety (missing targets, cycles)
  - Backward compatible with Phase 1-3 workflows (default factory)
  - Guild workflow uses open_guild_menu as recovery anchor
metrics:
  duration: 25 min
  completed_date: "2026-03-07"
---

# Phase 04 Plan 01: Recovery Contracts Schema Summary

Recovery contract schema and compiler validation for deterministic error recovery.

## What Was Built

### 1. Recovery Schema Extension (core/workflow_schema.py)

Added `RecoveryConfig` Pydantic model with four fields:
- `anchor: bool` - Marks step as stable recovery point
- `on_timeout: Optional[str]` - Step ID to rollback to on timeout
- `max_escalations: int` (default: 3, >=0) - Recovery retry limit
- `audit_context: Optional[dict]` - Error logging metadata

Integrated into `WorkflowStep` with `default_factory=RecoveryConfig` for backward compatibility.

### 2. Compiler Recovery Validation (core/workflow_compiler.py)

Extended `compile_workflow()` with:
- Validation that `recovery.on_timeout` references exist
- Detection of recovery-only cycles using DFS graph traversal
- Actionable error messages with step IDs

Added `_detect_recovery_cycles()` helper that:
- Builds recovery-only graph from on_timeout references
- Detects closed loops that would cause infinite recovery
- Reports cycle path for debugging

### 3. Guild Workflow Recovery Anchors (config/workflows/guild_donation.yaml)

Annotated workflow with recovery metadata:
- **Anchor**: `open_guild_menu` marked as recovery anchor with audit context
- **6 wait_image steps** configured with on_timeout rollback:
  - `wait_menu_appear` -> `open_guild_menu` (max 3 escalations)
  - `wait_donation_ui_appear` -> `open_guild_menu` (max 3)
  - `wait_confirm_appear` -> `open_guild_menu` (max 3)
  - `wait_confirm_disappear` -> `open_guild_menu` (max 2)
  - `wait_character_select_appear` -> `open_guild_menu` (max 3)
  - `wait_login_complete` -> `open_guild_menu` (max 2)

### 4. Test Coverage (tests/config_system/test_error_recovery_schema.py)

18 tests covering:
- Schema field validation (anchor, on_timeout, max_escalations, audit_context)
- Type validation (boolean, string, non-negative integers, dict)
- Compiler validation (missing targets, cycles, valid paths)
- Backward compatibility with Phase 1-3 workflows

## Verification

```bash
# All 121 config system tests pass
pytest tests/config_system/ -q
```

## Deviations from Plan

None - plan executed exactly as written.

## Requirements Mapping

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| ERR-02 | Complete | Recovery anchor schema with on_timeout rollback |
| ERR-04 | Partial | audit_context field ready for structured logging |
| ACE-02 | Not started | Timing jitter will be in Plan 04-04 |

## Commits

1. `3d21153` feat(04-01): extend workflow schema with recovery contracts
2. `22a844f` feat(04-01): add compiler semantic validation for recovery graph safety
3. `9270388` feat(04-01): mark recovery anchors in guild donation workflow

## Self-Check: PASSED

- [x] core/workflow_schema.py exists with RecoveryConfig
- [x] core/workflow_compiler.py has recovery validation
- [x] config/workflows/guild_donation.yaml has recovery anchors
- [x] tests/config_system/test_error_recovery_schema.py has 18 tests
- [x] All 121 tests pass
