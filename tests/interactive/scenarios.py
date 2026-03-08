"""
Test Scenarios Module - Hardcoded test scenarios for interactive testing.

Provides pre-defined test scenarios for guild donation and character detection
workflows with Chinese instructions.
"""

from typing import List, Optional, Callable
import time
import logging

from tests.interactive.test_flow import TestStep, TestScenario

logger = logging.getLogger(__name__)


# =============================================================================
# Hardware Action Functions
# =============================================================================

def create_mouse_move_action(dx: int = 100, dy: int = 100) -> Callable[[], bool]:
    """Create a mouse move action."""
    def action() -> bool:
        try:
            from core.ferrum_controller import FerrumController
            controller = FerrumController()
            if controller.is_connected():
                controller._move(dx, dy)  # 使用相对移动
                controller.close()
                return True
            controller.close()
            return False
        except Exception as e:
            logger.error(f"Mouse move action failed: {e}")
            return False
    return action


def create_mouse_click_action() -> Callable[[], bool]:
    """Create a mouse click action (click at current position)."""
    def action() -> bool:
        try:
            from core.ferrum_controller import FerrumController
            controller = FerrumController()
            if controller.is_connected():
                # 点击当前位置（不移动，所以delta为0,0）
                controller._send_command(f"km.click(0)")  # 0 = left button
                controller.close()
                return True
            controller.close()
            return False
        except Exception as e:
            logger.error(f"Mouse click action failed: {e}")
            return False
    return action


def create_key_press_action(key_name: str) -> Callable[[], bool]:
    """Create a key press action."""
    def action() -> bool:
        try:
            from core.ferrum_controller import FerrumController
            controller = FerrumController()
            if controller.is_connected():
                controller.press(key_name)  # 使用键名如 "esc"
                controller.close()
                return True
            controller.close()
            return False
        except Exception as e:
            logger.error(f"Key press action failed: {e}")
            return False
    return action


# =============================================================================
# Guild Donation Workflow Scenario
# =============================================================================

def create_wait_action(seconds: int) -> Callable[[], bool]:
    """Create a wait action that pauses for specified seconds."""
    def action() -> bool:
        try:
            print(f"[等待] 暂停 {seconds} 秒，请切换到游戏窗口...")
            time.sleep(seconds)
            return True
        except Exception as e:
            logger.error(f"Wait action failed: {e}")
            return False
    return action


GUILD_DONATION_SCENARIO = TestScenario(
    name="guild_donation",
    description="测试公会捐赠完整流程",
    steps=[
        TestStep(
            step_id="gd_01",
            instruction="准备开始测试，请切换到游戏窗口",
            expected_result="角色选择界面可见，显示角色列表",
            can_skip=False,
            wait_seconds=3
        ),
        TestStep(
            step_id="gd_02",
            instruction="按F11启动账号发现",
            expected_result="系统识别账号并显示角色数量",
            can_skip=True
        ),
        TestStep(
            step_id="gd_03",
            instruction="按F10启动自动化",
            expected_result="第一个角色开始执行公会捐赠",
            can_skip=False
        ),
        TestStep(
            step_id="gd_04",
            instruction="观察ESC菜单是否打开",
            expected_result="ESC菜单出现，显示公会按钮",
            can_skip=False
        ),
        TestStep(
            step_id="gd_05",
            instruction="观察公会界面是否加载",
            expected_result="公会捐赠界面可见",
            can_skip=False
        ),
        TestStep(
            step_id="gd_06",
            instruction="观察捐赠是否完成",
            expected_result="显示捐赠成功提示",
            can_skip=False
        ),
        TestStep(
            step_id="gd_07",
            instruction="观察角色切换",
            expected_result="自动切换到下一个角色",
            can_skip=True
        ),
        TestStep(
            step_id="gd_08",
            instruction="确认所有角色处理完成",
            expected_result="显示自动化完成信息",
            can_skip=False
        ),
    ]
)


# =============================================================================
# Character Detection Scenario
# =============================================================================

CHARACTER_DETECTION_SCENARIO = TestScenario(
    name="character_detection",
    description="测试角色检测和账号识别功能",
    steps=[
        TestStep(
            step_id="cd_01",
            instruction="打开游戏并进入角色选择界面",
            expected_result="角色选择界面可见",
            can_skip=False
        ),
        TestStep(
            step_id="cd_02",
            instruction="确认角色网格布局",
            expected_result="显示3x3角色网格",
            can_skip=False
        ),
        TestStep(
            step_id="cd_03",
            instruction="观察在线状态标签检测",
            expected_result="系统正确识别在线角色",
            can_skip=False
        ),
        TestStep(
            step_id="cd_04",
            instruction="如有多个角色页，观察滚动",
            expected_result="系统正确滚动并计数",
            can_skip=True
        ),
        TestStep(
            step_id="cd_05",
            instruction="确认账号识别结果",
            expected_result="显示正确的账号哈希和角色数量",
            can_skip=False
        ),
        TestStep(
            step_id="cd_06",
            instruction="检查数据库记录",
            expected_result="data/accounts.db 包含新记录",
            can_skip=True
        ),
    ]
)


# =============================================================================
# Scenario Registry
# =============================================================================

ALL_SCENARIOS: List[TestScenario] = [
    GUILD_DONATION_SCENARIO,
    CHARACTER_DETECTION_SCENARIO,
]


def get_scenario_by_name(name: str) -> Optional[TestScenario]:
    """
    Get a scenario by its name.

    Args:
        name: Scenario name to look up.

    Returns:
        TestScenario if found, None otherwise.
    """
    for scenario in ALL_SCENARIOS:
        if scenario.name == name:
            return scenario
    return None


def list_scenario_names() -> List[str]:
    """
    List all available scenario names.

    Returns:
        List of scenario names.
    """
    return [s.name for s in ALL_SCENARIOS]


def list_scenarios_with_descriptions() -> List[tuple]:
    """
    List all scenarios with their descriptions.

    Returns:
        List of (name, description) tuples.
    """
    return [(s.name, s.description) for s in ALL_SCENARIOS]
