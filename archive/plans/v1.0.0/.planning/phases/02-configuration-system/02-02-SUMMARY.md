---
phase: 02-configuration-system
plan: 02
name: Workflow Executor and Runtime
subsystem: config
completed: 2026-03-07
duration: 20 min
tasks: 2
tests: 15 new (38 config system total, 87 overall)
files_created: 3
files_modified: 1
requirements:
  - CFG-02: System executes multi-step workflows defined in configuration
  - CFG-04: Configuration supports conditional logic based on image detection
  - CFG-03: Configuration supports click, wait, press, and scroll actions
key-decisions:
  - Cursor-based step progression with explicit next resolution
  - Per-step retry policy with configurable retry count
  - Loop guard at 1000 steps prevents runaway execution
  - ActionDispatcher normalizes coordinates (absolute + ROI-relative)
  - ConditionEvaluator uses existing VisionEngine for image detection
tech-stack:
  added:
    - core/workflow_executor.py: Deterministic step execution engine
    - core/workflow_runtime.py: Action dispatch and condition evaluation
  patterns:
    - Explicit next-link traversal (no implicit ordering)
    - Stop-on-failure default with opt-in retry override
    - Image-based condition branching (on_true/on_false)
key-files:
  created:
    - core/workflow_executor.py: WorkflowExecutor, ExecutionResult, ExecutionError
    - core/workflow_runtime.py: ActionDispatcher, ConditionEvaluator
    - tests/config_system/test_workflow_executor.py: 15 comprehensive tests
  modified:
    - core/workflow_schema.py: Added retry and condition fields to WorkflowStep
---

# Phase 02 Plan 02: Workflow Executor and Runtime Summary

**One-liner:** Deterministic workflow execution engine with action dispatch, condition-based branching, and loop safety guards.

---

## What Was Built

### WorkflowExecutor (`core/workflow_executor.py`)
Main execution engine for compiled workflows:
- **Explicit cursor-based step progression**: Steps follow explicit `next` links, not implicit ordering
- **Per-step retry policy**: Configurable `retry` field (0 = no retries, N = N retry attempts)
- **Loop safety guard**: Hard cap at 1000 steps prevents infinite loops
- **Stop-on-failure default**: Execution halts on first error unless retry configured
- **ExecutionResult**: Returns success status, steps executed, final step, error, and duration

### ActionDispatcher (`core/workflow_runtime.py`)
Dispatches workflow actions to hardware controller:
- **click**: Absolute coordinates or ROI-relative (calculates absolute from ROI origin)
- **wait**: Millisecond duration converted to seconds for controller
- **press**: Key name passthrough to controller
- **scroll**: Direction and ticks passthrough

### ConditionEvaluator (`core/workflow_runtime.py`)
Evaluates image conditions for branching:
- Uses existing `VisionEngine.find_element()` for detection
- Supports ROI, threshold, and template path configuration
- Auto-captures screenshot if none provided
- Returns boolean for `on_true`/`on_false` routing

### Schema Extensions (`core/workflow_schema.py`)
Added to `WorkflowStep`:
- `retry: int = 0` - Number of retry attempts on failure
- `condition: Optional[dict]` - Condition configuration for branching

---

## Test Coverage

15 new tests covering:
- **Traversal**: Step sequence follows explicit links, terminal step termination
- **Failure handling**: Default stop-on-failure, retry override allows retries
- **Action dispatch**: All 4 action types with parameter normalization
- **Condition evaluation**: True/false routing, vision engine integration
- **Loop safety**: Guard triggers on excessive iterations, allows reasonable loops

---

## Execution Flow

```
WorkflowConfig (YAML)
    ↓
WorkflowSchema validation (Pydantic)
    ↓
compile_workflow() - semantic validation
    ↓
WorkflowExecutor.execute()
    ├── ActionDispatcher.dispatch(step)
    │   ├── click: controller.click(abs_x, abs_y)
    │   ├── wait: controller.wait(seconds)
    │   ├── press: controller.press(key_name)
    │   └── scroll: controller.scroll(direction, ticks)
    ├── ConditionEvaluator.evaluate(step)
    │   └── vision.find_element(screenshot, template, roi, threshold)
    └── _resolve_next_step() → next step ID or None
```

---

## Integration Points

| Component | Uses | Via |
|-----------|------|-----|
| WorkflowExecutor | CompiledWorkflow | step_index lookup |
| ActionDispatcher | Controller | click/wait/press/scroll methods |
| ConditionEvaluator | VisionEngine | find_element() method |

---

## Deviations from Plan

None - plan executed exactly as written.

---

## Auth Gates

None encountered.

---

## Self-Check: PASSED

- [x] `core/workflow_executor.py` exists and exports WorkflowExecutor
- [x] `core/workflow_runtime.py` exists and exports ActionDispatcher, ConditionEvaluator
- [x] `tests/config_system/test_workflow_executor.py` exists with 15 tests
- [x] All 87 tests pass (38 config system + 49 character detection)
- [x] Commit a2fab28: feat(02-02): implement workflow executor and runtime adapters

---

*Summary created: 2026-03-07*
*Plan 02-02 complete*
