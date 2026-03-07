---
phase: 04-error-recovery-xigncode3-compliance
plan: 02
subsystem: config-system
tags: [recovery, runtime, logging, err-01, err-02, err-03, err-04]
dependency_graph:
  requires: [04-01]
  provides: [04-03, 04-04, 04-05, 04-06]
  affects: [core/error_recovery.py, core/error_logger.py, core/workflow_executor.py]
tech_stack:
  added: []
  patterns: [error-taxonomy, escalation-state-machine, jsonl-logging, circuit-breaker]
key_files:
  created:
    - core/error_recovery.py
    - core/error_logger.py
    - tests/config_system/test_error_recovery_runtime.py
  modified:
    - core/workflow_executor.py
decisions:
  - ErrorKind enum with 5 classification types for recovery routing
  - Three-tier escalation L1 retry -> L2 rollback -> L3 skip
  - Circuit breaker pattern for same-kind failure detection
  - JSONL logging with daily file partitioning under logs/errors/
  - RoleSkipError for graceful role skip without forced restart
  - RecoveryOrchestrator integrated into WorkflowExecutor
metrics:
  duration: 20 min
  completed_date: "2026-03-07"
---

# Phase 04 Plan 02: Runtime Recovery and Structured Logging Summary

Error taxonomy, escalation state machine, and structured JSONL logging for resilient workflow execution.

## What Was Built

### 1. Error Taxonomy (core/error_recovery.py)

**ErrorKind Enum:**
- `NETWORK_LAG` - Extended timeout scenarios (30s+)
- `UI_TIMEOUT` - wait_image timeout failures
- `DISCONNECT` - Client disconnect detection
- `INPUT_POLICY_VIOLATION` - ACE compliance violations
- `UNKNOWN` - Unclassified errors

**ErrorContext Dataclass:**
Captures all required metadata for debugging:
- phase, step_id, action_type, attempt
- account_id, screenshot_path
- detail dict for extensible context

**classify_error() Function:**
Maps exceptions to ErrorKind based on:
- Error message patterns ("wait_image timeout", "network")
- Context markers (disconnect_detected)
- Elapsed time thresholds (30s for network lag)

### 2. Escalation State Machine (core/error_recovery.py)

**RecoveryOrchestrator:**
Implements three-tier escalation policy:
- **L1_RETRY**: Step-level retry (existing semantics)
- **L2_ROLLBACK**: Rollback to anchor step after 3 failures
- **L3_SKIP**: Skip current role after max escalations

**Circuit Breaker:**
- Tracks same-kind failure counts
- Opens circuit after 3 same-kind failures
- Prevents infinite recovery loops

**State Management:**
- Escalation counter per workflow run
- Error kind tracking for circuit breaker
- Reset on successful step execution

### 3. Structured JSONL Logging (core/error_logger.py)

**ErrorLogger Class:**
- Daily file partitioning: `logs/errors/YYYY-MM-DD.jsonl`
- Required fields per ERR-04:
  - ts, phase, step_id, error_kind, message
  - attempt, account, screenshot_path, context
- Console summary for immediate visibility
- Screenshot capture integration

**Log Record Format:**
```json
{
  "ts": "2026-03-07T15:30:00Z",
  "phase": "04",
  "step_id": "wait_guild_ui",
  "error_kind": "ui_timeout",
  "message": "wait_image timeout",
  "attempt": 2,
  "account": "abc123",
  "screenshot_path": "logs/screenshots/wait_guild_ui_20260307_153000.png",
  "context": {"image": "guild_flag.png"}
}
```

### 4. Executor Recovery Integration (core/workflow_executor.py)

**WorkflowExecutor Enhancements:**
- Integrated `RecoveryOrchestrator` for escalation decisions
- `_execute_step_with_recovery()` method for recovery routing
- `RoleSkipError` exception for L3 skip scenarios
- `skipped_role` flag in `ExecutionResult`

**Recovery Flow:**
1. Execute step with normal retry logic
2. On failure, classify error kind
3. Log error with full context
4. Determine recovery action (L1/L2/L3)
5. Execute rollback to anchor or skip role
6. Reset state on successful execution

**Disconnect Handling:**
- Immediate L3 skip for DISCONNECT errors
- No forced client restart
- Graceful continuation to next role

### 5. Test Coverage (tests/config_system/test_error_recovery_runtime.py)

**32 tests covering:**
- Error taxonomy classification (7 tests)
- Escalation state machine (8 tests)
- Recovery action routing (1 test)
- Executor integration (4 tests)
- JSONL logging (6 tests)
- Runtime integration (2 tests)
- End-to-end recovery flows (4 tests)

## Verification

```bash
# All 153 config system tests pass
pytest tests/config_system/ -q
```

## Deviations from Plan

None - plan executed exactly as written.

## Requirements Mapping

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| ERR-01 | Complete | Network lag classification with escalation to rollback/skip |
| ERR-02 | Complete | UI timeout recovery with anchor rollback |
| ERR-03 | Complete | Disconnect detection triggers role skip without restart |
| ERR-04 | Complete | JSONL logging with all required fields and screenshot paths |

## Commits

1. `51ebce2` test(04-02): add error taxonomy and escalation state machine tests
2. `652ff1c` feat(04-02): wire recovery decisions into executor runtime

## Self-Check: PASSED

- [x] core/error_recovery.py exists with ErrorKind, ErrorContext, RecoveryOrchestrator
- [x] core/error_logger.py exists with JSONL logging and daily partitioning
- [x] core/workflow_executor.py has recovery integration and RoleSkipError
- [x] tests/config_system/test_error_recovery_runtime.py has 32 tests
- [x] All 153 config system tests pass
