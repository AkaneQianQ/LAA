# Character Switch Index Navigation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace remaining-character selection with ordered `slot_index` navigation, using only target-slot verification and lightweight recovery.

**Architecture:** Keep `character_switch.yaml` unchanged and refactor the `ProcessRemainingDonations` custom action in `agent/py_service/modules/account_indexing/register.py`. Extract pure helpers for page mapping and ordered pending selection so behavior can be covered with small unit tests before the runtime loop is changed.

**Tech Stack:** Python 3.13, pytest, OpenCV, existing workflow executor and SQLite account database.

---

### Task 1: Add failing mapping tests

**Files:**
- Modify: `tests/test_account_indexing.py`
- Modify: `agent/py_service/modules/account_indexing/register.py`

**Step 1: Write the failing test**

Add tests for:
- default page mapping for indices `0, 1, 8, 9, 11, 12, 14, 15`
- target UI slot mapping from `(slot_index, page)`
- ordered pending list excluding slot `0`

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_account_indexing.py -k "page or pending" -v`
Expected: FAIL because helper functions do not exist yet.

**Step 3: Write minimal implementation**

Add pure helper functions in `register.py`:
- `_page_for_character_index`
- `_visible_start_for_page`
- `_ui_slot_for_character_on_page`
- `_ordered_pending_character_indices`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_account_indexing.py -k "page or pending" -v`
Expected: PASS

### Task 2: Add failing target-slot selection tests

**Files:**
- Modify: `tests/test_account_indexing.py`
- Modify: `agent/py_service/modules/account_indexing/register.py`

**Step 1: Write the failing test**

Add tests for:
- sequential next-target selection based on `current_character_index`
- grouping forward-only targets that never require backward navigation

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_account_indexing.py -k "target selection or forward" -v`
Expected: FAIL because helper functions do not exist yet.

**Step 3: Write minimal implementation**

Add helpers in `register.py`:
- `_next_pending_character_index`
- `_scroll_steps_between_character_defaults`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_account_indexing.py -k "target selection or forward" -v`
Expected: PASS

### Task 3: Refactor the runtime selection loop

**Files:**
- Modify: `agent/py_service/modules/account_indexing/register.py`
- Test: `tests/test_account_indexing.py`

**Step 1: Write the failing test**

Add a focused unit test for current-page fallback search helper using synthetic images so the runtime no longer depends on Hungarian assignment.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_account_indexing.py -k "fallback search" -v`
Expected: FAIL because the helper does not exist.

**Step 3: Write minimal implementation**

Refactor `ProcessRemainingDonations` to:
- compute `current_character_index`
- compute default page from current character
- compute target page and target UI slot for next pending index
- scroll only forward to the target page
- verify only the target slot image
- use current-page search only as recovery
- stop with a clear re-indexing message if verification still fails

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_account_indexing.py -k "fallback search" -v`
Expected: PASS

### Task 4: Run targeted regression tests

**Files:**
- Test: `tests/test_account_indexing.py`

**Step 1: Run focused test suite**

Run: `pytest tests/test_account_indexing.py -v`
Expected: PASS

**Step 2: Run hardware-unrelated regression coverage**

Run: `pytest tests/test_guild_donation.py -k "not hardware" -v`
Expected: PASS or known skips only.

**Step 3: Summarize manual hardware validation needs**

Document that a real indexed account should be used to validate forward-only sequential switching on characters `1..8`, `9..11`, and `12..14`.
