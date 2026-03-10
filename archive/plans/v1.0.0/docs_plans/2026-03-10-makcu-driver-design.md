# MAKCU Driver Design

**Date:** 2026-03-10

## Goal

Add a new MAKCU-based hardware driver without changing the existing Ferrum driver contract, and let users switch controller backends through configuration.

## Scope

- Keep `agent/py_service/pkg/ferrum/controller.py` intact as the existing backend.
- Add `agent/py_service/pkg/makcu/controller.py` with a `MakcuController` class that matches the operational surface used by the workflow runtime.
- Extend initialization logic so `interface.json` can declare which driver to instantiate.
- Add unit tests for MAKCU command formatting, response parsing, absolute-move conversion, and controller selection.

## Chosen Approach

1. Add a dedicated `pkg/makcu` package rather than folding MAKCU logic into the Ferrum package.
2. Mirror the practical interface already consumed by the codebase:
   `wait`, `is_connected`, `handshake`, `move_absolute`, `click`, `click_current`, `move_and_click`, `click_right`, `scroll`, `press`, `key_down`, `key_up`, `close`.
3. Use MAKCU string-key commands for keyboard input where possible instead of duplicating Ferrum HID-code behavior.
4. Select backend from controller config using a new `driver` field, defaulting to `"ferrum"` for compatibility.

## Error Handling

- Preserve serial validation and retry semantics similar to the existing controller.
- Parse prompt-terminated responses defensively.
- Keep `move_absolute` dependent on `win32api.GetCursorPos()` because the workflow code expects absolute target coordinates.

## Testing

- Mock serial I/O to verify command strings and prompt parsing.
- Mock `win32api.GetCursorPos()` to verify `move_absolute` and `move_and_click`.
- Cover `initialize()` backend selection with a fake controller class via monkeypatch.

## Notes

The worktree is already dirty with unrelated changes, so this design doc is added without attempting an isolated design-only commit.
