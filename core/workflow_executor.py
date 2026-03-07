"""
Workflow Executor Module

Provides deterministic step execution for compiled workflows.
Implements explicit cursor-based step progression with retry policy handling.

Exports:
    WorkflowExecutor: Main executor for running compiled workflows
    ExecutionResult: Result object containing execution metadata
    ExecutionError: Exception raised for step execution failures
"""

from typing import Optional, Any
from dataclasses import dataclass
from core.workflow_compiler import CompiledWorkflow
from core.workflow_schema import WorkflowStep


class ExecutionError(Exception):
    """Raised when a workflow step fails execution."""
    pass


@dataclass
class ExecutionResult:
    """Result of a workflow execution."""
    success: bool
    steps_executed: int
    final_step_id: Optional[str]
    error: Optional[Exception] = None
    duration_ms: Optional[float] = None


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
        condition_evaluator: Any
    ):
        """
        Initialize the workflow executor.

        Args:
            workflow: Compiled workflow to execute
            action_dispatcher: Object with dispatch(step) method for actions
            condition_evaluator: Object with evaluate(step, screenshot) method
        """
        self.workflow = workflow
        self.dispatcher = action_dispatcher
        self.condition = condition_evaluator
        self.steps_executed = 0
        self.current_step_id: Optional[str] = None

    def execute(self) -> ExecutionResult:
        """
        Execute the workflow from start to completion.

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

                # Execute step with retry logic
                success, error = self._execute_step(step)

                if not success:
                    return ExecutionResult(
                        success=False,
                        steps_executed=self.steps_executed,
                        final_step_id=self.current_step_id,
                        error=error,
                        duration_ms=(time.time() - start_time) * 1000
                    )

                # Track last successfully executed step
                last_executed_step_id = self.current_step_id

                # Determine next step
                self.current_step_id = self._resolve_next_step(step)

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
