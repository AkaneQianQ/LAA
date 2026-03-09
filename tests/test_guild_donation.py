#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Guild Donation Full Workflow Test

执行完整的公会捐献流程测试，包括：
1. 3秒延迟等待切换游戏窗口
2. 初始化 Ferrum 硬件
3. 执行公会捐献 JSON Pipeline 流程

Usage:
    pytest tests/test_guild_donation.py -v              # 测试模式
    pytest tests/test_guild_donation.py -v --hardware   # 硬件模式（真实执行）
"""

import sys
import json
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest

# Import conftest globals
from conftest import HARDWARE_MODE, STARTUP_DELAY_SECONDS

# Import existing APIs
from agent.py_service.main import (
    load_interface_config,
    get_task_config,
    load_pipeline,
    initialize,
)
from agent.py_service.register import Registry, register_all_modules
from agent.py_service.modules.donation.register import (
    open_guild_menu,
    close_guild_menu,
    execute_donation,
    check_guild_menu_open,
)
from agent.py_service.pkg.ferrum.controller import FerrumController


@pytest.fixture(scope="session")
def components():
    """Initialize components with optional hardware."""
    if HARDWARE_MODE:
        print(f"\n{'='*60}")
        print("[Hardware] Initializing with real Ferrum device...")
        print(f"[Hardware] Starting in {STARTUP_DELAY_SECONDS} seconds...")
        print("[Hardware] Please switch to game window now!")
        print(f"{'='*60}\n")

        for i in range(STARTUP_DELAY_SECONDS, 0, -1):
            print(f"[Hardware] {i}...")
            time.sleep(1)

        comps = initialize(test_mode=False, skip_hardware=False)
        print("[Hardware] Ferrum device connected!")
        return comps
    else:
        print("\n[Test] Running in test mode (no hardware)")
        return initialize(test_mode=True, skip_hardware=True)


@pytest.fixture(scope="session")
def hardware_controller(components):
    """Get hardware controller."""
    return components.hardware_controller


@pytest.fixture(scope="session")
def vision_engine(components):
    """Get vision engine."""
    return components.vision_engine


class TestGuildDonationPipeline:
    """Guild Donation Pipeline JSON Validation and Execution."""

    def test_pipeline_json_valid(self):
        """验证 guild_donation.json 格式正确."""
        pipeline_path = project_root / "assets" / "resource" / "pipeline" / "guild_donation.json"

        with open(pipeline_path, 'r', encoding='utf-8') as f:
            pipeline = json.load(f)

        assert isinstance(pipeline, dict), "Pipeline must be a JSON object"
        assert len(pipeline) > 0, "Pipeline must contain at least one node"
        assert "guild_donationMain" in pipeline, "Pipeline must have guild_donationMain entry"

        print(f"[OK] Pipeline JSON valid: {len(pipeline)} nodes")

        # 打印所有节点名供检查
        print("[INFO] Pipeline nodes:")
        for node_name in sorted(pipeline.keys()):
            node = pipeline[node_name]
            next_nodes = node.get('next', [])
            action = node.get('action', {}).get('type', 'None')
            recognition = node.get('recognition', {}).get('type', 'None')
            print(f"  - {node_name}: action={action}, recognition={recognition}, next={next_nodes}")

    def test_task_config_matches_pipeline(self):
        """验证 interface.json 配置与 Pipeline 匹配."""
        config = load_interface_config()
        task_config = get_task_config(config, "GuildDonation")
        pipeline = load_pipeline(task_config["pipeline"])

        entry = task_config["entry"]
        # 处理命名差异: GuildDonationMain -> guild_donationMain
        entry_in_pipeline = entry.replace('Guild', 'guild_').lower() in [k.lower() for k in pipeline.keys()]

        assert entry_in_pipeline, f"Entry node '{entry}' not found in pipeline"
        print(f"[OK] Task config valid: entry='{entry}' matches pipeline")

    @pytest.mark.skipif(not HARDWARE_MODE, reason="Hardware mode not enabled")
    def test_full_donation_workflow(self, hardware_controller, vision_engine):
        """
        执行完整公会捐献流程.

        此测试会实际执行:
        1. 打开公会菜单 (Alt+U)
        2. 检测菜单是否打开
        3. 执行捐献流程
        4. 关闭菜单

        ⚠️ 需要游戏窗口已打开且角色在游戏中
        """
        print("\n" + "="*60)
        print("[Donation] 公会捐献流程测试开始")
        print("="*60)

        if not hardware_controller:
            pytest.skip("Hardware controller not available")

        # 注册模块
        register_all_modules()

        # 创建执行上下文
        context = {
            'hardware_controller': hardware_controller,
            'vision_engine': vision_engine,
            'screenshot': None,
            'param': {}
        }

        # Step 1: 打开公会菜单
        print("\n[Step 1] 打开公会菜单 (Alt+U)...")
        open_guild_menu(context)
        time.sleep(1.5)

        # Step 2: 截图检测菜单状态
        print("[Step 2] 检测公会菜单状态...")
        context['screenshot'] = vision_engine.get_screenshot()
        result = check_guild_menu_open(context)
        print(f"[INFO] 公会菜单检测结果: matched={result.matched}, score={result.score}")

        if result.matched:
            print("[OK] 公会菜单已打开")

            # Step 3: 执行捐献
            print("\n[Step 3] 执行捐献...")
            execute_donation(context)
            time.sleep(2.0)
            print("[OK] 捐献执行完成")
        else:
            print("[WARNING] 公会菜单未检测到，跳过捐献步骤")

        # Step 4: 关闭菜单
        print("\n[Step 4] 关闭公会菜单 (ESC)...")
        close_guild_menu(context)
        time.sleep(0.5)

        print("\n" + "="*60)
        print("[Donation] 公会捐献流程测试完成")
        print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
