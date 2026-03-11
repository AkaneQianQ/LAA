#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline Executor - Modular workflow execution engine

Parses and executes Pipeline JSON/YAML workflows with support for:
- Actions: KeyPress, Click, Wait, Custom
- Recognition: TemplateMatch, Custom
- Branching: on_true/on_false conditions
- Error handling and recovery
"""

import time
import json
import random
import cv2
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum


DEFAULT_CLICK_DETECT_TIMEOUT_MS = 1000
DEFAULT_CLICK_DETECT_POLL_INTERVAL_MS = 100
POST_CLICK_DELAY_MS = 120


class ExecutionResult(Enum):
    """Node execution results"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class ExecutionContext:
    """Execution context passed to all actions"""
    hardware_controller: Any
    vision_engine: Any
    screenshot: Any = None
    param: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)


class ActionHandler:
    """Base class for action handlers"""

    def __init__(self, name: str):
        self.name = name

    def execute(self, context: ExecutionContext, action_param: Dict[str, Any]) -> ExecutionResult:
        raise NotImplementedError


class KeyPressHandler(ActionHandler):
    """Handle KeyPress action"""

    def __init__(self):
        super().__init__("KeyPress")

    def execute(self, context: ExecutionContext, action_param: Dict[str, Any]) -> ExecutionResult:
        key = action_param.get("key", "")
        if context.hardware_controller:
            context.hardware_controller.press(key)
            print(f"[Action] KeyPress: {key}")
            return ExecutionResult.SUCCESS
        return ExecutionResult.FAILED


class MoveHandler(ActionHandler):
    """Handle Move action - move mouse to absolute position"""

    def __init__(self):
        super().__init__("Move")

    def execute(self, context: ExecutionContext, action_param: Dict[str, Any]) -> ExecutionResult:
        target = action_param.get("target", [0, 0])
        if len(target) == 2:
            x, y = target
            if context.hardware_controller:
                context.hardware_controller.move_absolute(int(x), int(y))
                print(f"[Action] Move to ({x}, {y})")
                return ExecutionResult.SUCCESS
        return ExecutionResult.FAILED


class ScrollHandler(ActionHandler):
    """Handle Scroll action."""

    def __init__(self):
        super().__init__("Scroll")

    def execute(self, context: ExecutionContext, action_param: Dict[str, Any]) -> ExecutionResult:
        if not context.hardware_controller:
            return ExecutionResult.FAILED

        direction = str(action_param.get("direction", "down")).lower()
        ticks = int(action_param.get("ticks", 1))
        if ticks <= 0:
            return ExecutionResult.FAILED
        if direction not in ("up", "down"):
            return ExecutionResult.FAILED

        context.hardware_controller.scroll(direction, ticks)
        print(f"[Action] Scroll {direction} x{ticks}")
        return ExecutionResult.SUCCESS


