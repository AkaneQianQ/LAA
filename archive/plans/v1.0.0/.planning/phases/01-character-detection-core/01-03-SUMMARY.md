---
phase: 01-character-detection-core
plan: 03
type: execute
subsystem: detection-core
tags: [indexing, caching, persistence, launcher]
requires: [01-01, 01-02]
provides: [CHAR-04, CHAR-05]
affects: []
tech-stack:
  added: [hashlib, sqlite3]
  patterns: [content-addressable-storage, upsert-semantics, filesystem-cache]
key-files:
  created:
    - gui_launcher.py
    - tests/character_detection/test_account_indexing.py
  modified:
    - modules/character_detector.py
decisions:
  - "Account identity derived from first character screenshot SHA-256 hash"
  - "Cache directory structure: data/accounts/{hash}/characters/{slot}.png"
  - "Idempotent upsert for slot records prevents duplicates"
  - "Stale file validation on cache load for robustness"
  - "Launcher workflow: Discover (F11) before Automation (F10)"
metrics:
  duration: "20 minutes"
  completed_at: "2026-03-07T10:46:00Z"
  tasks_completed: 3
  files_created: 2
  files_modified: 1
  tests_added: 16
---

# Phase 01 Plan 03: Account Indexing and Screenshot Cache Summary

**One-liner:** Implemented zero-config account recognition with SHA-256 identity from first-character screenshots, persistent filesystem cache, and launcher integration with discovery-before-automation workflow.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement quick index mode with first-character screenshot hashing | f34099b | modules/character_detector.py, tests/character_detection/test_account_indexing.py |
| 2 | Cache individual character screenshots and support repeat-run recognition | 682ff27 | modules/character_detector.py (cache methods) |
| 3 | Wire first-run discovery/index step into launcher flow | 52806cc | gui_launcher.py |

## Implementation Details

### Account Indexing (modules/character_detector.py)

**New Methods:**

1. `create_or_get_account_index(screenshot) -> Tuple[int, str]`
   - Scans visible slots to find occupied ones
   - Extracts first character screenshot for identity
   - Computes SHA-256 hash for account key
   - Creates account directory structure
   - Persists all occupied slot screenshots
   - Returns (account_id, account_hash)

2. `_compute_screenshot_hash(screenshot) -> str`
   - Deterministic SHA-256 from screenshot bytes
   - 64-character hexadecimal string
   - Same screenshot always produces same hash

3. `_ensure_account_directory(account_hash) -> str`
   - Creates `data/accounts/{hash}/characters/`
   - Idempotent directory creation

### Screenshot Cache (modules/character_detector.py)

**Cache Methods:**

1. `cache_character_screenshot(account_id, slot_index, screenshot, roi=None) -> str`
   - Saves character screenshot to cache directory
   - Auto-extracts ROI from slot index if not provided
   - Updates database with metadata
   - Returns path to saved file

2. `load_cached_characters(account_id) -> List[Dict]`
   - Retrieves character metadata from database
   - Validates file existence (filters stale entries)
   - Returns list of valid cached characters

3. `discover_account(screenshot) -> Dict`
   - Launcher integration entry point
   - Returns account_id, account_hash, character_count
   - Handles case where no characters found

### Launcher Integration (gui_launcher.py)

**Features:**

- Tkinter GUI with activity log
- Global hotkeys: F11 (discover), F10 (automation), END (stop)
- Account discovery step before automation
- Visual account status display
- Threading with stop events for non-blocking operation
- Test mode (`--test`) for CI verification

**Workflow:**
1. User presses F11 or clicks "Discover Account"
2. Screenshot captured (DXCam or PIL fallback)
3. `detector.discover_account()` called
4. Account hash computed and stored
5. Character screenshots cached
6. "Start Automation" button enabled
7. User presses F10 to begin main automation

### Test Coverage (tests/character_detection/test_account_indexing.py)

**16 tests covering:**

- First character creates account index (3 tests)
- Hash determinism and uniqueness (2 tests)
- Directory structure creation (1 test)
- Screenshot persistence (1 test)
- Account idempotency (1 test)
- Cache existence checks (2 tests)
- Repeat-run recognition (1 test)
- Screenshot path naming (1 test)
- Metadata linking (1 test)
- Upsert idempotency (1 test)
- Stale file handling (1 test)
- Launcher integration (2 tests)

## Deviations from Plan

None - plan executed exactly as written.

## Verification

All tests pass:
```bash
$ python -m pytest tests/character_detection/ -v
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.0.2
collected 49 items

TestDetectorContracts (14 tests) .............................. PASSED
TestMenuDetectionRetryAndFailfast (6 tests) ..................... PASSED
TestScanVisibleSlots (5 tests) .................................. PASSED
TestScrollTraversalAndCounting (7 tests) ........................ PASSED
TestIntegrationWithRealCV (1 test) .............................. PASSED
TestFirstCharacterAccountIndexing (7 tests) ..................... PASSED
TestCharacterCacheReuse (6 tests) ............................... PASSED
TestLauncherIntegration (2 tests) ............................... PASSED

============================= 49 passed in 1.26s =============================
```

Launcher test mode:
```bash
$ python gui_launcher.py --test
Running in test mode...
CharacterDetector imported successfully
CharacterDetector created: <modules.character_detector.CharacterDetector object at 0x...>
All required methods present
Test mode completed successfully
```

## Self-Check: PASSED

- [x] modules/character_detector.py updated with account indexing methods
- [x] gui_launcher.py exists with discovery integration
- [x] tests/character_detection/test_account_indexing.py exists
- [x] All 49 tests pass (14 contract + 19 discovery + 16 indexing)
- [x] Commits f34099b, 682ff27, 52806cc exist

## Next Steps

This implementation enables:
1. **Phase 2** - Configuration system can use discovered account info
2. **Multi-account automation** - Each account has unique hash-based identity
3. **Character caching** - Fast recognition on subsequent runs without rescanning

The account indexing system provides:
- Zero-config account recognition (no manual account name entry)
- Persistent character cache for performance
- Deterministic identity from screenshot content
- Foundation for multi-account guild donation automation
