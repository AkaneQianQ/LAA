# Desktop Launcher Product Design

**Date:** 2026-03-10

## Goal

Upgrade the launcher into a product-like desktop application that hides the terminal window, supports editable COM ports per driver backend, and performs automatic/manual connection checks using the selected driver.

## Scope

- Keep the current single-window launcher shape
- Add product-level visual structure and status presentation
- Persist both backend choice and backend-specific COM ports
- Detect connectivity on startup, on driver switch, and on explicit user request
- Use `handshake()` as the success criterion
- Run packaged app without a visible console window

## Chosen Approach

1. Keep `ttkbootstrap` and redesign the launcher into distinct cards:
   - header
   - driver card
   - task card
   - status summary
   - log panel
2. Store launcher settings as:
   - `driver_backend`
   - `ports.ferrum`
   - `ports.makcu`
3. Add a launcher-side hardware probe helper that:
   - resolves the selected controller
   - clones that controller config
   - overrides the serial port with the user-entered COM value
   - constructs the controller
   - checks `is_connected()` and `handshake()`
   - closes the controller
4. Extend task execution so launcher-selected COM port is used for runtime, without mutating `assets/interface.json`
5. Build the executable with PyInstaller windowed mode to suppress the terminal

## UI Layout

- Header row:
  - app title
  - concise subtitle
  - small environment badge
- Main top row split:
  - left card: driver configuration
    - Ferrum / Makcu segmented radio group
    - COM input
    - detect button on the right
    - status pill under the inputs
  - right card: task launch
    - account indexing button
    - full auto donation button
    - short descriptions
- Lower row:
  - compact runtime summary
  - read-only log panel

## Detection Rules

- Launcher startup:
  - load saved backend and port
  - auto-run detection once
- Backend switch:
  - save the backend
  - load that backend's saved COM value
  - auto-run detection
- Manual COM edit:
  - value is saved on change/focus-out
  - user presses detect button to validate immediately
- Success state:
  - only `handshake()` success shows connected

## Runtime Rules

- While a task is running:
  - disable backend switch
  - disable COM input
  - disable detect button
  - disable task buttons
- Detection should also be prevented during active task execution
- Detection failure should not block task start, but the UI must show clear failure state

## Packaging

- Switch PyInstaller build to a windowed executable
- Keep one-folder distribution under `dist/FerrumBot/`
- Preserve assets, agent package, and data directory in bundle output

## Testing

- Settings tests for per-backend ports
- Service tests for controller-config override and connection probing
- Runner tests for detection completion callbacks
- Packaging smoke test should validate spec/build files still exist
