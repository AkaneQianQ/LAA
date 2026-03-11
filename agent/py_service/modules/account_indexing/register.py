#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Account Indexing Module Registration
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from ...register import action, recognition, RecognitionResult
from ...pkg.common.database import (
    find_account_by_hash,
    get_or_create_account,
    init_database,
    is_account_character_done_today,
    list_characters_by_account,
    list_all_accounts,
    mark_account_character_done,
    update_account_tag,
    upsert_character,
)
from ..character.detector import CharacterDetector, ALL_SLOT_ROIS

DEFAULT_ACCOUNT_TAG_ROI: Tuple[int, int, int, int] = (666, 793, 772, 902)
DEFAULT_SWITCH_ROI: Tuple[int, int, int, int] = (575, 907, 856, 952)
DEFAULT_BOTTOM_ROI: Tuple[int, int, int, int] = (1682, 815, 1698, 861)
SWITCH_TEMPLATE = "assets/resource/image/switchCharacter.bmp"
BOTTOM_TEMPLATE = "assets/resource/image/Buttom.bmp"
DEFAULT_DB_PATH = "data/accounts.db"
DEFAULT_DATA_DIR = "data"
DEFAULT_ACCOUNT_PHASH_THRESHOLD = 10
DEFAULT_CHARACTER_PHASH_THRESHOLD = 6
DEFAULT_SLOT_THRESHOLD = 0.8
SLOT_TEMPLATE_PATH = "assets/resource/image/CharacterISorNo.bmp"
_SLOT_TEMPLATE_GRAY: Optional[np.ndarray] = None
_SLOT_TEMPLATE_MASK: Optional[np.ndarray] = None
PRE_CLICK_SETTLE_S = 0.03

# Relative dedupe ROIs converted from slot 1-2 absolute coordinates:
# Slot 1-2 ROI is (1164,557,1412,624) => width=248, height=67.
# Portrait region abs: (1171,564,1213,603) => rel: (7,7,49,46).
# Text region abs:     (1218,567,1299,621) => rel: (54,10,135,64).
_SLOT_BASE_W = 248.0
_SLOT_BASE_H = 67.0
_REL_PORTRAIT_ROI = (
    7.0 / _SLOT_BASE_W,
    7.0 / _SLOT_BASE_H,
    49.0 / _SLOT_BASE_W,
    46.0 / _SLOT_BASE_H,
)
_REL_TEXT_ROI = (
    54.0 / _SLOT_BASE_W,
    10.0 / _SLOT_BASE_H,
    135.0 / _SLOT_BASE_W,
    64.0 / _SLOT_BASE_H,
)
# Character capture ROI calibrated from slot 1-2 absolute coordinates:
# slot 1-2: (1164,557,1412,624), capture: (1169,561,1294,621)
_REL_CHARACTER_CAPTURE_ROI = (
    5.0 / _SLOT_BASE_W,
    4.0 / _SLOT_BASE_H,
    130.0 / _SLOT_BASE_W,
    64.0 / _SLOT_BASE_H,
)


def _fresh_screenshot(context: dict) -> Optional[np.ndarray]:
    vision = context.get("vision_engine")
    if vision is not None:
        # Always fetch a fresh frame for runtime decisions after UI actions/clicks.
        return vision.get_screenshot(force_fresh=True)
    # Fallback for pure unit-test contexts without vision engine.
    return context.get("screenshot")


