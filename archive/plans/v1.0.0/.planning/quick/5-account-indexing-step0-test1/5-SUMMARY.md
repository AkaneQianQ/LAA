---
phase: quick
plan: 5
name: account-indexing-step0-test1
type: execute
subsystem: testing
status: completed
started_at: "2026-03-08T06:00:00Z"
completed_at: "2026-03-08T06:15:00Z"
duration_minutes: 15
tasks_completed: 1
tasks_total: 1
files_created:
  - tests/test1_account_indexing_step0.py
artifacts:
  - path: tests/test1_account_indexing_step0.py
    lines: 699
    description: Step0 account indexing test script with auto/manual modes
dependencies:
  requires:
    - core/perceptual_hash.py
    - modules/character_detector.py
  provides:
    - tests/test1_account_indexing_step0.py
tech_stack:
  patterns:
    - pytest-style test functions
    - argparse for CLI modes
    - dxcam/PIL for screenshot capture
    - tempfile for isolated test databases
key_decisions: []
---

# Phase Quick Plan 5: Account Indexing Step0 Test1 Summary

## One-Liner
Created comprehensive test script for account indexing Step0 workflow with automatic cache cleanup, mock/live screenshot modes, and visual hash comparison testing.

## What Was Built

### Test Script: tests/test1_account_indexing_step0.py (699 lines)

A complete test suite for validating the Step0 logic tree:

1. **Output Directory Management** (`clean_output_dir()`)
   - Automatically cleans `tests/output/test1/` on each run
   - Deletes all `.png` files from previous runs
   - Creates directory if it doesn't exist

2. **Step0 Workflow Implementation**
   - `step0_open_esc_menu()`: Simulates ESC menu open, saves full screenshot
   - `step1_wait_after_esc()`: Waits 200ms for UI stabilization
   - `step2_capture_account_tag()`: Captures ROI (666, 793, 772, 902), computes pHash
   - `step3_match_or_create_account()`: Matches against database or detects new account

3. **Test Functions**
   - `test_capture_roi()`: Validates ROI extraction dimensions and content
   - `test_perceptual_hash()`: Tests hash computation consistency and comparison
   - `test_account_matching()`: Tests account matching with mock database
   - `test_output_directory()`: Tests cache cleanup functionality

4. **Execution Modes**
   - `--auto` (default): Uses mock screenshots for automated testing
   - `--manual`: Uses live dxcam screen capture for real-world testing
   - `--clean`: Only cleans output directory

## Key Features

- **Chinese Output**: All messages use Chinese with `[测试] [信息] [错误] [完成]` prefixes
- **Windows Console Fix**: UTF-8 encoding fix for Chinese output
- **Screenshot Saving**: Each step saves descriptive PNG files to output directory
- **Database Integration**: Uses `core/database.py` and `core/perceptual_hash.py`
- **Mock/Live Dual Mode**: Supports both automated CI testing and manual screen testing

## File Structure

```
tests/
├── test1_account_indexing_step0.py    # Main test script (699 lines)
└── output/test1/                       # Screenshot output directory
    ├── step0_full_screen.png          # Full screenshot after ESC
    ├── step2_account_tag.png          # ROI extraction result
    └── step3_comparison_*.png         # Comparison screenshots
```

## Usage

```bash
# Run automated tests with mock screenshots
python tests/test1_account_indexing_step0.py --auto

# Run manual test with live screen capture
python tests/test1_account_indexing_step0.py --manual

# Clean output directory only
python tests/test1_account_indexing_step0.py --clean
```

## Verification

- [x] Script exists at `tests/test1_account_indexing_step0.py`
- [x] Script has 699 lines (exceeds 150 minimum)
- [x] `clean_output_dir()` function implemented
- [x] All 4 Step0 workflow steps implemented
- [x] Screenshot saving to `tests/output/test1/` directory
- [x] Chinese output messages throughout
- [x] Supports both `--auto` and `--manual` modes
- [x] All required functions present and verified

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| 2407a9c | test(quick-5): add Step0 account indexing test script with auto/manual modes |

## Self-Check: PASSED

- [x] File `tests/test1_account_indexing_step0.py` exists
- [x] Commit `2407a9c` exists in git log
- [x] All required functions verified via AST parsing
- [x] Line count verified (699 lines)
