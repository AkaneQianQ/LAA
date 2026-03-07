---
phase: 01-character-detection-core
plan: 01
type: execute
subsystem: detection-core
tags: [contracts, schema, tdd, foundation]
requires: []
provides: [CHAR-01, CHAR-02]
affects: [01-02-PLAN.md, 01-03-PLAN.md]
tech-stack:
  added: [opencv-python, numpy, pytest]
  patterns: [repository-pattern, typed-contracts, immutable-config]
key-files:
  created:
    - modules/character_detector.py
    - core/database.py
    - tests/character_detection/test_detector_contracts.py
  modified: []
decisions:
  - "ROI constants locked to 2560x1440 coordinates per phase context"
  - "TM_CCOEFF_NORMED matching method enforced (no reopening)"
  - "Slot threshold fixed at >=0.8 with 3 retry attempts"
  - "SQLite schema uses upsert pattern for character metadata"
  - "FF00FF masking implemented via HSV color space"
metrics:
  duration: "15 minutes"
  completed_at: "2026-03-07T10:28:00Z"
  tasks_completed: 3
  files_created: 3
  tests_added: 14
---

# Phase 01 Plan 01: Contracts and Persistence Foundation Summary

**One-liner:** Established typed detector API with locked ROI constants and SQLite persistence layer, validated by 14 automated contract tests.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create detector contracts and immutable ROI config | 0b32200 | modules/character_detector.py, modules/__init__.py |
| 2 | Implement SQLite schema and repository primitives | a675113 | core/database.py, core/__init__.py |
| 3 | Add tests for contracts and schema bootstrap | 269e9d5 | tests/character_detection/test_detector_contracts.py |

## Implementation Details

### CharacterDetector API (modules/character_detector.py)

**ROI Constants (locked per phase decision):**
- 9 slot ROIs: 248x67 pixels each, 3x3 grid starting at (904, 557)
- Scrollbar bottom ROI: 14x32 at (1683, 828, 1697, 860)
- ESC menu ROI: (657, 854, 831, 876) per CLAUDE.md

**Configuration Constants:**
- `TEMPLATE_MATCH_METHOD = cv2.TM_CCOEFF_NORMED` (locked)
- `SLOT_DETECTION_THRESHOLD = 0.8` (locked)
- `MAX_DETECTION_RETRIES = 3` (locked)

**Public Methods:**
- `detect_esc_menu(screenshot) -> Tuple[bool, float]` - Detect character selection screen
- `scan_slots_occupancy(screenshot) -> List[SlotOccupancyResult]` - Check all 9 slots
- `detect_scroll_bottom(screenshot) -> Tuple[bool, float]` - Check if scroll reached end
- `discover_characters(screenshot) -> CharacterDiscoveryResult` - Full discovery loop

**FF00FF Masking:**
Implemented via HSV color space detection (hue 140-180) to ignore magenta regions in templates.

### Database Layer (core/database.py)

**Schema:**
```sql
accounts:
  - id (PRIMARY KEY)
  - account_hash (UNIQUE)
  - created_at

characters:
  - id (PRIMARY KEY)
  - account_id (FOREIGN KEY)
  - slot_index
  - screenshot_path
  - created_at
  - updated_at
  - UNIQUE(account_id, slot_index)
```

**Repository Functions:**
- `init_database(db_path)` - Idempotent schema creation
- `create_account(db_path, account_hash) -> int`
- `find_account_by_hash(db_path, account_hash) -> Optional[Dict]`
- `get_or_create_account(db_path, account_hash) -> int`
- `upsert_character(db_path, account_id, slot_index, screenshot_path) -> int`
- `list_characters_by_account(db_path, account_id) -> List[Dict]`

### Test Coverage (tests/character_detection/test_detector_contracts.py)

**14 tests covering:**
- Module importability (no side effects)
- CharacterDetector class and method existence
- All 9 slot ROI constants with exact values
- Scrollbar ROI constant
- Threshold and retry constants
- Template matching method (TM_CCOEFF_NORMED)
- Return type annotations
- Database table creation
- Required columns in both tables
- Account create/find operations
- Character upsert semantics (no duplicates)

## Deviations from Plan

None - plan executed exactly as written.

## Verification

All tests pass:
```bash
$ python -m pytest tests/character_detection/test_detector_contracts.py -v
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.0.2
collected 14 items

TestDetectorContracts::test_detector_module_importable PASSED
TestDetectorContracts::test_detector_class_exists PASSED
TestDetectorContracts::test_detector_roi_constants_exist PASSED
TestDetectorContracts::test_detector_slot_roi_values PASSED
TestDetectorContracts::test_detector_scrollbar_roi_exists PASSED
TestDetectorContracts::test_detector_scrollbar_roi_value PASSED
TestDetectorContracts::test_detector_threshold_constants PASSED
TestDetectorContracts::test_detector_matching_method_locked PASSED
TestDetectorContracts::test_detector_return_types_documented PASSED
TestDatabaseSchema::test_database_module_importable PASSED
TestDatabaseSchema::test_database_init_creates_tables PASSED
TestDatabaseSchema::test_database_schema_columns PASSED
TestDatabaseSchema::test_database_account_operations PASSED
TestDatabaseSchema::test_database_character_upsert PASSED

============================= 14 passed in 0.37s =============================
```

## Self-Check: PASSED

- [x] modules/character_detector.py exists
- [x] core/database.py exists
- [x] tests/character_detection/test_detector_contracts.py exists
- [x] All 14 tests pass
- [x] Commits 0b32200, a675113, 269e9d5 exist

## Next Steps

This foundation enables:
1. **01-02-PLAN.md** - Vision engine integration with template matching
2. **01-03-PLAN.md** - Character discovery workflow implementation

The contracts defined here ensure downstream plans have stable APIs to build against.
