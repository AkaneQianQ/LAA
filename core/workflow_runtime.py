"""
Workflow Runtime Module

Provides runtime adapters for action dispatch and condition evaluation.
Integrates with vision engine for image-based conditions.

Exports:
    ActionDispatcher: Dispatches workflow actions to controller
    ConditionEvaluator: Evaluates image conditions using vision engine
"""

from typing import Optional, Any, Tuple
from core.workflow_schema import WorkflowStep, ClickAction, WaitAction, PressAction, ScrollAction


class ActionDispatcher:
    """
    Dispatches workflow actions to the hardware controller.

    Normalizes action parameters and translates them to controller calls.
    """

    def __init__(self, controller: Any):
        """
        Initialize the action dispatcher.

        Args:
            controller: Hardware controller with click, wait, press, scroll methods
        """
        self.controller = controller

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
