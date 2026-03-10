# Desktop Launcher Design

**Date:** 2026-03-10

## Goal

Add a minimal Windows desktop launcher for FerrumBot that lets users:

- choose the hardware driver backend (`Ferrum` or `Makcu`) and keep that choice across launches
- start `AccountIndexing`
- start the existing full automation flow via `CharacterSwitch`
- run the app from an unpacked folder that already contains all required Python libraries

## Scope

- Reuse existing task and controller definitions from `assets/interface.json`
- Reuse the existing Python service initialization and pipeline execution stack
- Add a standalone launcher entry point instead of changing task YAML behavior
- Add a persistent UI settings file under `data/`
- Add packaging scripts/config so the project can be bundled into a self-contained folder

## Chosen Approach

1. Build the launcher with `ttkbootstrap` on top of `tkinter`
2. Keep the UI intentionally small:
   - driver selection area
   - task buttons
   - runtime status
   - scrolling log output
3. Extend the service layer so a caller can explicitly choose the controller declared in `assets/interface.json`
4. Execute tasks in a worker thread so the UI stays responsive
5. Package with PyInstaller in `--onedir` mode so the output is a folder containing the executable, Python runtime, and dependent libraries

## Why This Approach

- `ttkbootstrap` keeps Windows compatibility close to standard `tkinter`, which is better for "extract and run" delivery than heavier UI stacks
- the service layer already knows how to load controllers, resources, tasks, and pipelines, so the launcher should delegate instead of duplicating workflow logic
- `--onedir` packaging maps directly to the user requirement: a folder with everything included

## UI Structure

- Header:
  - project title
  - current config path
- Driver card:
  - radio buttons for `Ferrum` and `Makcu`
  - saved automatically when changed
- Task card:
  - `账号读取` button -> `AccountIndexing`
  - `全自动捐献` button -> `CharacterSwitch`
- Status card:
  - selected driver
  - idle/running state
  - active task name
- Log card:
  - append stdout/stderr lines from the worker execution

## Data Flow

1. Launcher starts and loads `assets/interface.json`
2. Launcher loads `data/ui_settings.json`
3. Saved driver choice is mapped to a concrete controller name from `interface.json`
4. User clicks a task button
5. Launcher starts a background worker
6. Worker initializes service components with the selected controller
7. Worker runs the requested pipeline task
8. Worker streams logs back to the UI
9. UI re-enables controls when the run finishes

## Persistence

Settings file:

- path: `data/ui_settings.json`
- keys:
  - `driver_backend`: `ferrum` or `makcu`

If the file is missing or invalid, default to `ferrum`.

## Packaging

- Add launcher dependency declarations for `ttkbootstrap`
- Add a PyInstaller spec or build script
- Produce a distributable folder under `dist/FerrumBot/`
- Ensure the folder includes:
  - executable
  - third-party libraries
  - required project assets
  - default `data/` scaffolding where needed

## Error Handling

- Missing `ttkbootstrap` should surface during packaging/test, not silently fail at runtime
- Missing or mismatched controller definitions in `interface.json` should show a visible launcher error
- Runtime failures should be written to the log panel and reflected in the status bar
- The launcher must prevent starting a second task while one is already running

## Testing

- Unit tests for settings persistence
- Unit tests for driver-backend to controller-name resolution
- Unit tests for task-runner plumbing with mocked service execution
- Smoke verification for packaging script generation

## Notes

The repository is already dirty. This design keeps GUI-related work isolated and avoids overwriting unrelated user changes.