class ClickHandler(ActionHandler):
    """Handle Click action with polling detection"""

    def __init__(self):
        super().__init__("Click")
        self._template_size_cache: Dict[str, tuple[int, int]] = {}

    def _get_template_size(self, template_path: str) -> tuple[int, int]:
        """Get template (width, height) from disk with a tiny in-memory cache."""
        if template_path in self._template_size_cache:
            return self._template_size_cache[template_path]

        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            # Fallback to zero-size; caller should fallback to original ROI behavior.
            return (0, 0)

        h, w = template.shape[:2]
        self._template_size_cache[template_path] = (w, h)
        return (w, h)

    def _poll_and_click(
        self,
        context: ExecutionContext,
        template: str,
        roi: list,
        threshold: float,
        shrink_percent: float = 0,
        y_offset: float = 0,
        center_click: bool = False,
        timeout_ms: int = DEFAULT_CLICK_DETECT_TIMEOUT_MS,
        poll_interval_ms: int = DEFAULT_CLICK_DETECT_POLL_INTERVAL_MS
    ) -> ExecutionResult:
        """
        Poll for image detection and click immediately when found.

        Args:
            context: Execution context
            template: Template image path
            roi: Region of interest [x1, y1, x2, y2]
            threshold: Detection threshold
            shrink_percent: Shrink click area by this percentage
            y_offset: Skip top portion of clickable area
            timeout_ms: Maximum wait time in milliseconds
            poll_interval_ms: Polling interval in milliseconds

        Returns:
            ExecutionResult.SUCCESS if clicked, FAILED if timeout
        """
        import time
        start_time = time.time()
        timeout_s = timeout_ms / 1000.0 if timeout_ms > 0 else 0
        poll_interval_s = poll_interval_ms / 1000.0

        template_name = template.split('/')[-1] if '/' in template else template

        print(f"[Action] Polling for {template_name} (timeout {timeout_ms}ms, poll {poll_interval_ms}ms)")

        attempt = 0
        while True:
            attempt += 1
            loop_start = time.time()

            # Take fresh screenshot
            screenshot = context.vision_engine.get_screenshot(force_fresh=True)

            # Try to detect
            matched, score, box = context.vision_engine.find_element(
                screenshot,
                template_path=template,
                roi=tuple(roi),
                threshold=threshold
            )

            detect_time = (time.time() - loop_start) * 1000
            print(f"[Detection] {template_name}: attempt={attempt}, score={score:.3f}, threshold={threshold}, matched={matched}, time={detect_time:.1f}ms")

            if matched and box:
                # Detection successful - click inside matched template region.
                # `box` is top-left match position in absolute screen coordinates.
                match_x, match_y = int(box[0]), int(box[1])
                tpl_w, tpl_h = self._get_template_size(template)

                # Fallback to full ROI only if template size cannot be loaded.
                if tpl_w <= 0 or tpl_h <= 0:
                    x1, y1, x2, y2 = roi
                else:
                    x1, y1 = match_x, match_y
                    x2, y2 = match_x + tpl_w, match_y + tpl_h

                width = x2 - x1
                height = y2 - y1

                if center_click:
                    # Deterministic click at detected template center.
                    x = x1 + (width / 2.0)
                    y = y1 + (height / 2.0)
                else:
                    # Apply shrink_percent (shrink click area inward)
                    if shrink_percent > 0:
                        x1 += width * shrink_percent
                        x2 -= width * shrink_percent
                        y1 += height * shrink_percent
                        y2 -= height * shrink_percent

                    # Apply y_offset (skip top portion of clickable area)
                    if y_offset > 0:
                        y1 = max(y1, y1 + height * y_offset)

                    # Random click position within constrained area
                    x = random.uniform(x1, x2)
                    y = random.uniform(y1, y2)

                # Click immediately (no hardcoded wait)
                context.hardware_controller.move_absolute(int(x), int(y))
                context.hardware_controller.click_current()
                time.sleep(POST_CLICK_DELAY_MS / 1000.0)

                elapsed_ms = (time.time() - start_time) * 1000
                print(f"[Action] Click at ({int(x)}, {int(y)}) in ROI({int(x1)},{int(y1)},{int(x2)},{int(y2)}) after {elapsed_ms:.0f}ms")
                return ExecutionResult.SUCCESS

            # Wait before next poll
            time.sleep(poll_interval_s)

            # Check timeout
            if timeout_ms > 0 and time.time() - start_time >= timeout_s:
                print(f"[Action] Click timeout after {timeout_ms}ms")
                return ExecutionResult.FAILED

    def execute(self, context: ExecutionContext, action_param: Dict[str, Any]) -> ExecutionResult:
        target = action_param.get("target")
        template = action_param.get("template")

        if not context.hardware_controller:
            return ExecutionResult.FAILED

        if target and len(target) == 2:
            # Absolute position click (no detection needed)
            x, y = target
            context.hardware_controller.move_absolute(x, y)
            context.hardware_controller.click_current()
            time.sleep(POST_CLICK_DELAY_MS / 1000.0)
            print(f"[Action] Click at ({x}, {y})")
            return ExecutionResult.SUCCESS

        elif template:
            # Detection-based click with polling
            # Use default polling timeout values unless explicitly overridden in node params.
            roi = action_param.get("roi")
            threshold = action_param.get("threshold")
            shrink_percent = action_param.get("shrink_percent", 0)
            y_offset = action_param.get("y_offset", 0)
            center_click = bool(action_param.get("center_click", False))
            timeout_ms = action_param.get("timeout_ms", DEFAULT_CLICK_DETECT_TIMEOUT_MS)
            poll_interval_ms = action_param.get("poll_interval_ms", DEFAULT_CLICK_DETECT_POLL_INTERVAL_MS)

            if not roi:
                print("[Action] Click failed: no ROI specified")
                return ExecutionResult.FAILED
            if threshold is None:
                print("[Action] Click failed: no threshold specified")
                return ExecutionResult.FAILED

            result = self._poll_and_click(
                context,
                template,
                roi,
                threshold,
                shrink_percent,
                y_offset,
                center_click,
                timeout_ms=timeout_ms,
                poll_interval_ms=poll_interval_ms
            )
            # Return the result to caller - if detection failed, don't proceed
            return result

        else:
            # Fallback: click at last detection position (if available)
            box = context.variables.get("last_detection_box")
            if box:
                x, y = box
                context.hardware_controller.move_absolute(int(x), int(y))
                context.hardware_controller.click_current()
                time.sleep(POST_CLICK_DELAY_MS / 1000.0)
                print(f"[Action] Click at last detection ({int(x)}, {int(y)})")
                return ExecutionResult.SUCCESS
            else:
                print("[Action] Click failed: no target or template specified")
                return ExecutionResult.FAILED


