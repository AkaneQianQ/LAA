#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Account Indexing Tests
测试账号索引功能，包括账号tag获取和对比

[原有内容 - 保留信息，待重构]
====================================================
# Account Indexing Workflow Configuration
# Workflow for account tag recognition and character database ingestion
#
# This workflow:
# - Detects account identity from character selection screen
# - Captures character slot screenshots for visual hashing
# - Stores account/character metadata in SQLite database
# - Runs once per account to establish baseline
#
# Original YAML location: config/workflows/account_indexing.yaml
#
# Original steps:
# 1. verify_character_selection_screen - 验证角色选择界面
# 2. capture_account_tag - 截取账号标签ROI (657, 854, 831, 876)
# 3. scroll_to_top - 滚动到顶部
# 4-13. capture_slot_X_X - 截取9个角色格
# 14. write_to_database - 写入数据库
# 15. workflow_complete
#
# Original ROI Constants (2560x1440):
# - SLOT_1_1_ROI = (904, 557, 1152, 624)
# - SLOT_1_2_ROI = (1164, 557, 1412, 624)
# - SLOT_1_3_ROI = (1425, 557, 1673, 624)
# - ACCOUNT_TAG_ROI = (657, 854, 831, 876)  # 旧ROI，与ESC菜单重叠
# - NEW_ACCOUNT_TAG_ROI = (666, 793, 772, 902)  # 新ROI，避免UI变色
#
# Related modules (need refactoring):
# - modules/character_detector.py - CharacterDetector类
# - core/account_manager.py - AccountManager类
# - core/database.py - 数据库操作
#
# Issues to fix in refactoring:
# 1. ACCOUNT_TAG_ROI 与ESC菜单区域重叠，需要改为新ROI
# 2. 需要添加延迟首角色截图机制（避免选中状态颜色变化）
# 3. 需要添加鼠标安全位置移动（防止悬停导致UI变色）
# 4. 需要统一account_hash计算方式（基于tag截图而非全屏）
====================================================
"""

import sys
import io
import os
import cv2
import numpy as np
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple

# Fix Windows console encoding for Chinese output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modules.character_detector import CharacterDetector, ACCOUNT_TAG_ROI
from core.database import init_database, get_or_create_account, update_account_tag


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def temp_data_dir():
    """创建临时数据目录"""
    temp_dir = tempfile.mkdtemp(prefix="test_account_indexing_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def detector(temp_data_dir):
    """创建CharacterDetector实例"""
    # 使用项目中的assets目录
    assets_path = os.path.join(os.path.dirname(__file__), '..', 'assets')
    detector = CharacterDetector(
        assets_path=assets_path,
        data_dir=temp_data_dir,
        db_path=os.path.join(temp_data_dir, "accounts.db"),
        use_parallel=False
    )
    return detector


@pytest.fixture
def mock_screenshot():
    """创建模拟截图（2560x1440分辨率）"""
    # 创建黑底测试图像
    screenshot = np.zeros((1440, 2560, 3), dtype=np.uint8)

    # 在ACCOUNT_TAG_ROI区域填充特定颜色（模拟账号标签）
    x1, y1, x2, y2 = ACCOUNT_TAG_ROI
    screenshot[y1:y2, x1:x2] = [100, 150, 200]  # BGR格式

    return screenshot


@pytest.fixture
def mock_screenshot_different():
    """创建不同的模拟截图（用于对比测试）"""
    screenshot = np.zeros((1440, 2560, 3), dtype=np.uint8)

    # 在ACCOUNT_TAG_ROI区域填充不同颜色
    x1, y1, x2, y2 = ACCOUNT_TAG_ROI
    screenshot[y1:y2, x1:x2] = [200, 100, 50]  # 不同的BGR颜色

    return screenshot


# =============================================================================
# Account Tag Capture Tests
# =============================================================================

class TestAccountTagCapture:
    """测试账号标签截取功能"""

    def test_capture_account_tag_returns_correct_roi(self, detector, mock_screenshot):
        """测试截取的账号标签区域是否正确"""
        # 使用反射调用私有方法进行测试
        tag_screenshot = detector._capture_account_tag(mock_screenshot)

        # 验证返回的截图尺寸
        x1, y1, x2, y2 = ACCOUNT_TAG_ROI
        expected_width = x2 - x1
        expected_height = y2 - y1

        assert tag_screenshot is not None, "截图不应为空"
        assert tag_screenshot.shape[0] == expected_height, f"高度应为{expected_height}"
        assert tag_screenshot.shape[1] == expected_width, f"宽度应为{expected_width}"
        print(f"[OK] 账号标签截图尺寸正确: {tag_screenshot.shape}")

    def test_capture_account_tag_content(self, detector, mock_screenshot):
        """测试截取的账号标签内容是否正确"""
        tag_screenshot = detector._capture_account_tag(mock_screenshot)

        # 验证截图内容（我们填充的颜色）
        expected_color = np.array([200, 150, 100])  # BGR格式

        # 检查中心像素颜色
        center_y = tag_screenshot.shape[0] // 2
        center_x = tag_screenshot.shape[1] // 2
        actual_color = tag_screenshot[center_y, center_x]

        assert np.array_equal(actual_color, expected_color), \
            f"颜色不匹配: 期望{expected_color}, 实际{actual_color}"
        print(f"[OK] 账号标签内容正确")

    def test_compute_screenshot_hash_consistency(self, detector, mock_screenshot):
        """测试相同截图计算出的hash是否一致"""
        tag1 = detector._capture_account_tag(mock_screenshot)
        tag2 = detector._capture_account_tag(mock_screenshot)

        hash1 = detector._compute_screenshot_hash(tag1)
        hash2 = detector._compute_screenshot_hash(tag2)

        assert hash1 == hash2, "相同截图应产生相同的hash"
        assert len(hash1) == 64, "SHA-256 hash应为64字符"
        print(f"[OK] Hash一致性测试通过: {hash1[:16]}...")

    def test_compute_screenshot_hash_uniqueness(self, detector, mock_screenshot, mock_screenshot_different):
        """测试不同截图计算出的hash是否不同"""
        tag1 = detector._capture_account_tag(mock_screenshot)
        tag2 = detector._capture_account_tag(mock_screenshot_different)

        hash1 = detector._compute_screenshot_hash(tag1)
        hash2 = detector._compute_screenshot_hash(tag2)

        assert hash1 != hash2, "不同截图应产生不同的hash"
        print(f"[OK] Hash唯一性测试通过: {hash1[:16]}... != {hash2[:16]}...")


# =============================================================================
# Account Tag Matching Tests
# =============================================================================

class TestAccountTagMatching:
    """测试账号标签对比功能"""

    def test_match_account_tag_with_same_tag(self, detector, mock_screenshot, temp_data_dir):
        """测试相同账号标签应匹配成功"""
        # 初始化数据库
        init_database(detector.db_path)

        # 创建账号并保存tag
        tag_screenshot = detector._capture_account_tag(mock_screenshot)
        account_hash = detector._compute_screenshot_hash(tag_screenshot)

        # 创建账号记录
        account_id = get_or_create_account(detector.db_path, account_hash)

        # 保存tag截图到文件
        account_dir = os.path.join(temp_data_dir, "accounts", account_hash)
        os.makedirs(account_dir, exist_ok=True)
        tag_path = os.path.join(account_dir, "tag.png")
        cv2.imwrite(tag_path, tag_screenshot)

        # 更新数据库中的tag路径
        update_account_tag(detector.db_path, account_id, tag_path)

        # 测试匹配（使用相同截图）
        is_match = detector.match_account_tag(mock_screenshot, account_hash)

        assert is_match is True, "相同标签应匹配成功"
        print(f"[OK] 相同账号标签匹配成功")

    def test_match_account_tag_with_different_tag(self, detector, mock_screenshot,
                                                   mock_screenshot_different, temp_data_dir):
        """测试不同账号标签应匹配失败"""
        # 初始化数据库
        init_database(detector.db_path)

        # 使用mock_screenshot创建账号
        tag_screenshot = detector._capture_account_tag(mock_screenshot)
        account_hash = detector._compute_screenshot_hash(tag_screenshot)

        account_id = get_or_create_account(detector.db_path, account_hash)

        # 保存tag截图
        account_dir = os.path.join(temp_data_dir, "accounts", account_hash)
        os.makedirs(account_dir, exist_ok=True)
        tag_path = os.path.join(account_dir, "tag.png")
        cv2.imwrite(tag_path, tag_screenshot)

        update_account_tag(detector.db_path, account_id, tag_path)

        # 使用不同的截图进行匹配
        is_match = detector.match_account_tag(mock_screenshot_different, account_hash)

        assert is_match is False, "不同标签应匹配失败"
        print(f"[OK] 不同账号标签匹配失败（符合预期）")

    def test_match_account_tag_nonexistent_account(self, detector, mock_screenshot):
        """测试匹配不存在的账号应返回False"""
        init_database(detector.db_path)

        is_match = detector.match_account_tag(mock_screenshot, "nonexistent_hash")

        assert is_match is False, "不存在的账号应返回False"
        print(f"[OK] 不存在账号匹配返回False")

    def test_match_account_tag_missing_file(self, detector, mock_screenshot, temp_data_dir):
        """测试tag文件缺失时应返回False"""
        init_database(detector.db_path)

        # 创建账号但不保存tag文件
        tag_screenshot = detector._capture_account_tag(mock_screenshot)
        account_hash = detector._compute_screenshot_hash(tag_screenshot)

        account_id = get_or_create_account(detector.db_path, account_hash)

        # 设置一个不存在的路径
        update_account_tag(detector.db_path, account_id,
                           os.path.join(temp_data_dir, "nonexistent", "tag.png"))

        is_match = detector.match_account_tag(mock_screenshot, account_hash)

        assert is_match is False, "缺失tag文件应返回False"
        print(f"[OK] 缺失tag文件时返回False")


# =============================================================================
# Integration Tests
# =============================================================================

class TestAccountIndexingIntegration:
    """集成测试：完整的账号索引流程"""

    def test_create_or_get_account_index_new_account(self, detector, mock_screenshot, temp_data_dir):
        """测试创建新账号索引"""
        # 执行账号索引创建
        account_id, account_hash = detector.create_or_get_account_index(mock_screenshot)

        # 验证返回值
        assert account_id is not None, "应返回有效的account_id"
        assert account_hash is not None, "应返回有效的account_hash"
        assert len(account_hash) == 64, "account_hash应为64字符的SHA-256"

        # 验证目录结构
        account_dir = os.path.join(temp_data_dir, "accounts", account_hash)
        assert os.path.exists(account_dir), f"应创建账号目录: {account_dir}"
        assert os.path.exists(os.path.join(account_dir, "tag.png")), "应保存tag.png"

        print(f"[OK] 新账号索引创建成功: id={account_id}, hash={account_hash[:16]}...")

    def test_create_or_get_account_index_existing_account(self, detector, mock_screenshot, temp_data_dir):
        """测试获取已存在的账号索引"""
        # 第一次创建
        account_id1, account_hash1 = detector.create_or_get_account_index(mock_screenshot)

        # 第二次获取（使用相同截图）
        account_id2, account_hash2 = detector.create_or_get_account_index(mock_screenshot)

        # 验证返回相同的账号
        assert account_id1 == account_id2, "相同账号应返回相同的account_id"
        assert account_hash1 == account_hash2, "相同账号应返回相同的account_hash"

        print(f"[OK] 已存在账号索引获取成功: id={account_id2}")

    def test_account_info_json_created(self, detector, mock_screenshot, temp_data_dir):
        """测试account_info.json是否正确创建"""
        import json

        detector.create_or_get_account_index(mock_screenshot)

        # 查找创建的账号目录
        accounts_dir = os.path.join(temp_data_dir, "accounts")
        account_dirs = [d for d in os.listdir(accounts_dir)
                        if os.path.isdir(os.path.join(accounts_dir, d))]

        assert len(account_dirs) == 1, "应有一个账号目录"

        account_hash = account_dirs[0]
        info_path = os.path.join(accounts_dir, account_hash, "account_info.json")

        assert os.path.exists(info_path), "应创建account_info.json"

        with open(info_path, 'r', encoding='utf-8') as f:
            info = json.load(f)

        assert info['account_hash'] == account_hash, "account_hash应匹配"
        assert 'created_at' in info, "应包含created_at"
        assert 'updated_at' in info, "应包含updated_at"

        print(f"[OK] account_info.json创建成功: {info}")


# =============================================================================
# ROI Validation Tests
# =============================================================================

class TestROIValidation:
    """测试ROI常量是否正确"""

    def test_account_tag_roi_dimensions(self):
        """测试ACCOUNT_TAG_ROI尺寸是否合理"""
        x1, y1, x2, y2 = ACCOUNT_TAG_ROI

        width = x2 - x1
        height = y2 - y1

        # 检查坐标顺序
        assert x2 > x1, "x2应大于x1"
        assert y2 > y1, "y2应大于y1"

        # 检查尺寸合理性（标签区域不应太大或太小）
        assert 50 <= width <= 500, f"宽度{width}应在50-500像素之间"
        assert 50 <= height <= 300, f"高度{height}应在50-300像素之间"

        print(f"[OK] ACCOUNT_TAG_ROI尺寸合理: {width}x{height}")

    def test_account_tag_roi_within_screen(self):
        """测试ACCOUNT_TAG_ROI是否在屏幕范围内（2560x1440）"""
        x1, y1, x2, y2 = ACCOUNT_TAG_ROI

        assert x1 >= 0 and y1 >= 0, "坐标不应为负"
        assert x2 <= 2560, "x2不应超出屏幕宽度"
        assert y2 <= 1440, "y2不应超出屏幕高度"

        print(f"[OK] ACCOUNT_TAG_ROI在屏幕范围内: ({x1}, {y1}, {x2}, {y2})")


# =============================================================================
# Manual Test Entry Point
# =============================================================================

def run_manual_test():
    """
    手动测试入口，用于实际屏幕测试
    使用方法: python tests/test_index.py --manual
    """
    import argparse

    parser = argparse.ArgumentParser(description='Account Indexing Manual Test')
    parser.add_argument('--manual', action='store_true', help='Run manual test with screen capture')
    parser.add_argument('--compare', type=str, help='Compare current screen with stored account hash')
    args = parser.parse_args()

    if not args.manual:
        # 运行pytest
        pytest.main([__file__, '-v'])
        return

    print("[手动测试] 账号标签获取与对比")
    print("-" * 50)

    # 尝试导入dxcam进行屏幕捕获
    try:
        import dxcam
    except ImportError:
        print("[ERROR] 需要安装dxcam: pip install dxcam")
        return

    # 创建detector
    temp_dir = tempfile.mkdtemp(prefix="manual_test_")
    assets_path = os.path.join(os.path.dirname(__file__), '..', 'assets')

    detector = CharacterDetector(
        assets_path=assets_path,
        data_dir=temp_dir,
        db_path=os.path.join(temp_dir, "accounts.db")
    )

    # 捕获屏幕
    print("[INFO] 正在捕获屏幕...")
    camera = dxcam.create()
    screenshot = camera.grab()

    if screenshot is None:
        print("[ERROR] 屏幕捕获失败")
        return

    # 转换为BGR格式（OpenCV使用）
    screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
    print(f"[OK] 屏幕捕获成功: {screenshot.shape}")

    # 如果指定了对比模式
    if args.compare:
        print(f"[INFO] 正在与账号 {args.compare[:16]}... 对比")
        is_match = detector.match_account_tag(screenshot, args.compare)
        if is_match:
            print("[OK] 账号标签匹配成功！")
        else:
            print("[FAILED] 账号标签不匹配")
        return

    # 否则创建新账号索引
    print("[INFO] 正在创建账号索引...")
    account_id, account_hash = detector.create_or_get_account_index(screenshot)

    print(f"[OK] 账号索引创建完成:")
    print(f"  - Account ID: {account_id}")
    print(f"  - Account Hash: {account_hash}")
    print(f"  - Data Directory: {temp_dir}")

    # 保存截图供验证
    preview_path = os.path.join(temp_dir, "preview.png")
    cv2.imwrite(preview_path, screenshot)
    print(f"  - Preview saved: {preview_path}")

    # 截取并显示账号标签
    tag = detector._capture_account_tag(screenshot)
    tag_preview_path = os.path.join(temp_dir, "tag_preview.png")
    cv2.imwrite(tag_preview_path, tag)
    print(f"  - Tag preview saved: {tag_preview_path}")

    print("\n[提示] 使用以下命令进行对比测试:")
    print(f"  python tests/test_index.py --manual --compare {account_hash}")


if __name__ == '__main__':
    run_manual_test()
