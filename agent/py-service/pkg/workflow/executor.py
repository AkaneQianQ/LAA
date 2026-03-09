"""
Workflow Executor Module

Provides deterministic step execution for compiled workflows.
Implements explicit cursor-based step progression with retry policy handling
and recovery orchestration for error resilience.

Exports:
    WorkflowExecutor: Main executor for running compiled workflows
    ExecutionResult: Result object containing execution metadata
    ExecutionError: Exception raised for step execution failures
"""

from typing import Optional, Any
from dataclasses import dataclass, field
from core.workflow_compiler import CompiledWorkflow
from core.workflow_schema import WorkflowStep
from core.error_recovery import (
    RecoveryOrchestrator, RecoveryAction, ErrorKind, classify_error, ErrorContext
)
from core.error_logger import ErrorLogger


class ExecutionError(Exception):
    """Raised when a workflow step fails execution."""
    pass


class RoleSkipError(Exception):
    """Raised when a role should be skipped (e.g., disconnect)."""
    pass


@dataclass
class ExecutionResult:
    """Result of a workflow execution."""
    success: bool
    steps_executed: int
    final_step_id: Optional[str]
    error: Optional[Exception] = None
    duration_ms: Optional[float] = None
    skipped_role: bool = False  # True if role was skipped due to disconnect/recovery


