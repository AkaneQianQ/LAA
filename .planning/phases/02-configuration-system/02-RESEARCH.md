# Phase 2: Configuration System - Research

**Researched:** 2026-03-07
**Domain:** Python workflow configuration loading, schema validation, and deterministic step orchestration
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
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

### Deferred Ideas (OUT OF SCOPE)
- Extending condition sources beyond image detection (for example OCR/variable-expression logic) can be evaluated as a future phase if needed.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CFG-01 | System loads task definitions from YAML configuration files | Use PyYAML `safe_load` + strict model validation pipeline (parse -> validate -> compile). |
| CFG-02 | System executes multi-step workflows defined in configuration | Use explicit step graph + runtime executor with deterministic next-step resolution. |
| CFG-03 | Configuration supports click, wait, press, and scroll actions | Use discriminated action schema with typed parameter models per action kind. |
| CFG-04 | Configuration supports conditional logic based on image detection | Use condition nodes that call `VisionEngine.find_element(...)` and branch via `on_true`/`on_false`. |
</phase_requirements>

## Summary

Phase 2 should be planned as a strict three-stage pipeline: (1) load YAML safely, (2) validate/normalize into strongly typed workflow objects, and (3) execute with a small deterministic state machine. This aligns with locked decisions (strict startup validation, explicit next links, conditional branching/loops) and avoids mixing parsing concerns with runtime control logic.

For this codebase, plan to integrate at the orchestration boundary in `gui_launcher.py` while reusing existing runtime primitives in `core/vision_engine.py` and existing Ferrum interaction pathways. The configuration layer should define *what* to do; adapters should translate each action to existing control/vision calls.

**Primary recommendation:** Use `PyYAML + Pydantic v2 + registry-based step executor` with fail-fast config compilation before any automation starts.

## Project Context Notes

- `CLAUDE.md` not found in repository root.
- `.claude/skills/` and `.agents/skills/` not present in this repo; no project-local skill rules to incorporate.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyYAML | 6.x | YAML parsing | Mature Python YAML parser; supports safe parsing (`safe_load`) and C-backed loaders when available. |
| Pydantic | 2.x | Strict schema validation + typed models | Strong validation errors, typed coercion control, discriminated union support for action variants. |
| Python stdlib (`typing`, `dataclasses`/models, `pathlib`) | 3.13 | Runtime data structures and file handling | Already aligned with project baseline and keeps runtime dependencies low. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.x (already present in cache/tests) | Config/executor unit tests | Use for schema validation, branching, retry, loop control, and regression tests. |
| jsonschema (optional) | 4.26.x | External JSON Schema validation/export | Only if you need machine-readable schema distribution beyond Python runtime validation. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pydantic models | jsonschema-only validation | Better cross-language schema portability, but weaker direct Python typing ergonomics for executor code. |
| PyYAML | ruamel.yaml | Better YAML round-trip editing, but higher complexity and unnecessary for load-only execution config. |

**Installation:**
```bash
pip install pyyaml pydantic
```

## Architecture Patterns

### Recommended Project Structure
```text
core/
  config_loader.py        # file reading + YAML parse + top-level load API
  workflow_schema.py      # pydantic models for workflow/steps/actions/conditions
  workflow_compiler.py    # semantic validation: step refs, branch refs, loop safety checks
  workflow_executor.py    # runtime executor/state machine
```

### Pattern 1: Parse -> Validate -> Compile -> Execute
**What:** Separate concerns into sequential stages with explicit outputs.
**When to use:** Always for workflow startup.
**Example:**
```python
# Source: https://pyyaml.org/wiki/PyYAMLDocumentation
# Source: https://docs.pydantic.dev/latest/concepts/models/
raw = yaml.safe_load(config_text)
workflow = WorkflowConfig.model_validate(raw)
compiled = compile_workflow(workflow)  # checks refs/branch targets/retry bounds
executor = WorkflowExecutor(compiled, vision_engine, input_adapter)
executor.run()
```

### Pattern 2: Discriminated Action Models
**What:** Model `click|wait|press|scroll` with explicit action type + dedicated fields.
**When to use:** For CFG-03 and strict startup validation.
**Example:**
```python
# Source: https://docs.pydantic.dev/latest/concepts/unions/
class ClickAction(BaseModel):
    type: Literal["click"]
    x: int
    y: int
    roi: tuple[int, int, int, int] | None = None

class WaitAction(BaseModel):
    type: Literal["wait"]
    duration_ms: int

Action = Annotated[ClickAction | WaitAction | PressAction | ScrollAction, Field(discriminator="type")]
```

### Pattern 3: Explicit Next-Link State Machine
**What:** Every step has `step_id`, action payload, and next routing metadata.
**When to use:** CFG-02 and CFG-04 execution semantics.
**Example:**
```python
current = workflow.start_step_id
while current is not None:
    step = steps[current]
    result = execute_step(step)
    current = resolve_next(step, result)  # default_next / on_true / on_false / retry/stop
```

