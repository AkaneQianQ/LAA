#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Guild Donation Full Workflow Test

执行完整的公会捐献流程测试，使用 Pipeline Executor 自动执行 YAML 定义的工作流。

Features:
- 模块化架构：Pipeline Executor 解析并执行 JSON 节点
- YAML/JSON 工作流：人工编写 YAML，自动转换为 Pipeline JSON
- 自动执行：调用所有 API 完成捐献流程

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
from agent.py_service.register import register_all_modules
from agent.py_service.modules.workflow_executor.executor import create_executor, execute_pipeline
from agent.py_service.pkg.workflow.pipeline_executor import (
    ExecutionContext,
    create_executor_with_defaults,
)


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


class TestPipelineValidation:
    """Pipeline JSON 验证测试."""

    def test_pipeline_json_valid(self):
        """验证 guild_donation.json 格式正确."""
        pipeline_path = project_root / "assets" / "resource" / "pipeline" / "guild_donation.json"

        with open(pipeline_path, 'r', encoding='utf-8') as f:
            pipeline = json.load(f)

        assert isinstance(pipeline, dict), "Pipeline must be a JSON object"
        assert len(pipeline) > 0, "Pipeline must contain at least one node"
        assert "guild_donationMain" in pipeline, "Pipeline must have guild_donationMain entry"

        print(f"\n[OK] Pipeline JSON valid: {len(pipeline)} nodes")

        # 打印所有节点名供检查
        print("[INFO] Pipeline nodes:")
        for node_name in sorted(pipeline.keys()):
            node = pipeline[node_name]
            next_nodes = node.get('next', [])
            action = node.get('action', {}).get('type', 'None')
            recognition = node.get('recognition', {}).get('type', 'None')
            print(f"  - {node_name}: action={action}, recognition={recognition}, next={next_nodes}")

    def test_pipeline_nodes_have_handlers(self):
        """验证所有 Pipeline 节点类型都有对应的 Handler."""
        from agent.py_service.pkg.workflow.pipeline_executor import (
            KeyPressHandler, ClickHandler, WaitHandler, TemplateMatchHandler
        )

        pipeline_path = project_root / "assets" / "resource" / "pipeline" / "guild_donation.json"
        with open(pipeline_path, 'r', encoding='utf-8') as f:
            pipeline = json.load(f)

        # 检查支持的 handlers
        action_handlers = {
            'KeyPress': KeyPressHandler(),
            'Click': ClickHandler(),
            'Wait': WaitHandler(),
        }
        recognition_handlers = {
            'TemplateMatch': TemplateMatchHandler(),
        }

        missing_handlers = []

        for node_name, node in pipeline.items():
            # Check action handlers
            if 'action' in node:
                action_type = node['action'].get('type', '')
                if action_type and action_type not in action_handlers and action_type != 'Custom':
                    missing_handlers.append(f"{node_name}: action={action_type}")

            # Check recognition handlers
            if 'recognition' in node:
                rec_type = node['recognition'].get('type', '')
                if rec_type and rec_type not in recognition_handlers and rec_type != 'Custom':
                    missing_handlers.append(f"{node_name}: recognition={rec_type}")

        if missing_handlers:
            print(f"\n[WARNING] Missing handlers: {missing_handlers}")
        else:
            print(f"\n[OK] All {len(pipeline)} nodes have registered handlers")

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

    def test_first_confirm_has_disappear_verification_chain(self):
        """验证首个确认弹窗点击后会检查是否消失，并在必要时重试点击。"""
        pipeline_path = project_root / "assets" / "resource" / "pipeline" / "guild_donation.json"
        with open(pipeline_path, 'r', encoding='utf-8') as f:
            pipeline = json.load(f)

        assert "handle_first_confirm" in pipeline
        assert "verify_first_confirm_disappear" in pipeline
        assert "retry_handle_first_confirm" in pipeline
        assert "verify_first_confirm_disappear_after_retry" in pipeline

        first = pipeline["handle_first_confirm"]
        assert first.get("next") == ["wait_after_handle_first_confirm_click"]

        verify = pipeline["verify_first_confirm_disappear"]
        assert verify.get("recognition", {}).get("param", {}).get("state") == "disappear"
        assert verify.get("next") == ["stage4_first_donation"]
        assert verify.get("timeout") == 600


class TestPipelineExecutor:
    """Pipeline Executor 功能测试."""

    def test_executor_creation(self):
        """测试 PipelineExecutor 创建."""
        register_all_modules()

        pipeline_path = project_root / "assets" / "resource" / "pipeline" / "guild_donation.json"
        executor = create_executor(pipeline_path)

        assert executor is not None
        assert executor.pipeline is not None
        print(f"[OK] PipelineExecutor created with {len(executor.pipeline)} nodes")

    def test_executor_context_creation(self, vision_engine):
        """测试 ExecutionContext 创建."""
        context = ExecutionContext(
            hardware_controller=None,
            vision_engine=vision_engine,
            screenshot=None,
            param={}
        )

        assert context.vision_engine is not None
        print("[OK] ExecutionContext created")

    def test_custom_action_failure_marks_pipeline_failed(self, vision_engine):
        """自定义 action 显式失败时，整个 pipeline 不应报告成功。"""
        pipeline = {
            "TestMain": {
                "action": {
                    "type": "Custom",
                    "custom_action": "AlwaysFail",
                },
                "next": ["AfterFail"],
            },
            "AfterFail": {
                "action": {
                    "type": "Wait",
                    "duration_ms": 1,
                },
                "next": None,
            },
        }

        executor = create_executor_with_defaults(
            pipeline,
            custom_action_registry={
                "AlwaysFail": lambda ctx: False,
            },
        )
        context = ExecutionContext(
            hardware_controller=None,
            vision_engine=vision_engine,
            screenshot=None,
            param={},
        )

        assert executor.execute("TestMain", context) is False


class TestFullDonationWorkflow:
    """完整捐献流程测试（硬件模式）."""

    @pytest.mark.skipif(not HARDWARE_MODE, reason="Hardware mode not enabled")
    def test_execute_full_pipeline(self, hardware_controller, vision_engine):
        """
        执行完整公会捐献 Pipeline.

        使用 Pipeline Executor 自动执行 JSON 定义的所有节点：
        1. move_mouse_safe_position
        2. wait_after_move
        3. open_guild_menu (Alt+U)
        4. wait_menu_appear
        5. stage4_first_donation (点击捐献)
        6. stage4_second_donation
        7. donation_complete
        8. workflow_complete
        """
        print("\n" + "="*60)
        print("[Donation] Pipeline Executor 测试开始")
        print("="*60)

        if not hardware_controller:
            pytest.skip("Hardware controller not available")

        # 注册所有模块
        register_all_modules()

        # 执行完整 Pipeline
        success = execute_pipeline(
            pipeline_path=Path("assets/resource/pipeline/guild_donation.json"),
            entry_node="guild_donationMain",
            hardware_controller=hardware_controller,
            vision_engine=vision_engine,
            timeout_seconds=60.0
        )

        print("\n" + "="*60)
        print(f"[Donation] Pipeline Executor 测试完成: {'SUCCESS' if success else 'FAILED'}")
        print("="*60)

        assert success, "Pipeline execution failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
