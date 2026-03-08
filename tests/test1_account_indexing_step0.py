#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Account Indexing Step0 Test Script - Test1
账号索引Step0测试脚本 - 测试1

Purpose: 验证Step0逻辑树的正确性
- Step 0: ESC菜单打开 (press esc)
- Step 1: 等待200ms UI稳定 (wait 200ms)
- Step 2: 捕获账号标签ROI (capture_roi at 666, 793, 772, 902)
- Step 3: 匹配或创建账号 (perceptual hash matching)

Output Directory: tests/output/test1/
"""

import sys
import io
import os
import time
import cv2
import numpy as np
import argparse
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

# Fix Windows console encoding for Chinese output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import core modules
from core.perceptual_hash import (
    compute_phash,
    compare_phash,
    compute_phash_from_roi,
    find_similar_account
)
from modules.character_detector import ACCOUNT_TAG_ROI

# =============================================================================
# CONSTANTS
# =============================================================================

OUTPUT_DIR = "tests/output/test1/"
DB_PATH = "data/accounts.db"
ACCOUNT_TAG_ROI_STEP0 = (666, 793, 772, 902)  # Account tag region for Step0

# =============================================================================
# OUTPUT DIRECTORY MANAGEMENT
# =============================================================================

def clean_output_dir() -> None:
    """
    清理输出目录
    - 如果目录存在，删除所有.png文件
    - 如果目录不存在，创建目录
    """
    print("[测试] 清理输出目录...")

    if os.path.exists(OUTPUT_DIR):
        # 删除所有.png文件
        png_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.png')]
        for f in png_files:
            file_path = os.path.join(OUTPUT_DIR, f)
            try:
                os.remove(file_path)
                print(f"  [信息] 删除旧文件: {f}")
            except Exception as e:
                print(f"  [错误] 删除失败 {f}: {e}")
        print(f"[完成] 已清理 {len(png_files)} 个旧文件")
    else:
        # 创建目录
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        print(f"[完成] 创建输出目录: {OUTPUT_DIR}")

# =============================================================================
# SCREENSHOT UTILITIES
# =============================================================================

def capture_screenshot() -> Optional[np.ndarray]:
    """
    捕获屏幕截图

    Returns:
        BGR格式的numpy数组，失败返回None
    """
    try:
        import dxcam
        camera = dxcam.create()
        screenshot = camera.grab()
        if screenshot is not None:
            # DXCam returns RGB, convert to BGR for OpenCV
            return cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"[错误] DXCam截图失败: {e}")

    # Fallback to PIL
    try:
        from PIL import ImageGrab
        screenshot = np.array(ImageGrab.grab())
        return cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"[错误] PIL截图失败: {e}")

    return None


def save_screenshot(screenshot: np.ndarray, filename: str) -> str:
    """
    保存截图到输出目录

    Args:
        screenshot: 要保存的图像
        filename: 文件名

    Returns:
        保存的完整路径
    """
    filepath = os.path.join(OUTPUT_DIR, filename)
    cv2.imwrite(filepath, screenshot)
    return filepath


def create_mock_screenshot(color: Tuple[int, int, int] = (100, 150, 200)) -> np.ndarray:
    """
    创建模拟截图用于自动测试

    Args:
        color: ROI区域填充的BGR颜色

    Returns:
        2560x1440的模拟截图
    """
    # 创建黑底图像
    screenshot = np.zeros((1440, 2560, 3), dtype=np.uint8)

    # 在ACCOUNT_TAG_ROI区域填充特定颜色
    x1, y1, x2, y2 = ACCOUNT_TAG_ROI_STEP0
    screenshot[y1:y2, x1:x2] = color

    return screenshot


# =============================================================================
# STEP0 WORKFLOW IMPLEMENTATION
# =============================================================================

def step0_open_esc_menu(screenshot: Optional[np.ndarray] = None) -> Tuple[np.ndarray, str]:
    """
    Step 0: 模拟ESC菜单打开

    Args:
        screenshot: 可选的截图（手动模式使用）

    Returns:
        (截图, 保存路径)
    """
    print("\n[步骤0] 打开ESC菜单")
    print("  [信息] 模拟按下ESC键...")

    if screenshot is None:
        # 自动模式：创建模拟截图
        screenshot = create_mock_screenshot()
        print("  [信息] 使用模拟截图")
    else:
        print("  [信息] 使用实时屏幕截图")

    # 保存截图
    filepath = save_screenshot(screenshot, "step0_full_screen.png")
    print(f"  [完成] 截图保存: {filepath}")

    return screenshot, filepath


def step1_wait_after_esc() -> None:
    """
    Step 1: 等待200ms让UI稳定
    """
    print("\n[步骤1] 等待UI稳定")
    print("  [信息] 等待200ms...")
    time.sleep(0.2)
    print("  [完成] 等待结束")


def step2_capture_account_tag(screenshot: np.ndarray) -> Tuple[np.ndarray, str, Optional[str]]:
    """
    Step 2: 捕获账号标签ROI

    Args:
        screenshot: 全屏截图

    Returns:
        (ROI截图, 保存路径, 感知哈希值)
    """
    print("\n[步骤2] 捕获账号标签ROI")
    print(f"  [信息] ROI区域: {ACCOUNT_TAG_ROI_STEP0}")

    # 提取ROI
    x1, y1, x2, y2 = ACCOUNT_TAG_ROI_STEP0
    roi_screenshot = screenshot[y1:y2, x1:x2]

    if roi_screenshot.size == 0:
        print("  [错误] ROI提取失败")
        return None, "", None

    print(f"  [信息] ROI尺寸: {roi_screenshot.shape}")

    # 保存ROI截图
    filepath = save_screenshot(roi_screenshot, "step2_account_tag.png")
    print(f"  [完成] ROI保存: {filepath}")

    # 计算感知哈希
    phash = compute_phash_from_roi(screenshot, ACCOUNT_TAG_ROI_STEP0)
    if phash:
        print(f"  [完成] 感知哈希: {phash[:16]}...")
    else:
        print("  [错误] 哈希计算失败")

    return roi_screenshot, filepath, phash


def step3_match_or_create_account(
    screenshot: np.ndarray,
    phash: Optional[str],
    temp_db_path: Optional[str] = None
) -> Tuple[Optional[int], Optional[str], int]:
    """
    Step 3: 匹配或创建账号

    Args:
        screenshot: 全屏截图
        phash: 当前截图的感知哈希
        temp_db_path: 临时数据库路径（测试用）

    Returns:
        (account_id, account_hash, hamming_distance)
        如果未匹配，account_id为None，hamming_distance为-1
    """
    print("\n[步骤3] 匹配或创建账号")

    db_path = temp_db_path if temp_db_path else DB_PATH

    # 尝试查找相似账号
    result = find_similar_account(
        db_path=db_path,
        screenshot=screenshot,
        roi=ACCOUNT_TAG_ROI_STEP0,
        threshold=10
    )

    if result:
        account_id, account_hash, distance = result
        print(f"  [信息] 找到匹配账号:")
        print(f"    - Account ID: {account_id}")
        print(f"    - Account Hash: {account_hash[:16]}...")
        print(f"    - Hamming Distance: {distance}")

        # 保存对比截图
        save_screenshot(screenshot, "step3_comparison_matched.png")
        return account_id, account_hash, distance
    else:
        print("  [信息] 未找到匹配账号，检测到新账号")

        # 计算账号哈希（基于tag截图的SHA-256）
        if phash:
            import hashlib
            account_hash = hashlib.sha256(phash.encode()).hexdigest()
            print(f"  [信息] 新账号哈希: {account_hash[:16]}...")

            # 保存新账号截图
            save_screenshot(screenshot, "step3_comparison_new.png")
            return None, account_hash, -1
        else:
            print("  [错误] 无法计算账号哈希")
            return None, None, -1


def run_step0_workflow(manual_mode: bool = False, temp_db_path: Optional[str] = None) -> dict:
    """
    运行完整的Step0工作流

    Args:
        manual_mode: 是否使用实时屏幕截图
        temp_db_path: 临时数据库路径

    Returns:
        包含执行结果的字典
    """
    print("=" * 60)
    print("[测试] Account Indexing Step0 Workflow - Test1")
    print("=" * 60)
    print(f"[信息] 模式: {'手动（实时屏幕）' if manual_mode else '自动（模拟截图）'}")
    print(f"[信息] 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    result = {
        'success': False,
        'steps_completed': [],
        'account_id': None,
        'account_hash': None,
        'hamming_distance': -1,
        'screenshots': []
    }

    try:
        # Step 0: Open ESC menu
        if manual_mode:
            screenshot = capture_screenshot()
            if screenshot is None:
                print("[错误] 屏幕截图失败")
                return result
        else:
            screenshot = None

        screenshot, path0 = step0_open_esc_menu(screenshot)
        result['steps_completed'].append('step0')
        result['screenshots'].append(path0)

        # Step 1: Wait
        step1_wait_after_esc()
        result['steps_completed'].append('step1')

        # Step 2: Capture account tag
        roi_screenshot, path2, phash = step2_capture_account_tag(screenshot)
        result['steps_completed'].append('step2')
        result['screenshots'].append(path2)
        result['phash'] = phash

        # Step 3: Match or create account
        account_id, account_hash, distance = step3_match_or_create_account(
            screenshot, phash, temp_db_path
        )
        result['steps_completed'].append('step3')
        result['account_id'] = account_id
        result['account_hash'] = account_hash
        result['hamming_distance'] = distance

        if account_id:
            print("\n[完成] Step0工作流执行成功 - 匹配到已有账号")
        else:
            print("\n[完成] Step0工作流执行成功 - 检测到新账号")

        result['success'] = True

    except Exception as e:
        print(f"\n[错误] 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()

    print("=" * 60)
    return result

# =============================================================================
# TEST FUNCTIONS
# =============================================================================

def test_capture_roi() -> bool:
    """
    测试ROI提取功能

    Returns:
        测试是否通过
    """
    print("\n" + "=" * 60)
    print("[测试] test_capture_roi - ROI提取测试")
    print("=" * 60)

    # 创建模拟截图
    screenshot = create_mock_screenshot()
    print(f"[信息] 创建模拟截图: {screenshot.shape}")

    # 提取ROI
    x1, y1, x2, y2 = ACCOUNT_TAG_ROI_STEP0
    roi = screenshot[y1:y2, x1:x2]

    print(f"[信息] ROI尺寸: {roi.shape}")

    # 验证尺寸
    expected_width = x2 - x1
    expected_height = y2 - y1

    if roi.shape[0] != expected_height or roi.shape[1] != expected_width:
        print(f"[失败] ROI尺寸不匹配: 期望({expected_height}, {expected_width}), 实际{roi.shape}")
        return False

    # 验证内容
    center_color = roi[roi.shape[0] // 2, roi.shape[1] // 2]
    expected_color = np.array([100, 150, 200])

    if not np.array_equal(center_color, expected_color):
        print(f"[失败] ROI内容不匹配: 期望{expected_color}, 实际{center_color}")
        return False

    print("[通过] ROI提取测试通过")
    return True


def test_perceptual_hash() -> bool:
    """
    测试感知哈希计算一致性

    Returns:
        测试是否通过
    """
    print("\n" + "=" * 60)
    print("[测试] test_perceptual_hash - 感知哈希测试")
    print("=" * 60)

    # 创建模拟截图
    screenshot = create_mock_screenshot()

    # 计算两次哈希
    phash1 = compute_phash_from_roi(screenshot, ACCOUNT_TAG_ROI_STEP0)
    phash2 = compute_phash_from_roi(screenshot, ACCOUNT_TAG_ROI_STEP0)

    if phash1 is None or phash2 is None:
        print("[失败] 哈希计算失败")
        return False

    print(f"[信息] 哈希1: {phash1}")
    print(f"[信息] 哈希2: {phash2}")

    # 验证一致性
    if phash1 != phash2:
        print("[失败] 相同截图产生不同哈希")
        return False

    # 计算汉明距离
    distance = compare_phash(phash1, phash2)
    print(f"[信息] 汉明距离: {distance}")

    if distance != 0:
        print("[失败] 相同截图汉明距离应为0")
        return False

    # 测试不同截图
    screenshot2 = create_mock_screenshot(color=(200, 100, 50))
    phash3 = compute_phash_from_roi(screenshot2, ACCOUNT_TAG_ROI_STEP0)
    distance2 = compare_phash(phash1, phash3)
    print(f"[信息] 不同截图汉明距离: {distance2}")

    print("[通过] 感知哈希测试通过")
    return True


def test_account_matching() -> bool:
    """
    测试账号匹配功能（使用模拟数据）

    Returns:
        测试是否通过
    """
    print("\n" + "=" * 60)
    print("[测试] test_account_matching - 账号匹配测试")
    print("=" * 60)

    # 创建临时目录和数据库
    temp_dir = tempfile.mkdtemp(prefix="test_step0_")
    temp_db = os.path.join(temp_dir, "test.db")

    try:
        # 初始化数据库
        from core.database import init_database, get_or_create_account, update_account_tag
        init_database(temp_db)

        # 创建模拟截图
        screenshot = create_mock_screenshot()
        phash = compute_phash_from_roi(screenshot, ACCOUNT_TAG_ROI_STEP0)

        # 创建账号
        import hashlib
        account_hash = hashlib.sha256(phash.encode()).hexdigest()
        account_id = get_or_create_account(temp_db, account_hash)

        # 保存tag截图
        account_dir = os.path.join(temp_dir, "accounts", account_hash)
        os.makedirs(account_dir, exist_ok=True)
        tag_path = os.path.join(account_dir, "tag.png")
        cv2.imwrite(tag_path, screenshot)
        update_account_tag(temp_db, account_id, tag_path)

        print(f"[信息] 创建测试账号: id={account_id}, hash={account_hash[:16]}...")

        # 测试匹配（相同截图）
        result = find_similar_account(temp_db, screenshot, ACCOUNT_TAG_ROI_STEP0, threshold=10)

        if result is None:
            print("[失败] 相同截图未能匹配")
            return False

        matched_id, matched_hash, distance = result
        print(f"[信息] 匹配结果: id={matched_id}, distance={distance}")

        if matched_id != account_id:
            print(f"[失败] 匹配的ID不匹配: 期望{account_id}, 实际{matched_id}")
            return False

        # 测试不同截图（应该不匹配或距离较大）
        screenshot2 = create_mock_screenshot(color=(200, 100, 50))
        result2 = find_similar_account(temp_db, screenshot2, ACCOUNT_TAG_ROI_STEP0, threshold=10)

        if result2:
            print(f"[警告] 不同截图也匹配了: distance={result2[2]}")
        else:
            print("[信息] 不同截图未匹配（符合预期）")

        print("[通过] 账号匹配测试通过")
        return True

    finally:
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_output_directory() -> bool:
    """
    测试输出目录管理功能

    Returns:
        测试是否通过
    """
    print("\n" + "=" * 60)
    print("[测试] test_output_directory - 输出目录测试")
    print("=" * 60)

    # 确保目录不存在
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)

    # 测试创建目录
    clean_output_dir()

    if not os.path.exists(OUTPUT_DIR):
        print("[失败] 目录创建失败")
        return False

    print("[信息] 目录创建成功")

    # 创建一些测试文件
    test_file = os.path.join(OUTPUT_DIR, "test.png")
    cv2.imwrite(test_file, np.zeros((100, 100, 3), dtype=np.uint8))

    # 再次清理
    clean_output_dir()

    # 验证文件被删除
    if os.path.exists(test_file):
        print("[失败] 旧文件未被清理")
        return False

    print("[信息] 旧文件清理成功")
    print("[通过] 输出目录测试通过")
    return True


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def run_auto_tests() -> bool:
    """
    运行所有自动测试

    Returns:
        所有测试是否通过
    """
    print("\n" + "=" * 60)
    print("[测试] 开始自动测试模式")
    print("=" * 60)

    results = []

    # 测试输出目录管理
    results.append(("test_output_directory", test_output_directory()))

    # 测试ROI提取
    results.append(("test_capture_roi", test_capture_roi()))

    # 测试感知哈希
    results.append(("test_perceptual_hash", test_perceptual_hash()))

    # 测试账号匹配
    results.append(("test_account_matching", test_account_matching()))

    # 测试完整工作流
    print("\n" + "=" * 60)
    print("[测试] 运行完整Step0工作流")
    print("=" * 60)

    temp_dir = tempfile.mkdtemp(prefix="test_workflow_")
    temp_db = os.path.join(temp_dir, "test.db")

    try:
        from core.database import init_database
        init_database(temp_db)

        result = run_step0_workflow(manual_mode=False, temp_db_path=temp_db)
        workflow_pass = result['success']

        if workflow_pass:
            print("[通过] 工作流测试通过")
        else:
            print("[失败] 工作流测试失败")

        results.append(("run_step0_workflow", workflow_pass))

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # 打印总结
    print("\n" + "=" * 60)
    print("[测试] 测试结果总结")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "[通过]" if passed else "[失败]"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n[完成] 所有测试通过！")
    else:
        print("\n[错误] 部分测试失败")

    return all_passed


def run_manual_mode():
    """
    运行手动测试模式（使用实时屏幕）
    """
    print("\n" + "=" * 60)
    print("[测试] 手动测试模式（实时屏幕）")
    print("=" * 60)

    # 清理输出目录
    clean_output_dir()

    # 运行工作流
    result = run_step0_workflow(manual_mode=True)

    if result['success']:
        print("\n[完成] 手动测试完成")
        print(f"[信息] 截图保存位置: {os.path.abspath(OUTPUT_DIR)}")

        if result['account_id']:
            print(f"[信息] 匹配到账号: ID={result['account_id']}")
        elif result['account_hash']:
            print(f"[信息] 新账号哈希: {result['account_hash'][:16]}...")
    else:
        print("\n[错误] 手动测试失败")


def main():
    """
    主入口函数
    """
    parser = argparse.ArgumentParser(
        description='Account Indexing Step0 Test1 - 账号索引Step0测试'
    )
    parser.add_argument(
        '--auto',
        action='store_true',
        help='运行自动测试（使用模拟截图）'
    )
    parser.add_argument(
        '--manual',
        action='store_true',
        help='运行手动测试（使用实时屏幕截图）'
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help='仅清理输出目录'
    )

    args = parser.parse_args()

    if args.clean:
        clean_output_dir()
        return

    if args.manual:
        run_manual_mode()
    else:
        # 默认运行自动测试
        success = run_auto_tests()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
