# Phase 2: Configuration System - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a YAML/JSON-driven workflow configuration system so automation logic can be changed through config files instead of Python code edits.

</domain>

<decisions>
## Implementation Decisions

### Configuration File Structure
- Use **YAML only** as the primary configuration format for Phase 2.
- Use **single file per workflow** layout.
- Require explicit `step_id` for every step.
- Apply **strict startup validation**; invalid config blocks execution.

### Execution and Branching Semantics
- Use **explicit next links + conditional branching** model.
- Default failure behavior is **stop on failure**, with per-step retry override.
- Conditions in Phase 2 are based on **image detection results**.
- Support **conditional loops** in workflow control.

### Action Parameter Standard
- `click` supports **absolute coordinates** and optional ROI-relative coordinates.
- `wait` uses **milliseconds integer** as the single time unit.
- `press` uses readable `key_name`, mapped to HID internally by engine.
- `scroll` uses semantic fields: `direction` + `ticks`.

### Claude's Discretion
- Exact schema naming (field names and nesting style) as long as it follows the locked decisions above.
- Internal executor architecture and parser organization.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/vision_engine.py`: existing image matching capability can power config conditions.
- `modules/` task modules: existing procedural workflows provide reference behavior for config migration.
- `core/database.py` and JSON persistence style: existing pattern for local config/state file usage.

### Established Patterns
- Python 3.13 project structure with `core/` + `modules/`.
- Print-based operational logs and direct action sequencing.
- Coordinate-driven automation logic already established in current scripts.

### Integration Points
- New config loader/executor should connect where task orchestration currently starts (`gui_launcher.py` / runtime task entry flow).
- Action execution should reuse current Ferrum control and vision detection interfaces rather than re-implementing hardware logic.

</code_context>

<specifics>
## Specific Ideas

- Keep configuration user-editable and readable for guild donation automation maintenance.
- Ensure config semantics can represent existing click/wait/press/scroll behavior directly.

</specifics>

<deferred>
## Deferred Ideas

- Extending condition sources beyond image detection (for example OCR/variable-expression logic) can be evaluated as a future phase if needed.

</deferred>

---

*Phase: 02-configuration-system*
*Context gathered: 2026-03-07*
