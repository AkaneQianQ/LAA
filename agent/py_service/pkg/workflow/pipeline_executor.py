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
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum


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


class ClickHandler(ActionHandler):
    """Handle Click action"""

    def __init__(self):
        super().__init__("Click")

    def execute(self, context: ExecutionContext, action_param: Dict[str, Any]) -> ExecutionResult:
        target = action_param.get("target")

        if context.hardware_controller:
            if target and len(target) == 2:
                # Absolute position click
                x, y = target
                context.hardware_controller.move_absolute(x, y)
                time.sleep(0.05)
                # Click at current position (relative 0,0)
                context.hardware_controller.click(0, 0)
                print(f"[Action] Click at ({x}, {y})")
            else:
                # Click at current position (for detection-based clicks)
                print("[Action] Click at current position")
            return ExecutionResult.SUCCESS
        return ExecutionResult.FAILED


class WaitHandler(ActionHandler):
    """Handle Wait action"""

    def __init__(self):
        super().__init__("Wait")

    def execute(self, context: ExecutionContext, action_param: Dict[str, Any]) -> ExecutionResult:
        duration_ms = action_param.get("duration_ms", 1000)
        duration_s = duration_ms / 1000.0
        print(f"[Action] Wait: {duration_ms}ms")
        time.sleep(duration_s)
        return ExecutionResult.SUCCESS


class CustomActionHandler(ActionHandler):
    """Handle Custom action - delegates to registered functions"""

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
                'param': action_param.get("param", {})
            }
            self.registry[custom_action](ctx)
            print(f"[Action] Custom: {custom_action}")
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
        template = recognition_param.get("template", "")
        roi = recognition_param.get("roi", [])
        threshold = recognition_param.get("threshold", 0.8)

        if not context.vision_engine:
            return False, None, 0.0

        # Take fresh screenshot if needed
        if context.screenshot is None:
            context.screenshot = context.vision_engine.get_screenshot()

        result = context.vision_engine.find_element(
            template_path=template,
            roi=tuple(roi) if roi else None,
            threshold=threshold
        )

        matched = result is not None
        score = 1.0 if matched else 0.0

        print(f"[Recognition] TemplateMatch: {template} -> matched={matched}")
        return matched, result, score


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
                'param': recognition_param.get("param", {})
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
                rec_param = recognition.get("param", recognition)
                matched, box, score = handler.execute(context, rec_param)
                recognition_result = matched

                # Update context with detection result
                if box:
                    context.variables["last_detection_box"] = box
            else:
                print(f"[Warning] Recognition handler not found: {rec_type}")

        # Execute action if present
        if "action" in node:
            action = node["action"]
            action_type = action.get("type", "")

            if action_type in self.action_handlers:
                handler = self.action_handlers[action_type]
                action_param = action.get("param", action)
                result = handler.execute(context, action_param)

                if result == ExecutionResult.FAILED and "on_error" in node:
                    return node["on_error"][0] if node["on_error"] else None
            else:
                print(f"[Warning] Action handler not found: {action_type}")

        # Determine next node
        # Priority: on_true/on_false (conditional) > next (sequential)
        if "on_true" in node and recognition_result:
            return node["on_true"]
        elif "on_false" in node and not recognition_result:
            return node["on_false"]
        elif "next" in node:
            next_nodes = node["next"]
            if isinstance(next_nodes, list) and len(next_nodes) > 0:
                return next_nodes[0]
            elif isinstance(next_nodes, str):
                return next_nodes

        return None

    def execute(self, entry_node: str, context: ExecutionContext) -> bool:
        """
        Execute pipeline starting from entry node

        Returns:
            True if completed successfully, False otherwise
        """
        current_node = entry_node
        iteration = 0

        print(f"\n{'='*60}")
        print(f"[Pipeline] Starting execution from: {entry_node}")
        print(f"{'='*60}")

        while current_node and iteration < self.max_iterations:
            next_node = self.execute_node(current_node, context)

            self.execution_log.append({
                "node": current_node,
                "next": next_node,
                "iteration": iteration
            })

            current_node = next_node
            iteration += 1

            # Small delay between nodes
            time.sleep(0.1)

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

    # Register custom action handler with registry
    if custom_action_registry:
        executor.register_action_handler("Custom", CustomActionHandler(custom_action_registry))

    # Register default recognition handlers
    executor.register_recognition_handler("TemplateMatch", TemplateMatchHandler())

    # Register custom recognition handler with registry
    if custom_recognition_registry:
        executor.register_recognition_handler("Custom", CustomRecognitionHandler(custom_recognition_registry))

    return executor
