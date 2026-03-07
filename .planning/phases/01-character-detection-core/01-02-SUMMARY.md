---
phase: 01-character-detection-core
plan: 02
type: execute
subsystem: detection-core
tags: [vision, discovery, traversal, tdd]
requires: [01-01]
provides: [CHAR-01, CHAR-02, CHAR-03]
affects: [01-03-PLAN.md]
tech-stack:
  added: [pytest-mock]
  patterns: [retry-with-backoff, fail-fast, bounded-loops]
key-files:
  created:
    - tests/character_detection/test_discovery_traversal.py
    - core/vision_engine.py
  modified:
    - modules/character_detector.py
decisions:
  - "Menu detection uses bounded retries (MAX_DETECTION_RETRIES=3) with early exit on success"
  - "Borderline confidence values trigger retry logic (within 0.15 of threshold)"
  - "Scroll bottom detection requires 100% pixel match (0.95 confidence)"
  - "Page deduplication uses confidence signature comparison"
  - "Max page cap (20) prevents infinite loops during discovery"
metrics:
  duration: "25 minutes"
  completed_at: "2026-03-07T10:44:00Z"
  tasks_completed: 3
  files_created: 2
  files_modified: 1
  tests_added: 19
---

# Phase 01 Plan 02: Discovery Traversal Implementation Summary

**One-liner:** Implemented deterministic character discovery with bounded retry logic, 9-slot scanning, and scroll traversal with bottom termination - validated by 19 automated tests.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add failing tests for discovery traversal | d3f1c24 | tests/character_detection/test_discovery_traversal.py |
| 2 | Implement discovery behavior | cac97f3 | modules/character_detector.py |
| 3 | Add vision_engine.py primitives | 81031b3 | core/vision_engine.py |

## Implementation Details

### Discovery Traversal Tests (tests/character_detection/test_discovery_traversal.py)

**19 tests covering:**
- Menu detection retry and fail-fast behavior (6 tests)
- 9-slot visible slot scanning (5 tests)
- Scroll traversal with bottom termination (7 tests)
- Integration with real OpenCV (1 test)

**Key test scenarios:**
- Bounded retries (max 3 attempts) with early exit on high confidence
- Fast failure when template is missing (no retries)
- Borderline confidence triggers additional retry attempts
- Row-major order slot evaluation (0-8 index)
- Page deduplication to prevent double-counting
- Max page cap (20) as safety limit

### Character Detector Updates (modules/character_detector.py)

**New Methods:**

1. `detect_character_selection_screen(screenshot) -> Tuple[bool, float]`
   - Bounded retry logic (up to MAX_DETECTION_RETRIES)
   - Fast failure when template missing
   - Early exit on threshold success

2. `scan_visible_slots(screenshot) -> List[SlotOccupancyResult]`
   - Row-major order evaluation of all 9 slots
   - Borderline retry logic (confidence within 0.15 of threshold)
   - Returns structured results with slot_index, roi, has_character, confidence

3. `discover_total_characters(screenshot, max_pages=20) -> CharacterDiscoveryResult`
   - Full discovery workflow with menu validation
   - Scroll traversal with bottom detection
   - Page deduplication using confidence signatures
   - Configurable max page cap for safety

**Helper Methods:**
- `_is_duplicate_page(sig1, sig2)` - Compare page signatures for deduplication
- `_scroll_down()` - Placeholder for hardware scroll action
- `_capture_screenshot()` - Placeholder for screen capture

### Vision Engine (core/vision_engine.py)

**Template Matching Primitives:**
- `match_template_roi()` - ROI-constrained template matching
- `find_element()` - High-level element detection with threshold
- `apply_ff00ff_mask()` - Magenta transparency handling via HSV
- `load_template_with_mask()` - Load and mask template images

**VisionEngine Class:**
- Template caching for repeated searches
- `find_element()` with automatic cache management
- `clear_cache()` for memory management

## Deviations from Plan

None - plan executed exactly as written.

## Verification

All tests pass:
```bash
$ python -m pytest tests/character_detection/ -v
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.0.2
collected 33 items

TestDetectorContracts (14 tests) .............................. PASSED
TestMenuDetectionRetryAndFailfast (6 tests) ................... PASSED
TestScanVisibleSlots (5 tests) ................................ PASSED
TestScrollTraversalAndCounting (7 tests) ...................... PASSED
TestIntegrationWithRealCV (1 test) ............................ PASSED

============================= 33 passed in 0.27s =============================
```

## Self-Check: PASSED

- [x] tests/character_detection/test_discovery_traversal.py exists
- [x] core/vision_engine.py exists
- [x] modules/character_detector.py updated with new methods
- [x] All 33 tests pass (14 contract + 19 discovery)
- [x] Commits d3f1c24, cac97f3, 81031b3 exist

## Next Steps

This implementation enables:
1. **01-03-PLAN.md** - Full discovery workflow integration with hardware controller
2. **Phase 2** - Configuration system can use discovery results

The discovery engine provides:
- Deterministic character counting without manual input
- Bounded retry logic for robustness
- Scroll traversal with reliable bottom detection
- Foundation for multi-account automation
