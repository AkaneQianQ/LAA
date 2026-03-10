# AGENTS.md

This file defines repository-specific rules for Codex and compatible coding agents.

## Mandatory Rule

Before implementing any new feature, API, module, or behavior change, you MUST read `API_REFERENCE.md` first and verify:
1. Whether the capability already exists (avoid duplicate implementations)
2. Whether existing APIs can be reused or extended
3. Whether naming and interface conventions remain consistent

If a planned API overlaps with existing capability, prefer reuse/extension over new duplicate code.

## Project Overview

- Project: FerrumBot (Lost Ark KR guild donation automation)
- Architecture: MaaFramework-style Pipeline JSON + Python Agent Service
- Resolution: `2560x1440` only (locked)
- Input: KMBox serial device (`COM2`, `115200`)

## Runbook

```bash
python gui_launcher.py
python -m agent.py_service.main --task GuildDonation
python -m agent.py_service.main --list-tasks
python tools/convert_yaml_to_pipeline.py assets/tasks/guild_donation.yaml
python -m pytest tests/ -v
```

## Architecture Constraints

- Pipelines are declarative JSON under `assets/resource/pipeline/*.json`
- Custom recognizers/actions MUST be registered in module `register.py`
- New feature modules MUST include `register.py`
- `assets/interface.json` is the source of task/controller/resource wiring

## Pipeline Rules

- Public node names: `PascalCase` (e.g. `DonationMain`)
- Private node names: `_PascalCase` (e.g. `_OpenMenu`)
- Error node names: `*Err` or `*Error`
- Prefer explicit `roi`; full-screen template match is prohibited
- Avoid hardcoded delays; use pipeline wait mechanisms
- Provide `on_error` handling for recognition/timeout paths
- Add focus messages when user-facing progress/failure context is useful

## Module Rules

When adding a module under `agent/py_service/modules/{name}`:
1. Create `__init__.py` and `register.py`
2. Register recognizers/actions via decorators from `agent.py_service.register`
3. Add/extend corresponding pipeline JSON
4. Update `assets/interface.json` task entries if needed

## Code Style

- Python file header (shebang + UTF-8) is required in new Python files
- Naming:
  - Classes: `PascalCase`
  - Functions/variables: `snake_case`
  - Constants: `UPPER_CASE`
  - Recognizers/actions: `PascalCase`
- Logs use ASCII bracket prefixes only, e.g. `[OK]`, `[ERROR]`, `[Vision]`, `[Pipeline]`
- Keep imports consistent with repository conventions

## ROI and Resolution (Critical)

- Supported resolution is fixed at `2560x1440`
- Full-screen matching is disallowed
- Character slot ROIs are fixed and must not be changed without explicit migration:
  - `(904,557,1152,624)`, `(1164,557,1412,624)`, `(1425,557,1673,624)`
  - `(904,674,1152,741)`, `(1164,674,1412,741)`, `(1425,674,1673,741)`
  - `(904,791,1152,858)`, `(1164,791,1412,858)`, `(1425,791,1673,858)`

## Error Handling

- Pipeline nodes with timeout/recognition logic should define explicit recovery branches
- Non-critical Python failures may fallback silently only when safe
- Long-running loops should support cancellation checks (`stop_event` pattern)

## Testing Expectations

- Pipeline tests live under `tests/{feature}/test_*.json`
- Unit tests should verify recognizers/actions with representative screenshots/mocks
- Prefer targeted regression tests when modifying existing behavior

## Migration / Compatibility

- Prefer new structure under `agent/py_service/pkg/*` and `agent/py_service/modules/*`
- Legacy compatibility imports may exist but should not drive new design

## Dependencies (Key)

- `opencv-python`, `dxcam`, `pyyaml`, `pyserial`, `keyboard`, `numpy`

## References

- Required first read: `API_REFERENCE.md`
- MaaFramework docs: https://maafw.com/
- Planning references:
  - `.planning/MAA_REFACTOR_GUIDE.md`
  - `.planning/REFACTOR_EXAMPLES.md`
  - `.planning/QUICK_REFERENCE.md`

## Agent Behavior in This Repo

- Treat this `AGENTS.md` as repo policy for implementation decisions
- Do not introduce duplicate APIs or parallel abstraction layers without necessity
- Keep changes minimal, composable, and consistent with existing Maa-style workflow design