### Anti-Patterns to Avoid
- **Implicit fall-through by file order:** breaks determinism; always resolve via explicit next links.
- **Validation during execution only:** violates strict startup validation decision.
- **Action handlers importing parser internals:** creates coupling and fragile evolution.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing | Custom parser/string splitter | PyYAML `safe_load` | YAML edge cases are subtle and security-sensitive. |
| Structural validation | Manual nested `if` checks for each field | Pydantic model validation | Better error reporting and maintainability. |
| Image condition primitive | New template match engine | `core/vision_engine.py` (`find_element`) | Reuses tested behavior and thresholds from Phase 1 base. |

**Key insight:** Hand-rolled parsing/validation increases silent misconfiguration risk; this phase needs deterministic fail-fast behavior.

## Common Pitfalls

### Pitfall 1: Unsafe YAML Load
**What goes wrong:** Runtime can execute unintended constructors with unsafe loaders.
**Why it happens:** Using `yaml.load` on untrusted/user-edited files.
**How to avoid:** Use `yaml.safe_load` only.
**Warning signs:** Loader code uses `yaml.load(...)` without `SafeLoader`.

### Pitfall 2: Dangling Step References
**What goes wrong:** Runtime fails mid-flow because `next`/branch step IDs do not exist.
**Why it happens:** No compile-time graph validation.
**How to avoid:** Compile pass must verify all referenced step IDs exist.
**Warning signs:** KeyError-like failures when resolving next step.

### Pitfall 3: Infinite Conditional Loops
**What goes wrong:** Workflow never exits due to looping branch conditions.
**Why it happens:** Loops are allowed but unbounded.
**How to avoid:** Add loop guard (`max_iterations` or per-step execution cap) in executor.
**Warning signs:** Repeated same step IDs beyond expected limits.

### Pitfall 4: Ambiguous Coordinate Semantics
**What goes wrong:** Clicks land incorrectly when mixing absolute and ROI-relative coordinates.
**Why it happens:** No normalized coordinate contract before dispatch.
**How to avoid:** Normalize into a single canonical absolute coordinate in executor adapter.
**Warning signs:** Action logs show inconsistent final coordinates for same config.

## Code Examples

Verified patterns from official sources:

### Safe YAML + Typed Validation
```python
# Source: https://pyyaml.org/wiki/PyYAMLDocumentation
# Source: https://docs.pydantic.dev/latest/concepts/models/
import yaml
from pydantic import BaseModel

class WorkflowConfig(BaseModel):
    name: str

with open("workflow.yaml", "r", encoding="utf-8") as f:
    raw = yaml.safe_load(f)
cfg = WorkflowConfig.model_validate(raw)
```

### JSON Schema Validator Reuse (Optional)
```python
# Source: https://python-jsonschema.readthedocs.io/en/stable/validate/
from jsonschema import Draft202012Validator

validator = Draft202012Validator(schema)
validator.validate(instance)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Ad-hoc dict parsing with manual checks | Typed model validation (Pydantic v2) | 2023-2025 ecosystem shift | Better error quality and safer config evolution. |
| Hardcoded script order | Config-defined explicit step graphs | Ongoing | Non-developer edits become feasible and auditable. |

**Deprecated/outdated:**
- Treating YAML as trusted code input via permissive loader patterns (`yaml.load`) is not acceptable for user-editable automation config.

## Open Questions

1. **Where should workflow files live for users?**
   - What we know: single-file workflow is required.
   - What's unclear: canonical directory (e.g., `config/workflows/`) and naming convention.
   - Recommendation: lock path convention in planning to prevent launcher ambiguity.

2. **Should Phase 2 accept JSON files in addition to YAML for CFG wording alignment?**
   - What we know: locked decision says YAML-only primary for Phase 2.
   - What's unclear: whether JSON compatibility is required now or deferred.
   - Recommendation: treat JSON as deferred unless user explicitly reopens scope.

3. **How should retries be represented for all action types?**
   - What we know: default stop-on-failure with per-step retry override is locked.
   - What's unclear: exact fields (`max_retries`, `retry_delay_ms`) and defaults.
   - Recommendation: define uniform retry policy object at step level during planning.

## Sources

### Primary (HIGH confidence)
- https://pyyaml.org/wiki/PyYAMLDocumentation - safe loading behavior, loader classes, parser guidance.
- https://docs.pydantic.dev/latest/concepts/models/ - model validation and typed model workflow.
- https://docs.pydantic.dev/latest/concepts/unions/ - discriminated unions for action polymorphism.
- https://python-jsonschema.readthedocs.io/en/stable/validate/ - validator API patterns and draft validators.

### Secondary (MEDIUM confidence)
- Local project code (`core/vision_engine.py`, `gui_launcher.py`, `modules/character_detector.py`) for integration constraints and existing execution patterns.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - strong official docs support; exact version pin selection still project-specific.
- Architecture: MEDIUM - strong fit with locked decisions and existing code boundaries; runtime UX details remain to be decided in planning.
- Pitfalls: HIGH - directly derived from locked constraints plus well-known config/executor failure modes.

**Research date:** 2026-03-07
**Valid until:** 2026-04-06
