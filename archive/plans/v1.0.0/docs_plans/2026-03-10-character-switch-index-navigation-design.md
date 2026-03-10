# Character Switch Index Navigation Design

**Date:** 2026-03-10

## Goal
Replace the current image-heavy remaining-character selection loop with deterministic `slot_index`-driven navigation, while keeping a single-slot visual confirmation before clicking a target character.

## Constraints
- Keep `slot_index=0` on the existing fixed first-character donation path.
- Treat `slot_index` ordering as the source of truth for switching.
- If ordering drifts, fail fast and guide account re-indexing.
- Preserve current `character_switch.yaml` orchestration where possible.
- Supported resolution remains 2560x1440 with fixed slot ROIs.

## UI Model
- If the current logged-in character is in `0..8`, opening the switch panel lands on homepage `0..8`.
- If current character is in `9..11`, opening the switch panel lands on the page whose visible range is `3..11`.
- If current character is in `12..14`, opening the switch panel lands on the page whose visible range is `6..14`.
- In general, the default page after `ESC` is determined by the current character's global index, not by the previously browsed page.
- Because of that, runtime page state is only valid within a single panel-open session.

## Recommended Approach
Use deterministic navigation for `slot_index >= 1`:
1. Load pending characters from DB in ascending `slot_index` order.
2. Track `current_character_index` starting at `0` after the fixed first-character flow.
3. Each loop recomputes the panel's default page from `current_character_index`.
4. Compute target page and target UI slot from the next pending `slot_index`.
5. Scroll forward from the default page to the target page.
6. Verify only the target slot against the target character image.
7. Click, login, donate, mark done, then update `current_character_index`.

## Mapping Rules
- `default_page_for_index(i)`
  - `0` for `i <= 8`
  - `((i - 9) // 3) + 1` for `i >= 9`
- `visible_start_for_page(p) = p * 3`
- `ui_slot_for_index_on_page(i, p) = i - visible_start_for_page(p)`
- Sequential processing guarantees target pages do not move backwards.

## Recovery Strategy
1. Retry the target slot capture once.
2. Search only the current visible page for the target character image.
3. If still unresolved, stop and report probable ordering drift requiring re-indexing.

## Files To Change
- `agent/py_service/modules/account_indexing/register.py`
- `tests/test_account_indexing.py`
- Optional: a new focused test module if the current test file grows too large.

## Verification
- Unit tests for page/index mapping and ordered pending selection.
- Unit tests for fallback search on the visible page.
- Existing account-indexing tests must remain green.
- Manual hardware validation on a real indexed account after code changes.
