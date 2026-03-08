---
phase: quick
plan: 2
subsystem: character_detection
tags: [roi, account-tag, mouse-move, delayed-capture]
dependency_graph:
  requires: [ferrum-controller, hardware-gateway, database]
  provides: [account-identification, character-caching]
  affects: [character_detector, database, account_manager]
tech_stack:
  added: []
  patterns: [account-tag-roi, delayed-screenshot, mouse-safe-position]
key_files:
  created: []
  modified:
    - modules/character_detector.py
    - core/ferrum_controller.py
    - core/hardware_input_gateway.py
    - core/database.py
    - core/account_manager.py
decisions:
  - ACCOUNT_TAG_ROI = (666, 793, 772, 902) for account identification
  - MOUSE_SAFE_POSITION = (827, 516) to prevent UI color change
  - Delayed first slot capture to avoid UI selection highlight
  - Account directory structure with tag.png and account_info.json
metrics:
  duration: 20 min
  completed_date: "2026-03-08"
---

# Quick Task 2: 修改账号TAG ROI和截图逻辑 Summary

## One-liner
Implemented new account tag ROI (666,793,772,902) with mouse-safe positioning and delayed first-slot screenshot capture to avoid UI color change artifacts.

## What Was Built

### Task 1: Add ACCOUNT_TAG_ROI constant and mouse move support
- Added `ACCOUNT_TAG_ROI = (666, 793, 772, 902)` constant for account tag recognition
- Added `MOUSE_SAFE_POSITION = (827, 516)` constant to prevent UI color change
- Implemented `move_absolute(x, y)` method in `FerrumController` using `win32api.GetCursorPos()`
- Exposed `move_mouse(x, y)` method in `HardwareInputGateway` wrapping `move_absolute()`

### Task 2: Refactor account identification logic
- Added `_move_mouse_to_safe_position()` method to move mouse before screenshot
- Added `_capture_account_tag()` method to extract account tag from ROI
- Added `match_account_tag()` method for comparing account tags
- Refactored `create_or_get_account_index()` to use account tag ROI instead of first character
- Added `tag_screenshot_path` column to `accounts` table
- Added `update_account_tag()` and `get_account_tag_path()` database functions

### Task 3: Implement delayed first-slot screenshot logic
- Added `_pending_first_slot_capture` state tracking in `CharacterDetector`
- Added `capture_first_slot_on_switch()` method for delayed first slot capture
- Added `is_first_slot_capture_pending()` method to check pending state
- Modified `create_or_get_account_index()` to skip slot 0 on first entry (mark as pending)
- Added `capture_pending_first_slot()` to `AccountManager` for integration
- Added `is_first_slot_capture_pending()` to `AccountManager` for checking state

### Task 4: Update account library file structure
- Updated `_ensure_account_directory()` to create new structure:
  ```
  data/accounts/{account_hash}/
    ├── tag.png              # Account tag ROI screenshot
    ├── characters/          # Character screenshots directory
    │   ├── 0.png           # Character 1 screenshot (delayed)
    │   ├── 1.png           # Character 2 screenshot
    │   └── ...
    └── account_info.json   # Account metadata
  ```
- Added `_save_account_info()` to save account metadata (hash, character count, timestamps)
- Added `_load_account_info()` to read account metadata
- Added `_update_account_info()` to update account metadata

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Commit | Message | Files |
|--------|---------|-------|
| 443e389 | feat(quick-2): add ACCOUNT_TAG_ROI constant and mouse move support | character_detector.py, ferrum_controller.py, hardware_input_gateway.py |
| 91545d7 | feat(quick-2): refactor account identification logic with new ROI | character_detector.py, database.py |
| 3f1fd05 | feat(quick-2): implement delayed first-slot screenshot logic | character_detector.py, account_manager.py |
| 4d067c8 | feat(quick-2): update account library file structure | character_detector.py |

## Self-Check: PASSED

- [x] ACCOUNT_TAG_ROI constant defined correctly: (666, 793, 772, 902)
- [x] MOUSE_SAFE_POSITION constant defined correctly: (827, 516)
- [x] move_absolute method implemented in FerrumController
- [x] move_mouse method exposed in HardwareInputGateway
- [x] _move_mouse_to_safe_position method implemented
- [x] _capture_account_tag method implemented
- [x] match_account_tag method implemented
- [x] create_or_get_account_index logic refactored
- [x] Database schema updated with tag_screenshot_path
- [x] _pending_first_slot_capture state added
- [x] capture_first_slot_on_switch method implemented
- [x] AccountManager integrated with delayed screenshot logic
- [x] Directory structure updated with tag.png and account_info.json
- [x] All files pass syntax check

## Technical Notes

### Mouse Movement Implementation
The `move_absolute` method uses `win32api.GetCursorPos()` to get the current cursor position, then calculates the relative displacement (`dx = target_x - current_x`, `dy = target_y - current_y`) and sends it via `km.move(dx, dy)`. This ensures compatibility with the Ferrum device's relative coordinate protocol.

### Delayed First Slot Capture
When first entering the character selection screen, slot 0 is typically selected (highlighted), which changes its visual appearance. By delaying the screenshot capture until switching to the second character, we capture a clean, unhighlighted version of the first character.

### Account Tag ROI
The new ROI (666, 793, 772, 902) captures a specific region of the UI that uniquely identifies the account without being affected by character selection state changes.