class WorkflowExecutor:
    """
    Executes compiled workflows with deterministic step traversal.

    Features:
    - Explicit cursor-based step progression
    - Per-step retry policy handling
    - Loop safety with execution cap guard
    - Stop-on-failure default behavior
    """

    # Maximum steps to prevent infinite loops
    MAX_STEPS = 1000

    def __init__(
        self,
        workflow: CompiledWorkflow,
        action_dispatcher: Any,
        condition_evaluator: Any,
        error_logger: Optional[ErrorLogger] = None,
        account_id: Optional[str] = None
    ):
        """
        Initialize the workflow executor.

        Args:
            workflow: Compiled workflow to execute
            action_dispatcher: Object with dispatch(step) method for actions
            condition_evaluator: Object with evaluate(step, screenshot) method
            error_logger: Optional ErrorLogger for structured error logging
            account_id: Optional account ID for error context
        """
        self.workflow = workflow
        self.dispatcher = action_dispatcher
        self.condition = condition_evaluator
        self.error_logger = error_logger or ErrorLogger()
        self.account_id = account_id
        self.steps_executed = 0
        self.current_step_id: Optional[str] = None
        self.orchestrator = RecoveryOrchestrator()
        self._recovery_attempt_count: dict[str, int] = {}

    def execute(self) -> ExecutionResult:
        """
        Execute the workflow from start to completion with recovery handling.

        Returns:
            ExecutionResult with success status and metadata
        """
        import time

        start_time = time.time()
        self.steps_executed = 0
        self.current_step_id = self.workflow.start_step_id
        last_executed_step_id: Optional[str] = None

        try:
            while self.current_step_id is not None:
                # Loop guard: prevent infinite execution
                if self.steps_executed >= self.MAX_STEPS:
                    return ExecutionResult(
                        success=False,
                        steps_executed=self.steps_executed,
                        final_step_id=last_executed_step_id,
                        error=ExecutionError(
                            f"Loop guard triggered: exceeded {self.MAX_STEPS} steps"
                        ),
                        duration_ms=(time.time() - start_time) * 1000
                    )

                # Get current step
                step = self.workflow.get_step(self.current_step_id)
                if step is None:
                    return ExecutionResult(
                        success=False,
                        steps_executed=self.steps_executed,
                        final_step_id=last_executed_step_id,
                        error=ExecutionError(
                            f"Step '{self.current_step_id}' not found in workflow"
                        ),
                        duration_ms=(time.time() - start_time) * 1000
                    )

                # Execute step with retry logic and recovery
                success, error = self._execute_step_with_recovery(step)

                if not success:
                    # Check if this is a skip result (role skip, not failure)
                    if isinstance(error, RoleSkipError):
                        return ExecutionResult(
                            success=True,  # Not a failure, just skipped
                            steps_executed=self.steps_executed,
                            final_step_id=last_executed_step_id,
                            error=None,
                            duration_ms=(time.time() - start_time) * 1000,
                            skipped_role=True
                        )

                    return ExecutionResult(
                        success=False,
                        steps_executed=self.steps_executed,
                        final_step_id=self.current_step_id,
                        error=error,
                        duration_ms=(time.time() - start_time) * 1000
                    )

                # Track last successfully executed step
                last_executed_step_id = self.current_step_id

                # Get current step for next resolution (may have changed due to recovery)
                current_step = self.workflow.get_step(self.current_step_id)
                if current_step is None:
                    return ExecutionResult(
                        success=False,
                        steps_executed=self.steps_executed,
                        final_step_id=last_executed_step_id,
                        error=ExecutionError(
                            f"Step '{self.current_step_id}' not found in workflow during next resolution"
                        ),
                        duration_ms=(time.time() - start_time) * 1000
                    )

                # Determine next step
                self.current_step_id = self._resolve_next_step(current_step)

            # Workflow completed successfully
            return ExecutionResult(
                success=True,
                steps_executed=self.steps_executed,
                final_step_id=last_executed_step_id,
                error=None,
                duration_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                steps_executed=self.steps_executed,
                final_step_id=self.current_step_id,
                error=e,
                duration_ms=(time.time() - start_time) * 1000
            )

    def _execute_step(self, step: WorkflowStep) -> tuple[bool, Optional[Exception]]:
        """
        Execute a single step with retry handling.

        Args:
            step: The workflow step to execute

        Returns:
            Tuple of (success, error)
        """
        import time

        # Get retry count from step (default: 0 = no retries)
        retry_count = getattr(step, 'retry', 0)
        max_attempts = retry_count + 1  # Initial attempt + retries

        # Get retry interval (step override > workflow default)
        retry_interval_ms = self._resolve_retry_interval_ms(step)
        retry_interval_sec = retry_interval_ms / 1000.0

        last_error: Optional[Exception] = None

        for attempt in range(max_attempts):
            try:
                # Pass workflow defaults to dispatcher for wait_image resolution
                if hasattr(self.workflow, 'wait_defaults'):
                    self.dispatcher._workflow_defaults = self.workflow.wait_defaults
                self.dispatcher.dispatch(step)
                self.steps_executed += 1
                return True, None
            except ExecutionError as e:
                last_error = e
                if attempt < max_attempts - 1:
                    # Will retry - wait configured interval before next attempt
                    time.sleep(retry_interval_sec)
                    continue
                else:
                    # No more retries - count the final failed attempt
                    self.steps_executed += 1
                    break
            except Exception as e:
                # Non-execution errors are not retried - count as executed
                self.steps_executed += 1
                return False, e

        return False, last_error

    def _execute_step_with_recovery(
        self,
        step: WorkflowStep
    ) -> tuple[bool, Optional[Exception]]:
        """
        Execute a step with recovery orchestration for timeout failures.

        Routes wait_image timeouts through the classifier and orchestrator
        to determine L1 retry, L2 rollback, or L3 skip actions.

        Args:
            step: The workflow step to execute

        Returns:
            Tuple of (success, error) - error may be RoleSkipError for L3
        """
        # Track recovery attempts for this step
        step_key = step.step_id
        recovery_attempt = self._recovery_attempt_count.get(step_key, 0)

        # First, try normal step execution with retries
        success, error = self._execute_step(step)

        if success:
            # Success - reset recovery state for this step
            self.orchestrator.record_success(step_key)
            self._recovery_attempt_count[step_key] = 0
            return True, None

        # Failure - classify the error
        error_kind = classify_error(
            error or Exception("Unknown error"),
            {"step_id": step.step_id}
        )

        # Log the error
        if self.error_logger:
            context = ErrorContext(
                phase="04",
                step_id=step.step_id,
                action_type=step.action.type if hasattr(step, 'action') else 'unknown',
                attempt=recovery_attempt + 1,
                account_id=self.account_id,
                detail={"error": str(error), "recovery": True}
            )
            self.error_logger.log_error(error_kind, str(error) or "Step failed", context)

        # Handle disconnect - immediate L3 skip
        if error_kind == ErrorKind.DISCONNECT:
            return False, RoleSkipError(f"Role skipped due to disconnect at step {step.step_id}")

        # Check if step has explicit on_timeout recovery configured
        # For UI_TIMEOUT errors with on_timeout target, skip normal escalation and rollback immediately
        has_on_timeout_target = (
            hasattr(step, 'recovery') and
            step.recovery and
            step.recovery.on_timeout and
            self.workflow.get_step(step.recovery.on_timeout)
        )

        if error_kind == ErrorKind.UI_TIMEOUT and has_on_timeout_target:
            # Immediate L2 rollback for UI timeout with configured target
            rollback_target = step.recovery.on_timeout
            attempt_count = recovery_attempt + 1
            print(f"[Recovery] Step '{step.step_id}' timeout, rollback to '{rollback_target}' (attempt {attempt_count})")
            self.current_step_id = rollback_target
            self._recovery_attempt_count[step_key] = attempt_count
            # Return success to continue execution from rollback target
            return True, None

        # Determine recovery action via normal escalation
        action = self.orchestrator.determine_action(
            error_kind.value,
            step_key,
            recovery_attempt + 1
        )

        # Handle L2 rollback
        if action == RecoveryAction.L2_ROLLBACK:
            rollback_target = step.recovery.on_timeout if hasattr(step, 'recovery') else None
            if rollback_target and self.workflow.get_step(rollback_target):
                # Rollback to anchor step
                self.current_step_id = rollback_target
                self._recovery_attempt_count[step_key] = recovery_attempt + 1
                # Return success to continue execution from anchor
                return True, None
            else:
                # No valid rollback target - continue to failure
                pass

        # Handle L3 skip
        if action == RecoveryAction.L3_SKIP:
            return False, RoleSkipError(f"Role skipped after max escalations at step {step.step_id}")

        # L1 retry already handled by _execute_step, or no recovery possible
        return False, error

    def _resolve_retry_interval_ms(self, step: WorkflowStep) -> int:
        """
        Resolve retry interval with step > workflow priority.

        Args:
            step: Workflow step that may have retry_interval_ms override

        Returns:
            Retry interval in milliseconds
        """
        # Step-level override
        step_interval = getattr(step, 'retry_interval_ms', None)
        if step_interval is not None:
            return step_interval

        # Workflow default from compiled workflow
        if hasattr(self.workflow, 'wait_defaults'):
            return self.workflow.wait_defaults.retry_interval_ms

        # Fallback default
        return 1000  # 1 second

    def _resolve_next_step(self, step: WorkflowStep) -> Optional[str]:
        """
        Resolve the next step based on routing configuration.

        Args:
            step: Current step with routing info

        Returns:
            Next step ID or None to terminate
        """
        # Check for conditional routing first
        has_conditional = step.on_true is not None or step.on_false is not None

        if has_conditional:
            # Evaluate condition to determine branch
            condition_result = self.condition.evaluate(step)

            if condition_result and step.on_true is not None:
                return step.on_true
            elif not condition_result and step.on_false is not None:
                return step.on_false
            else:
                # No matching branch - terminate
                return None

        # Simple routing via 'next' field
        return step.next
