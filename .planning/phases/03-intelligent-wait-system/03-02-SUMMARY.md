---
phase: 03-intelligent-wait-system
plan: 02
type: execute
subsystem: config
status: complete
requirements:
  - WAIT-01
  - WAIT-02
  - WAIT-03
  - WAIT-04
dependency_graph:
  requires:
    - core/workflow_schema.py (WaitImageAction schema)
    - core/workflow_executor.py (retry loop infrastructure)
    - tests/config_system/test_workflow_executor.py (existing test patterns)
  provides:
    - wait_image runtime with 2-hit stability
    - retry interval handling in executor
    - timeout/retry integration without parallel retry systems
  affects:
    - core/workflow_runtime.py
    - core/workflow_executor.py
    - core/workflow_compiler.py
    - core/workflow_schema.py
    - tests/config_system/test_workflow_executor.py
tech_stack:
  added: []
  patterns:
    - 2-hit stability gating for image state changes
    - Monotonic deadline control for timeouts
    - Three-tier configuration override (action > step > workflow)
    - Executor-owned retry with configurable intervals
key_files:
  created: []
  modified:
    - core/workflow_runtime.py
    - core/workflow_executor.py
    - core/workflow_compiler.py
    - core/workflow_schema.py
    - tests/config_system/test_workflow_executor.py
decisions:
  - "2-hit stability prevents flickering - require 2 consecutive evaluations"
  - "Executor remains single retry authority - wait_image raises ExecutionError on timeout"
  - "CompiledWorkflow stores wait_defaults for runtime access"
  - "ActionDispatcher accepts optional vision_engine for image checking"
  - "time.monotonic() for deadline control prevents clock skew issues"
metrics:
  duration: 20 min
  completed_date: "2026-03-07"
  tests_added: 9
  tests_passing: 24
---

# Phase 03 Plan 02: Wait Image Runtime Semantics Summary

Implement intelligent wait execution semantics and wire timeout/retry behavior into the existing deterministic executor.

## What Was Built

### 1. Wait Image Runtime (Task 1)

Extended `ActionDispatcher` to handle `wait_image` actions with intelligent polling:

```python
def _dispatch_wait_image(self, action: WaitImageAction, step: WorkflowStep) -> None:
    # Monotonic deadline control
    deadline = time.monotonic() + timeout_sec

    # 2-hit stability tracking
    consecutive_hits = 0
    required_hits = 2

    while time.monotonic() < deadline:
        is_present = self._check_image_present(action.image, action.roi)

        if action.state == 'appear':
            if is_present:
                consecutive_hits += 1
                if consecutive_hits >= required_hits:
                    return  # Success
            else:
                consecutive_hits = 0  # Reset on miss
        elif action.state == 'disappear':
            if not is_present:
                consecutive_hits += 1
                if consecutive_hits >= required_hits:
                    return  # Success
            else:
                consecutive_hits = 0  # Reset on hit

        time.sleep(poll_interval_sec)

    raise ExecutionError("wait_image timeout...")
```

**Key features:**
- **2-hit stability**: Both appear and disappear require 2 consecutive matching evaluations
- **Monotonic deadline**: `time.monotonic()` prevents clock skew issues
- **Configurable timeouts**: Three-tier override (action > step > workflow > default)
- **Executor retry integration**: Timeout raises `ExecutionError` for executor handling

### 2. Retry Interval Semantics (Task 2)

Extended `WorkflowExecutor._execute_step()` with configurable retry intervals:

```python
def _execute_step(self, step: WorkflowStep) -> tuple[bool, Optional[Exception]]:
    retry_interval_ms = self._resolve_retry_interval_ms(step)
    retry_interval_sec = retry_interval_ms / 1000.0

    for attempt in range(max_attempts):
        try:
            self.dispatcher.dispatch(step)
            return True, None
        except ExecutionError as e:
            if attempt < max_attempts - 1:
                time.sleep(retry_interval_sec)  # Wait before retry
                continue
            else:
                break
```

**Key features:**
- **Step-level override**: `retry_interval_ms` field on WorkflowStep
- **Workflow default**: Falls back to `wait_defaults.retry_interval_ms`
- **Fixed short default**: 1 second fallback
- **No parallel retry**: Timeout errors flow through existing executor retry

### 3. CompiledWorkflow Enhancement

Added `wait_defaults` to `CompiledWorkflow` for runtime access:

```python
class CompiledWorkflow:
    def __init__(self, ..., wait_defaults: Optional[WaitDefaults] = None):
        ...
        self.wait_defaults = wait_defaults or WaitDefaults()
```

This allows both executor and dispatcher to resolve configuration defaults.

## Test Coverage

Added 9 new tests across 2 test classes:

| Test Class | Purpose | Count |
|------------|---------|-------|
| `TestWaitImageRuntime` | wait_image appear/disappear/timeout | 5 |
| `TestRetryInterval` | retry interval semantics | 4 |

**Total test suite:** 24 tests passing

### Key Test Scenarios

1. **WAIT-01 (appear)**: `test_wait_image_appear_succeeds_after_two_consecutive_hits`
2. **WAIT-02 (disappear)**: `test_wait_image_disappear_succeeds_after_two_consecutive_misses`
3. **WAIT-03 (timeout)**: `test_wait_image_timeout_raises_execution_error`
4. **WAIT-04 (retry)**: `test_timeout_errors_flow_through_executor_retry`
5. **Stability**: `test_wait_image_appear_single_hit_not_enough`
6. **Retry interval**: `test_retry_interval_waits_between_attempts`
7. **Override**: `test_step_level_retry_interval_overrides_default`

## Files Modified

| File | Changes |
|------|---------|
| `core/workflow_runtime.py` | +130 lines: wait_image dispatch, stability gating, timeout handling |
| `core/workflow_executor.py` | +34 lines: retry interval resolution, sleep between retries |
| `core/workflow_compiler.py` | +1 line: pass wait_defaults to CompiledWorkflow |
| `core/workflow_schema.py` | +5 lines: wait_defaults field in CompiledWorkflow |
| `tests/config_system/test_workflow_executor.py` | +280 lines: 9 new test methods |

## Verification

```bash
# Run all executor tests
pytest tests/config_system/test_workflow_executor.py -x
# 24 passed

# Run wait_image specific tests
pytest tests/config_system/test_workflow_executor.py -k "wait_image" -x
# 5 passed

# Run retry interval tests
pytest tests/config_system/test_workflow_executor.py -k "retry_interval" -x
# 4 passed
```

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **2-hit stability**: Prevents false positives from UI flickering or transient detection issues.

2. **Executor-owned retry**: `wait_image` raises `ExecutionError` on timeout rather than implementing internal retry. This keeps the executor as the single retry authority and prevents nested retry loops.

3. **Monotonic clock**: `time.monotonic()` for deadline calculation prevents issues with system clock changes during long waits.

4. **CompiledWorkflow stores defaults**: Rather than passing defaults through multiple layers, the compiled workflow stores them for runtime access.

5. **ActionDispatcher vision_engine**: Optional constructor parameter allows tests to inject mock vision engines while production code can use the controller's vision.

## Next Steps

Plan 03-03 will migrate the guild donation workflow from hardcoded sleeps to intelligent waits using the new `wait_image` action type.

---

*Completed: 2026-03-07*
*Commits: 00b4ceb, f98d318*