def _capture_roi(screenshot: np.ndarray, roi: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
    if screenshot is None or screenshot.size == 0:
        return None
    h, w = screenshot.shape[:2]
    x1, y1, x2, y2 = roi
    x1 = max(0, min(x1, w))
    x2 = max(0, min(x2, w))
    y1 = max(0, min(y1, h))
    y2 = max(0, min(y2, h))
    if x1 >= x2 or y1 >= y2:
        return None
    return screenshot[y1:y2, x1:x2]


def _compute_sha256(image: np.ndarray) -> str:
    return hashlib.sha256(image.tobytes()).hexdigest()


def _page_for_character_index(character_index: int) -> int:
    if character_index <= 8:
        return 0
    return ((int(character_index) - 9) // 3) + 1


def _visible_start_for_page(page_index: int) -> int:
    return max(0, int(page_index)) * 3


def _ui_slot_for_character_on_page(character_index: int, page_index: int) -> int:
    return int(character_index) - _visible_start_for_page(int(page_index))


def _ordered_pending_character_indices(
    character_indices: List[int],
    done_map: Dict[int, bool],
) -> List[int]:
    return [
        int(idx)
        for idx in sorted(int(v) for v in character_indices)
        if int(idx) > 0 and not bool(done_map.get(int(idx), False))
    ]


def _next_pending_character_index(
    pending_indices: List[int],
    current_character_index: int,
) -> Optional[int]:
    for idx in sorted(int(v) for v in pending_indices):
        if int(idx) > int(current_character_index):
            return int(idx)
    return None


def _scroll_steps_between_character_defaults(
    current_character_index: int,
    target_character_index: int,
) -> int:
    return _page_for_character_index(int(target_character_index)) - _page_for_character_index(int(current_character_index))


def _choose_target_ui_slot(
    verified_ui_slot: Optional[int],
    target_ui_slot: int,
    allow_unverified_target_click: bool,
) -> Optional[int]:
    if verified_ui_slot is not None:
        return int(verified_ui_slot)
    if allow_unverified_target_click:
        return int(target_ui_slot)
    return None


def _compute_stable_account_hash(tag_image: np.ndarray) -> str:
    """
    Compute a stable account hash resilient to minor rendering jitter.
    """
    gray = cv2.cvtColor(tag_image, cv2.COLOR_BGR2GRAY)
    # Denoise + normalize to suppress subtle dynamic effects.
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    norm = cv2.normalize(blur, None, 0, 255, cv2.NORM_MINMAX)
    # Quantize to reduce per-frame micro-variation.
    quant = ((norm // 16) * 16).astype(np.uint8)
    return hashlib.sha256(quant.tobytes()).hexdigest()


def _compute_phash_safe(image_or_path) -> Optional[str]:
    try:
        from ...pkg.vision.perceptual_hash import compute_phash
        return compute_phash(image_or_path)
    except Exception as exc:
        print(f"[ERROR] pHash unavailable: {exc}")
        return None


def _compare_phash_safe(hash1: str, hash2: str) -> int:
    try:
        from ...pkg.vision.perceptual_hash import compare_phash
        return compare_phash(hash1, hash2)
    except Exception:
        return 64


def _ensure_account_dirs(data_dir: str, account_hash: str) -> Path:
    account_dir = Path(data_dir) / "accounts" / account_hash
    (account_dir / "characters").mkdir(parents=True, exist_ok=True)
    return account_dir


def _ensure_staging_session_dir(data_dir: str, session_id: str) -> Path:
    session_dir = Path(data_dir) / "staging" / "account_indexing" / session_id
    (session_dir / "characters").mkdir(parents=True, exist_ok=True)
    return session_dir


def _get_or_create_staging_session_dir(variables: dict, data_dir: str) -> Path:
    session_id = str(variables.get("staging_session_id") or uuid.uuid4().hex)
    variables["staging_session_id"] = session_id
    session_dir = _ensure_staging_session_dir(data_dir, session_id)
    variables["staging_session_dir"] = str(session_dir)
    variables["staging_characters_dir"] = str(session_dir / "characters")
    return session_dir


def _load_slot_template_masked() -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    global _SLOT_TEMPLATE_GRAY, _SLOT_TEMPLATE_MASK
    if _SLOT_TEMPLATE_GRAY is not None and _SLOT_TEMPLATE_MASK is not None:
        return _SLOT_TEMPLATE_GRAY, _SLOT_TEMPLATE_MASK

    template = cv2.imread(SLOT_TEMPLATE_PATH, cv2.IMREAD_COLOR)
    if template is None:
        return None, None

    # Mask out FF00FF-like magenta pixels; keep only non-magenta ring features.
    b, g, r = cv2.split(template)
    magenta = (b >= 230) & (g <= 30) & (r >= 230)
    mask = np.where(magenta, 0, 255).astype(np.uint8)

    _SLOT_TEMPLATE_GRAY = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    _SLOT_TEMPLATE_MASK = mask
    return _SLOT_TEMPLATE_GRAY, _SLOT_TEMPLATE_MASK


def _scan_slot_occupancy_relaxed(
    screenshot: np.ndarray,
    threshold: float,
) -> List[Tuple[int, bool, float]]:
    template_gray, mask = _load_slot_template_masked()
    if template_gray is None or mask is None:
        return [(idx, False, 0.0) for idx in range(len(ALL_SLOT_ROIS))]

    results: List[Tuple[int, bool, float]] = []
    for idx, (x1, y1, x2, y2) in enumerate(ALL_SLOT_ROIS):
        slot = screenshot[y1:y2, x1:x2]
        if slot.size == 0:
            results.append((idx, False, 0.0))
            continue

        slot_gray = cv2.cvtColor(slot, cv2.COLOR_BGR2GRAY)
        try:
            # Same-size masked similarity: focuses on non-magenta ring region.
            score = float(cv2.matchTemplate(
                slot_gray,
                template_gray,
                cv2.TM_CCORR_NORMED,
                mask=mask
            )[0][0])
        except cv2.error:
            score = 0.0

        results.append((idx, score >= threshold, score))

    return results


def _scan_slot_occupancy_by_anchor_color(
    screenshot: np.ndarray,
    target_rgb: Tuple[int, int, int],
    tolerance: int,
    min_pixels: int,
) -> List[Tuple[int, bool, float]]:
    # OpenCV uses BGR order.
    target_bgr = np.array([target_rgb[2], target_rgb[1], target_rgb[0]], dtype=np.int16)
    results: List[Tuple[int, bool, float]] = []

    for idx, (x1, y1, x2, y2) in enumerate(ALL_SLOT_ROIS):
        slot = screenshot[y1:y2, x1:x2]
        if slot.size == 0:
            results.append((idx, False, 0.0))
            continue

        diff = np.abs(slot.astype(np.int16) - target_bgr[None, None, :])
        match_mask = np.all(diff <= tolerance, axis=2)
        match_count = int(np.count_nonzero(match_mask))
        ratio = float(match_count) / float(match_mask.size) if match_mask.size > 0 else 0.0
        has_character = match_count >= max(1, min_pixels)
        results.append((idx, has_character, ratio))

    return results


def _anchor_color_metrics(slot_img: np.ndarray, target_rgb: Tuple[int, int, int], tolerance: int) -> Tuple[int, float]:
    if slot_img is None or slot_img.size == 0:
        return 0, 0.0
    target_bgr = np.array([target_rgb[2], target_rgb[1], target_rgb[0]], dtype=np.int16)
    diff = np.abs(slot_img.astype(np.int16) - target_bgr[None, None, :])
    match_mask = np.all(diff <= tolerance, axis=2)
    match_count = int(np.count_nonzero(match_mask))
    ratio = float(match_count) / float(match_mask.size) if match_mask.size > 0 else 0.0
    return match_count, ratio


def _scan_slot_occupancy(
    screenshot: np.ndarray,
    param: dict,
) -> Tuple[List[Tuple[int, bool, float]], str, float]:
    slot_threshold = float(param.get("occupied_threshold", 0.45))
    occupancy_mode = str(param.get("occupancy_mode", "template")).strip().lower()
    occupied_score_threshold = slot_threshold

    if occupancy_mode == "anchor_color":
        anchor_rgb = tuple(param.get("anchor_rgb", [101, 96, 70]))
        color_tolerance = int(param.get("anchor_tolerance", 6))
        min_anchor_pixels = int(param.get("anchor_min_pixels", 1))
        occupied_score_threshold = float(param.get("anchor_min_ratio", 0.0))
        slot_results = _scan_slot_occupancy_by_anchor_color(
            screenshot,
            target_rgb=(int(anchor_rgb[0]), int(anchor_rgb[1]), int(anchor_rgb[2])),
            tolerance=color_tolerance,
            min_pixels=min_anchor_pixels,
        )
    else:
        slot_results = _scan_slot_occupancy_relaxed(screenshot, threshold=slot_threshold)

    return slot_results, occupancy_mode, occupied_score_threshold


def _get_next_character_index(db_path: str, account_id: int) -> int:
    chars = list_characters_by_account(db_path, account_id)
    if not chars:
        return 1
    used = sorted(int(c["slot_index"]) for c in chars if int(c["slot_index"]) > 0)
    next_index = 1
    for idx in used:
        if idx == next_index:
            next_index += 1
        elif idx > next_index:
            break
    return next_index


def _load_existing_character_images(db_path: str, account_id: int) -> Dict[int, np.ndarray]:
    images: Dict[int, np.ndarray] = {}
    for row in list_characters_by_account(db_path, account_id):
        path = row.get("screenshot_path")
        idx = int(row["slot_index"])
        if path and Path(path).exists():
            img = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if img is not None and img.size > 0:
                images[idx] = img
    return images


def _extract_relative_roi(
    image: np.ndarray,
    rel_roi: Tuple[float, float, float, float],
) -> Optional[np.ndarray]:
    if image is None or image.size == 0:
        return None
    h, w = image.shape[:2]
    rx1, ry1, rx2, ry2 = rel_roi
    x1 = int(round(w * float(rx1)))
    x2 = int(round(w * float(rx2)))
    y1 = int(round(h * float(ry1)))
    y2 = int(round(h * float(ry2)))
    x1 = max(0, min(x1, w))
    x2 = max(0, min(x2, w))
    y1 = max(0, min(y1, h))
    y2 = max(0, min(y2, h))
    if x1 >= x2 or y1 >= y2:
        return None
    return image[y1:y2, x1:x2]


def _extract_dedupe_roi(image: np.ndarray) -> Optional[np.ndarray]:
    # Use raw capture ROI as the dedupe surface (single-region compare).
    if image is None or image.size == 0:
        return None
    return image


def _extract_character_capture_roi(image: np.ndarray) -> Optional[np.ndarray]:
    """Extract the fixed character-id patch from a slot image."""
    return _extract_relative_roi(image, _REL_CHARACTER_CAPTURE_ROI)


def _prepare_dedupe_gray(image: np.ndarray) -> Optional[np.ndarray]:
    if image is None or image.size == 0:
        return None
    if len(image.shape) == 2:
        gray = image
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(blur)
    return enhanced


def _sauvola_binarize(gray: np.ndarray, window_size: int = 25, k: float = 0.2, r: float = 128.0) -> Optional[np.ndarray]:
    """
    Sauvola local thresholding for robust UI text/icon binarization.
    """
    if gray is None or gray.size == 0:
        return None
    if window_size < 3:
        window_size = 3
    if window_size % 2 == 0:
        window_size += 1

    gray_f = gray.astype(np.float32)
    mean = cv2.boxFilter(gray_f, ddepth=-1, ksize=(window_size, window_size), normalize=True)
    sqmean = cv2.boxFilter(gray_f * gray_f, ddepth=-1, ksize=(window_size, window_size), normalize=True)
    var = np.maximum(sqmean - mean * mean, 0.0)
    std = np.sqrt(var)
    thresh = mean * (1.0 + k * ((std / max(1.0, r)) - 1.0))
    binary = np.where(gray_f > thresh, 255, 0).astype(np.uint8)
    return binary


def _wolf_binarize(gray: np.ndarray, block_size: int = 25, k: float = 0.2) -> Optional[np.ndarray]:
    """
    Wolf/Jolion local thresholding via OpenCV ximgproc when available.
    """
    if gray is None or gray.size == 0:
        return None
    if block_size < 3:
        block_size = 3
    if block_size % 2 == 0:
        block_size += 1
    ximgproc = getattr(cv2, "ximgproc", None)
    if ximgproc is None or not hasattr(ximgproc, "niBlackThreshold"):
        return None
    try:
        return ximgproc.niBlackThreshold(
            gray,
            255,
            cv2.THRESH_BINARY,
            int(block_size),
            float(k),
            ximgproc.BINARIZATION_WOLF,
        )
    except Exception:
        return None


def _thin_binary(binary: np.ndarray) -> Optional[np.ndarray]:
    if binary is None or binary.size == 0:
        return None
    ximgproc = getattr(cv2, "ximgproc", None)
    if ximgproc is not None and hasattr(ximgproc, "thinning"):
        try:
            return ximgproc.thinning(binary, thinningType=ximgproc.THINNING_ZHANGSUEN)
        except Exception:
            pass
    # Fallback: keep binary as-is when thinning backend is unavailable.
    return binary


def _prepare_dedupe_binary(image: np.ndarray) -> Optional[np.ndarray]:
    gray = _prepare_dedupe_gray(image)
    if gray is None or gray.size == 0:
        return None
    # Prefer Wolf for UI glyph stability; fallback to Sauvola.
    binary = _wolf_binarize(gray, block_size=25, k=0.2)
    if binary is None:
        binary = _sauvola_binarize(gray, window_size=25, k=0.2, r=128.0)
    if binary is None:
        return None
    return _thin_binary(binary)


def _prepare_character_image_for_storage(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Keep original ROI for storage to avoid binarization-induced information loss.
    """
    if image is None or image.size == 0:
        return None
    return image.copy()


def _compute_binary_sha256(image: np.ndarray) -> Optional[str]:
    if image is None or image.size == 0:
        return None
    return hashlib.sha256(np.ascontiguousarray(image).tobytes()).hexdigest()


def _phash_distance(a: np.ndarray, b: np.ndarray) -> int:
    ha = _compute_phash_safe(a)
    hb = _compute_phash_safe(b)
    if not ha or not hb:
        return 64
    return int(_compare_phash_safe(ha, hb))


def _blockmean_hash_distance(a: np.ndarray, b: np.ndarray) -> int:
    if a is None or b is None or a.size == 0 or b.size == 0:
        return 256
    try:
        if hasattr(cv2, "img_hash") and hasattr(cv2.img_hash, "BlockMeanHash_create"):
            hasher = cv2.img_hash.BlockMeanHash_create()
            ha = hasher.compute(a)
            hb = hasher.compute(b)
            if ha is None or hb is None:
                return 256
            ba = np.unpackbits(np.ascontiguousarray(ha).reshape(-1))
            bb = np.unpackbits(np.ascontiguousarray(hb).reshape(-1))
            n = min(len(ba), len(bb))
            if n <= 0:
                return 256
            return int(np.count_nonzero(ba[:n] != bb[:n]))
    except Exception:
        pass

    # Fallback when img_hash module is unavailable.
    ga = _prepare_dedupe_gray(a)
    gb = _prepare_dedupe_gray(b)
    if ga is None or gb is None:
        return 256
    ha = cv2.resize(ga, (16, 16), interpolation=cv2.INTER_AREA)
    hb = cv2.resize(gb, (16, 16), interpolation=cv2.INTER_AREA)
    ba = (ha > float(np.mean(ha))).astype(np.uint8).reshape(-1)
    bb = (hb > float(np.mean(hb))).astype(np.uint8).reshape(-1)
    return int(np.count_nonzero(ba != bb))


def _max_similarity_with_shift(
    a: np.ndarray,
    b: np.ndarray,
    max_shift: int = 3,
    use_binary: bool = False,
) -> Tuple[float, float]:
    if a is None or b is None or a.size == 0 or b.size == 0:
        return 0.0, 255.0
    if a.shape[:2] != b.shape[:2]:
        b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)

    ag = _prepare_dedupe_gray(a)
    bg = _prepare_dedupe_gray(b)
    if ag is None or bg is None:
        return 0.0, 255.0

    best = -1.0
    best_mad = 255.0
    h, w = ag.shape[:2]
    for dx in range(-max_shift, max_shift + 1):
        for dy in range(-max_shift, max_shift + 1):
            ax1 = max(0, dx)
            ay1 = max(0, dy)
            bx1 = max(0, -dx)
            by1 = max(0, -dy)
            cw = w - abs(dx)
            ch = h - abs(dy)
            if cw <= 4 or ch <= 4:
                continue
            pa = ag[ay1:ay1 + ch, ax1:ax1 + cw]
            pb = bg[by1:by1 + ch, bx1:bx1 + cw]
            try:
                score = float(cv2.matchTemplate(pa, pb, cv2.TM_CCOEFF_NORMED)[0][0])
            except cv2.error:
                score = -1.0
            mad = float(np.mean(cv2.absdiff(pa, pb)))
            if score > best:
                best = score
                best_mad = mad
    return max(0.0, best), best_mad


def _shape_distance_with_shift(
    a: np.ndarray,
    b: np.ndarray,
    max_shift: int = 3,
) -> float:
    """
    Compute minimum partial Hausdorff distance across small shifts on binary glyphs.
    Lower is more similar.
    """
    if a is None or b is None or a.size == 0 or b.size == 0:
        return 1e9
    if a.shape[:2] != b.shape[:2]:
        b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_NEAREST)

    ag = _prepare_dedupe_gray(a)
    bg = _prepare_dedupe_gray(b)
    if ag is None or bg is None:
        return 1e9

    h, w = ag.shape[:2]
    extractor = None
    if hasattr(cv2, "createHausdorffDistanceExtractor"):
        try:
            extractor = cv2.createHausdorffDistanceExtractor()
        except Exception:
            extractor = None

    best_dist = 1e9
    for dx in range(-max_shift, max_shift + 1):
        for dy in range(-max_shift, max_shift + 1):
            ax1 = max(0, dx)
            ay1 = max(0, dy)
            bx1 = max(0, -dx)
            by1 = max(0, -dy)
            cw = w - abs(dx)
            ch = h - abs(dy)
            if cw <= 4 or ch <= 4:
                continue

            pa = ag[ay1:ay1 + ch, ax1:ax1 + cw]
            pb = bg[by1:by1 + ch, bx1:bx1 + cw]
            ea = cv2.Canny(pa, 50, 150)
            eb = cv2.Canny(pb, 50, 150)
            ca, _ = cv2.findContours(ea, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cb, _ = cv2.findContours(eb, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            if not ca or not cb:
                continue
            cnt_a = max(ca, key=cv2.contourArea)
            cnt_b = max(cb, key=cv2.contourArea)

            if extractor is not None:
                try:
                    dist = float(extractor.computeDistance(cnt_a, cnt_b))
                except Exception:
                    dist = 1e9
            else:
                # Fallback to Hu-moment shape distance when Hausdorff extractor is unavailable.
                try:
                    dist = float(cv2.matchShapes(cnt_a, cnt_b, cv2.CONTOURS_MATCH_I1, 0.0))
                except Exception:
                    dist = 1e9

            if dist < best_dist:
                best_dist = dist

    return float(best_dist)


def _is_duplicate_character_by_image(
    candidate_img: np.ndarray,
    existing_images: Dict[int, np.ndarray],
    similarity_threshold: float,
    mad_threshold: float,
    max_shift: int = 3,
) -> bool:
    candidate_roi = _extract_dedupe_roi(candidate_img)
    if candidate_roi is None:
        return False
    for saved_img in existing_images.values():
        saved_roi = _extract_dedupe_roi(saved_img)
        if saved_roi is None:
            continue
        score, mad = _max_similarity_with_shift(
            candidate_roi,
            saved_roi,
            max_shift=max_shift,
        )
        # Require both high structure similarity and low per-pixel difference.
        if score >= similarity_threshold and mad <= mad_threshold:
            return True
    return False


def _find_duplicate_character_match(
    candidate_img: np.ndarray,
    existing_images: Dict[int, np.ndarray],
    max_shift: int = 3,
) -> Tuple[Optional[int], float, float, float, int, int, bool]:
    candidate_roi = _extract_dedupe_roi(candidate_img)
    if candidate_roi is None:
        return None, 0.0, 255.0, 1e9, 64, 256, False

    candidate_sha = _compute_binary_sha256(candidate_roi)

    best_idx: Optional[int] = None
    best_score = -1.0
    best_mad = 255.0
    best_shape_dist = 1e9
    best_phash_dist = 64
    best_block_dist = 256
    exact_match = False

    # Stage A: exact binary hash dedupe (hard gate).
    for idx, saved_img in existing_images.items():
        saved_roi = _extract_dedupe_roi(saved_img)
        if saved_roi is None:
            continue
        saved_sha = _compute_binary_sha256(saved_roi)
        if candidate_sha is not None and saved_sha is not None and candidate_sha == saved_sha:
            return int(idx), 1.0, 0.0, 0.0, 0, 0, True

    # Stage B: pHash candidate shortlist.
    phash_candidates: List[Tuple[int, np.ndarray, int]] = []
    for idx, saved_img in existing_images.items():
        saved_roi = _extract_dedupe_roi(saved_img)
        if saved_roi is None:
            continue
        pd = _phash_distance(candidate_roi, saved_roi)
        phash_candidates.append((int(idx), saved_roi, int(pd)))
    phash_candidates.sort(key=lambda x: x[2])
    shortlist = phash_candidates[: min(8, len(phash_candidates))]

    # Stage C: BlockMeanHash + NCC/MAD/shape on shortlist.
    for idx, saved_roi, pd in shortlist:
        score, mad = _max_similarity_with_shift(candidate_roi, saved_roi, max_shift=max_shift)
        shape_dist = _shape_distance_with_shift(candidate_roi, saved_roi, max_shift=max_shift)
        block_dist = _blockmean_hash_distance(candidate_roi, saved_roi)
        if (
            score > best_score
            or (abs(score - best_score) < 1e-9 and block_dist < best_block_dist)
            or (abs(score - best_score) < 1e-9 and block_dist == best_block_dist and shape_dist < best_shape_dist)
        ):
            best_score = score
            best_mad = mad
            best_shape_dist = shape_dist
            best_phash_dist = pd
            best_block_dist = block_dist
            best_idx = int(idx)
    return (
        best_idx,
        max(0.0, best_score),
        best_mad,
        float(best_shape_dist),
        int(best_phash_dist),
        int(best_block_dist),
        exact_match,
    )


def _compute_pair_match_metrics(
    candidate_img: np.ndarray,
    saved_img: np.ndarray,
    max_shift: int = 3,
) -> Tuple[float, float, float]:
    score, mad = _max_similarity_with_shift(candidate_img, saved_img, max_shift=max_shift, use_binary=False)
    shape_dist = _shape_distance_with_shift(candidate_img, saved_img, max_shift=max_shift)
    return float(score), float(mad), float(shape_dist)


def _find_target_character_ui_slot_on_page(
    screenshot: np.ndarray,
    page_index: int,
    target_index: int,
    target_image: np.ndarray,
    similarity_threshold: float,
    mad_threshold: float,
    shape_distance_threshold: float,
    max_shift: int = 3,
) -> Optional[int]:
    if screenshot is None or screenshot.size == 0 or target_image is None or target_image.size == 0:
        return None

    visible_start = _visible_start_for_page(page_index)
    visible_end = visible_start + 8
    if int(target_index) < visible_start or int(target_index) > visible_end:
        return None

    best_ui_slot: Optional[int] = None
    best_score = -1.0
    best_mad = 255.0
    best_shape = 1e9

    for ui_slot in range(9):
        global_index = visible_start + ui_slot
        if global_index <= 0:
            continue
        x1, y1, x2, y2 = ALL_SLOT_ROIS[ui_slot]
        roi_img = screenshot[y1:y2, x1:x2]
        if roi_img is None or roi_img.size == 0:
            continue
        capture_img = _extract_character_capture_roi(roi_img)
        if capture_img is None or capture_img.size == 0:
            continue
        score, mad, shape_dist = _compute_pair_match_metrics(
            capture_img,
            target_image,
            max_shift=max_shift,
        )
        is_match = (
            score >= similarity_threshold
            and mad <= mad_threshold
            and shape_dist <= shape_distance_threshold
        )
        if is_match and (
            score > best_score
            or (abs(score - best_score) < 1e-9 and mad < best_mad)
            or (abs(score - best_score) < 1e-9 and abs(mad - best_mad) < 1e-9 and shape_dist < best_shape)
        ):
            best_ui_slot = ui_slot
            best_score = float(score)
            best_mad = float(mad)
            best_shape = float(shape_dist)

    return best_ui_slot


def _hungarian_maximize(weights: List[List[float]]) -> List[Tuple[int, int, float]]:
    """
    Solve max-weight bipartite matching with Hungarian algorithm.
    Returns list of (row_idx, col_idx, weight). Rows may be unmatched.
    """
    if not weights or not weights[0]:
        return []

    orig_rows = len(weights)
    orig_cols = len(weights[0])
    n = max(orig_rows, orig_cols)
    pad_weight = 0.0
    invalid_floor = -1e8

    # Build square max-weight matrix with zero-weight dummy rows/cols.
    w_sq: List[List[float]] = [[pad_weight for _ in range(n)] for _ in range(n)]
    max_w = pad_weight
    for i in range(orig_rows):
        for j in range(orig_cols):
            wij = float(weights[i][j])
            w_sq[i][j] = wij
            if wij > max_w:
                max_w = wij

    # Convert to min-cost matrix for Hungarian.
    cost: List[List[float]] = [[max_w - w_sq[i][j] for j in range(n)] for i in range(n)]

    # Hungarian (minimization), 1-indexed implementation.
    u = [0.0] * (n + 1)
    v = [0.0] * (n + 1)
    p = [0] * (n + 1)
    way = [0] * (n + 1)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [float("inf")] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = float("inf")
            j1 = 0
            for j in range(1, n + 1):
                if used[j]:
                    continue
                cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if minv[j] < delta:
                    delta = minv[j]
                    j1 = j
            for j in range(0, n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    # Decode assignments: p[j] is row assigned to column j.
    row_to_col = [-1] * n
    for j in range(1, n + 1):
        if p[j] != 0:
            row_to_col[p[j] - 1] = j - 1

    out: List[Tuple[int, int, float]] = []
    for i in range(orig_rows):
        j = row_to_col[i]
        if 0 <= j < orig_cols:
            w = float(weights[i][j])
            if w > invalid_floor:
                out.append((i, j, w))
    return out


def _wait_template(
    vision,
    template: str,
    roi: Tuple[int, int, int, int],
    threshold: float,
    timeout_ms: int,
    poll_interval_ms: int,
) -> Tuple[bool, float, Optional[Tuple[int, int, int, int]]]:
    start_ts = time.monotonic()
    deadline = start_ts + (timeout_ms / 1000.0)
    best_score = 0.0
    best_box = None
    best_frame = None
    last_frame = None
    poll_count = 0
    while time.monotonic() < deadline:
        poll_count += 1
        screenshot = vision.get_screenshot(force_fresh=True)
        last_frame = screenshot
        matched, score, box = vision.find_element(
            screenshot,
            template_path=template,
            roi=roi,
            threshold=threshold,
        )
        try:
            score_val = float(score) if score is not None else 0.0
        except (TypeError, ValueError):
            score_val = 0.0
        if np.isnan(score_val):
            score_val = 0.0
        if score_val >= best_score:
            best_score = score_val
            best_box = box
            best_frame = screenshot
        if matched:
            if os.getenv("FERRUMBOT_DEBUG") == "1":
                elapsed_ms = int((time.monotonic() - start_ts) * 1000)
                print(
                    f"[Debug] wait_template matched: template={template}, polls={poll_count}, "
                    f"elapsed_ms={elapsed_ms}, score={score_val:.4f}, threshold={threshold}"
                )
            return True, score_val, box
        time.sleep(max(0.01, poll_interval_ms / 1000.0))

    if os.getenv("FERRUMBOT_DEBUG") == "1":
        elapsed_ms = int((time.monotonic() - start_ts) * 1000)
        print(
            f"[Debug] wait_template timeout: template={template}, roi={roi}, "
            f"threshold={threshold}, polls={poll_count}, elapsed_ms={elapsed_ms}, "
            f"best_score={best_score:.4f}, best_box={best_box}"
        )
        frame_to_dump = best_frame if best_frame is not None else last_frame
        if frame_to_dump is not None:
            x1, y1, x2, y2 = int(roi[0]), int(roi[1]), int(roi[2]), int(roi[3])
            h, w = frame_to_dump.shape[:2]
            x1 = max(0, min(x1, w))
            x2 = max(0, min(x2, w))
            y1 = max(0, min(y1, h))
            y2 = max(0, min(y2, h))
            if x2 > x1 and y2 > y1:
                debug_dir = Path("logs/debug")
                debug_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                roi_img = frame_to_dump[y1:y2, x1:x2]
                out_path = debug_dir / f"wait_template_timeout_{ts}.png"
                ok = cv2.imwrite(str(out_path), roi_img)
                print(f"[Debug] wait_template dump saved={ok}: {out_path}")
        else:
            print("[Debug] wait_template dump skipped: no frame captured")
    return False, best_score, best_box


def _safe_absolute_click(hardware, x: int, y: int) -> None:
    """
    Reliable absolute click helper.
    Prefer controller-provided move_and_click atomic sequence.
    """
    if hasattr(hardware, "move_and_click"):
        hardware.move_and_click(int(x), int(y))
        return
    hardware.move_absolute(int(x), int(y))
    time.sleep(PRE_CLICK_SETTLE_S)
    hardware.click_current()


def _click_roi_center(
    hardware,
    roi: Tuple[int, int, int, int],
    jitter: int = 2,
    pre_click_delay_ms: int = 0,
) -> Tuple[int, int]:
    x1, y1, x2, y2 = int(roi[0]), int(roi[1]), int(roi[2]), int(roi[3])
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    if jitter > 0:
        cx += random.randint(-jitter, jitter)
        cy += random.randint(-jitter, jitter)
    if pre_click_delay_ms > 0:
        hardware.move_absolute(int(cx), int(cy))
        time.sleep(pre_click_delay_ms / 1000.0)
        hardware.click_current()
    else:
        _safe_absolute_click(hardware, cx, cy)
    return cx, cy


def _click_box_shrink(
    hardware,
    box,
    shrink_percent: float = 0.10,
    template_path: Optional[str] = None,
    fallback_roi: Optional[Tuple[int, int, int, int]] = None,
) -> None:
    x1 = y1 = x2 = y2 = None
    if isinstance(box, (list, tuple)) and len(box) >= 4:
        x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
    elif isinstance(box, (list, tuple)) and len(box) == 2:
        x = int(box[0])
        y = int(box[1])
        if template_path:
            tpl = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
            if tpl is not None and tpl.size > 0:
                th, tw = tpl.shape[:2]
                x1, y1, x2, y2 = x, y, x + int(tw), y + int(th)
        if (x1 is None or x2 is None) and fallback_roi is not None:
            x1, y1, x2, y2 = (
                int(fallback_roi[0]),
                int(fallback_roi[1]),
                int(fallback_roi[2]),
                int(fallback_roi[3]),
            )
    if x1 is None or y1 is None or x2 is None or y2 is None:
        raise ValueError(f"Unsupported click box format: {box}")

    w = max(1, int(x2 - x1))
    h = max(1, int(y2 - y1))
    shrink_x = int(w * shrink_percent)
    shrink_y = int(h * shrink_percent)
    cx1 = min(x2 - 1, x1 + shrink_x)
    cx2 = max(cx1 + 1, x2 - shrink_x)
    cy1 = min(y2 - 1, y1 + shrink_y)
    cy2 = max(cy1 + 1, y2 - shrink_y)
    click_x = random.randint(cx1, cx2 - 1)
    click_y = random.randint(cy1, cy2 - 1)
    _safe_absolute_click(hardware, click_x, click_y)


def _click_box_center(
    hardware,
    box,
    template_path: Optional[str] = None,
    fallback_roi: Optional[Tuple[int, int, int, int]] = None,
    jitter: int = 2,
    pre_click_delay_ms: int = 0,
) -> Tuple[int, int]:
    x1 = y1 = x2 = y2 = None
    if isinstance(box, (list, tuple)) and len(box) >= 4:
        x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
    elif isinstance(box, (list, tuple)) and len(box) == 2:
        x = int(box[0])
        y = int(box[1])
        if template_path:
            tpl = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
            if tpl is not None and tpl.size > 0:
                th, tw = tpl.shape[:2]
                x1, y1, x2, y2 = x, y, x + int(tw), y + int(th)
        if (x1 is None or x2 is None) and fallback_roi is not None:
            x1, y1, x2, y2 = (
                int(fallback_roi[0]),
                int(fallback_roi[1]),
                int(fallback_roi[2]),
                int(fallback_roi[3]),
            )
    if x1 is None or y1 is None or x2 is None or y2 is None:
        raise ValueError(f"Unsupported click box format: {box}")

    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    if jitter > 0:
        cx += random.randint(-jitter, jitter)
        cy += random.randint(-jitter, jitter)

    if pre_click_delay_ms > 0:
        hardware.move_absolute(int(cx), int(cy))
        time.sleep(pre_click_delay_ms / 1000.0)
        hardware.click_current()
    else:
        _safe_absolute_click(hardware, cx, cy)
    return cx, cy


@recognition("SwitchCharacterVisible")
def switch_character_visible(context: dict) -> RecognitionResult:
    vision = context.get("vision_engine")
    param = context.get("param", {})
    if vision is None:
        return RecognitionResult(matched=False)

    roi = tuple(param.get("roi", DEFAULT_SWITCH_ROI))
    threshold = float(param.get("threshold", 0.8))
    timeout_ms = int(param.get("timeout_ms", 1000))
    poll_interval_ms = int(param.get("poll_interval_ms", 100))
    template = param.get("template", SWITCH_TEMPLATE)

    deadline = time.monotonic() + (timeout_ms / 1000.0)
    best_score = 0.0
    while time.monotonic() < deadline:
        screenshot = vision.get_screenshot(force_fresh=True)
        matched, score, box = vision.find_element(
            screenshot,
            template_path=template,
            roi=roi,
            threshold=threshold,
        )
        best_score = max(best_score, float(score))
        if matched:
            return RecognitionResult(matched=True, box=box, score=float(score))
        time.sleep(max(0.01, poll_interval_ms / 1000.0))

    return RecognitionResult(matched=False, score=best_score)


@recognition("ResolveAccountByTag")
def resolve_account_by_tag(context: dict) -> RecognitionResult:
    screenshot = _fresh_screenshot(context)
    param = context.get("param", {})
    variables = context.get("variables", {})

    if screenshot is None:
        return RecognitionResult(matched=False)

    roi = tuple(param.get("roi", DEFAULT_ACCOUNT_TAG_ROI))
    db_path = param.get("db_path", DEFAULT_DB_PATH)
    data_dir = param.get("data_dir", DEFAULT_DATA_DIR)
    threshold = int(param.get("phash_threshold", DEFAULT_ACCOUNT_PHASH_THRESHOLD))
    create_if_missing = bool(param.get("create_if_missing", True))
    staging_mode = bool(param.get("staging_mode", False))

    tag_image = _capture_roi(screenshot, roi)
    if tag_image is None or tag_image.size == 0:
        return RecognitionResult(matched=False)

    sha_hash = _compute_stable_account_hash(tag_image)
    candidate_phash = _compute_phash_safe(tag_image)
    matched_existing = False
    account_id = None
    account_hash = None

    if staging_mode:
        account_hash = sha_hash
        account_id = 0
    else:
        init_database(db_path)

    if not staging_mode:
        if candidate_phash:
            best_distance = 65
            best_row = None
            for row in list_all_accounts(db_path):
                tag_path = row.get("tag_screenshot_path")
                if not tag_path or not Path(tag_path).exists():
                    continue
                stored_hash = _compute_phash_safe(tag_path)
                if not stored_hash:
                    continue
                distance = _compare_phash_safe(candidate_phash, stored_hash)
                if distance < best_distance:
                    best_distance = distance
                    best_row = row
            if best_row is not None and best_distance <= threshold:
                account_id = int(best_row["id"])
                account_hash = str(best_row["account_hash"])
                matched_existing = True

        if account_id is None:
            existing = find_account_by_hash(db_path, sha_hash)
            if existing:
                account_id = int(existing["id"])
                account_hash = str(existing["account_hash"])
                matched_existing = True

        if account_id is None and create_if_missing:
            account_hash = sha_hash
            account_id = get_or_create_account(db_path, account_hash)
            row = find_account_by_hash(db_path, account_hash)
            if row:
                account_hash = str(row["account_hash"])

    if account_id is None or account_hash is None:
        if isinstance(variables, dict):
            variables["account_id"] = None
            variables["account_hash"] = None
            variables["db_path"] = db_path
            variables["data_dir"] = data_dir
        return RecognitionResult(
            matched=False,
            score=0.0,
            payload={"existing": False, "account_id": None, "account_hash": None},
        )

    if staging_mode:
        if not isinstance(variables, dict):
            return RecognitionResult(matched=False)
        session_dir = _get_or_create_staging_session_dir(variables, data_dir)
        tag_path = session_dir / "account_tag.png"
    else:
        account_dir = _ensure_account_dirs(data_dir, account_hash)
        tag_path = account_dir / "tag.png"
    cv2.imwrite(str(tag_path), tag_image)
    if not staging_mode:
        update_account_tag(db_path, account_id, str(tag_path))

    if isinstance(variables, dict):
        variables["account_id"] = int(account_id)
        variables["account_hash"] = str(account_hash)
        variables["db_path"] = db_path
        variables["data_dir"] = data_dir
        variables["scroll_loop_count"] = 0
        variables["staging_mode"] = staging_mode
        variables["staged_tag_path"] = str(tag_path)
        variables.setdefault("staged_character_paths", [])
        variables.setdefault("staged_character_count", 0)

    return RecognitionResult(
        matched=matched_existing,
        score=1.0 if matched_existing else 0.0,
        payload={
            "account_id": account_id,
            "account_hash": account_hash,
            "existing": matched_existing,
        },
    )


@recognition("BottomReached")
def bottom_reached(context: dict) -> RecognitionResult:
    vision = context.get("vision_engine")
    param = context.get("param", {})
    if vision is None:
        return RecognitionResult(matched=False)

    roi = tuple(param.get("roi", DEFAULT_BOTTOM_ROI))
    threshold = float(param.get("threshold", 0.95))
    timeout_ms = int(param.get("timeout_ms", 600))
    poll_interval_ms = int(param.get("poll_interval_ms", 100))
    template = param.get("template", BOTTOM_TEMPLATE)

    deadline = time.monotonic() + (timeout_ms / 1000.0)
    best_score = 0.0
    while time.monotonic() < deadline:
        screenshot = vision.get_screenshot(force_fresh=True)
        matched, score, box = vision.find_element(
            screenshot,
            template_path=template,
            roi=roi,
            threshold=threshold,
        )
        best_score = max(best_score, float(score))
        if matched:
            return RecognitionResult(matched=True, box=box, score=float(score))
        time.sleep(max(0.01, poll_interval_ms / 1000.0))

    return RecognitionResult(matched=False, score=best_score)


@recognition("FirstPageIncomplete")
def first_page_incomplete_recognition(context: dict) -> RecognitionResult:
    screenshot = _fresh_screenshot(context)
    param = context.get("param", {})
    if screenshot is None or screenshot.size == 0:
        return RecognitionResult(matched=False, payload={"occupied_slots": [], "empty_slots": []})

    slot_results, occupancy_mode, occupied_threshold = _scan_slot_occupancy(screenshot, param)
    skip_first_slot = bool(param.get("skip_first_slot", False))
    occupied_slots = [
        int(slot_index)
        for slot_index, has_character, confidence in slot_results
        if (not (skip_first_slot and int(slot_index) == 0))
        and bool(has_character)
        and float(confidence) >= float(occupied_threshold)
    ]
    ignored_slots = {0} if skip_first_slot else set()
    empty_slots = [idx for idx in range(len(ALL_SLOT_ROIS)) if idx not in occupied_slots and idx not in ignored_slots]
    matched = len(empty_slots) > 0

    return RecognitionResult(
        matched=matched,
        score=1.0 if matched else 0.0,
        payload={
            "occupied_slots": occupied_slots,
            "empty_slots": empty_slots,
            "occupancy_mode": occupancy_mode,
            "occupied_threshold": occupied_threshold,
        },
    )


@recognition("ScrollLoopExceeded")
def scroll_loop_exceeded(context: dict) -> RecognitionResult:
    variables = context.get("variables", {})
    param = context.get("param", {})
    if not isinstance(variables, dict):
        return RecognitionResult(matched=False)
    current = int(variables.get("scroll_loop_count", 0))
    max_loops = int(param.get("max_loops", 8))
    return RecognitionResult(
        matched=current >= max_loops,
        score=1.0 if current >= max_loops else 0.0,
        payload={"current": current, "max_loops": max_loops},
    )


@action("RecordVisibleCharacters")
def record_visible_characters(context: dict):
    screenshot = _fresh_screenshot(context)
    variables = context.get("variables", {})
    param = context.get("param", {})

    if screenshot is None or not isinstance(variables, dict):
        return

    account_id = int(variables.get("account_id", 0))
    account_hash = str(variables.get("account_hash", ""))
    db_path = str(variables.get("db_path", param.get("db_path", DEFAULT_DB_PATH)))
    data_dir = str(variables.get("data_dir", param.get("data_dir", DEFAULT_DATA_DIR)))
    staging_mode = bool(variables.get("staging_mode", param.get("staging_mode", False)))
    if (not staging_mode and account_id <= 0) or not account_hash:
        print("[ERROR] RecordVisibleCharacters missing account context")
        return

    slot_results, occupancy_mode, occupied_score_threshold = _scan_slot_occupancy(screenshot, param)

    skip_first_slot = bool(param.get("skip_first_slot", False))
    only_occupied = bool(param.get("only_occupied", True))
    dedupe = bool(param.get("dedupe", False))
    dedupe_similarity_threshold = float(param.get("dedupe_similarity_threshold", 0.991))
    dedupe_mad_threshold = float(param.get("dedupe_mad_threshold", 4.0))
    dedupe_shape_distance_threshold = float(param.get("dedupe_shape_distance_threshold", 12.0))
    dedupe_phash_threshold = int(param.get("dedupe_phash_threshold", 8))
    dedupe_blockmean_threshold = int(param.get("dedupe_blockmean_threshold", 14))
    dedupe_ncc_threshold = float(param.get("dedupe_ncc_threshold", 0.991))
    dedupe_max_shift = int(param.get("dedupe_max_shift", 3))
    occupied_threshold = occupied_score_threshold

    page_index = int(variables.get("scroll_loop_count", 0))
    print(
        f"[AccountIndexing] RecordVisibleCharacters page={page_index}, "
        f"skip_first_slot={skip_first_slot}, only_occupied={only_occupied}, "
        f"dedupe={dedupe}, occupied_threshold={occupied_threshold:.2f}, "
        f"occupancy_mode={occupancy_mode}"
    )
    print("[AccountIndexing] Slot scan:")
    for slot_index, has_character, confidence in slot_results:
        print(
            f"  - slot={int(slot_index)+1}, has_character={bool(has_character)}, "
            f"confidence={float(confidence):.4f}"
        )

    if staging_mode:
        session_dir = _get_or_create_staging_session_dir(variables, data_dir)
        chars_dir = session_dir / "characters"
        next_index = int(variables.get("staged_next_character_index", 1))
        existing_images: Dict[int, np.ndarray] = {}
        for idx, path in enumerate(variables.get("staged_character_paths", []), start=1):
            if Path(path).exists():
                img = cv2.imread(str(path), cv2.IMREAD_COLOR)
                if img is not None and img.size > 0:
                    existing_images[idx] = img
    else:
        account_dir = _ensure_account_dirs(data_dir, account_hash)
        chars_dir = account_dir / "characters"
        next_index = _get_next_character_index(db_path, account_id)
        existing_images = _load_existing_character_images(db_path, account_id)

    saved_count = 0
    for slot_index, has_character, confidence in slot_results:
        slot_index = int(slot_index)
        if skip_first_slot and slot_index == 0:
            print(f"[AccountIndexing] Skip slot={slot_index+1}: first slot masked on first page")
            continue
        if only_occupied and (not has_character or confidence < occupied_threshold):
            print(
                f"[AccountIndexing] Skip slot={slot_index+1}: occupancy not met "
                f"(has={bool(has_character)}, conf={float(confidence):.4f}, "
                f"threshold={occupied_threshold:.2f})"
            )
            continue

        x1, y1, x2, y2 = ALL_SLOT_ROIS[slot_index]
        char_img = screenshot[y1:y2, x1:x2]
        if char_img.size == 0:
            print(f"[AccountIndexing] Skip slot={slot_index+1}: empty ROI image")
            continue
        capture_img = _extract_character_capture_roi(char_img)
        if capture_img is None or capture_img.size == 0:
            print(f"[AccountIndexing] Skip slot={slot_index+1}: empty capture ROI image")
            continue

        is_focus_slot = slot_index in (3, 5)  # 2-1 and 2-3
        if is_focus_slot and occupancy_mode == "anchor_color":
            anchor_rgb = tuple(param.get("anchor_rgb", [101, 96, 70]))
            color_tolerance = int(param.get("anchor_tolerance", 6))
            hit_count, hit_ratio = _anchor_color_metrics(
                char_img,
                target_rgb=(int(anchor_rgb[0]), int(anchor_rgb[1]), int(anchor_rgb[2])),
                tolerance=color_tolerance,
            )
            print(
                f"[Focus] slot={slot_index+1} (2-{1 if slot_index == 3 else 3}) "
                f"anchor_hits={hit_count}, anchor_ratio={hit_ratio:.6f}, "
                f"occupancy_conf={float(confidence):.6f}, has_character={bool(has_character)}"
            )

        if dedupe:
            (
                best_idx,
                best_score,
                best_mad,
                best_shape_dist,
                best_phash_dist,
                best_block_dist,
                exact_match,
            ) = _find_duplicate_character_match(
                capture_img,
                existing_images,
                max_shift=dedupe_max_shift,
            )
            is_dup = (
                exact_match
                or (
                    best_idx is not None
                    and best_phash_dist <= dedupe_phash_threshold
                    and best_block_dist <= dedupe_blockmean_threshold
                    and best_score >= dedupe_ncc_threshold
                    and best_mad <= dedupe_mad_threshold
                    and best_shape_dist <= dedupe_shape_distance_threshold
                )
            )
            if is_focus_slot:
                print(
                    f"[Focus] slot={slot_index+1} dedupe_check "
                    f"best_match_index={best_idx}, best_score={best_score:.6f}, "
                    f"best_mad={best_mad:.3f}, shape_dist={best_shape_dist:.3f}, "
                    f"phash_dist={best_phash_dist}, block_dist={best_block_dist}, "
                    f"exact={exact_match}, ncc_th={dedupe_ncc_threshold:.3f}, "
                    f"mad_th={dedupe_mad_threshold:.2f}, "
                    f"shape_th={dedupe_shape_distance_threshold:.2f}, "
                    f"phash_th={dedupe_phash_threshold}, "
                    f"block_th={dedupe_blockmean_threshold}, duplicate={is_dup}"
                )
        else:
            is_dup = False

        if is_dup:
            print(
                f"[AccountIndexing] Skip slot={slot_index+1}: duplicate detected "
                f"(ncc_threshold={dedupe_ncc_threshold:.3f}, "
                f"mad_threshold={dedupe_mad_threshold:.2f}, "
                f"shape_threshold={dedupe_shape_distance_threshold:.2f}, "
                f"phash_threshold={dedupe_phash_threshold}, "
                f"blockmean_threshold={dedupe_blockmean_threshold}, "
                f"max_shift={dedupe_max_shift})"
            )
            continue

        processed_img = _prepare_character_image_for_storage(capture_img)
        if processed_img is None or processed_img.size == 0:
            print(f"[AccountIndexing] Skip slot={slot_index+1}: processing failed for storage")
            continue

        save_path = chars_dir / f"{next_index}.png"
        cv2.imwrite(str(save_path), processed_img)
        if staging_mode:
            staged_paths = list(variables.get("staged_character_paths", []))
            staged_paths.append(str(save_path))
            variables["staged_character_paths"] = staged_paths
        else:
            upsert_character(db_path, account_id, next_index, str(save_path))
        existing_images[next_index] = processed_img
        print(
            f"[AccountIndexing] Saved slot={slot_index+1} -> character_index={next_index}, "
            f"path={save_path}"
        )
        next_index += 1
        saved_count += 1

    variables["saved_in_last_page"] = saved_count
    if staging_mode:
        variables["staged_next_character_index"] = next_index
        variables["staged_character_count"] = len(list(variables.get("staged_character_paths", [])))
        variables["account_character_count"] = int(variables["staged_character_count"])
    else:
        variables["account_character_count"] = len(list_characters_by_account(db_path, account_id))
    print(
        f"[AccountIndexing] Page result: saved={saved_count}, "
        f"total_characters={variables['account_character_count']}"
    )


@action("FinalizeAccountIndex")
def finalize_account_index(context: dict):
    variables = context.get("variables", {})
    param = context.get("param", {})
    if not isinstance(variables, dict):
        return

    account_id = int(variables.get("account_id", 0))
    account_hash = str(variables.get("account_hash", ""))
    db_path = str(variables.get("db_path", param.get("db_path", DEFAULT_DB_PATH)))
    data_dir = str(variables.get("data_dir", param.get("data_dir", DEFAULT_DATA_DIR)))
    staging_mode = bool(variables.get("staging_mode", param.get("staging_mode", False)))
    if (not staging_mode and account_id <= 0) or not account_hash:
        return

    if staging_mode:
        session_dir = _get_or_create_staging_session_dir(variables, data_dir)
        count_switchable = int(variables.get("staged_character_count", len(list(variables.get("staged_character_paths", [])))))
        count_total = count_switchable + 1
        summary = {
            "session_id": str(variables.get("staging_session_id")),
            "account_hash": account_hash,
            "character_count_switchable": count_switchable,
            "character_count_total": count_total,
            "staging_dir": str(session_dir),
            "characters_dir": str(session_dir / "characters"),
            "tag_path": str(variables.get("staged_tag_path", session_dir / "account_tag.png")),
            "character_paths": list(variables.get("staged_character_paths", [])),
        }
        (session_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        variables["account_character_count"] = count_switchable
        variables["staging_summary_path"] = str(session_dir / "summary.json")
        print(
            f"[OK] AccountIndexing staged session_id={summary['session_id']}, "
            f"character_count_switchable={count_switchable}, total={count_total}"
        )
        return

    count = len(list_characters_by_account(db_path, account_id))
    account_dir = _ensure_account_dirs(data_dir, account_hash)
    info_path = account_dir / "account_info.json"
    info = {
        "account_id": account_id,
        "account_hash": account_hash,
        "character_count": count,
    }
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    variables["account_character_count"] = count
    print(f"[OK] AccountIndexing finalized account_id={account_id}, character_count={count}")


@action("IncrementScrollLoop")
def increment_scroll_loop(context: dict):
    variables = context.get("variables", {})
    if not isinstance(variables, dict):
        return
    variables["scroll_loop_count"] = int(variables.get("scroll_loop_count", 0)) + 1


@action("MarkAccountCharacterDone")
def mark_account_character_done_action(context: dict):
    variables = context.get("variables", {})
    param = context.get("param", {})
    if not isinstance(variables, dict):
        return

    account_id = int(variables.get("account_id") or 0)
    db_path = str(variables.get("db_path", param.get("db_path", DEFAULT_DB_PATH)))
    slot_index = param.get("slot_index")
    if slot_index is None:
        slot_index = variables.get("current_character_slot_index")
    if slot_index is None:
        print("[ERROR] MarkAccountCharacterDone missing slot index")
        return
    if account_id <= 0:
        print("[ERROR] MarkAccountCharacterDone missing account context")
        return

    ok = mark_account_character_done(
        db_path=db_path,
        account_id=account_id,
        slot_index=int(slot_index),
        character_name=str(param.get("character_name", "")) or None,
    )
    if ok:
        print(f"[OK] Progress marked done account_id={account_id}, slot_index={int(slot_index)}")
    else:
        print(f"[ERROR] Failed to mark done account_id={account_id}, slot_index={int(slot_index)}")


@recognition("AccountCharacterDoneToday")
def account_character_done_today_recognition(context: dict) -> RecognitionResult:
    variables = context.get("variables", {})
    param = context.get("param", {})
    if not isinstance(variables, dict):
        return RecognitionResult(matched=False)

    account_id = int(variables.get("account_id") or 0)
    db_path = str(variables.get("db_path", param.get("db_path", DEFAULT_DB_PATH)))
    slot_index = param.get("slot_index")
    if slot_index is None:
        slot_index = variables.get("current_character_slot_index")
    if slot_index is None or account_id <= 0:
        return RecognitionResult(matched=False)

    done = is_account_character_done_today(
        db_path=db_path,
        account_id=account_id,
        slot_index=int(slot_index),
    )
    return RecognitionResult(
        matched=bool(done),
        score=1.0 if done else 0.0,
        payload={"account_id": account_id, "slot_index": int(slot_index), "done_today": bool(done)},
    )


@action("ProcessRemainingDonations")
def process_remaining_donations(context: dict):
    """
    Process character donations for all non-first slots according to indexed account data.
    """
    variables = context.get("variables", {})
    param = context.get("param", {})
    hardware = context.get("hardware_controller")
    vision = context.get("vision_engine")
    if not isinstance(variables, dict) or hardware is None or vision is None:
        print("[ERROR] ProcessRemainingDonations missing runtime context")
        return False

    account_id = int(variables.get("account_id") or 0)
    db_path = str(variables.get("db_path", param.get("db_path", DEFAULT_DB_PATH)))
    if account_id <= 0:
        print("[ERROR] ProcessRemainingDonations missing account_id")
        return False

    character_images = _load_existing_character_images(db_path, account_id)
    if not character_images:
        print("[ERROR] ProcessRemainingDonations no indexed characters for account")
        return False

    switch_template = str(param.get("switch_template", SWITCH_TEMPLATE))
    switch_roi = tuple(param.get("switch_roi", DEFAULT_SWITCH_ROI))
    switch_threshold = float(param.get("switch_threshold", 0.78))
    switch_timeout_ms = int(param.get("switch_timeout_ms", 1000))
    poll_interval_ms = int(param.get("poll_interval_ms", 100))

    switch_check_template = str(param.get("switch_check_template", "assets/resource/image/CharacterSwitchCheck.bmp"))
    switch_check_roi = tuple(param.get("switch_check_roi", [1308, 912, 1580, 947]))
    switch_check_threshold = float(param.get("switch_check_threshold", 0.62))
    switch_check_timeout_ms = int(param.get("switch_check_timeout_ms", 1800))
    switch_check_retry_rounds = int(param.get("switch_check_retry_rounds", 2))
    max_esc_open_attempts = int(param.get("max_esc_open_attempts", 5))
    first_panel_pre_click_settle_ms = int(param.get("first_panel_pre_click_settle_ms", 200))
    login_template = str(param.get("login_template", "assets/resource/image/loginButton.bmp"))
    login_roi = tuple(param.get("login_roi", [1308, 912, 1441, 948]))
    confirm_template = str(param.get("confirm_template", "assets/resource/image/ConfirmButton2.bmp"))
    confirm_roi = tuple(param.get("confirm_roi", [1176, 776, 1278, 812]))

    safe_x = int(param.get("safe_x", 1689))
    safe_y = int(param.get("safe_y", 698))
    pixel_x = int(param.get("load_pixel_x", 973))
    pixel_y = int(param.get("load_pixel_y", 1146))
    pixel_rgb = tuple(param.get("load_pixel_rgb", [148, 12, 8]))
    pixel_tol = int(param.get("load_pixel_tolerance", 18))
    load_color_timeout_ms = int(param.get("load_color_timeout_ms", 20000))
    load_color_min_consecutive_hits = int(param.get("load_color_min_consecutive_hits", 2))
    slot_click_settle_ms = int(param.get("slot_click_settle_ms", 150))
    max_switch_loops = int(param.get("max_switch_loops", 24))

    bottom_template = str(param.get("bottom_template", BOTTOM_TEMPLATE))
    bottom_roi = tuple(param.get("bottom_roi", DEFAULT_BOTTOM_ROI))
    bottom_threshold = float(param.get("bottom_threshold", 0.95))
    similarity_threshold = float(param.get("dedupe_similarity_threshold", 0.995))
    mad_threshold = float(param.get("dedupe_mad_threshold", 4.0))
    shape_distance_threshold = float(param.get("dedupe_shape_distance_threshold", 6.0))
    dedupe_max_shift = int(param.get("dedupe_max_shift", 3))
    allow_unverified_target_click = bool(param.get("allow_unverified_target_click", False))

    from ...modules.workflow_executor.executor import execute_pipeline

    def _log(msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[CharacterSwitch][{ts}] {msg}")

    def open_switch_panel_with_two_esc() -> bool:
        # Guard: if switch button already visible, do not press ESC again.
        pre_matched, pre_score, _ = _wait_template(
            vision=vision,
            template=switch_template,
            roi=switch_roi,
            threshold=switch_threshold,
            timeout_ms=250,
            poll_interval_ms=poll_interval_ms,
        )
        _log(
            f"open_switch_panel precheck: matched={pre_matched}, "
            f"score={pre_score:.4f}, threshold={switch_threshold}"
        )
        if pre_matched:
            return True

        for attempt in range(max(1, max_esc_open_attempts)):
            _log(f"open_switch_panel attempt={attempt+1}: press ESC")
            hardware.press("esc")
            time.sleep(0.12)
            matched, score, _ = _wait_template(
                vision=vision,
                template=switch_template,
                roi=switch_roi,
                threshold=switch_threshold,
                timeout_ms=switch_timeout_ms,
                poll_interval_ms=poll_interval_ms,
            )
            _log(
                f"open_switch_panel attempt={attempt+1} result: "
                f"matched={matched}, score={score:.4f}, threshold={switch_threshold}"
            )
            if matched:
                return True
        return False

    def poll_and_click_switch_button(pre_click_delay_ms: int = 0) -> bool:
        """
        Poll switchCharacter.bmp and click immediately when detected.
        This guarantees click completion before moving to next step.
        """
        matched, score, switch_box = _wait_template(
            vision=vision,
            template=switch_template,
            roi=switch_roi,
            threshold=switch_threshold,
            timeout_ms=switch_timeout_ms,
            poll_interval_ms=poll_interval_ms,
        )
        if not matched or switch_box is None:
            _log(
                f"[ERROR] switch button polling failed "
                f"(matched={matched}, score={score:.4f}, threshold={switch_threshold})"
            )
            return False
        click_x, click_y = _click_box_center(
            hardware,
            switch_box,
            template_path=switch_template,
            fallback_roi=switch_roi,
            jitter=2,
            pre_click_delay_ms=pre_click_delay_ms,
        )
        if os.getenv("FERRUMBOT_DEBUG") == "1":
            _log(
                f"switch button clicked at ({click_x}, {click_y}), "
                f"detected box={switch_box}, score={score:.4f}, settle_ms={int(PRE_CLICK_SETTLE_S*1000)}"
            )
        return True

    def wait_switch_check() -> bool:
        matched, score, _ = _wait_template(
            vision=vision,
            template=switch_check_template,
            roi=switch_check_roi,
            threshold=switch_check_threshold,
            timeout_ms=switch_check_timeout_ms,
            poll_interval_ms=poll_interval_ms,
        )
        if os.getenv("FERRUMBOT_DEBUG") == "1":
            _log(
                f"switch_check result matched={matched}, score={score:.4f}, "
                f"threshold={switch_check_threshold}, timeout_ms={switch_check_timeout_ms}"
            )
        return bool(matched)

    def wait_world_color_ready() -> bool:
        deadline = time.monotonic() + max(0.1, load_color_timeout_ms / 1000.0)
        consecutive_hits = 0
        total_polls = 0
        while time.monotonic() < deadline:
            total_polls += 1
            frame = vision.get_screenshot(force_fresh=True)
            if frame is None or frame.size == 0:
                time.sleep(0.05)
                continue
            h, w = frame.shape[:2]
            if not (0 <= pixel_x < w and 0 <= pixel_y < h):
                return False
            bgr = frame[pixel_y, pixel_x]
            rgb = (int(bgr[2]), int(bgr[1]), int(bgr[0]))
            if (
                abs(rgb[0] - int(pixel_rgb[0])) <= pixel_tol
                and abs(rgb[1] - int(pixel_rgb[1])) <= pixel_tol
                and abs(rgb[2] - int(pixel_rgb[2])) <= pixel_tol
            ):
                consecutive_hits += 1
                if consecutive_hits >= max(1, load_color_min_consecutive_hits):
                    _log(
                        f"world color ready: polls={total_polls}, "
                        f"consecutive_hits={consecutive_hits}, rgb={rgb}, tol={pixel_tol}"
                    )
                    return True
            else:
                consecutive_hits = 0
            time.sleep(max(0.01, poll_interval_ms / 1000.0))
        _log(
            f"[ERROR] world color timeout: timeout_ms={load_color_timeout_ms}, polls={total_polls}, "
            f"required_hits={max(1, load_color_min_consecutive_hits)}"
        )
        return False

    def verify_target_slot(
        screenshot: np.ndarray,
        target_index: int,
        target_ui_slot: int,
        target_image: np.ndarray,
    ) -> Optional[int]:
        if not (0 <= int(target_ui_slot) < len(ALL_SLOT_ROIS)):
            return None
        x1, y1, x2, y2 = ALL_SLOT_ROIS[int(target_ui_slot)]
        roi_img = screenshot[y1:y2, x1:x2]
        capture_img = _extract_character_capture_roi(roi_img)
        if capture_img is not None and capture_img.size > 0:
            score, mad, shape_dist = _compute_pair_match_metrics(
                capture_img,
                target_image,
                max_shift=dedupe_max_shift,
            )
            if os.getenv("FERRUMBOT_DEBUG") == "1":
                _log(
                    f"target verify slot_index={int(target_index)} ui_slot={int(target_ui_slot)} "
                    f"sim={score:.4f} mad={mad:.2f} shape={shape_dist:.3f}"
                )
            if (
                score >= similarity_threshold
                and mad <= mad_threshold
                and shape_dist <= shape_distance_threshold
            ):
                return int(target_ui_slot)

        found_slot = _find_target_character_ui_slot_on_page(
            screenshot=screenshot,
            page_index=_page_for_character_index(int(target_index)),
            target_index=int(target_index),
            target_image=target_image,
            similarity_threshold=similarity_threshold,
            mad_threshold=mad_threshold,
            shape_distance_threshold=shape_distance_threshold,
            max_shift=dedupe_max_shift,
        )
        if found_slot is not None:
            _log(
                f"[WARN] target slot fallback matched slot_index={int(target_index)} "
                f"expected_ui={int(target_ui_slot)} actual_ui={int(found_slot)}"
            )
        return found_slot

    processed_count = 0
    session_run_done: set[int] = set()
    current_character_index = int(variables.get("current_character_slot_index", 0) or 0)
    for loop_idx in range(max_switch_loops):
        _log(
            f"loop_start idx={loop_idx+1}/{max_switch_loops}, processed_count={processed_count}, "
            f"current_character_index={current_character_index}"
        )
        db_done_map: Dict[int, bool] = {
            int(idx): bool(is_account_character_done_today(db_path=db_path, account_id=account_id, slot_index=int(idx)))
            for idx in character_images.keys()
        }
        pending_indices = _ordered_pending_character_indices(list(character_images.keys()), db_done_map)
        next_target_index = _next_pending_character_index(pending_indices, current_character_index)
        if next_target_index is None:
            _log(f"[OK] completed, processed={processed_count}, no pending characters remain")
            variables["current_character_slot_index"] = int(current_character_index)
            return True

        default_page = _page_for_character_index(current_character_index)
        target_page = _page_for_character_index(next_target_index)
        target_ui_slot = _ui_slot_for_character_on_page(next_target_index, target_page)
        if not (0 <= int(target_ui_slot) < len(ALL_SLOT_ROIS)):
            _log(
                f"[ERROR] invalid target ui slot for slot_index={int(next_target_index)} "
                f"page={int(target_page)} ui_slot={int(target_ui_slot)}"
            )
            return False
        scroll_steps = _scroll_steps_between_character_defaults(current_character_index, next_target_index)
        if scroll_steps < 0:
            _log(
                f"[ERROR] backward navigation required current={int(current_character_index)} "
                f"target={int(next_target_index)}; please re-index account ordering"
            )
            return False

        panel_ready = False
        for panel_try in range(max(1, switch_check_retry_rounds)):
            _log(f"panel_try={panel_try+1}/{max(1, switch_check_retry_rounds)}")
            if not open_switch_panel_with_two_esc():
                _log("[ERROR] cannot open character switch panel with ESC retries")
                return False

            pre_click_delay_ms = first_panel_pre_click_settle_ms if panel_try == 0 else 0
            if not poll_and_click_switch_button(pre_click_delay_ms=pre_click_delay_ms):
                return False

            if wait_switch_check():
                panel_ready = True
                break
            _log("[WARN] selection panel check failed, retry this loop")

        if not panel_ready:
            _log("[ERROR] selection panel did not appear after switch button click")
            return False

        _log(f"move mouse to safe position ({safe_x}, {safe_y})")
        hardware.move_absolute(safe_x, safe_y)
        time.sleep(0.05)
        for step_idx in range(scroll_steps):
            _log(
                f"scroll_to_target step={step_idx+1}/{scroll_steps}: "
                f"default_page={default_page}, target_page={target_page}"
            )
            hardware.scroll("down", 1)
            time.sleep(0.10)
            hardware.move_absolute(safe_x, safe_y)
            time.sleep(0.05)

        screenshot = vision.get_screenshot(force_fresh=True)
        if screenshot is None or screenshot.size == 0:
            _log("[ERROR] failed to capture screenshot after opening selection panel")
            return False

        target_image = character_images.get(int(next_target_index))
        if target_image is None or target_image.size == 0:
            _log(f"[ERROR] missing indexed screenshot for slot_index={int(next_target_index)}")
            return False

        chosen_ui_slot = verify_target_slot(
            screenshot=screenshot,
            target_index=int(next_target_index),
            target_ui_slot=int(target_ui_slot),
            target_image=target_image,
        )
        if chosen_ui_slot is None:
            time.sleep(0.08)
            screenshot_retry = vision.get_screenshot(force_fresh=True)
            chosen_ui_slot = verify_target_slot(
                screenshot=screenshot_retry,
                target_index=int(next_target_index),
                target_ui_slot=int(target_ui_slot),
                target_image=target_image,
            )

        selected_ui_slot = _choose_target_ui_slot(
            verified_ui_slot=chosen_ui_slot,
            target_ui_slot=int(target_ui_slot),
            allow_unverified_target_click=allow_unverified_target_click,
        )

        if chosen_ui_slot is None and selected_ui_slot is not None:
            _log(
                f"[WARN] target verify failed for slot_index={int(next_target_index)} on "
                f"target_page={int(target_page)}; continue with expected_ui={int(selected_ui_slot)}"
            )

        if selected_ui_slot is not None:
            x1, y1, x2, y2 = ALL_SLOT_ROIS[int(selected_ui_slot)]
            roi = (x1, y1, x2, y2)
            bx, by = _click_roi_center(hardware, roi, jitter=2)
            _log(
                f"slot ui={int(selected_ui_slot)} selected slot_index={int(next_target_index)} "
                f"target_page={int(target_page)} -> click ({bx}, {by}) roi={roi}"
            )
            if slot_click_settle_ms > 0:
                time.sleep(slot_click_settle_ms / 1000.0)

            login_ok, login_score, login_box = _wait_template(
                vision=vision,
                template=login_template,
                roi=login_roi,
                threshold=0.7,
                timeout_ms=1000,
                poll_interval_ms=poll_interval_ms,
            )
            if not login_ok or login_box is None:
                bx2, by2 = _click_roi_center(hardware, roi, jitter=1)
                _log(
                    f"[WARN] login button not found after first click, retry slot click at ({bx2}, {by2})"
                )
                if slot_click_settle_ms > 0:
                    time.sleep(slot_click_settle_ms / 1000.0)
                login_ok, login_score, login_box = _wait_template(
                    vision=vision,
                    template=login_template,
                    roi=login_roi,
                    threshold=0.7,
                    timeout_ms=1000,
                    poll_interval_ms=poll_interval_ms,
                )
            if not login_ok or login_box is None:
                _log(
                    f"[ERROR] login button not found for slot_index={int(next_target_index)}, "
                    f"score={login_score:.4f}"
                )
                return False
            _click_box_shrink(
                hardware,
                login_box,
                shrink_percent=0.10,
                template_path=login_template,
                fallback_roi=login_roi,
            )

            confirm_ok, _, confirm_box = _wait_template(
                vision=vision,
                template=confirm_template,
                roi=confirm_roi,
                threshold=0.7,
                timeout_ms=1000,
                poll_interval_ms=poll_interval_ms,
            )
            if confirm_ok and confirm_box is not None:
                _click_box_shrink(
                    hardware,
                    confirm_box,
                    shrink_percent=0.10,
                    template_path=confirm_template,
                    fallback_roi=confirm_roi,
            )

            if not wait_world_color_ready():
                _log(f"[ERROR] world-load color not detected for slot_index={int(next_target_index)}")
                return False

            success = execute_pipeline(
                pipeline_path=Path("assets/resource/pipeline/guild_donation.json"),
                entry_node="guild_donationMain",
                hardware_controller=hardware,
                vision_engine=vision,
                timeout_seconds=60.0,
            )
            if not success:
                _log(f"[ERROR] guild donation failed for slot_index={int(next_target_index)}")
                return False

            mark_account_character_done(db_path=db_path, account_id=account_id, slot_index=int(next_target_index))
            session_run_done.add(int(next_target_index))
            current_character_index = int(next_target_index)
            _log(f"mark done slot_index={int(next_target_index)}")
            variables["current_character_slot_index"] = int(current_character_index)
            processed_count += 1
            _log("loop end: picked one character and completed donation")
            continue

        _log(
            f"[ERROR] unable to verify slot_index={int(next_target_index)} on target_page={int(target_page)}; "
            f"possible ordering drift, please rebuild account index"
        )
        return False

    _log(f"[ERROR] reached max loops={max_switch_loops}, processed={processed_count}")
    return False


def register():
    print("[模块] account_indexing 已注册")
