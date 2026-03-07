"""
Test Scenarios Module - Hardcoded test scenarios for interactive testing.

Provides pre-defined test scenarios for guild donation and character detection
workflows with Chinese instructions.
"""

from typing import List, Optional

from tests.interactive.test_flow import TestStep, TestScenario


# =============================================================================
# Guild Donation Workflow Scenario
# =============================================================================

GUILD_DONATION_SCENARIO = TestScenario(
    name="guild_donation",
    description="测试公会捐赠完整流程",
    steps=[
        TestStep(
            step_id="gd_01",
            instruction="打开游戏并进入角色选择界面",
            expected_result="角色选择界面可见，显示角色列表",
            can_skip=False
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