class WaitHandler(ActionHandler):
    """Handle Wait action"""

    def __init__(self):
        super().__init__("Wait")

    def execute(self, context: ExecutionContext, action_param: Dict[str, Any]) -> ExecutionResult:
        duration_ms = action_param.get("duration_ms", 1000)
        duration_s = duration_ms / 1000.0
        print(f"[Action] Wait: {duration_ms}ms")
        stop_event = context.param.get("stop_event") if isinstance(context.param, dict) else None
        deadline = time.monotonic() + duration_s
        while True:
            if stop_event is not None and stop_event.is_set():
                print("[Pipeline] Cancellation requested during wait")
                return ExecutionResult.FAILED
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.05, remaining))
        return ExecutionResult.SUCCESS


class CustomActionHandler(ActionHandler):
    """Handle Custom action - delegates to registered functions"""

    FAILURE_SENTINEL = "__PIPELINE_ACTION_FAILED__"

    def __init__(self, registry: Dict[str, Callable]):
        super().__init__("Custom")
        self.registry = registry

    def execute(self, context: ExecutionContext, action_param: Dict[str, Any]) -> ExecutionResult:
        custom_action = action_param.get("custom_action", "")

        if custom_action in self.registry:
            # Build context dict for compatibility
            ctx = {
                'hardware_controller': context.hardware_controller,
                'vision_engine': context.vision_engine,
                'screenshot': context.screenshot,
                'param': action_param.get("param", {}),
                'variables': context.variables,
                'execution_context': context,
            }
            result = self.registry[custom_action](ctx)
            print(f"[Action] Custom: {custom_action}")
            if result is False:
                context.variables[self.FAILURE_SENTINEL] = custom_action
                return ExecutionResult.FAILED
            context.variables.pop(self.FAILURE_SENTINEL, None)
            return ExecutionResult.SUCCESS

        print(f"[Action] Custom action not found: {custom_action}")
        return ExecutionResult.FAILED


class RecognitionHandler:
    """Base class for recognition handlers"""

    def __init__(self, name: str):
        self.name = name

    def execute(self, context: ExecutionContext, recognition_param: Dict[str, Any]) -> tuple:
        """Returns (matched: bool, box: Optional[tuple], score: float)"""
        raise NotImplementedError


class TemplateMatchHandler(RecognitionHandler):
    """Handle TemplateMatch recognition"""

    def __init__(self):
        super().__init__("TemplateMatch")

    def execute(self, context: ExecutionContext, recognition_param: Dict[str, Any]) -> tuple:
        import time
        template = recognition_param.get("template", "")
        roi = recognition_param.get("roi", [])
        threshold = recognition_param.get("threshold", 0.8)

        template_name = template.split('/')[-1] if '/' in template else template

        if not context.vision_engine:
            print(f"[Recognition] {template_name}: FAILED - no vision engine")
            return False, None, 0.0

        # Always capture a fresh screenshot for each recognition.
        # Reusing old frames across nodes causes stale detections after UI-changing actions.
        screenshot_start = time.time()
        context.screenshot = context.vision_engine.get_screenshot(force_fresh=True)
        screenshot_time = (time.time() - screenshot_start) * 1000

        # VisionEngine.find_element requires screenshot as first argument
        match_start = time.time()
        result = context.vision_engine.find_element(
            context.screenshot,
            template_path=template,
            roi=tuple(roi) if roi else None,
            threshold=threshold
        )
        match_time = (time.time() - match_start) * 1000

        # result is Tuple[bool, float, Tuple[int, int]]
        if isinstance(result, tuple) and len(result) == 3:
            matched, score, box = result
        else:
            matched = False
            score = 0.0
            box = None

        status = "SUCCESS" if matched else "FAILED"
        print(f"[Recognition] {template_name}: {status}, score={score:.3f}, threshold={threshold}, screenshot={screenshot_time:.1f}ms, match={match_time:.1f}ms")
        return matched, box, score


