"""
Workflow Runtime Module

Provides runtime adapters for action dispatch and condition evaluation.
Integrates with vision engine for image-based conditions.

Exports:
    ActionDispatcher: Dispatches workflow actions to controller
    ConditionEvaluator: Evaluates image conditions using vision engine
"""

import time
from typing import Optional, Any, Tuple
from core.workflow_schema import WorkflowStep, ClickAction, WaitAction, PressAction, ScrollAction, WaitImageAction


class ActionDispatcher:
    """
    Dispatches workflow actions to the hardware controller.

    Normalizes action parameters and translates them to controller calls.
    """

    def __init__(self, controller: Any, vision_engine: Any = None):
        """
        Initialize the action dispatcher.

        Args:
            controller: Hardware controller with click, wait, press, scroll methods
            vision_engine: Optional vision engine for image-based actions
        """
        self.controller = controller
        self.vision = vision_engine

    def dispatch(self, step: WorkflowStep) -> None:
        """
        Dispatch the action for a workflow step.

        Args:
            step: Workflow step containing the action

        Raises:
            ExecutionError: If action dispatch fails
        """
        from core.workflow_executor import ExecutionError

        action = step.action

        try:
            if isinstance(action, ClickAction):
                self._dispatch_click(action)
            elif isinstance(action, WaitAction):
                self._dispatch_wait(action)
            elif isinstance(action, PressAction):
                self._dispatch_press(action)
            elif isinstance(action, ScrollAction):
                self._dispatch_scroll(action)
            elif isinstance(action, WaitImageAction):
                self._dispatch_wait_image(action, step)
            else:
                raise ExecutionError(f"Unknown action type: {type(action)}")
        except Exception as e:
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(f"Action dispatch failed: {e}") from e

    def _dispatch_click(self, action: ClickAction) -> None:
        """Dispatch a click action with coordinate normalization."""
        # Calculate absolute coordinates
        if action.roi is not None:
            # ROI-relative coordinates: add ROI origin
            x1, y1, _, _ = action.roi
            abs_x = x1 + action.x
            abs_y = y1 + action.y
        else:
            # Absolute coordinates
            abs_x = action.x
            abs_y = action.y

        self.controller.click(abs_x, abs_y)

    def _dispatch_wait(self, action: WaitAction) -> None:
        """Dispatch a wait action (convert ms to seconds)."""
        self.controller.wait(action.duration_ms / 1000.0)

    def _dispatch_press(self, action: PressAction) -> None:
        """Dispatch a key press action."""
        self.controller.press(action.key_name)

    def _dispatch_scroll(self, action: ScrollAction) -> None:
        """Dispatch a scroll action."""
        self.controller.scroll(action.direction, action.ticks)

    def _dispatch_wait_image(self, action: WaitImageAction, step: WorkflowStep) -> None:
        """
        Dispatch a wait_image action with intelligent polling and stability gating.

        Waits for image to appear or disappear with 2-hit stability requirement.
        Uses monotonic deadline control for timeout handling.

        Args:
            action: WaitImageAction with state, image, roi, timeout, poll_interval
            step: Workflow step for accessing workflow defaults

        Raises:
            ExecutionError: On timeout or polling failure
        """
        from core.workflow_executor import ExecutionError

        # Get timeout from action override, step, or workflow default
        timeout_ms = self._resolve_timeout_ms(action, step)
        poll_interval_ms = self._resolve_poll_interval_ms(action, step)

        # Convert to seconds
        timeout_sec = timeout_ms / 1000.0
        poll_interval_sec = poll_interval_ms / 1000.0

        # Calculate deadline using monotonic clock
        deadline = time.monotonic() + timeout_sec

        # Stability tracking: need 2 consecutive hits for success
        consecutive_hits = 0
        required_hits = 2

        while time.monotonic() < deadline:
            # Check current image state
            is_present = self._check_image_present(action.image, action.roi)

            if action.state == 'appear':
                # For appear: success when image is present
                if is_present:
                    consecutive_hits += 1
                    if consecutive_hits >= required_hits:
                        return  # Success - image appeared with stability
                else:
                    consecutive_hits = 0  # Reset on miss
            elif action.state == 'disappear':
                # For disappear: success when image is absent
                if not is_present:
                    consecutive_hits += 1
                    if consecutive_hits >= required_hits:
                        return  # Success - image disappeared with stability
                else:
                    consecutive_hits = 0  # Reset on hit

            # Wait before next poll
            time.sleep(poll_interval_sec)

        # Timeout reached
        raise ExecutionError(
            f"wait_image timeout: image '{action.image}' did not {action.state} "
            f"within {timeout_ms}ms (required {required_hits} consecutive hits)"
        )

    def _resolve_timeout_ms(self, action: WaitImageAction, step: WorkflowStep) -> int:
        """Resolve timeout with action > workflow priority."""
        # Action-level override
        if action.timeout_ms is not None:
            return action.timeout_ms

        # Workflow default if available (set by executor before dispatch)
        workflow_defaults = getattr(self, '_workflow_defaults', None)
        if workflow_defaults is not None:
            return workflow_defaults.timeout_ms

        # Fallback default
        return 10000  # 10 seconds

    def _resolve_poll_interval_ms(self, action: WaitImageAction, step: WorkflowStep) -> int:
        """Resolve poll interval with action > workflow priority."""
        # Action-level override
        if action.poll_interval_ms is not None:
            return action.poll_interval_ms

        # Workflow default if available
        workflow_defaults = getattr(self, '_workflow_defaults', None)
        if workflow_defaults is not None:
            return workflow_defaults.poll_interval_ms

        # Fallback default
        return 50  # 50ms

    def _check_image_present(self, image: str, roi: Tuple[int, int, int, int]) -> bool:
        """
        Check if an image is present in the specified ROI.

        Args:
            image: Template image filename
            roi: Region of interest as (x1, y1, x2, y2)

        Returns:
            True if image is found, False otherwise
        """
        if self.vision is None:
            # No vision engine available - cannot check image presence
            return False

        try:
            # Capture screenshot
            screenshot = self._capture_screenshot()

            # Use vision engine to find element
            found, _, _ = self.vision.find_element(screenshot, image, roi=roi)
            return found
        except Exception:
            return False

    def _capture_screenshot(self) -> Any:
        """Capture a screenshot using available methods."""
        import numpy as np

        # Try DXCam first
        try:
            import dxcam
            import cv2
            camera = dxcam.create()
            screenshot = camera.grab()
            if screenshot is not None:
                return cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        except Exception:
            pass

        # Fallback to PIL
        try:
            from PIL import ImageGrab
            screenshot = np.array(ImageGrab.grab())
            import cv2
            return cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        except Exception:
            pass

        return np.zeros((1440, 2560, 3), dtype=np.uint8)


