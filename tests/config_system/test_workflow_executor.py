"""
Workflow Executor and Runtime Tests

Tests validate:
- Deterministic step traversal with explicit next links
- Terminal step handling (workflow termination)
- Default failure behavior (stop on failure)
- Retry override policy handling
- Action dispatch for click/wait/press/scroll
- Conditional branching (on_true/on_false)
- Loop safety with execution cap guard
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, call

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestWorkflowExecutorTraversal:
    """Test deterministic step traversal and basic execution flow."""

    def test_step_sequence_follows_explicit_next_links(self):
        """Step sequence follows explicit next_step_id links."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor

        # Create a 3-step linear workflow
        config = {
            'name': 'linear_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': 'step2'
                },
                {
                    'step_id': 'step2',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': 'step3'
                },
                {
                    'step_id': 'step3',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        # Create executor with mocked runtime
        mock_dispatcher = Mock()
        mock_condition = Mock()
        executor = WorkflowExecutor(compiled, mock_dispatcher, mock_condition)

        # Execute workflow
        result = executor.execute()

        # Should complete successfully
        assert result.success is True
        assert result.steps_executed == 3
        assert result.final_step_id == 'step3'

        # Verify steps executed in order
        executed_steps = [call[0][0].step_id for call in mock_dispatcher.dispatch.call_args_list]
        assert executed_steps == ['step1', 'step2', 'step3']

    def test_workflow_terminates_on_terminal_step(self):
        """Workflow terminates on terminal step without next link."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor

        config = {
            'name': 'terminal_workflow',
            'start_step_id': 'only_step',
            'steps': [
                {
                    'step_id': 'only_step',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None  # Terminal step
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        mock_dispatcher = Mock()
        mock_condition = Mock()
        executor = WorkflowExecutor(compiled, mock_dispatcher, mock_condition)

        result = executor.execute()

        assert result.success is True
        assert result.steps_executed == 1
        assert result.final_step_id == 'only_step'

    def test_default_failure_stops_execution(self):
        """Default failure behavior stops execution immediately."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor, ExecutionError

        config = {
            'name': 'failing_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'click', 'x': 100, 'y': 200},
                    'next': 'step2'
                },
                {
                    'step_id': 'step2',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        # Mock dispatcher to fail on first step
        mock_dispatcher = Mock()
        mock_dispatcher.dispatch.side_effect = [
            ExecutionError("Click failed"),
            None  # Should not reach here
        ]
        mock_condition = Mock()

        executor = WorkflowExecutor(compiled, mock_dispatcher, mock_condition)
        result = executor.execute()

        assert result.success is False
        assert result.error is not None
        assert "Click failed" in str(result.error)
        assert result.steps_executed == 1  # Only first step attempted
        assert result.final_step_id == 'step1'

    def test_retry_override_allows_step_retry(self):
        """Retry override allows step retry before fail-stop."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor, ExecutionError

        config = {
            'name': 'retry_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'click', 'x': 100, 'y': 200},
                    'next': None,
                    'retry': 2  # Retry up to 2 times
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        # Mock dispatcher to fail twice, then succeed
        mock_dispatcher = Mock()
        call_count = [0]

        def dispatch_with_retry(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise ExecutionError(f"Attempt {call_count[0]} failed")
            return None  # Success on 3rd try

        mock_dispatcher.dispatch.side_effect = dispatch_with_retry
        mock_condition = Mock()

        executor = WorkflowExecutor(compiled, mock_dispatcher, mock_condition)
        result = executor.execute()

        assert result.success is True
        assert result.steps_executed == 1
        # Dispatcher should be called 3 times (initial + 2 retries)
        assert mock_dispatcher.dispatch.call_count == 3


class TestActionDispatcher:
    """Test action dispatch for all action types."""

    def test_click_action_invokes_dispatcher_with_normalized_params(self):
        """Click action invokes dispatcher with normalized parameters."""
        from core.workflow_schema import ClickAction, WorkflowStep
        from core.workflow_runtime import ActionDispatcher

        mock_controller = Mock()
        dispatcher = ActionDispatcher(mock_controller)

        step = WorkflowStep(
            step_id='test',
            action=ClickAction(type='click', x=100, y=200)
        )
        dispatcher.dispatch(step)

        mock_controller.click.assert_called_once_with(100, 200)

    def test_click_action_with_roi_calculates_absolute_coordinates(self):
        """Click action with ROI calculates absolute coordinates."""
        from core.workflow_schema import ClickAction, WorkflowStep
        from core.workflow_runtime import ActionDispatcher

        mock_controller = Mock()
        dispatcher = ActionDispatcher(mock_controller)

        # ROI (x1, y1, x2, y2) with relative coordinates
        step = WorkflowStep(
            step_id='test',
            action=ClickAction(type='click', x=50, y=75, roi=(1000, 500, 1500, 900))
        )
        dispatcher.dispatch(step)

        # Absolute coordinates: ROI origin + relative offset
        mock_controller.click.assert_called_once_with(1050, 575)

    def test_wait_action_invokes_dispatcher_with_milliseconds(self):
        """Wait action invokes dispatcher with millisecond duration."""
        from core.workflow_schema import WaitAction, WorkflowStep
        from core.workflow_runtime import ActionDispatcher

        mock_controller = Mock()
        dispatcher = ActionDispatcher(mock_controller)

        step = WorkflowStep(
            step_id='test',
            action=WaitAction(type='wait', duration_ms=1500)
        )
        dispatcher.dispatch(step)

        mock_controller.wait.assert_called_once_with(1.5)  # Converted to seconds

    def test_press_action_invokes_dispatcher_with_key_name(self):
        """Press action invokes dispatcher with key_name."""
        from core.workflow_schema import PressAction, WorkflowStep
        from core.workflow_runtime import ActionDispatcher

        mock_controller = Mock()
        dispatcher = ActionDispatcher(mock_controller)

        step = WorkflowStep(
            step_id='test',
            action=PressAction(type='press', key_name='enter')
        )
        dispatcher.dispatch(step)

        mock_controller.press.assert_called_once_with('enter')

    def test_scroll_action_invokes_dispatcher_with_direction_and_ticks(self):
        """Scroll action invokes dispatcher with direction and ticks."""
        from core.workflow_schema import ScrollAction, WorkflowStep
        from core.workflow_runtime import ActionDispatcher

        mock_controller = Mock()
        dispatcher = ActionDispatcher(mock_controller)

        step = WorkflowStep(
            step_id='test',
            action=ScrollAction(type='scroll', direction='down', ticks=3)
        )
        dispatcher.dispatch(step)

        mock_controller.scroll.assert_called_once_with('down', 3)


class TestConditionEvaluator:
    """Test condition evaluation for branching."""

    def test_image_condition_true_routes_to_on_true_step(self):
        """Image condition true routes to on_true_step_id."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor

        config = {
            'name': 'conditional_workflow',
            'start_step_id': 'check',
            'steps': [
                {
                    'step_id': 'check',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'on_true': 'success_step',
                    'on_false': 'failure_step'
                },
                {
                    'step_id': 'success_step',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                },
                {
                    'step_id': 'failure_step',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        mock_dispatcher = Mock()
        mock_condition = Mock()
        # Condition returns True, so should route to on_true
        mock_condition.evaluate.return_value = True

        executor = WorkflowExecutor(compiled, mock_dispatcher, mock_condition)
        result = executor.execute()

        assert result.success is True
        # Should execute check -> success_step
        executed_steps = [call[0][0].step_id for call in mock_dispatcher.dispatch.call_args_list]
        assert executed_steps == ['check', 'success_step']

    def test_image_condition_false_routes_to_on_false_step(self):
        """Image condition false routes to on_false_step_id."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor

        config = {
            'name': 'conditional_workflow',
            'start_step_id': 'check',
            'steps': [
                {
                    'step_id': 'check',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'on_true': 'success_step',
                    'on_false': 'failure_step'
                },
                {
                    'step_id': 'success_step',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                },
                {
                    'step_id': 'failure_step',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        mock_dispatcher = Mock()
        mock_condition = Mock()
        # Condition returns False, so should route to on_false
        mock_condition.evaluate.return_value = False

        executor = WorkflowExecutor(compiled, mock_dispatcher, mock_condition)
        result = executor.execute()

        assert result.success is True
        # Should execute check -> failure_step
        executed_steps = [call[0][0].step_id for call in mock_dispatcher.dispatch.call_args_list]
        assert executed_steps == ['check', 'failure_step']

    def test_condition_evaluator_uses_vision_engine(self):
        """Condition evaluator uses vision engine for image detection."""
        from core.workflow_runtime import ConditionEvaluator
        from core.workflow_schema import WorkflowStep

        mock_vision = Mock()
        mock_screenshot = Mock()

        # Mock vision engine to find image
        mock_vision.find_element.return_value = (True, 0.95, (100, 200))

        evaluator = ConditionEvaluator(mock_vision)

        # Create a step with condition configuration
        step = WorkflowStep(
            step_id='check',
            action={'type': 'wait', 'duration_ms': 100},
            condition={
                'type': 'image',
                'template': 'assets/test.png',
                'roi': [100, 100, 200, 200],
                'threshold': 0.8
            }
        )

        result = evaluator.evaluate(step, mock_screenshot)

        assert result is True
        mock_vision.find_element.assert_called_once_with(
            mock_screenshot,
            'assets/test.png',
            roi=(100, 100, 200, 200),
            threshold=0.8
        )


class TestLoopSafety:
    """Test loop safety with execution cap guard."""

    def test_looped_branches_execute_up_to_guard_limit(self):
        """Looped branches execute up to guard limit."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor

        # Create a workflow that loops: check -> loop_back -> check
        config = {
            'name': 'loop_workflow',
            'start_step_id': 'check',
            'steps': [
                {
                    'step_id': 'check',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'on_true': 'exit_step',
                    'on_false': 'loop_back'
                },
                {
                    'step_id': 'loop_back',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': 'check'  # Loop back to check
                },
                {
                    'step_id': 'exit_step',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        mock_dispatcher = Mock()
        mock_condition = Mock()
        # Condition always returns False (keep looping) until guard kicks in
        mock_condition.evaluate.return_value = False

        executor = WorkflowExecutor(compiled, mock_dispatcher, mock_condition)
        result = executor.execute()

        # Should fail due to loop guard
        assert result.success is False
        assert "loop guard" in str(result.error).lower() or "max steps" in str(result.error).lower()

    def test_loop_guard_allows_reasonable_iterations(self):
        """Loop guard allows reasonable number of iterations."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor

        # Create a workflow that loops exactly 5 times then exits
        config = {
            'name': 'limited_loop',
            'start_step_id': 'check',
            'steps': [
                {
                    'step_id': 'check',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'on_true': 'exit_step',
                    'on_false': 'loop_back'
                },
                {
                    'step_id': 'loop_back',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': 'check'
                },
                {
                    'step_id': 'exit_step',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        mock_dispatcher = Mock()
        mock_condition = Mock()

        # Return False 5 times (loop), then True (exit)
        call_count = [0]
        def conditional_return(*args, **kwargs):
            call_count[0] += 1
            return call_count[0] > 5  # Exit after 5 loops

        mock_condition.evaluate.side_effect = conditional_return

        executor = WorkflowExecutor(compiled, mock_dispatcher, mock_condition)
        result = executor.execute()

        assert result.success is True
        # Should execute: check (x6) + loop_back (x5) + exit_step (x1) = 12 steps
        assert result.steps_executed == 12


class TestExecutionResult:
    """Test execution result object."""

    def test_result_contains_execution_metadata(self):
        """Execution result contains success status, steps executed, timing."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor

        config = {
            'name': 'simple_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        mock_dispatcher = Mock()
        mock_condition = Mock()
        executor = WorkflowExecutor(compiled, mock_dispatcher, mock_condition)

        result = executor.execute()

        assert hasattr(result, 'success')
        assert hasattr(result, 'steps_executed')
        assert hasattr(result, 'final_step_id')
        assert hasattr(result, 'error')
        assert hasattr(result, 'duration_ms')

        assert result.success is True
        assert result.steps_executed == 1
        assert result.final_step_id == 'step1'
        assert result.error is None


class TestWaitImageRuntime:
    """Test wait_image action runtime behavior with appear/disappear states."""

    def test_wait_image_appear_succeeds_after_two_consecutive_hits(self):
        """wait_image with state=appear succeeds only after two consecutive positive evaluations."""
        from core.workflow_schema import WorkflowConfig, WaitImageAction, WorkflowStep
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor
        from core.workflow_runtime import ActionDispatcher, ConditionEvaluator
        from unittest.mock import Mock, patch

        # Create workflow with wait_image action
        config = {
            'name': 'wait_image_workflow',
            'start_step_id': 'wait_step',
            'steps': [
                {
                    'step_id': 'wait_step',
                    'action': {
                        'type': 'wait_image',
                        'state': 'appear',
                        'image': 'btn_login.png',
                        'roi': [100, 100, 200, 200],
                        'timeout_ms': 5000,
                        'poll_interval_ms': 50
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        # Mock controller and vision engine
        mock_controller = Mock()
        mock_vision = Mock()

        # Simulate: not found, not found, found, found (2-hit stability required)
        mock_vision.find_element.side_effect = [
            (False, 0.3, None),   # Poll 1: not found
            (False, 0.4, None),   # Poll 2: not found
            (True, 0.95, (150, 150)),   # Poll 3: found (1st hit)
            (True, 0.96, (150, 150)),   # Poll 4: found (2nd hit - success)
        ]

        dispatcher = ActionDispatcher(mock_controller, vision_engine=mock_vision)
        condition = ConditionEvaluator(mock_vision)

        executor = WorkflowExecutor(compiled, dispatcher, condition)
        result = executor.execute()

        assert result.success is True
        assert result.steps_executed == 1
        # Should have polled 4 times (2 negative, 2 positive for stability)
        assert mock_vision.find_element.call_count == 4

    def test_wait_image_disappear_succeeds_after_two_consecutive_misses(self):
        """wait_image with state=disappear succeeds only after two consecutive negative evaluations."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor
        from core.workflow_runtime import ActionDispatcher, ConditionEvaluator
        from unittest.mock import Mock

        config = {
            'name': 'wait_image_workflow',
            'start_step_id': 'wait_step',
            'steps': [
                {
                    'step_id': 'wait_step',
                    'action': {
                        'type': 'wait_image',
                        'state': 'disappear',
                        'image': 'loading_spinner.png',
                        'roi': [500, 500, 600, 600],
                        'timeout_ms': 5000,
                        'poll_interval_ms': 50
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        mock_controller = Mock()
        mock_vision = Mock()

        # Simulate: found, found, not found, not found (2-hit stability required)
        mock_vision.find_element.side_effect = [
            (True, 0.9, (550, 550)),    # Poll 1: found
            (True, 0.91, (550, 550)),   # Poll 2: found
            (False, 0.2, None),         # Poll 3: not found (1st miss)
            (False, 0.1, None),         # Poll 4: not found (2nd miss - success)
        ]

        dispatcher = ActionDispatcher(mock_controller, vision_engine=mock_vision)
        condition = ConditionEvaluator(mock_vision)

        executor = WorkflowExecutor(compiled, dispatcher, condition)
        result = executor.execute()

        assert result.success is True
        assert result.steps_executed == 1
        # Should have polled 4 times (2 positive, 2 negative for stability)
        assert mock_vision.find_element.call_count == 4

    def test_wait_image_timeout_raises_execution_error(self):
        """wait_image timeout expiration raises ExecutionError."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor, ExecutionError
        from core.workflow_runtime import ActionDispatcher, ConditionEvaluator
        from unittest.mock import Mock

        config = {
            'name': 'wait_image_workflow',
            'start_step_id': 'wait_step',
            'wait_defaults': {
                'timeout_ms': 100,  # Very short timeout for testing
                'poll_interval_ms': 10
            },
            'steps': [
                {
                    'step_id': 'wait_step',
                    'action': {
                        'type': 'wait_image',
                        'state': 'appear',
                        'image': 'never_appears.png',
                        'roi': [100, 100, 200, 200]
                        # Uses workflow default timeout
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        mock_controller = Mock()
        mock_vision = Mock()
        # Image never appears
        mock_vision.find_element.return_value = (False, 0.1, None)

        dispatcher = ActionDispatcher(mock_controller, vision_engine=mock_vision)
        condition = ConditionEvaluator(mock_vision)

        executor = WorkflowExecutor(compiled, dispatcher, condition)
        result = executor.execute()

        assert result.success is False
        assert result.error is not None
        assert isinstance(result.error, ExecutionError)
        assert "timeout" in str(result.error).lower()

    def test_wait_image_appear_single_hit_not_enough(self):
        """wait_image appear requires 2 consecutive hits - single hit is not enough."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor
        from core.workflow_runtime import ActionDispatcher, ConditionEvaluator
        from unittest.mock import Mock

        config = {
            'name': 'wait_image_workflow',
            'start_step_id': 'wait_step',
            'steps': [
                {
                    'step_id': 'wait_step',
                    'action': {
                        'type': 'wait_image',
                        'state': 'appear',
                        'image': 'btn_login.png',
                        'roi': [100, 100, 200, 200],
                        'timeout_ms': 500,
                        'poll_interval_ms': 50
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        mock_controller = Mock()
        mock_vision = Mock()

        # Simulate: not found, found (single hit), not found (lost again)
        # This should eventually timeout because we never got 2 consecutive hits
        mock_vision.find_element.side_effect = [
            (False, 0.3, None),         # Poll 1: not found
            (True, 0.95, (150, 150)),   # Poll 2: found (1st hit - need one more)
            (False, 0.4, None),         # Poll 3: not found (reset counter)
            (False, 0.3, None),         # Poll 4: not found
            (False, 0.2, None),         # Poll 5: not found
            (False, 0.1, None),         # Poll 6: not found (will timeout)
        ]

        dispatcher = ActionDispatcher(mock_controller, vision_engine=mock_vision)
        condition = ConditionEvaluator(mock_vision)

        executor = WorkflowExecutor(compiled, dispatcher, condition)
        result = executor.execute()

        # Should fail due to timeout (never got 2 consecutive hits)
        assert result.success is False
        assert "timeout" in str(result.error).lower()

    def test_wait_image_dispatches_correctly(self):
        """ActionDispatcher correctly handles wait_image action type."""
        from core.workflow_schema import WaitImageAction, WorkflowStep
        from core.workflow_runtime import ActionDispatcher
        from unittest.mock import Mock, patch
        import time

        mock_controller = Mock()
        dispatcher = ActionDispatcher(mock_controller)

        step = WorkflowStep(
            step_id='test',
            action=WaitImageAction(
                type='wait_image',
                state='appear',
                image='btn_login.png',
                roi=(100, 100, 200, 200),
                timeout_ms=100,
                poll_interval_ms=10
            )
        )

        # Mock the _dispatch_wait_image method to avoid actual waiting
        with patch.object(dispatcher, '_dispatch_wait_image') as mock_wait:
            mock_wait.return_value = None
            dispatcher.dispatch(step)
            mock_wait.assert_called_once()


class TestRetryInterval:
    """Test retry interval semantics in executor retry loop."""

    def test_retry_interval_waits_between_attempts(self):
        """Failed step with retries waits configured interval before next attempt."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor, ExecutionError
        from unittest.mock import Mock, patch
        import time

        config = {
            'name': 'retry_interval_workflow',
            'start_step_id': 'step1',
            'wait_defaults': {
                'retry_interval_ms': 100  # 100ms between retries
            },
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'click', 'x': 100, 'y': 200},
                    'next': None,
                    'retry': 2  # 2 retries
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        mock_dispatcher = Mock()
        mock_dispatcher.dispatch.side_effect = [
            ExecutionError("Attempt 1 failed"),
            ExecutionError("Attempt 2 failed"),
            None  # Success on 3rd try
        ]
        mock_condition = Mock()

        executor = WorkflowExecutor(compiled, mock_dispatcher, mock_condition)

        # Track sleep calls
        sleep_calls = []
        original_sleep = time.sleep

        def mock_sleep(duration):
            sleep_calls.append(duration)
            # Don't actually sleep to speed up test

        with patch('time.sleep', mock_sleep):
            result = executor.execute()

        assert result.success is True
        # Should have 2 sleep calls (between 3 attempts)
        assert len(sleep_calls) == 2
        # Each sleep should be ~0.1s (100ms)
        assert all(0.09 <= s <= 0.11 for s in sleep_calls)

    def test_step_level_retry_interval_overrides_default(self):
        """Step-level retry_interval_ms overrides workflow default."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor, ExecutionError
        from unittest.mock import Mock, patch
        import time

        config = {
            'name': 'retry_interval_workflow',
            'start_step_id': 'step1',
            'wait_defaults': {
                'retry_interval_ms': 1000  # 1s default (should be overridden)
            },
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'click', 'x': 100, 'y': 200},
                    'next': None,
                    'retry': 1,
                    'retry_interval_ms': 50  # Override: 50ms
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        mock_dispatcher = Mock()
        mock_dispatcher.dispatch.side_effect = [
            ExecutionError("Attempt 1 failed"),
            None  # Success on 2nd try
        ]
        mock_condition = Mock()

        executor = WorkflowExecutor(compiled, mock_dispatcher, mock_condition)

        sleep_calls = []

        def mock_sleep(duration):
            sleep_calls.append(duration)

        with patch('time.sleep', mock_sleep):
            result = executor.execute()

        assert result.success is True
        assert len(sleep_calls) == 1
        # Should use step-level override (50ms), not default (1000ms)
        assert 0.04 <= sleep_calls[0] <= 0.06

    def test_max_retries_still_terminates_with_failure(self):
        """Max retries still terminates with final failure."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor, ExecutionError
        from unittest.mock import Mock, patch
        import time

        config = {
            'name': 'retry_fail_workflow',
            'start_step_id': 'step1',
            'wait_defaults': {
                'retry_interval_ms': 10  # Fast for testing
            },
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'click', 'x': 100, 'y': 200},
                    'next': None,
                    'retry': 2  # 2 retries = 3 total attempts
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        mock_dispatcher = Mock()
        # Always fails
        mock_dispatcher.dispatch.side_effect = ExecutionError("Always fails")
        mock_condition = Mock()

        executor = WorkflowExecutor(compiled, mock_dispatcher, mock_condition)

        with patch('time.sleep'):
            result = executor.execute()

        assert result.success is False
        assert result.error is not None
        assert "Always fails" in str(result.error)
        # Should have tried 3 times (initial + 2 retries)
        assert mock_dispatcher.dispatch.call_count == 3

    def test_timeout_errors_flow_through_executor_retry(self):
        """Timeout errors from wait_image are retried via existing step.retry."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow
        from core.workflow_executor import WorkflowExecutor, ExecutionError
        from core.workflow_runtime import ActionDispatcher, ConditionEvaluator
        from unittest.mock import Mock, patch
        import time

        config = {
            'name': 'wait_retry_workflow',
            'start_step_id': 'wait_step',
            'wait_defaults': {
                'timeout_ms': 50,  # Very short timeout
                'poll_interval_ms': 10,
                'retry_interval_ms': 20
            },
            'steps': [
                {
                    'step_id': 'wait_step',
                    'action': {
                        'type': 'wait_image',
                        'state': 'appear',
                        'image': 'btn_login.png',
                        'roi': [100, 100, 200, 200]
                    },
                    'next': None,
                    'retry': 2  # Retry timeout failures twice
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        mock_controller = Mock()
        mock_vision = Mock()
        # Image never appears - will always timeout
        mock_vision.find_element.return_value = (False, 0.1, None)

        dispatcher = ActionDispatcher(mock_controller, vision_engine=mock_vision)
        condition = ConditionEvaluator(mock_vision)

        executor = WorkflowExecutor(compiled, dispatcher, condition)

        with patch('time.sleep'):
            result = executor.execute()

        # Should fail after all retries exhausted
        assert result.success is False
        assert result.error is not None
        # Dispatcher should be called 3 times (initial + 2 retries)
        # Each call attempts wait_image which times out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
