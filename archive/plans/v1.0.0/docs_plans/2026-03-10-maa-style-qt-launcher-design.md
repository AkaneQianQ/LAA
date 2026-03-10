# MAA-Style Qt Launcher Design

**Date:** 2026-03-10

## Goal

Rebuild the current FerrumBot desktop launcher UI with `PySide6` so it visually matches the local MAA client as closely as practical, while preserving the existing Python task/service layer and launcher settings behavior.

## Primary Reference

- Local installed MAA client: `E:\MAA`
- Existing FerrumBot launcher entry: `gui_launcher.py`
- Existing launcher service modules: `launcher/service.py`, `launcher/settings.py`, `launcher/trigger_service.py`

The local MAA installation is the primary fidelity source for icons, spacing, colors, window structure, and runtime behavior. The screenshot supplied by the user remains the acceptance reference for the main window composition.

## Constraints

- GUI stack changes from `tkinter + ttkbootstrap` to `PySide6`
- Existing task execution and controller probing logic must be reused instead of rewritten
- Existing persistent settings file under `data/ui_settings.json` must remain compatible
- Current repository worktree is dirty, so this work must stay isolated to launcher/UI files and must not assume a clean commit baseline
- The first deliverable must be fully usable, not just a static mockup

## Non-Goals

- Rewriting automation workflows, pipelines, or controller internals
- Recreating every MAA feature outside the current FerrumBot launcher scope
- Adding network-backed announcement systems in the first pass
- Chasing animation parity before core layout and behavior parity

## Chosen Approach

1. Introduce a new `PySide6` launcher package dedicated to UI composition and theming
2. Preserve the existing launcher business layer and call it through a Qt-friendly bridge
3. Use a centralized theme system backed by QSS, shared color tokens, and bundled assets
4. Reconstruct the window as a custom-framed dark desktop shell modeled after the MAA client
5. Deliver the main launcher workflow first, then refine parity details against the local `E:\MAA` installation

## Why This Approach

- `PySide6` gives enough control over painting, layout, iconography, hover states, and typography to get close to the target MAA desktop look
- FerrumBot already has working service code for task execution, probing, and settings, so GUI replacement should not duplicate that logic
- A strict UI/business split reduces migration risk and keeps future style iterations local to the Qt layer

## Architecture

### UI Layer

Create a new package:

- `gui_qt/main.py`
- `gui_qt/window.py`
- `gui_qt/titlebar.py`
- `gui_qt/views/`
- `gui_qt/widgets/`
- `gui_qt/theme/`
- `gui_qt/adapters/`

Responsibilities:

- window/frame composition
- tab navigation
- task/config widgets
- status rendering
- theme loading
- icon/font loading
- forwarding user actions into the service bridge

### Service Bridge Layer

Create a Qt-aware bridge module that adapts the existing launcher services to `QObject` signals and worker threads.

Responsibilities:

- read/write launcher settings
- probe controller connectivity
- run selected tasks in background threads
- run/stop the trigger service
- stream log messages back to the UI
- expose runtime state changes without leaking Qt into the existing launcher service modules

### Preserved Business Layer

Reuse as-is wherever possible:

- `launcher/service.py`
- `launcher/settings.py`
- `launcher/trigger_service.py`
- `assets/interface.json`
- task execution through `agent.py_service.main`

## Window and Layout Design

### Main Shell

- custom title bar with application title and window controls
- top navigation tabs styled to match the MAA client
- three-zone body:
  - left task rail
  - center configuration/content area
  - optional top-right runtime/status strip within the content header

### Main Tab

Target visual features:

- dark neutral background
- low-contrast card separation
- thin borders
- bright blue selected states
- compact, high-density spacing
- white/gray typography hierarchy

Sections:

- left task card with checkable task rows, small gear buttons, and bottom action controls
- central checklist/config panel matching the MAA visual rhythm
- secondary button group for normal/advanced settings
- lower descriptive text block
- small runtime information strip at the top-right

### Trigger Tab

Reuse the business functionality of the current trigger page, but restyle it into the same MAA visual system:

- matching title typography
- outlined buttons
- dark content panels
- consistent spacing and border treatment

### Logs Tab

Keep the log feed behavior but present it inside the same visual shell:

- framed dark console panel
- matching typography and scrollbars
- toolbar/action area consistent with the rest of the launcher

## Fidelity Strategy

### First-Pass Parity

The first pass must match:

- overall composition
- panel proportions
- tab sizing and selected indicator
- button treatments
- checkbox visuals
- title bar look
- core typography hierarchy
- palette and contrast

### Second-Pass Refinement

After the functional UI is running, refine:

- icon exactness
- spacing calibration
- hover/pressed polish
- micro-alignment against the local MAA window
- optional subtle transitions where they materially improve parity

## Asset Strategy

Primary source: `E:\MAA`

Candidate asset categories:

- application/window icons
- settings/refresh/gear icons
- button and checkbox SVG/PNG resources when reusable
- fonts if locally bundled and legally usable within the project context

Implementation rules:

- prefer local reusable assets from `E:\MAA` where they directly improve parity
- if an exact asset is unsuitable, create a close in-project substitute rather than forcing a bad fit
- keep launcher assets under a dedicated project folder so the Qt UI does not depend on the external `E:\MAA` path at runtime

## Data Flow

1. Qt launcher starts
2. Theme and bundled assets load
3. Existing settings are loaded from `data/ui_settings.json`
4. UI populates from settings and known task metadata
5. User starts detection, a task queue, or the trigger service
6. Bridge spawns worker execution using existing launcher services
7. Worker emits log and status updates to the UI
8. UI reflects running/busy/idle/error states without blocking the main event loop

## Error Handling

- missing `PySide6` should fail clearly during startup or packaging
- missing launcher assets should fall back to in-project defaults, not crash the window
- background worker exceptions must surface in the runtime state and log view
- the UI must continue to block conflicting actions while a task or trigger run is active
- if an MAA-derived asset cannot be loaded, the launcher should degrade gracefully with a local fallback

## Testing Strategy

- preserve and extend launcher tests around settings, controller resolution, busy-state logic, and bridge behavior
- add focused tests for any non-visual Qt adapter logic that can be exercised headlessly
- perform manual visual verification against the local `E:\MAA` client for parity-sensitive elements
- keep visual tuning separate from business behavior verification

## Delivery Plan

### Phase 1

- add `PySide6`
- build the new launcher shell
- connect settings, runtime state, logs, and task execution
- preserve current launcher feature coverage

### Phase 2

- tune layout and spacing against `E:\MAA`
- import/select final icon assets
- refine title bar, tabs, buttons, and checkbox styles

### Phase 3

- polish trigger/log views
- package the Qt launcher
- verify startup from the bundled distribution

## Acceptance Criteria

- launcher runs through `PySide6` without regressing current task/trigger functionality
- users can still detect the controller, start tasks, stop trigger mode, and view logs
- the main window is visually close to the provided MAA reference, especially in tabs, left task panel, and control styling
- settings persistence remains compatible with the existing JSON file
- the UI is clearly a new MAA-style launcher, not a recolored `ttkbootstrap` window

## Notes

- Because the repository is already dirty, this design deliberately avoids broad refactors outside launcher/UI boundaries
- The current `tkinter` launcher should remain available until the Qt launcher is verified, then it can be retired or reduced to a compatibility shim
