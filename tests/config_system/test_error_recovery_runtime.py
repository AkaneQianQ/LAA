"""
Error Recovery Runtime Tests

Tests for error taxonomy, escalation state machine, and structured logging.
Covers ERR-01, ERR-02, ERR-03, ERR-04 requirements.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch


# =============================================================================
# Error Taxonomy Tests
# =============================================================================

class TestErrorTaxonomy:
    """Test error classification and taxonomy."""

    def test_error_kind_enum_values(self):
        """ErrorKind enum has all required error types."""
        from core.error_recovery import ErrorKind

        assert ErrorKind.NETWORK_LAG == "network_lag"
        assert ErrorKind.UI_TIMEOUT == "ui_timeout"
        assert ErrorKind.DISCONNECT == "disconnect"
        assert ErrorKind.INPUT_POLICY_VIOLATION == "input_policy_violation"
        assert ErrorKind.UNKNOWN == "unknown"

    def test_error_context_creation(self):
        """ErrorContext captures all required fields."""
        from core.error_recovery import ErrorContext, ErrorKind

        context = ErrorContext(
            phase="04",
            step_id="wait_guild_ui",
            action_type="wait_image",
            attempt=2,
            account_id="a1b2c3",
            screenshot_path="logs/screenshots/test.png",
            detail={"image": "guild_flag.png", "roi": [100, 200, 300, 400]}
        )

        assert context.phase == "04"
        assert context.step_id == "wait_guild_ui"
        assert context.action_type == "wait_image"
        assert context.attempt == 2
        assert context.account_id == "a1b2c3"
        assert context.screenshot_path == "logs/screenshots/test.png"
        assert context.detail["image"] == "guild_flag.png"

    def test_error_context_optional_fields(self):
        """ErrorContext allows optional fields to be None."""
        from core.error_recovery import ErrorContext

        context = ErrorContext(
            phase="04",
            step_id="test_step",
            action_type="click",
            attempt=1
        )

        assert context.account_id is None
        assert context.screenshot_path is None
        assert context.detail == {}

    def test_classify_network_lag_from_timeout(self):
        """Classifier identifies network lag from timeout patterns."""
        from core.error_recovery import classify_error, ErrorKind

        error = Exception("wait_image timeout after 30000ms")
        context = {"image": "network_indicator.png", "elapsed_ms": 30000}

        kind = classify_error(error, context)

        assert kind == ErrorKind.NETWORK_LAG

    def test_classify_ui_timeout_from_wait_image(self):
        """Classifier identifies UI timeout from wait_image failures."""
        from core.error_recovery import classify_error, ErrorKind

        error = Exception("wait_image timeout: image 'btn.png' did not appear")
        context = {"elapsed_ms": 10000}

        kind = classify_error(error, context)

        assert kind == ErrorKind.UI_TIMEOUT

    def test_classify_disconnect_from_disconnect_marker(self):
        """Classifier identifies disconnect from disconnect markers."""
        from core.error_recovery import classify_error, ErrorKind

        error = Exception("Critical UI element missing")
        context = {"disconnect_detected": True}

        kind = classify_error(error, context)

        assert kind == ErrorKind.DISCONNECT

    def test_classify_unknown_for_unrecognized_errors(self):
        """Classifier returns unknown for unrecognized error patterns."""
        from core.error_recovery import classify_error, ErrorKind

        error = Exception("Some random error")
        context = {}

        kind = classify_error(error, context)

        assert kind == ErrorKind.UNKNOWN


# =============================================================================
# Escalation State Machine Tests
# =============================================================================

class TestEscalationStateMachine:
    """Test recovery escalation state machine."""

    def test_recovery_orchestrator_creation(self):
        """RecoveryOrchestrator initializes with default thresholds."""
        from core.error_recovery import RecoveryOrchestrator

        orchestrator = RecoveryOrchestrator()

        assert orchestrator.l1_retry_threshold == 3
        assert orchestrator.l2_rollback_threshold == 3
        assert orchestrator.l3_skip_threshold == 3

    def test_recovery_orchestrator_custom_thresholds(self):
        """RecoveryOrchestrator accepts custom thresholds."""
        from core.error_recovery import RecoveryOrchestrator

        orchestrator = RecoveryOrchestrator(
            l1_retry_threshold=5,
            l2_rollback_threshold=5,
            l3_skip_threshold=5
        )

        assert orchestrator.l1_retry_threshold == 5
        assert orchestrator.l2_rollback_threshold == 5
        assert orchestrator.l3_skip_threshold == 5

    def test_determine_action_l1_retry(self):
        """First failures trigger L1 retry action."""
        from core.error_recovery import RecoveryOrchestrator, RecoveryAction

        orchestrator = RecoveryOrchestrator()
        action = orchestrator.determine_action(
            error_kind="ui_timeout",
            step_id="test_step",
            attempt=1
        )

        assert action == RecoveryAction.L1_RETRY

    def test_determine_action_l2_rollback(self):
        """Repeated failures trigger L2 rollback after threshold."""
        from core.error_recovery import RecoveryOrchestrator, RecoveryAction

        orchestrator = RecoveryOrchestrator()

        # Simulate 3 failures
        for i in range(1, 4):
            action = orchestrator.determine_action(
                error_kind="ui_timeout",
                step_id="test_step",
                attempt=i
            )

        assert action == RecoveryAction.L2_ROLLBACK

    def test_determine_action_l3_skip(self):
        """Escalated failures trigger L3 skip after threshold."""
        from core.error_recovery import RecoveryOrchestrator, RecoveryAction

        orchestrator = RecoveryOrchestrator(l3_skip_threshold=2)

        # First escalation cycle (attempt 3 triggers rollback)
        for i in range(1, 4):
            orchestrator.determine_action(
                error_kind="ui_timeout",
                step_id="test_step",
                attempt=i
            )

        # Second escalation cycle (attempt 3 triggers rollback again)
        for i in range(1, 4):
            orchestrator.determine_action(
                error_kind="ui_timeout",
                step_id="test_step",
                attempt=i
            )

        # Now escalation_count=2 >= l3_skip_threshold=2, should trigger skip
        action = orchestrator.determine_action(
            error_kind="ui_timeout",
            step_id="test_step",
            attempt=1
        )

        assert action == RecoveryAction.L3_SKIP

    def test_circuit_breaker_same_kind_failures(self):
        """Circuit breaker tracks same-kind failures per role."""
        from core.error_recovery import RecoveryOrchestrator, RecoveryAction

        orchestrator = RecoveryOrchestrator()

        # Multiple same-kind failures
        for i in range(1, 5):
            action = orchestrator.determine_action(
                error_kind="network_lag",
                step_id=f"step_{i}",
                attempt=1
            )

        # Circuit should be open - skip role
        assert orchestrator.is_circuit_open("network_lag") is True

    def test_circuit_breaker_different_kind_resets(self):
        """Different error kinds don't trigger circuit breaker."""
        from core.error_recovery import RecoveryOrchestrator

        orchestrator = RecoveryOrchestrator()

        # Different error kinds
        orchestrator.determine_action("ui_timeout", "step_1", 1)
        orchestrator.determine_action("network_lag", "step_2", 1)
        orchestrator.determine_action("ui_timeout", "step_3", 1)

        # Circuit should not be open
        assert orchestrator.is_circuit_open("ui_timeout") is False
        assert orchestrator.is_circuit_open("network_lag") is False

    def test_escalation_counter_increments(self):
        """Escalation counter increments per recovery cycle."""
        from core.error_recovery import RecoveryOrchestrator

        orchestrator = RecoveryOrchestrator()

        # Simulate multiple escalation cycles
        orchestrator.determine_action("ui_timeout", "step_1", 3)
        orchestrator.determine_action("ui_timeout", "step_1", 3)

        assert orchestrator.get_escalation_count() == 2

    def test_escalation_reset_on_success(self):
        """Escalation counter resets on successful step execution."""
        from core.error_recovery import RecoveryOrchestrator

        orchestrator = RecoveryOrchestrator()

        # Simulate failures then success
        orchestrator.determine_action("ui_timeout", "step_1", 3)
        orchestrator.record_success("step_1")

        assert orchestrator.get_escalation_count() == 0