class ConditionEvaluator:
    """
    Evaluates workflow conditions using the vision engine.

    Supports image-based conditions for branching workflows.
    """

    def __init__(self, vision_engine: Any):
        """
        Initialize the condition evaluator.

        Args:
            vision_engine: Vision engine with find_element method
        """
        self.vision = vision_engine

    def evaluate(self, step: WorkflowStep, screenshot: Optional[Any] = None) -> bool:
        """
        Evaluate the condition for a workflow step.

        Args:
            step: Workflow step that may contain a condition
            screenshot: Optional screenshot for image conditions
                       (if None, will capture fresh screenshot)

        Returns:
            True if condition is met, False otherwise
        """
        # Get condition config from step (if any)
        condition = getattr(step, 'condition', None)

        if condition is None:
            # No condition - default to True for on_true routing
            return True

        condition_type = condition.get('type')

        if condition_type == 'image':
            return self._evaluate_image_condition(condition, screenshot)
        else:
            # Unknown condition type - default to False
            return False

    def _evaluate_image_condition(
        self,
        condition: dict,
        screenshot: Optional[Any] = None
    ) -> bool:
        """
        Evaluate an image-based condition.

        Args:
            condition: Condition dict with template, roi, threshold
            screenshot: Optional screenshot (captures if None)

        Returns:
            True if image is found with sufficient confidence
        """
        import numpy as np

        # Capture screenshot if not provided
        if screenshot is None:
            screenshot = self._capture_screenshot()

        template_path = condition.get('template')
        roi = condition.get('roi')
        threshold = condition.get('threshold', 0.8)

        if template_path is None:
            return False

        # Convert ROI list to tuple if needed
        if roi is not None and isinstance(roi, list):
            roi = tuple(roi)

        # Use vision engine to find element
        found, confidence, _ = self.vision.find_element(
            screenshot,
            template_path,
            roi=roi,
            threshold=threshold
        )

        return found

    def _capture_screenshot(self) -> Any:
        """
        Capture a screenshot using available methods.

        Returns:
            Screenshot as numpy array
        """
        import numpy as np

        # Try DXCam first
        try:
            import dxcam
            import cv2
            camera = dxcam.create()
            screenshot = camera.grab()
            if screenshot is not None:
                # DXCam returns RGB, convert to BGR for OpenCV
                return cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        except Exception:
            pass

        # Fallback to PIL
        try:
            from PIL import ImageGrab
            screenshot = np.array(ImageGrab.grab())
            import cv2
            return cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        except Exception:
            pass

        # Return empty array as last resort
        return np.zeros((1440, 2560, 3), dtype=np.uint8)
