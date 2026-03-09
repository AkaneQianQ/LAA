"""
Workflow Runtime Module

Provides runtime adapters for action dispatch and condition evaluation.
Integrates with vision engine for image-based conditions.

Exports:
    ActionDispatcher: Dispatches workflow actions to controller
    ConditionEvaluator: Evaluates image conditions using vision engine
"""

import os
import time
import random
from typing import Optional, Any, Tuple
from .schema import WorkflowStep, ClickAction, WaitAction, PressAction, ScrollAction, WaitImageAction, ClickDetectedAction, MoveAction, CaptureROIAction


def calculate_safe_click_roi(roi: Tuple[int, int, int, int], shrink_percent: float = 0.10) -> Tuple[int, int, int, int]:
    """
    计算安全点击区域，缩小ROI避免点击边缘。

    Args:
        roi: 原始ROI区域 (x1, y1, x2, y2)
        shrink_percent: 缩小比例，默认10%

    Returns:
        缩小后的安全区域 (safe_x1, safe_y1, safe_x2, safe_y2)
    """
    x1, y1, x2, y2 = roi
    width = x2 - x1
    height = y2 - y1

    # 计算缩小量（至少保留一定边距）
    shrink_x = max(int(width * shrink_percent), 5)
    shrink_y = max(int(height * shrink_percent), 5)

    # 计算安全区域（确保不会超出原始ROI）
    safe_x1 = x1 + shrink_x
    safe_y1 = y1 + shrink_y
    safe_x2 = x2 - shrink_x
    safe_y2 = y2 - shrink_y

    # 确保区域有效
    if safe_x1 >= safe_x2:
        safe_x1 = x1 + 2
        safe_x2 = x2 - 2
    if safe_y1 >= safe_y2:
        safe_y1 = y1 + 2
        safe_y2 = y2 - 2

    return (safe_x1, safe_y1, safe_x2, safe_y2)


