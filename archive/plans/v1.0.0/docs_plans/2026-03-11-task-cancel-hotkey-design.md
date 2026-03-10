# Task Cancel And F10 Hotkey Design

## Goal

Allow the home-page task runner to be interrupted from either the `Link Start!` button or a global `F10` hotkey.

## Scope

- Applies to home-page task execution only.
- While a task is running, `Link Start!` changes to `运行中...`.
- Clicking the same button again requests task cancellation.
- Pressing global `F10` also requests task cancellation.
- Trigger mode behavior is unchanged.

## Approach

- Add a `threading.Event`-based cancellation signal in `LauncherBridge` for task execution.
- Register a global `F10` hotkey in the Qt window using the `keyboard` library, and route it into the same cancellation path as the button.
- Propagate `stop_event` through `run_selected_task()` -> `service_main.run_task()` -> workflow executor context.
- Make pipeline execution cooperative: before each node and during waits, check the stop event and exit cleanly.

## Failure Handling

- If global hotkey registration fails, log it and keep the button-based cancellation path available.
- Cancellation is best-effort and cooperative; the current node is allowed to finish its smallest safe step before exit.
- UI must always return the button text to `Link Start!` after completion or cancellation.

## Testing

- Bridge tests for start/stop requests and task-finished signals.
- Window tests for button text toggling while running.
- Window tests for F10 registration and callback routing.
- Workflow/runtime tests for cooperative cancellation through stop_event.
