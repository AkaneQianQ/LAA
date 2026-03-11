#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Account indexing recognizer/action tests.
"""

import json
import numpy as np
import cv2

from agent.py_service.modules.account_indexing.register import (
    ALL_SLOT_ROIS,
    _choose_target_ui_slot,
    _find_target_character_ui_slot_on_page,
    _is_duplicate_character_by_image,
    _get_next_character_index,
    _next_pending_character_index,
    _ordered_pending_character_indices,
    _page_for_character_index,
    _scroll_steps_between_character_defaults,
    _ui_slot_for_character_on_page,
    first_page_incomplete_recognition,
    resolve_account_by_tag,
    record_visible_characters,
    finalize_account_index,
)
from launcher.service import discard_account_indexing_staging, save_account_indexing_staging
from agent.py_service.pkg.common.database import init_database, list_all_accounts, list_characters_by_account
from agent.py_service.pkg.common.database import (
    delete_character_by_account_slot,
    get_or_create_account,
    upsert_character,
)


def _make_screenshot() -> np.ndarray:
    screenshot = np.zeros((1440, 2560, 3), dtype=np.uint8)
    screenshot[793:902, 666:772] = 220
    # Fill slot areas so occupancy matcher has stable positive signals in tests.
    screenshot[557:624, 904:1152] = 255
    screenshot[557:624, 1164:1412] = 255
    screenshot[557:624, 1425:1673] = 255
    return screenshot


def _make_first_page_screenshot(occupied_slots: list[int]) -> np.ndarray:
    screenshot = np.zeros((1440, 2560, 3), dtype=np.uint8)
    for slot_index in occupied_slots:
        x1, y1, x2, y2 = ALL_SLOT_ROIS[slot_index]
        screenshot[y1:y2, x1:x2] = (70, 96, 101)
    return screenshot


def test_resolve_account_by_tag_create_then_match(tmp_path):
    db_path = tmp_path / "accounts.db"
    data_dir = tmp_path / "data"
    init_database(str(db_path))

    screenshot = _make_screenshot()
    variables = {}

    ctx = {
        "screenshot": screenshot,
        "param": {
            "roi": [666, 793, 772, 902],
            "db_path": str(db_path),
            "data_dir": str(data_dir),
            "phash_threshold": 10,
        },
        "variables": variables,
    }

    first = resolve_account_by_tag(ctx)
    assert first.matched is False
    assert variables["account_id"] > 0

    second = resolve_account_by_tag(ctx)
    assert second.matched is True
    assert len(list_all_accounts(str(db_path))) == 1


def test_record_and_finalize_account_characters(tmp_path):
    db_path = tmp_path / "accounts.db"
    data_dir = tmp_path / "data"
    init_database(str(db_path))

    screenshot = _make_screenshot()
    variables = {}

    resolve_account_by_tag({
        "screenshot": screenshot,
        "param": {
            "roi": [666, 793, 772, 902],
            "db_path": str(db_path),
            "data_dir": str(data_dir),
            "phash_threshold": 10,
        },
        "variables": variables,
    })

    record_visible_characters({
        "screenshot": screenshot,
        "variables": variables,
        "param": {
            "skip_first_slot": True,
            "only_occupied": False,
            "dedupe": False,
        },
    })

    chars = list_characters_by_account(str(db_path), int(variables["account_id"]))
    assert len(chars) > 0

    finalize_account_index({
        "variables": variables,
        "param": {
            "db_path": str(db_path),
            "data_dir": str(data_dir),
        },
    })

    assert int(variables["account_character_count"]) == len(chars)


def test_character_image_dedupe_distinguishes_different_text():
    # Simulate same UI frame with only text region changed.
    base = np.full((67, 248, 3), 120, dtype=np.uint8)
    candidate = base.copy()
    existing = base.copy()

    # Draw different "text-like" strokes in dedupe-sensitive right-lower region.
    cv2.putText(existing, "ABC", (130, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(candidate, "XYZ", (130, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    is_dup = _is_duplicate_character_by_image(
        candidate,
        {1: existing},
        similarity_threshold=0.985,
        mad_threshold=8.0,
        max_shift=3,
    )
    assert is_dup is False


def test_get_next_character_index_backfills_gap(tmp_path):
    db_path = tmp_path / "accounts.db"
    init_database(str(db_path))
    account_id = get_or_create_account(str(db_path), "acc-hash-for-backfill")
    upsert_character(str(db_path), account_id, 1, "p1.png")
    upsert_character(str(db_path), account_id, 2, "p2.png")
    upsert_character(str(db_path), account_id, 3, "p3.png")
    upsert_character(str(db_path), account_id, 5, "p5.png")

    next_index = _get_next_character_index(str(db_path), int(account_id))
    assert next_index == 4


def test_page_for_character_index_matches_ui_defaults():
    assert _page_for_character_index(0) == 0
    assert _page_for_character_index(1) == 0
    assert _page_for_character_index(8) == 0
    assert _page_for_character_index(9) == 1
    assert _page_for_character_index(11) == 1
    assert _page_for_character_index(12) == 2
    assert _page_for_character_index(14) == 2
    assert _page_for_character_index(15) == 3


def test_ui_slot_for_character_on_page_matches_visible_layout():
    assert _ui_slot_for_character_on_page(1, 0) == 1
    assert _ui_slot_for_character_on_page(8, 0) == 8
    assert _ui_slot_for_character_on_page(9, 1) == 6
    assert _ui_slot_for_character_on_page(10, 1) == 7
    assert _ui_slot_for_character_on_page(11, 1) == 8
    assert _ui_slot_for_character_on_page(12, 2) == 6
    assert _ui_slot_for_character_on_page(14, 2) == 8


def test_ordered_pending_character_indices_excludes_first_slot_and_done_entries():
    pending = _ordered_pending_character_indices(
        character_indices=[0, 1, 2, 3, 8, 9, 12],
        done_map={2: True, 8: True},
    )
    assert pending == [1, 3, 9, 12]


def test_next_pending_character_index_is_sequential():
    pending = [1, 3, 4, 9]
    assert _next_pending_character_index(pending, current_character_index=0) == 1
    assert _next_pending_character_index(pending, current_character_index=1) == 3
    assert _next_pending_character_index(pending, current_character_index=4) == 9
    assert _next_pending_character_index(pending, current_character_index=9) is None


def test_scroll_steps_between_character_defaults_is_forward_only_for_sequential_indices():
    assert _scroll_steps_between_character_defaults(current_character_index=0, target_character_index=1) == 0
    assert _scroll_steps_between_character_defaults(current_character_index=8, target_character_index=9) == 1
    assert _scroll_steps_between_character_defaults(current_character_index=9, target_character_index=10) == 0
    assert _scroll_steps_between_character_defaults(current_character_index=11, target_character_index=12) == 1


def test_find_target_character_ui_slot_on_page_locates_target_without_full_assignment():
    screenshot = np.zeros((1440, 2560, 3), dtype=np.uint8)
    target_slot = 7
    x1, y1, x2, y2 = ALL_SLOT_ROIS[target_slot]
    screenshot[y1 + 4:y1 + 64, x1 + 5:x1 + 130] = 80
    cv2.putText(
        screenshot,
        "TARGET",
        (x1 + 22, y1 + 44),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    target_capture = screenshot[y1 + 4:y1 + 64, x1 + 5:x1 + 130].copy()

    found_slot = _find_target_character_ui_slot_on_page(
        screenshot=screenshot,
        page_index=1,
        target_index=10,
        target_image=target_capture,
        similarity_threshold=0.995,
        mad_threshold=1.0,
        shape_distance_threshold=0.1,
        max_shift=1,
    )
    assert found_slot == target_slot


def test_choose_target_ui_slot_falls_back_to_expected_slot_when_allowed():
    chosen_slot = _choose_target_ui_slot(
        verified_ui_slot=None,
        target_ui_slot=2,
        allow_unverified_target_click=True,
    )
    assert chosen_slot == 2


def test_choose_target_ui_slot_still_blocks_when_fallback_disabled():
    chosen_slot = _choose_target_ui_slot(
        verified_ui_slot=None,
        target_ui_slot=2,
        allow_unverified_target_click=False,
    )
    assert chosen_slot is None


def test_delete_character_by_account_slot_removes_only_requested_slot(tmp_path):
    db_path = tmp_path / "accounts.db"
    init_database(str(db_path))
    account_id = get_or_create_account(str(db_path), "acc-hash-delete-by-slot")
    upsert_character(str(db_path), account_id, 20, "p20.png")
    upsert_character(str(db_path), account_id, 21, "p21.png")

    deleted = delete_character_by_account_slot(str(db_path), int(account_id), 21)
    assert deleted is True

    chars = list_characters_by_account(str(db_path), int(account_id))
    assert [int(c["slot_index"]) for c in chars] == [20]


def test_first_page_incomplete_recognition_matches_when_home_page_has_empty_slots():
    screenshot = _make_first_page_screenshot([0, 1, 2, 3, 4, 5, 6])

    result = first_page_incomplete_recognition({
        "screenshot": screenshot,
        "param": {
            "occupancy_mode": "anchor_color",
            "anchor_rgb": [101, 96, 70],
            "anchor_tolerance": 6,
            "anchor_min_pixels": 1,
        },
    })

    assert result.matched is True
    assert result.payload["occupied_slots"] == [0, 1, 2, 3, 4, 5, 6]
    assert result.payload["empty_slots"] == [7, 8]


def test_first_page_incomplete_recognition_does_not_match_when_home_page_is_full():
    screenshot = _make_first_page_screenshot(list(range(9)))

    result = first_page_incomplete_recognition({
        "screenshot": screenshot,
        "param": {
            "occupancy_mode": "anchor_color",
            "anchor_rgb": [101, 96, 70],
            "anchor_tolerance": 6,
            "anchor_min_pixels": 1,
        },
    })

    assert result.matched is False
    assert result.payload["occupied_slots"] == list(range(9))
    assert result.payload["empty_slots"] == []


def test_first_page_incomplete_recognition_ignores_first_slot_when_requested():
    screenshot = _make_first_page_screenshot([1, 2, 3, 4, 5, 6, 7, 8])

    result = first_page_incomplete_recognition({
        "screenshot": screenshot,
        "param": {
            "occupancy_mode": "anchor_color",
            "anchor_rgb": [101, 96, 70],
            "anchor_tolerance": 6,
            "anchor_min_pixels": 1,
            "skip_first_slot": True,
        },
    })

    assert result.matched is False
    assert result.payload["occupied_slots"] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert result.payload["empty_slots"] == []


def test_account_indexing_staging_flow_writes_summary_without_persistent_db(tmp_path):
    db_path = tmp_path / "accounts.db"
    data_dir = tmp_path / "data"
    init_database(str(db_path))

    screenshot = _make_screenshot()
    variables = {}

    resolve_account_by_tag({
        "screenshot": screenshot,
        "param": {
            "roi": [666, 793, 772, 902],
            "db_path": str(db_path),
            "data_dir": str(data_dir),
            "phash_threshold": 10,
            "staging_mode": True,
        },
        "variables": variables,
    })

    record_visible_characters({
        "screenshot": screenshot,
        "variables": variables,
        "param": {
            "skip_first_slot": True,
            "only_occupied": True,
            "dedupe": False,
            "db_path": str(db_path),
            "data_dir": str(data_dir),
            "staging_mode": True,
            "occupancy_mode": "anchor_color",
            "anchor_rgb": [255, 255, 255],
            "anchor_tolerance": 0,
            "anchor_min_pixels": 1,
            "anchor_min_ratio": 0.0,
        },
    })

    finalize_account_index({
        "variables": variables,
        "param": {
            "db_path": str(db_path),
            "data_dir": str(data_dir),
            "staging_mode": True,
        },
    })

    assert list_all_accounts(str(db_path)) == []
    summary_path = data_dir / "staging" / "account_indexing" / variables["staging_session_id"] / "summary.json"
    assert summary_path.exists()
    summary = summary_path.read_text(encoding="utf-8")
    assert '"character_count_total": 3' in summary


def test_save_account_indexing_staging_imports_into_persistent_storage(tmp_path):
    db_path = tmp_path / "accounts.db"
    data_dir = tmp_path / "data"
    init_database(str(db_path))

    screenshot = _make_screenshot()
    variables = {}

    resolve_account_by_tag({
        "screenshot": screenshot,
        "param": {
            "roi": [666, 793, 772, 902],
            "db_path": str(db_path),
            "data_dir": str(data_dir),
            "phash_threshold": 10,
            "staging_mode": True,
        },
        "variables": variables,
    })
    record_visible_characters({
        "screenshot": screenshot,
        "variables": variables,
        "param": {
            "skip_first_slot": True,
            "only_occupied": True,
            "dedupe": False,
            "db_path": str(db_path),
            "data_dir": str(data_dir),
            "staging_mode": True,
            "occupancy_mode": "anchor_color",
            "anchor_rgb": [255, 255, 255],
            "anchor_tolerance": 0,
            "anchor_min_pixels": 1,
            "anchor_min_ratio": 0.0,
        },
    })
    finalize_account_index({
        "variables": variables,
        "param": {
            "db_path": str(db_path),
            "data_dir": str(data_dir),
            "staging_mode": True,
        },
    })

    result = save_account_indexing_staging(str(db_path), str(data_dir), variables["staging_session_id"])

    assert result["character_count_total"] == 3
    accounts = list_all_accounts(str(db_path))
    assert len(accounts) == 1
    chars = list_characters_by_account(str(db_path), int(accounts[0]["id"]))
    assert len(chars) == 2
    account_info = json.loads((data_dir / "accounts" / result["account_hash"] / "account_info.json").read_text(encoding="utf-8"))
    assert account_info["character_count"] == 3
    assert not (data_dir / "staging" / "account_indexing" / variables["staging_session_id"]).exists()


def test_discard_account_indexing_staging_removes_staging_without_db_write(tmp_path):
    db_path = tmp_path / "accounts.db"
    data_dir = tmp_path / "data"
    init_database(str(db_path))

    screenshot = _make_screenshot()
    variables = {}

    resolve_account_by_tag({
        "screenshot": screenshot,
        "param": {
            "roi": [666, 793, 772, 902],
            "db_path": str(db_path),
            "data_dir": str(data_dir),
            "phash_threshold": 10,
            "staging_mode": True,
        },
        "variables": variables,
    })
    finalize_account_index({
        "variables": variables,
        "param": {
            "db_path": str(db_path),
            "data_dir": str(data_dir),
            "staging_mode": True,
        },
    })

    result = discard_account_indexing_staging(str(data_dir), variables["staging_session_id"])

    assert result["discarded"] is True
    assert list_all_accounts(str(db_path)) == []
    assert not (data_dir / "staging" / "account_indexing" / variables["staging_session_id"]).exists()
