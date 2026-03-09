#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Perceptual Hash Module

Provides perceptual hashing (pHash) for visual similarity comparison.
Used for account tag matching with tolerance for minor visual variations.

Exports:
    compute_phash: Compute perceptual hash from image path or numpy array
    compare_phash: Compare two hashes and return hamming distance
    find_similar_account: Find best matching account from database
    compute_phash_from_roi: Compute hash directly from screenshot ROI
"""

import sys
import io

# Fix Windows console encoding for Chinese output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
from typing import Optional, Tuple, Union, List, Dict, Any
import numpy as np

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import imagehash
except ImportError:
    imagehash = None

import cv2


# =============================================================================
# PERCEPTUAL HASH FUNCTIONS
# =============================================================================

def compute_phash(image_source: Union[str, np.ndarray]) -> Optional[str]:
    """
    计算图像的感知哈希值 (pHash)。

    Args:
        image_source: 图像文件路径或numpy数组 (BGR格式，OpenCV默认)

    Returns:
        64位哈希字符串 (16进制，16字符)，失败返回None
    """
    if imagehash is None:
        print("[ERROR] imagehash library not installed. Run: pip install imagehash")
        return None

    if Image is None:
        print("[ERROR] PIL (Pillow) library not installed. Run: pip install Pillow")
        return None

    try:
        # Handle numpy array (OpenCV BGR format)
        if isinstance(image_source, np.ndarray):
            # Convert BGR to RGB for PIL
            if len(image_source.shape) == 3 and image_source.shape[2] == 3:
                rgb_image = cv2.cvtColor(image_source, cv2.COLOR_BGR2RGB)
            else:
                rgb_image = image_source
            pil_image = Image.fromarray(rgb_image)
        else:
            # Handle file path
            if not os.path.exists(image_source):
                print(f"[ERROR] Image file not found: {image_source}")
                return None
            pil_image = Image.open(image_source)

        # Compute pHash (perceptual hash)
        phash = imagehash.phash(pil_image)

        # Return as hex string
        return str(phash)

    except Exception as e:
        print(f"[ERROR] Failed to compute pHash: {e}")
        return None


def compare_phash(hash1: str, hash2: str) -> int:
    """
    比较两个感知哈希值，返回汉明距离。

    Args:
        hash1: 第一个哈希字符串 (16进制)
        hash2: 第二个哈希字符串 (16进制)

    Returns:
        汉明距离 (0-64)，数值越小表示图像越相似
    """
    if imagehash is None:
        print("[ERROR] imagehash library not installed")
        return 64  # Maximum distance

    try:
        # Parse hex strings to ImageHash objects
        phash1 = imagehash.hex_to_hash(hash1)
        phash2 = imagehash.hex_to_hash(hash2)

        # Calculate hamming distance
        return phash1 - phash2

    except Exception as e:
        print(f"[ERROR] Failed to compare pHash: {e}")
        return 64  # Maximum distance on error


def compute_phash_from_roi(screenshot: np.ndarray, roi: Tuple[int, int, int, int]) -> Optional[str]:
    """
    从截图的指定ROI区域计算感知哈希。

    Args:
        screenshot: 全屏截图 (BGR numpy数组)
        roi: ROI区域坐标 (x1, y1, x2, y2)

    Returns:
        64位哈希字符串，失败返回None
    """
    try:
        x1, y1, x2, y2 = roi

        # Validate ROI bounds
        if screenshot is None or screenshot.size == 0:
            print("[ERROR] Invalid screenshot for ROI extraction")
            return None

        height, width = screenshot.shape[:2]
        x1 = max(0, min(x1, width))
        x2 = max(0, min(x2, width))
        y1 = max(0, min(y1, height))
        y2 = max(0, min(y2, height))

        if x1 >= x2 or y1 >= y2:
            print(f"[ERROR] Invalid ROI dimensions: ({x1}, {y1}, {x2}, {y2})")
            return None

        # Extract ROI region
        roi_region = screenshot[y1:y2, x1:x2]

        if roi_region.size == 0:
            print("[ERROR] Empty ROI region extracted")
            return None

        # Compute pHash from ROI
        return compute_phash(roi_region)

    except Exception as e:
        print(f"[ERROR] Failed to compute pHash from ROI: {e}")
        return None


def find_similar_account(
    db_path: str,
    screenshot: np.ndarray,
    roi: Tuple[int, int, int, int] = (666, 793, 772, 902),
    threshold: int = 10
) -> Optional[Tuple[int, str, int]]:
    """
    从数据库中查找与当前截图相似的账号。

    使用感知哈希比较，找到汉明距离最小的匹配账号。

    Args:
        db_path: SQLite数据库路径
        screenshot: 全屏截图 (BGR numpy数组)
        roi: 账号标签ROI区域 (默认: 666, 793, 772, 902)
        threshold: 汉明距离阈值 (默认10)，小于等于此值视为匹配

    Returns:
        元组 (account_id, account_hash, hamming_distance) 或 None
    """
    # Compute pHash for current screenshot ROI
    current_hash = compute_phash_from_roi(screenshot, roi)
    if current_hash is None:
        print("[ERROR] Failed to compute pHash for current screenshot")
        return None

    # Load all accounts from database
    try:
        from ..common.database import list_all_accounts
        accounts = list_all_accounts(db_path)
    except Exception as e:
        print(f"[ERROR] Failed to load accounts from database: {e}")
        return None

    if not accounts:
        print("[Vision] No existing accounts in database")
        return None

    # Find best match
    best_match = None
    best_distance = 64  # Maximum possible distance

    for account in accounts:
        tag_path = account.get('tag_screenshot_path')
        if not tag_path or not os.path.exists(tag_path):
            continue

        # Compute pHash for stored tag
        stored_hash = compute_phash(tag_path)
        if stored_hash is None:
            continue

        # Compare hashes
        distance = compare_phash(current_hash, stored_hash)

        print(f"[Vision] Account {account['id']} hash distance: {distance}")

        # Track best match
        if distance < best_distance:
            best_distance = distance
            best_match = account

    # Return best match if within threshold
    if best_match and best_distance <= threshold:
        print(f"[Vision] Found similar account: id={best_match['id']}, distance={best_distance}")
        return (best_match['id'], best_match['account_hash'], best_distance)

    print(f"[Vision] No similar account found (best distance: {best_distance}, threshold: {threshold})")
    return None


def find_similar_account_by_hash(
    db_path: str,
    image_hash: str,
    threshold: int = 10
) -> Optional[Tuple[int, str, int]]:
    """
    通过哈希值从数据库中查找相似账号。

    Args:
        db_path: SQLite数据库路径
        image_hash: 当前图像的感知哈希值
        threshold: 汉明距离阈值 (默认10)

    Returns:
        元组 (account_id, account_hash, hamming_distance) 或 None
    """
    # Load all accounts from database
    try:
        from ..common.database import list_all_accounts
        accounts = list_all_accounts(db_path)
    except Exception as e:
        print(f"[ERROR] Failed to load accounts from database: {e}")
        return None

    if not accounts:
        return None

    # Find best match
    best_match = None
    best_distance = 64

    for account in accounts:
        tag_path = account.get('tag_screenshot_path')
        if not tag_path or not os.path.exists(tag_path):
            continue

        # Compute pHash for stored tag
        stored_hash = compute_phash(tag_path)
        if stored_hash is None:
            continue

        # Compare hashes
        distance = compare_phash(image_hash, stored_hash)

        if distance < best_distance:
            best_distance = distance
            best_match = account

    # Return best match if within threshold
    if best_match and best_distance <= threshold:
        return (best_match['id'], best_match['account_hash'], best_distance)

    return None