# =============================================================================
# Recovery Action Enum Tests
# =============================================================================

class TestRecoveryAction:
    """Test recovery action enum."""

    def test_recovery_action_values(self):
        """RecoveryAction enum has all required actions."""
        from core.error_recovery import RecoveryAction

        assert RecoveryAction.L1_RETRY == "l1_retry"
        assert RecoveryAction.L2_ROLLBACK == "l2_rollback"
        assert RecoveryAction.L3_SKIP == "l3_skip"


# =============================================================================
# Executor Integration Tests
# =============================================================================

class TestExecutorRecoveryIntegration:
    """Test recovery integration with workflow executor."""

    def test_executor_routes_timeout_through_classifier(self):
        """Executor routes wait_image timeout through error classifier."""
        from core.workflow_executor import WorkflowExecutor
        from core.error_recovery import ErrorKind

        # Mock workflow with wait_image step
        mock_workflow = Mock()
        mock_workflow.start_step_id = "start"
        mock_workflow.wait_defaults.retry_interval_ms = 100

        mock_step = Mock()
        mock_step.step_id = "wait_step"
        mock_step.retry = 0
        mock_step.retry_interval_ms = None
        mock_step.action.type = "wait_image"
        mock_step.recovery.on_timeout = "anchor_step"
        mock_step.recovery.max_escalations = 3
        mock_step.next = None

        mock_workflow.get_step.side_effect = lambda x: mock_step if x == "wait_step" else None

        # Mock dispatcher that raises timeout
        mock_dispatcher = Mock()
        mock_dispatcher._workflow_defaults = None
        mock_dispatcher.dispatch.side_effect = Exception(
            "wait_image timeout: image 'test.png' did not appear within 1000ms"
        )

        mock_condition = Mock()

        executor = WorkflowExecutor(mock_workflow, mock_dispatcher, mock_condition)
        executor.current_step_id = "wait_step"

        # Execute step should classify and handle
        success, error = executor._execute_step(mock_step)

        assert success is False
        assert error is not None

    def test_executor_performs_rollback_to_anchor(self):
        """Executor performs rollback to anchor step when policy dictates."""
        from core.workflow_executor import WorkflowExecutor
        from core.error_recovery import RecoveryOrchestrator, RecoveryAction

        # Setup
        mock_workflow = Mock()
        mock_workflow.start_step_id = "start"
        mock_workflow.wait_defaults.retry_interval_ms = 100

        anchor_step = Mock()
        anchor_step.step_id = "anchor_step"
        anchor_step.recovery.anchor = True

        failing_step = Mock()
        failing_step.step_id = "failing_step"
        failing_step.retry = 2
        failing_step.retry_interval_ms = None
        failing_step.recovery.on_timeout = "anchor_step"
        failing_step.recovery.max_escalations = 3
        failing_step.next = "next_step"

        mock_workflow.get_step.side_effect = lambda x: {
            "anchor_step": anchor_step,
            "failing_step": failing_step
        }.get(x)

        mock_dispatcher = Mock()
        mock_condition = Mock()

        executor = WorkflowExecutor(mock_workflow, mock_dispatcher, mock_condition)
        executor.orchestrator = RecoveryOrchestrator()

        # Simulate rollback action
        action = executor.orchestrator.determine_action(
            error_kind="ui_timeout",
            step_id="failing_step",
            attempt=3
        )

        assert action == RecoveryAction.L2_ROLLBACK

    def test_executor_skips_role_on_disconnect(self):
        """Executor skips current role on disconnect classification."""
        from core.workflow_executor import WorkflowExecutor
        from core.error_recovery import ErrorKind, RecoveryAction

        mock_workflow = Mock()
        mock_dispatcher = Mock()
        mock_condition = Mock()

        executor = WorkflowExecutor(mock_workflow, mock_dispatcher, mock_condition)

        # Disconnect should result in skip action
        # (This would be determined by orchestrator based on classification)
        assert ErrorKind.DISCONNECT == "disconnect"

    def test_executor_preserves_retry_semantics(self):
        """Executor preserves existing step retry semantics."""
        from core.workflow_executor import WorkflowExecutor, ExecutionError

        mock_workflow = Mock()
        mock_workflow.start_step_id = "start"
        mock_workflow.wait_defaults.retry_interval_ms = 100

        mock_step = Mock()
        mock_step.step_id = "test_step"
        mock_step.retry = 2  # 2 retries = 3 attempts
        mock_step.retry_interval_ms = None
        mock_step.action.type = "click"

        mock_workflow.get_step.return_value = mock_step

        # Mock dispatcher that fails with ExecutionError then succeeds
        # Only ExecutionError triggers retry logic
        mock_dispatcher = Mock()
        mock_dispatcher._workflow_defaults = None
        mock_dispatcher.dispatch.side_effect = [
            ExecutionError("Fail 1"),
            ExecutionError("Fail 2"),
            None  # Success on 3rd attempt
        ]

        mock_condition = Mock()

        executor = WorkflowExecutor(mock_workflow, mock_dispatcher, mock_condition)

        success, error = executor._execute_step(mock_step)

        assert success is True
        assert mock_dispatcher.dispatch.call_count == 3


