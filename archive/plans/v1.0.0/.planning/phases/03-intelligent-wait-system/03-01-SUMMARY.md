---
phase: 03-intelligent-wait-system
plan: 01
type: execute
subsystem: config
status: complete
requirements:
  - WAIT-01
  - WAIT-02
  - WAIT-03
dependency_graph:
  requires:
    - core/workflow_schema.py (existing ActionConfig union)
    - tests/config_system/test_config_loader_and_schema.py (existing test patterns)
  provides:
    - WaitImageAction schema contract
    - WaitDefaults configuration model
    - Step-level retry_interval_ms override
  affects:
    - core/workflow_schema.py
    - tests/config_system/test_config_loader_and_schema.py
tech_stack:
  added: []
  patterns:
    - Pydantic v2 discriminated unions for action types
    - Tiered configuration defaults with override semantics
    - TDD RED-GREEN for schema validation
key_files:
  created: []
  modified:
    - core/workflow_schema.py
    - tests/config_system/test_config_loader_and_schema.py
decisions:
  - "WaitImageAction is a separate model from WaitAction to maintain clear semantics"
  - "Explicit state field with Literal[appear, disappear] for type safety"
  - "Global WaitDefaults with per-step and per-action override capability"
  - "retry_interval_ms added to WorkflowStep for retry timing control"
  - "Legacy wait(duration_ms) preserved for phased migration"
metrics:
  duration: 8 min
  completed_date: "2026-03-07"
  tests_added: 16
  tests_passing: 36
---

# Phase 03 Plan 01: Intelligent Wait Schema Contracts Summary

Define the configuration contracts for intelligent waits so executors can implement state-driven wait behavior without guessing field semantics.

## What Was Built

### 1. WaitImageAction Schema

New action type `wait_image` with explicit state semantics:

```python
class WaitImageAction(BaseModel):
    type: Literal["wait_image"]
    state: Literal["appear", "disappear"]
    image: str  # Template filename
    roi: Tuple[int, int, int, int]  # Search region
    timeout_ms: Optional[int] = None  # Override default
    poll_interval_ms: Optional[int] = None  # Override default
```

**Key design decisions:**
- `state` field is explicit with locked `appear|disappear` values
- `image` and `roi` are required fields (fail fast on missing)
- Optional override fields for timeout/poll at action level

### 2. WaitDefaults Model

Global workflow configuration for wait behavior:

```python
class WaitDefaults(BaseModel):
    timeout_ms: int = 10000        # 10s default
    poll_interval_ms: int = 50     # 50ms between checks
    retry_interval_ms: int = 1000  # 1s between retries
```

Integrated into `WorkflowConfig`:
```python
class WorkflowConfig(BaseModel):
    # ... existing fields ...
    wait_defaults: WaitDefaults = Field(default_factory=WaitDefaults)
```

### 3. Step-Level Override

Added `retry_interval_ms` to `WorkflowStep`:

```python
class WorkflowStep(BaseModel):
    # ... existing fields ...
    retry: int = 0
    retry_interval_ms: Optional[int] = None  # Override workflow default
```

### 4. Backward Compatibility

Legacy `wait(duration_ms)` action remains fully supported:

```yaml
# Old style - still valid
- step_id: legacy_wait
  action:
    type: wait
    duration_ms: 1000

# New style - intelligent wait
- step_id: smart_wait
  action:
    type: wait_image
    state: appear
    image: btn_login.png
    roi: [100, 200, 300, 400]
```

## Test Coverage

Added 16 new tests across 3 test classes:

| Test Class | Purpose | Count |
|------------|---------|-------|
| `TestWaitImageSchema` | Core wait_image validation | 6 |
| `TestWaitDefaultsAndOverrides` | Defaults and override semantics | 5 |
| `TestWaitImageValidationEdgeCases` | Edge case validation | 3 |

**Total test suite:** 36 tests passing

### Key Test Scenarios

1. **WAIT-01 (appear):** `test_wait_image_accepts_appear_state`
2. **WAIT-02 (disappear):** `test_wait_image_accepts_disappear_state`
3. **WAIT-03 (timeout):** `test_wait_image_with_timeout_override`, `test_workflow_level_wait_defaults`
4. **Backward compatibility:** `test_legacy_wait_action_remains_valid`
5. **Validation:** Missing fields, invalid states, malformed ROI all fail fast

## Files Modified

| File | Changes |
|------|---------|
| `core/workflow_schema.py` | +72 lines: WaitImageAction, WaitDefaults, retry_interval_ms field |
| `tests/config_system/test_config_loader_and_schema.py` | +344 lines: 16 new test methods |

## Verification

```bash
# Run new wait-related tests
pytest tests/config_system/test_config_loader_and_schema.py -k "wait_image or retry_interval or wait_action" -x
# 12 passed

# Run full schema test suite
pytest tests/config_system/test_config_loader_and_schema.py -x
# 36 passed
```

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Separate models for wait types:** `WaitImageAction` is distinct from `WaitAction` rather than extending it, maintaining clear semantic boundaries.

2. **Explicit state values:** Used `Literal["appear", "disappear"]` instead of boolean flags for readability and type safety.

3. **Three-tier override hierarchy:** Action-level fields override Step-level fields, which override Workflow-level defaults.

4. **Default values:** Selected based on typical automation needs:
   - 10s timeout balances responsiveness with slow UI scenarios
   - 50ms poll interval provides ~20 FPS checking without excessive CPU
   - 1s retry interval prevents thrashing on transient failures

## Next Steps

Plan 03-02 will implement the runtime semantics for `wait_image` actions in the workflow executor, including:
- Image state polling loop
- Timeout handling with retry integration
- Condition evaluator integration for appearance/disappearance detection

---

*Completed: 2026-03-07*
*Commit: ecef86f*
