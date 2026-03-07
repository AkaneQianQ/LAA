"""
Test Flow Module - Orchestration for interactive test scenarios.

Manages test scenario execution, step progression, and integration with
overlay UI and test logger.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional, Any
import logging

from tests.interactive.overlay import TestOverlay
from tests.interactive.test_logger import TestLogger, StepResult


logger_module = logging.getLogger(__name__)


class TestState(Enum):
    """Test flow state machine states."""
    IDLE = "idle"
    WAITING_FOR_START = "waiting_for_start"
    RUNNING = "running"
    WAITING_FOR_FEEDBACK = "waiting_for_feedback"
    COMPLETED = "completed"
    TERMINATED = "terminated"


@dataclass
class TestStep:
    """Definition of a single test step."""
    step_id: str
    instruction: str  # What user should do/see
    expected_result: str  # What should happen
    can_skip: bool = True  # Whether user can skip this step


@dataclass
class TestScenario:
    """Definition of a test scenario with multiple steps."""
    name: str
    description: str
    steps: List[TestStep] = field(default_factory=list)


class TestFlow:
    """
    Orchestrates test scenario execution.

    Manages state machine, step progression, and integration with
    overlay UI and test logger.
    """

    def __init__(self, overlay: TestOverlay, logger: TestLogger):
        """
        Initialize TestFlow.

        Args:
            overlay: TestOverlay instance for UI display.
            logger: TestLogger instance for result persistence.
        """
        self.overlay = overlay
        self.logger = logger
        self.scenario: Optional[TestScenario] = None
        self.state = TestState.IDLE
        self.current_step_index = -1
        self.test_id: Optional[str] = None
        self._current_feedback: Optional[str] = None
        self._hotkey_callbacks: Dict[str, Callable[[], None]] = {}

        logger_module.debug("TestFlow initialized")

    def load_scenario(self, scenario: TestScenario) -> None:
        """
        Load a test scenario to run.

        Args:
            scenario: TestScenario to execute.
        """
        self.scenario = scenario
        self.state = TestState.WAITING_FOR_START
        self.current_step_index = -1
        logger_module.info(f"Loaded scenario: {scenario.name} with {len(scenario.steps)} steps")

    def start(self) -> None:
        """Begin test flow (shows ready prompt, waits for F1)."""
        if self.scenario is None:
            self._show_error("No scenario loaded. Call load_scenario() first.")
            return

        self.state = TestState.WAITING_FOR_START
        self.test_id = self.logger.start_test(self.scenario.name)

        # Show ready prompt
        ready_text = (
            f"准备就绪？\n"
            f"场景: {self.scenario.description}\n"
            f"步骤数: {len(self.scenario.steps)}\n\n"
            f"按 F1 开始测试"
        )
        self.overlay.set_instruction(ready_text)
        logger_module.info(f"Test started: {self.test_id}")

    def next_step(self) -> None:
        """
        Advance to next step (called on F1).

        If currently waiting for start, begins first step.
        If currently waiting for feedback, advances after recording.
        """
        if self.state == TestState.WAITING_FOR_START:
            # Start the first step
            self._begin_step(0)
            return

        if self.state == TestState.WAITING_FOR_FEEDBACK:
            # Record feedback and advance
            if self._current_feedback is not None:
                self._record_current_step()
                self._current_feedback = None

            # Check if there are more steps
            if self.current_step_index + 1 < len(self.scenario.steps):
                self._begin_step(self.current_step_index + 1)
            else:
                self._complete_test()
            return

        if self.state == TestState.RUNNING:
            # User pressed F1 without giving feedback, show reminder
            self._show_feedback_reminder()
            return

    def _begin_step(self, index: int) -> None:
        """Begin a specific step."""
        if self.scenario is None or index >= len(self.scenario.steps):
            self._complete_test()
            return

        self.current_step_index = index
        self.state = TestState.RUNNING
        self._current_feedback = None

        step = self.scenario.steps[index]
        step_text = (
            f"步骤 {index + 1}/{len(self.scenario.steps)}\n"
            f"指令: {step.instruction}\n"
            f"预期: {step.expected_result}"
        )
        if step.can_skip:
            step_text += "\n\n按 Y 通过, N 失败, F1 跳过"
        else:
            step_text += "\n\n按 Y 通过, N 失败"

        self.overlay.set_instruction(step_text)
        logger_module.debug(f"Started step {index + 1}: {step.step_id}")

    def record_feedback(self, feedback: str) -> None:
        """
        Record Y/N/SKIP feedback for current step.

        Args:
            feedback: "Y", "N", or "SKIP"
        """
        if self.state != TestState.RUNNING:
            logger_module.warning(f"Cannot record feedback in state {self.state}")
            return

        self._current_feedback = feedback
        self.state = TestState.WAITING_FOR_FEEDBACK

        # Show confirmation and prompt for next step
        step = self.scenario.steps[self.current_step_index]
        confirm_text = (
            f"步骤 {self.current_step_index + 1}/{len(self.scenario.steps)}\n"
            f"指令: {step.instruction}\n"
            f"反馈: {'通过' if feedback == 'Y' else '失败' if feedback == 'N' else '跳过'}\n\n"
            f"按 F1 继续下一步"
        )
        self.overlay.set_instruction(confirm_text)
        logger_module.debug(f"Recorded feedback for step {self.current_step_index + 1}: {feedback}")

    def skip_step(self) -> None:
        """Skip current step (if allowed)."""
        if self.state != TestState.RUNNING:
            return

        step = self.scenario.steps[self.current_step_index]
        if not step.can_skip:
            self.overlay.set_instruction("此步骤不能跳过\n\n请按 Y 或 N 提供反馈")
            return

        self.record_feedback("SKIP")

    def terminate(self) -> None:
        """End test early (called on END)."""
        if self.test_id:
            self.logger.end_test(self.test_id, "INCOMPLETE")

        self.state = TestState.TERMINATED
        self.overlay.set_instruction("测试已终止\n按 END 关闭")
        logger_module.info(f"Test terminated: {self.test_id}")

    def _record_current_step(self) -> None:
        """Record the current step result to logger."""
        if self.test_id is None or self.scenario is None:
            return

        step = self.scenario.steps[self.current_step_index]
        step_result = StepResult(
            step_number=self.current_step_index + 1,
            instruction=step.instruction,
            expected_result=step.expected_result,
            user_feedback=self._current_feedback or "N",
            timestamp=datetime.now().isoformat()
        )
        self.logger.log_step(self.test_id, step_result)

    def _complete_test(self) -> None:
        """Mark test as completed."""
        if self.test_id:
            # Determine overall result based on step feedback
            result = self.logger.get_test_result(self.test_id)
            if result:
                has_fail = any(s.user_feedback == "N" for s in result.steps)
                overall = "FAIL" if has_fail else "PASS"
            else:
                overall = "INCOMPLETE"

            self.logger.end_test(self.test_id, overall)

        self.state = TestState.COMPLETED
        self.overlay.set_instruction(f"测试完成！\n结果: {overall}\n按 END 关闭")
        logger_module.info(f"Test completed: {self.test_id} with result {overall}")

    def _show_feedback_reminder(self) -> None:
        """Show reminder to provide feedback."""
        step = self.scenario.steps[self.current_step_index]
        reminder_text = (
            f"步骤 {self.current_step_index + 1}/{len(self.scenario.steps)}\n"
            f"指令: {step.instruction}\n"
            f"预期: {step.expected_result}\n\n"
            f"请先按 Y 或 N 提供反馈，然后按 F1 继续"
        )
        self.overlay.set_instruction(reminder_text)

    def _show_error(self, message: str) -> None:
        """Display error message in overlay."""
        self.overlay.set_instruction(f"错误: {message}\n按 END 关闭")
        logger_module.error(message)

    def get_current_state(self) -> Dict[str, Any]:
        """
        Get current test flow state.

        Returns:
            Dictionary with state information.
        """
        return {
            "state": self.state.value,
            "scenario_name": self.scenario.name if self.scenario else None,
            "current_step": self.current_step_index + 1 if self.current_step_index >= 0 else None,
            "total_steps": len(self.scenario.steps) if self.scenario else 0,
            "test_id": self.test_id
        }

    def setup_hotkeys(self) -> None:
        """Register hotkeys with the overlay."""
        self._hotkey_callbacks = {
            "f1": self.next_step,
            "end": self.terminate,
            "y": lambda: self.record_feedback("Y"),
            "n": lambda: self.record_feedback("N"),
        }
        self.overlay.register_hotkeys(self._hotkey_callbacks)
        logger_module.debug("Hotkeys registered")


# =============================================================================
# Unit Tests
# =============================================================================

import pytest


class TestTestFlow:
    """Unit tests for TestFlow class."""

    @pytest.fixture
    def mock_overlay(self):
        """Provide mock overlay."""
        class MockOverlay:
            def __init__(self):
                self.instructions = []
                self._hotkeys = {}

            def set_instruction(self, text):
                self.instructions.append(text)

            def is_visible(self):
                return True

            def register_hotkeys(self, callbacks):
                self._hotkeys = callbacks

            def unregister_hotkeys(self):
                self._hotkeys = {}

        return MockOverlay()

    @pytest.fixture
    def temp_logger(self, tmp_path):
        """Provide TestLogger with temp directory."""
        return TestLogger(str(tmp_path / "logs"))

    @pytest.fixture
    def flow(self, mock_overlay, temp_logger):
        """Provide TestFlow instance."""
        return TestFlow(mock_overlay, temp_logger)

    @pytest.fixture
    def sample_scenario(self):
        """Provide sample test scenario."""
        return TestScenario(
            name="test_scenario",
            description="Test description",
            steps=[
                TestStep("step1", "Instruction 1", "Expected 1"),
                TestStep("step2", "Instruction 2", "Expected 2"),
            ]
        )

    def test_load_scenario(self, flow, sample_scenario):
        """Test loading a scenario."""
        flow.load_scenario(sample_scenario)
        assert flow.scenario.name == "test_scenario"
        assert len(flow.scenario.steps) == 2
        assert flow.state == TestState.WAITING_FOR_START

    def test_start_shows_ready_prompt(self, flow, sample_scenario, mock_overlay):
        """Test that start shows ready prompt."""
        flow.load_scenario(sample_scenario)
        flow.start()
        assert "准备就绪" in mock_overlay.instructions[0]

    def test_next_step_advances(self, flow, sample_scenario, mock_overlay):
        """Test advancing to next step."""
        flow.load_scenario(sample_scenario)
        flow.start()
        flow.next_step()  # From ready prompt to step 1
        assert "步骤 1/2" in mock_overlay.instructions[-1]

    def test_record_feedback_logs_step(self, flow, sample_scenario, temp_logger):
        """Test that feedback is logged."""
        flow.load_scenario(sample_scenario)
        flow.start()
        flow.next_step()
        flow.record_feedback("Y")

        # Verify logger has the step
        result = temp_logger.get_test_result(flow.test_id)
        assert len(result.steps) == 0  # Not logged yet, waiting for next_step

        flow.next_step()  # This triggers logging
        result = temp_logger.get_test_result(flow.test_id)
        assert len(result.steps) == 1
        assert result.steps[0].user_feedback == "Y"

    def test_terminate_ends_early(self, flow, sample_scenario, temp_logger):
        """Test early termination."""
        flow.load_scenario(sample_scenario)
        flow.start()
        flow.terminate()
        assert flow.state == TestState.TERMINATED

        result = temp_logger.get_test_result(flow.test_id)
        assert result.overall_result == "INCOMPLETE"

    def test_complete_test(self, flow, sample_scenario, mock_overlay):
        """Test completing all steps."""
        flow.load_scenario(sample_scenario)
        flow.start()

        # Go through all steps
        flow.next_step()  # Start step 1
        flow.record_feedback("Y")
        flow.next_step()  # Start step 2
        flow.record_feedback("Y")
        flow.next_step()  # Complete

        assert flow.state == TestState.COMPLETED
        assert "测试完成" in mock_overlay.instructions[-1]

    def test_skip_step(self, flow, sample_scenario):
        """Test skipping a step."""
        flow.load_scenario(sample_scenario)
        flow.start()
        flow.next_step()
        flow.skip_step()
        assert flow._current_feedback == "SKIP"

    def test_cannot_skip_non_skippable(self, flow):
        """Test that non-skippable steps cannot be skipped."""
        scenario = TestScenario(
            name="non_skippable",
            description="Test",
            steps=[
                TestStep("step1", "Instruction", "Expected", can_skip=False)
            ]
        )
        flow.load_scenario(scenario)
        flow.start()
        flow.next_step()
        flow.skip_step()
        # Should not change feedback since step cannot be skipped
        assert flow._current_feedback is None