def get_random_click_position(roi: Tuple[int, int, int, int], shrink_percent: float = 0.10) -> Tuple[int, int]:
    """
    在ROI安全区域内生成随机点击坐标。

    Args:
        roi: ROI区域 (x1, y1, x2, y2)
        shrink_percent: 缩小比例，默认10%

    Returns:
        随机点击坐标 (x, y)
    """
    safe_x1, safe_y1, safe_x2, safe_y2 = calculate_safe_click_roi(roi, shrink_percent)

    x = random.randint(safe_x1, safe_x2)
    y = random.randint(safe_y1, safe_y2)

    return (x, y)


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
        from .executor import ExecutionError

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
            elif isinstance(action, ClickDetectedAction):
                self._dispatch_click_detected(action, step)
            elif isinstance(action, MoveAction):
                self._dispatch_move(action)
            elif isinstance(action, CaptureROIAction):
                self._dispatch_capture_roi(action)
            else:
                raise ExecutionError(f"Unknown action type: {type(action)}")
        except Exception as e:
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(f"Action dispatch failed: {e}") from e

    def _dispatch_click(self, action: ClickAction) -> None:
        """Dispatch a click action with coordinate normalization."""
        import random

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

        # Apply random Y offset if specified
        random_y = getattr(action, 'random_y', 0)
        if random_y > 0:
            abs_y += random.randint(-random_y, random_y)

        print(f"[5D Debug] 点击坐标: ({abs_x}, {abs_y}), random_y={random_y}")

        # Use move_and_click for absolute coordinates (consistent with click_detected)
        if hasattr(self.controller, 'move_and_click'):
            print(f"[5D Debug] 调用 move_and_click({abs_x}, {abs_y})")
            self.controller.move_and_click(abs_x, abs_y)
            print(f"[5D Debug] 点击完成，等待 100ms 让 UI 响应...")
            time.sleep(0.1)
        else:
            # Fallback: move then click separately
            print(f"[5D Debug] 回退到 move_absolute + click")
            self.controller.move_absolute(abs_x, abs_y)
            self.controller._send_command("km.click(0)")  # 0 = left button
            time.sleep(0.1)

    def _dispatch_wait(self, action: WaitAction) -> None:
        """Dispatch a wait action (convert ms to seconds)."""
        self.controller.wait(action.duration_ms / 1000.0)

    def _dispatch_press(self, action: PressAction) -> None:
        """Dispatch a key press action."""
        self.controller.press(action.key_name)

    def _dispatch_move(self, action: MoveAction) -> None:
        """Dispatch a move action to absolute coordinates without clicking."""
        if hasattr(self.controller, 'move_absolute'):
            self.controller.move_absolute(action.x, action.y)
        else:
            # Fallback: use relative move if absolute not available
            # Get current position first (if available)
            current_x, current_y = 0, 0
            try:
                import win32api
                current_x, current_y = win32api.GetCursorPos()
            except Exception:
                pass
            dx = action.x - current_x
            dy = action.y - current_y
            if hasattr(self.controller, 'move'):
                self.controller.move(dx, dy)

    def _dispatch_capture_roi(self, action: CaptureROIAction) -> None:
        """
        Dispatch a capture_roi action to extract and store ROI from screenshot.

        Captures the specified ROI from the current screenshot and stores it
        in the workflow context under the specified output_key. Optionally
        saves the captured image to a file path.

        Args:
            action: CaptureROIAction with roi, output_key, and optional save_path
        """
        from .executor import ExecutionError

        # Capture screenshot
        screenshot = self._capture_screenshot()

        if screenshot is None or screenshot.size == 0:
            raise ExecutionError("Failed to capture screenshot for ROI extraction")

        # Extract ROI
        x1, y1, x2, y2 = action.roi

        # Validate bounds
        height, width = screenshot.shape[:2]
        x1 = max(0, min(x1, width))
        x2 = max(0, min(x2, width))
        y1 = max(0, min(y1, height))
        y2 = max(0, min(y2, height))

        if x1 >= x2 or y1 >= y2:
            raise ExecutionError(f"Invalid ROI dimensions: ({x1}, {y1}, {x2}, {y2})")

        # Extract region
        roi_region = screenshot[y1:y2, x1:x2]

        if roi_region.size == 0:
            raise ExecutionError(f"Empty ROI region extracted from ({x1}, {y1}, {x2}, {y2})")

        # Store in controller's workflow context if available
        if hasattr(self.controller, 'workflow_context'):
            self.controller.workflow_context[action.output_key] = roi_region
            print(f"[Vision] Captured ROI stored in context['{action.output_key}']")
        else:
            # Fallback: store in dispatcher context
            if not hasattr(self, '_capture_context'):
                self._capture_context = {}
            self._capture_context[action.output_key] = roi_region
            print(f"[Vision] Captured ROI stored in dispatcher context['{action.output_key}']")

        # Optionally save to file
        if action.save_path:
            try:
                import cv2
                # Ensure directory exists
                save_dir = os.path.dirname(action.save_path)
                if save_dir and not os.path.exists(save_dir):
                    os.makedirs(save_dir, exist_ok=True)

                cv2.imwrite(action.save_path, roi_region)
                print(f"[Vision] ROI saved to: {action.save_path}")
            except Exception as e:
                print(f"[WARNING] Failed to save ROI to {action.save_path}: {e}")

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
        from .executor import ExecutionError

        # Get timeout from action override, step, or workflow default
        timeout_ms = self._resolve_timeout_ms(action, step)
        poll_interval_ms = self._resolve_poll_interval_ms(action, step)

        # Convert to seconds
        timeout_sec = timeout_ms / 1000.0
        poll_interval_sec = poll_interval_ms / 1000.0

        # Calculate deadline using monotonic clock
        deadline = time.monotonic() + timeout_sec

        # Stability tracking: configurable consecutive hits for success
        consecutive_hits = 0
        required_hits = getattr(action, 'stability_hits', 1)

        # Get threshold from action (default 0.8)
        threshold = getattr(action, 'threshold', 0.8)

        while time.monotonic() < deadline:
            # Check current image state with custom threshold
            is_present = self._check_image_present(action.image, action.roi, threshold)

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

    def _dispatch_click_detected(self, action: ClickDetectedAction, step: WorkflowStep) -> None:
        """
        Dispatch a click_detected action at detected image center with random offset.

        Performs single-shot detection and clicks the center of matched region
        with configurable random offset for anti-detection purposes.

        Args:
            action: ClickDetectedAction with image, roi, threshold, random_offset
            step: Workflow step for context

        Raises:
            ExecutionError: If image not found or click fails
        """
        from .executor import ExecutionError

        if self.vision is None:
            raise ExecutionError("Cannot click_detected: no vision engine available")

        try:
            # Capture screenshot
            screenshot = self._capture_screenshot()

            # Find element
            found, confidence, location = self.vision.find_element(
                screenshot,
                action.image,
                roi=action.roi,
                threshold=action.threshold
            )

            if not found:
                raise ExecutionError(
                    f"click_detected failed: '{action.image}' not found in ROI {action.roi} "
                    f"(confidence: {confidence:.2f})"
                )

            # 使用检测到的匹配位置作为ROI，在安全区域内随机点击
            # 这样不需要读取模板文件，且兼容性更好
            match_x, match_y = location

            # 构建匹配区域的ROI（以匹配位置为起点，假设一个合理的大小）
            # 如果检测成功，使用匹配位置周围的小区域作为点击范围
            import cv2
            import os
            template_path = action.image
            if not os.path.isabs(template_path) and not template_path.startswith("assets/") and not template_path.startswith("assets\\"):
                template_path = os.path.join("assets", template_path)
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

            if template is not None:
                h, w = template.shape
                # 点击模板中心点，而不是随机位置
                center_x = match_x + w // 2
                center_y = match_y + h // 2
                final_x, final_y = center_x, center_y
            else:
                # 如果无法读取模板，使用传入的ROI中心
                x1, y1, x2, y2 = action.roi
                final_x = (x1 + x2) // 2
                final_y = (y1 + y2) // 2

            print(f"[5C Debug] 检测位置: ({match_x}, {match_y}), 模板尺寸: {w}x{h}, 中心点击: ({final_x}, {final_y})")

            # 执行点击：使用优化的 move_and_click 减少串口往返延迟
            if hasattr(self.controller, 'move_and_click'):
                print(f"[5C Debug] 调用 move_and_click({final_x}, {final_y})")
                self.controller.move_and_click(final_x, final_y)
                print(f"[5C Debug] 点击完成，等待 100ms 让 UI 响应...")
                time.sleep(0.1)  # 添加延迟让 UI 响应
            else:
                # 回退到旧方法
                print(f"[5C Debug] 回退到 move_absolute + click")
                self.controller.move_absolute(final_x, final_y)
                self.controller._send_command("km.click(0)")  # 0 = 左键
                time.sleep(0.1)

        except Exception as e:
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(f"click_detected failed: {e}") from e

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

    def _check_image_present(self, image: str, roi: Tuple[int, int, int, int], threshold: float = 0.8, debug: bool = False) -> bool:
        """
        Check if an image is present in the specified ROI.

        Args:
            image: Template image filename
            roi: Region of interest as (x1, y1, x2, y2)
            threshold: Matching confidence threshold (default 0.8)
            debug: Save ROI screenshot for debugging (default False)

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
            found, confidence, _ = self.vision.find_element(screenshot, image, roi=roi, threshold=threshold)

            return found
        except Exception as e:
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
            result = self._evaluate_image_condition(condition, screenshot)
            template = condition.get('template', 'unknown')
            print(f"[Condition] Image check '{template}': {'FOUND' if result else 'NOT FOUND'}")
            return result
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
