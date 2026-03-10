# Lost Ark Window Focus Design

## Goal

When the user starts a task from the Qt launcher, the launcher should try to switch focus to the running Lost Ark game window before starting backend automation.

## Scope

- Only applies to task startup from the main Qt launcher.
- Does not apply to image-trigger mode.
- Uses Windows process name `LOSTARK.exe` as the primary lookup signal.

## Approach

- Add a launcher-level helper in `launcher/service.py` to find a top-level visible window belonging to process `LOSTARK.exe`.
- If a matching window is minimized, restore it first.
- Bring the window to the foreground with standard Win32 calls.
- Call this helper from `gui_qt/adapters/launcher_bridge.py` before `run_selected_task()`.

## Failure Handling

- If no Lost Ark window is found, emit a launcher log entry and continue starting the task.
- If Win32 APIs are unavailable or focus calls fail, emit a launcher log entry and continue starting the task.
- The focus step is best-effort and must not block task execution.

## Testing

- Unit test the service helper with monkeypatched Win32/process APIs.
- Unit test the Qt bridge to verify it attempts focus before executing the task.