class CustomRecognitionHandler(RecognitionHandler):
    """Handle Custom recognition - delegates to registered functions"""

    def __init__(self, registry: Dict[str, Callable]):
        super().__init__("Custom")
        self.registry = registry

    def execute(self, context: ExecutionContext, recognition_param: Dict[str, Any]) -> tuple:
        custom_recognition = recognition_param.get("custom_recognition", "")

        if custom_recognition in self.registry:
            ctx = {
                'hardware_controller': context.hardware_controller,
                'vision_engine': context.vision_engine,
                'screenshot': context.screenshot,
                'param': recognition_param.get("param", {}),
                'variables': context.variables,
                'execution_context': context,
            }
            result = self.registry[custom_recognition](ctx)
            print(f"[Recognition] Custom: {custom_recognition} -> matched={result.matched}")
            return result.matched, result.box, result.score

        print(f"[Recognition] Custom recognition not found: {custom_recognition}")
        return False, None, 0.0


class PipelineExecutor:
    """
    Main pipeline execution engine

    Usage:
        executor = PipelineExecutor(pipeline_json)
        executor.register_action_handler("KeyPress", KeyPressHandler())
        executor.register_recognition_handler("TemplateMatch", TemplateMatchHandler())

        context = ExecutionContext(hardware, vision)
        result = executor.execute("entry_node_name", context)
    """

    def __init__(self, pipeline: Dict[str, Any]):
        self.pipeline = pipeline
        self.action_handlers: Dict[str, ActionHandler] = {}
        self.recognition_handlers: Dict[str, RecognitionHandler] = {}
        self.execution_log: List[Dict[str, Any]] = []
        self.max_iterations = 1000  # Prevent infinite loops

    def register_action_handler(self, action_type: str, handler: ActionHandler):
        """Register an action handler"""
        self.action_handlers[action_type] = handler

    def register_recognition_handler(self, recognition_type: str, handler: RecognitionHandler):
        """Register a recognition handler"""
        self.recognition_handlers[recognition_type] = handler

    def execute_node(self, node_name: str, context: ExecutionContext) -> Optional[str]:
        """
        Execute a single node and return next node name

        Returns:
            Next node name, or None if workflow complete
        """
        import time
        node_start_time = time.time()

        if node_name not in self.pipeline:
            print(f"[Error] Node not found: {node_name}")
            return None

        node = self.pipeline[node_name]
        print(f"\n[Node] {node_name}: {node.get('desc', '')}")

        # Execute recognition if present
        recognition_result = False
        if "recognition" in node:
            recognition = node["recognition"]
            rec_type = recognition.get("type", "")

            if rec_type in self.recognition_handlers:
                handler = self.recognition_handlers[rec_type]
                # Custom recognition needs full config to keep custom_recognition name.
                rec_param = recognition if rec_type == "Custom" else recognition.get("param", recognition)
                matched, box, score = handler.execute(context, rec_param)

                # Handle state=disappear (wait for image to disappear)
                state = rec_param.get("state", "appear")
                if state == "disappear":
                    # For disappear state: success = NOT matched (image is gone)
                    recognition_result = not matched
                    if recognition_result:
                        print(f"[Recognition] State=disappear: image gone (was matched={matched})")
                else:
                    # Default: appear state - success = matched (image found)
                    recognition_result = matched

                # Update context with detection result
                if matched and box:
                    context.variables["last_detection_box"] = box
                else:
                    # Clear detection box on recognition failure
                    context.variables.pop("last_detection_box", None)
            else:
                print(f"[Warning] Recognition handler not found: {rec_type}")

        # Execute action if present
        if "action" in node:
            action = node["action"]
            action_type = action.get("type", "")

            has_recognition = "recognition" in node
            # Custom action needs full config to keep custom_action name.
            action_param = action if action_type == "Custom" else action.get("param", action)
            is_detection_click = False

            # Merge recognition params for click constraints/detection context
            if has_recognition and action_type == "Click":
                rec = node["recognition"]
                rec_param = rec.get("param", rec)
                merged_param = dict(rec_param)  # Copy recognition params
                merged_param.update(action_param)  # Override with action params
                action_param = merged_param
                is_detection_click = bool(action_param.get("template")) and not bool(action_param.get("target"))

            # Gate only non-detection clicks on recognition success.
            # Detection clicks must run polling logic even when single-shot recognition fails.
            if has_recognition and action_type == "Click" and not recognition_result and not is_detection_click:
                print(f"[Action] Click skipped: recognition failed, no detection to click on")
                if "on_error" in node:
                    return node["on_error"][0] if node["on_error"] else None
                if "on_false" in node:
                    return node["on_false"]
                return None

            if action_type in self.action_handlers:
                handler = self.action_handlers[action_type]

                result = handler.execute(context, action_param)

                if result == ExecutionResult.FAILED and "on_error" in node:
                    return node["on_error"][0] if node["on_error"] else None
                if result == ExecutionResult.FAILED:
                    return CustomActionHandler.FAILURE_SENTINEL
            else:
                print(f"[Warning] Action handler not found: {action_type}")

        # Determine next node
        # Priority: on_true/on_false (conditional) > next (sequential)
        next_node = None
        if "on_true" in node and recognition_result:
            next_node = node["on_true"]
        elif "on_false" in node and not recognition_result:
            next_node = node["on_false"]
        elif "next" in node:
            next_nodes = node["next"]
            if isinstance(next_nodes, list) and len(next_nodes) > 0:
                next_node = next_nodes[0]
            elif isinstance(next_nodes, str):
                next_node = next_nodes

        node_elapsed = (time.time() - node_start_time) * 1000
        print(f"[Node] {node_name} completed in {node_elapsed:.1f}ms -> {next_node if next_node else 'END'}")

        return next_node

    def execute(self, entry_node: str, context: ExecutionContext) -> bool:
        """
        Execute pipeline starting from entry node

        Returns:
            True if completed successfully, False otherwise
        """
        current_node = entry_node
        iteration = 0
        start_time = time.monotonic()
        max_duration_seconds = None
        if isinstance(getattr(context, "param", None), dict):
            max_duration_seconds = context.param.get("max_duration_seconds")
            stop_event = context.param.get("stop_event")
        else:
            stop_event = None
        if max_duration_seconds is not None:
            try:
                max_duration_seconds = float(max_duration_seconds)
            except (TypeError, ValueError):
                max_duration_seconds = None

        print(f"\n{'='*60}")
        print(f"[Pipeline] Starting execution from: {entry_node}")
        print(f"{'='*60}")

        while current_node and iteration < self.max_iterations:
            if stop_event is not None and stop_event.is_set():
                print("[Pipeline] Cancellation requested")
                return False
            if max_duration_seconds is not None:
                elapsed = time.monotonic() - start_time
                if elapsed >= max_duration_seconds:
                    print(f"[Pipeline] Timeout reached: {elapsed:.1f}s >= {max_duration_seconds:.1f}s")
                    return False

            next_node = self.execute_node(current_node, context)
            if next_node == CustomActionHandler.FAILURE_SENTINEL:
                print(f"[Pipeline] Action failed at node: {current_node}")
                return False

            self.execution_log.append({
                "node": current_node,
                "next": next_node,
                "iteration": iteration
            })

            current_node = next_node
            iteration += 1

            # No hardcoded delay - all delays controlled by YAML configuration
            # Use Wait action in pipeline if delay is needed

        success = current_node is None or iteration < self.max_iterations

        print(f"\n{'='*60}")
        print(f"[Pipeline] Execution {'completed' if success else 'timeout'}")
        print(f"{'='*60}")

        return success


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution"""
    pipeline_path: Path
    entry_node: str
    hardware_controller: Any
    vision_engine: Any


def create_executor_with_defaults(
    pipeline: Dict[str, Any],
    custom_action_registry: Dict[str, Callable] = None,
    custom_recognition_registry: Dict[str, Callable] = None
) -> PipelineExecutor:
    """
    Create a PipelineExecutor with default handlers registered

    Args:
        pipeline: Pipeline JSON dict
        custom_action_registry: Optional dict of custom action functions
        custom_recognition_registry: Optional dict of custom recognition functions

    Returns:
        Configured PipelineExecutor
    """
    executor = PipelineExecutor(pipeline)

    # Register default action handlers
    executor.register_action_handler("KeyPress", KeyPressHandler())
    executor.register_action_handler("Click", ClickHandler())
    executor.register_action_handler("Wait", WaitHandler())
    executor.register_action_handler("Move", MoveHandler())
    executor.register_action_handler("Scroll", ScrollHandler())

    # Register custom action handler with registry
    if custom_action_registry:
        executor.register_action_handler("Custom", CustomActionHandler(custom_action_registry))

    # Register default recognition handlers
    executor.register_recognition_handler("TemplateMatch", TemplateMatchHandler())

    # Register custom recognition handler with registry
    if custom_recognition_registry:
        executor.register_recognition_handler("Custom", CustomRecognitionHandler(custom_recognition_registry))

    return executor