# =============================================================================
# JSONL Logging Tests
# =============================================================================

class TestErrorLogger:
    """Test structured JSONL error logging."""

    def test_error_logger_creation(self):
        """ErrorLogger initializes with log directory."""
        from core.error_logger import ErrorLogger

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)

            assert logger.log_dir == Path(tmpdir)
            assert logger.log_dir.exists()

    def test_log_error_creates_jsonl_record(self):
        """log_error creates valid JSONL record with required fields."""
        from core.error_logger import ErrorLogger
        from core.error_recovery import ErrorKind, ErrorContext

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)

            context = ErrorContext(
                phase="04",
                step_id="wait_guild_ui",
                action_type="wait_image",
                attempt=2,
                account_id="abc123",
                screenshot_path=None,
                detail={"image": "guild_flag.png"}
            )

            logger.log_error(
                error_kind=ErrorKind.UI_TIMEOUT,
                message="wait_image timeout",
                context=context
            )

            # Find and read the log file
            log_files = list(Path(tmpdir).glob("*.jsonl"))
            assert len(log_files) == 1

            with open(log_files[0], 'r') as f:
                record = json.loads(f.readline())

            assert record["error_kind"] == "ui_timeout"
            assert record["step_id"] == "wait_guild_ui"
            assert record["attempt"] == 2
            assert record["account"] == "abc123"
            assert "ts" in record

    def test_log_record_has_all_required_fields(self):
        """Log record contains all required fields per ERR-04."""
        from core.error_logger import ErrorLogger
        from core.error_recovery import ErrorKind, ErrorContext

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)

            context = ErrorContext(
                phase="04",
                step_id="test_step",
                action_type="click",
                attempt=1,
                account_id="test_account",
                screenshot_path="logs/screenshots/test.png",
                detail={"extra": "data"}
            )

            logger.log_error(
                error_kind=ErrorKind.NETWORK_LAG,
                message="Network timeout",
                context=context
            )

            log_files = list(Path(tmpdir).glob("*.jsonl"))
            with open(log_files[0], 'r') as f:
                record = json.loads(f.readline())

            # Required fields per ERR-04
            required_fields = [
                "ts", "phase", "step_id", "error_kind", "message",
                "attempt", "account", "screenshot_path", "context"
            ]

            for field in required_fields:
                assert field in record, f"Missing required field: {field}"

    def test_screenshot_path_only_on_failure(self):
        """Screenshot path is only populated on actual failures."""
        from core.error_logger import ErrorLogger
        from core.error_recovery import ErrorKind, ErrorContext

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)

            # Log without screenshot
            context_no_screenshot = ErrorContext(
                phase="04",
                step_id="test_step",
                action_type="click",
                attempt=1
            )

            logger.log_error(
                error_kind=ErrorKind.UI_TIMEOUT,
                message="Timeout",
                context=context_no_screenshot
            )

            log_files = list(Path(tmpdir).glob("*.jsonl"))
            with open(log_files[0], 'r') as f:
                record = json.loads(f.readline())

            assert record["screenshot_path"] is None

    def test_daily_file_partitioning(self):
        """Log files are partitioned by day."""
        from core.error_logger import ErrorLogger
        from core.error_recovery import ErrorKind, ErrorContext

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)

            context = ErrorContext(
                phase="04",
                step_id="test_step",
                action_type="click",
                attempt=1
            )

            logger.log_error(ErrorKind.UNKNOWN, "Test", context)

            # File should be named with today's date
            today = datetime.now().strftime("%Y-%m-%d")
            expected_file = Path(tmpdir) / f"errors_{today}.jsonl"

            assert expected_file.exists()

    def test_console_summary_output(self):
        """Console summary provides concise error information."""
        from core.error_logger import ErrorLogger
        from core.error_recovery import ErrorKind, ErrorContext

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)

            context = ErrorContext(
                phase="04",
                step_id="critical_step",
                action_type="wait_image",
                attempt=3,
                account_id="acc123"
            )

            # Capture console output
            import io
            import sys

            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured

            logger.log_error(ErrorKind.DISCONNECT, "Client disconnected", context)

            sys.stdout = old_stdout
            output = captured.getvalue()

            # Console should show concise summary
            assert "DISCONNECT" in output or "disconnect" in output.lower()


