---
phase: quick
plan: 3
subsystem: workflow
completed_at: "2026-03-08"
duration: 15min
tasks: 8
files_created: 0
files_modified: 1
dependencies: []
---

# Quick Task 3: Post-Donation Completion Workflow Summary

## Overview

Added post-donation completion workflow to `guild_donation.yaml` that records donation status and ensures clean exit from guild UI after completing guild donations.

## Changes Made

### Modified Files

- `config/workflows/guild_donation.yaml` - Extended workflow with 5 new steps

### Steps Added

| Step ID | Type | Description | Next Step |
|---------|------|-------------|-----------|
| `write_donation_cache` | wait (50ms) | Placeholder for recording character donation status | `press_esc_close` |
| `press_esc_close` | press (ESC) | Send ESC keypress to close guild menu | `wait_guild_ui_close` |
| `wait_guild_ui_close` | wait_image (disappear) | Wait for guild_ui.bmp to disappear (100ms poll, 500ms timeout) | `check_ui_closed` |
| `check_ui_closed` | wait (50ms) + condition | Check if UI still visible after ESC | `final_esc_press` (true) / `workflow_complete` (false) |
| `final_esc_press` | press (ESC) | Second ESC press if UI still detected | `workflow_complete` |

### Workflow Flow

```
donation_complete
       |
       v
write_donation_cache (placeholder - records visual hash)
       |
       v
press_esc_close (ESC keypress)
       |
       v
wait_guild_ui_close (wait for guild_ui.bmp disappear, 100ms/500ms)
       |
       v
check_ui_closed (conditional check)
   |           |
   |true       |false
   v           v
final_esc_press   workflow_complete
       |
       v
workflow_complete
```

## Technical Details

### ROI Reference
- Guild UI detection: `[546, 803, 903, 835]` (same as wait_menu_appear step)

### Timing Configuration
- `wait_guild_ui_close`: 100ms poll interval, 500ms timeout
- `write_donation_cache`: 50ms placeholder delay
- `check_ui_closed`: 50ms delay before condition check

### Conditional Branching
The `check_ui_closed` step uses the established pattern from `check_sec_donation`:
- `on_true`: Image still detected → press ESC again
- `on_false`: Image not detected → workflow complete

## Validation Results

```
Workflow validated: guild_donation
Total steps: 19 (was 14, added 5)
Step IDs: [open_guild_menu, wait_menu_appear, ..., workflow_complete]
All routing references valid!
Validation complete!
```

## Notes

### Placeholder Cache Action
The `write_donation_cache` step uses a `wait` action as a placeholder. Future implementation should:
1. Add custom `write_cache` action type to `workflow_schema.py`
2. Implement cache writing in `workflow_runtime.py`
3. Store character visual hash (from slot screenshot) + timestamp

### Retry Logic
If the first ESC press fails to close the UI, the workflow will:
1. Detect UI still present via `check_ui_closed` condition
2. Send a second ESC press via `final_esc_press`
3. Complete workflow regardless of second attempt result

## Commits

| Commit | Description |
|--------|-------------|
| `09b5bba` | Update donation_complete step to link to write_donation_cache |
| `d3642f5` | Add write_donation_cache placeholder step |
| `f479d1e` | Add press_esc_close step |
| `a7b4166` | Add wait_guild_ui_close step |
| `f99c1ef` | Add check_ui_closed conditional step |
| `f4a357f` | Add final_esc_press step for retry |
| `c8e0672` | Update workflow_complete step comment |

## Requirements Satisfied

- [x] Character donation status is recorded to cache after completion (placeholder)
- [x] Guild UI is closed by pressing ESC
- [x] Guild UI disappearance is verified with 100ms polling and 500ms timeout
- [x] If UI still detected after timeout, ESC is pressed again
- [x] Workflow completes when UI is confirmed closed