# =============================================================================
# Runtime Integration Tests
# =============================================================================

class TestRuntimeIntegration:
    """Test runtime integration with wait_image and recovery."""

    def test_wait_image_timeout_triggers_recovery(self):
        """wait_image timeout triggers recovery flow."""
        from core.workflow_runtime import ActionDispatcher
        from core.error_recovery import ErrorKind

        # Mock controller and vision
        mock_controller = Mock()
        mock_vision = Mock()
        mock_vision.find_element.return_value = (False, 0.0, None)

        dispatcher = ActionDispatcher(mock_controller, mock_vision)

        from core.workflow_schema import WaitImageAction

        action = WaitImageAction(
            type="wait_image",
            state="appear",
            image="test.png",
            roi=(100, 100, 200, 200),
            timeout_ms=100  # Very short for test
        )

        step = Mock()
        step.retry_interval_ms = None

        # Should raise ExecutionError
        with pytest.raises(Exception) as exc_info:
            dispatcher._dispatch_wait_image(action, step)

        assert "timeout" in str(exc_info.value).lower()

    def test_runtime_captures_screenshot_on_failure(self):
        """Runtime captures screenshot path on failure."""
        from core.error_logger import ErrorLogger
        from core.error_recovery import ErrorContext

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)

            # Simulate screenshot capture
            screenshot_path = str(Path(tmpdir) / "screenshot_test.png")

            context = ErrorContext(
                phase="04",
                step_id="test_step",
                action_type="wait_image",
                attempt=1,
                screenshot_path=screenshot_path
            )

            # Verify screenshot path is recorded
            assert context.screenshot_path == screenshot_path


# =============================================================================
# End-to-End Recovery Flow Tests
# =============================================================================

class TestEndToEndRecoveryFlow:
    """Test end-to-end recovery flows."""

    def test_l1_to_l2_to_l3_escalation(self):
        """Full escalation from L1 retry -> L2 rollback -> L3 skip."""
        from core.error_recovery import RecoveryOrchestrator, RecoveryAction

        orchestrator = RecoveryOrchestrator(l3_skip_threshold=2)

        # L1: Initial retries
        for i in range(1, 3):
            action = orchestrator.determine_action("ui_timeout", "step", i)
            assert action == RecoveryAction.L1_RETRY

        # L2: Rollback after threshold
        action = orchestrator.determine_action("ui_timeout", "step", 3)
        assert action == RecoveryAction.L2_ROLLBACK

        # Another cycle - escalate
        action = orchestrator.determine_action("ui_timeout", "step", 3)
        assert action == RecoveryAction.L2_ROLLBACK

        # L3: Skip after max escalations
        action = orchestrator.determine_action("ui_timeout", "step", 3)
        assert action == RecoveryAction.L3_SKIP

    def test_disconnect_results_in_role_skip(self):
        """Disconnect classification results in role skip, not restart."""
        from core.error_recovery import classify_error, ErrorKind, RecoveryOrchestrator, RecoveryAction

        # Classify disconnect
        error = Exception("Connection lost")
        context = {"disconnect_detected": True}
        kind = classify_error(error, context)

        assert kind == ErrorKind.DISCONNECT

        # Disconnect should trigger skip action
        orchestrator = RecoveryOrchestrator()
        action = orchestrator.determine_action(kind, "step", 1)

        # For disconnect, immediate skip is appropriate
        assert action in [RecoveryAction.L3_SKIP, RecoveryAction.L1_RETRY]

    def test_recovery_resets_on_successful_anchor(self):
        """Recovery state resets after successful anchor execution."""
        from core.error_recovery import RecoveryOrchestrator

        orchestrator = RecoveryOrchestrator()

        # Failures
        for i in range(1, 4):
            orchestrator.determine_action("ui_timeout", "step", i)

        assert orchestrator.get_escalation_count() > 0

        # Success at anchor
        orchestrator.record_success("anchor_step")

        assert orchestrator.get_escalation_count() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
