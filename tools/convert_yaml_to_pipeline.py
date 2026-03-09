#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML Workflow to JSON Pipeline Converter

Converts YAML workflow definitions to MaaEnd-style JSON Pipeline format.
Keeps original YAML files intact - creates new JSON files in assets/resource/pipeline/

Usage:
    python tools/convert_yaml_to_pipeline.py assets/tasks/account_indexing.yaml
    python tools/convert_yaml_to_pipeline.py assets/tasks/guild_donation.yaml
    python tools/convert_yaml_to_pipeline.py assets/tasks/character_switch.yaml
"""

import yaml
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def convert_press_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Convert press action to KeyPress"""
    return {
        "type": "KeyPress",
        "param": {
            "key": action.get("key_name", action.get("key", ""))
        }
    }


def convert_click_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Convert click action to Click"""
    coords = action.get("coordinates", [0, 0])
    return {
        "type": "Click",
        "param": {
            "target": coords
        }
    }


def convert_click_detected_action(action: Dict[str, Any]) -> tuple:
    """Convert click_detected to Recognition + Click"""
    recognition = {
        "type": "TemplateMatch",
        "param": {
            "template": action.get("image", ""),
            "roi": action.get("roi", []),
            "threshold": action.get("threshold", 0.8)
        }
    }

    click_action = {
        "type": "Click"
    }

    return recognition, click_action


def convert_wait_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Convert wait action to Wait"""
    return {
        "type": "Wait",
        "param": {
            "duration_ms": action.get("duration_ms", 1000)
        }
    }


def convert_wait_image_action(action: Dict[str, Any]) -> tuple:
    """Convert wait_image to Recognition with timeout"""
    recognition = {
        "type": "TemplateMatch",
        "param": {
            "template": action.get("image", ""),
            "roi": action.get("roi", []),
            "threshold": action.get("threshold", 0.8)
        }
    }

    # timeout is handled at node level
    return recognition, action.get("timeout_ms", 5000)


def convert_capture_roi_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Convert capture_roi to Custom recognition"""
    return {
        "type": "Custom",
        "custom_recognition": "CaptureROI",
        "param": {
            "roi": action.get("roi", []),
            "output_key": action.get("output_key", "captured_roi")
        }
    }


def convert_scroll_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Convert scroll action to Scroll"""
    return {
        "type": "Scroll",
        "param": {
            "direction": action.get("direction", "down"),
            "ticks": action.get("ticks", 3)
        }
    }


def convert_step_to_node(step: Dict[str, Any], index: int) -> tuple:
    """Convert a YAML step to a Pipeline node"""
    step_id = step.get("step_id", f"Step{index}")
    action = step.get("action", {})
    action_type = action.get("type", "")

    node = {
        "desc": step.get("name", step_id)
    }

    # Convert action based on type
    if action_type == "press":
        node["action"] = convert_press_action(action)

    elif action_type == "click":
        node["action"] = convert_click_action(action)

    elif action_type == "click_detected":
        recognition, click_action = convert_click_detected_action(action)
        node["recognition"] = recognition
        node["action"] = click_action

    elif action_type == "wait":
        node["action"] = convert_wait_action(action)

    elif action_type == "wait_image":
        recognition, timeout = convert_wait_image_action(action)
        node["recognition"] = recognition
        node["timeout"] = timeout

    elif action_type == "capture_roi":
        node["recognition"] = convert_capture_roi_action(action)

    elif action_type == "scroll":
        node["action"] = convert_scroll_action(action)

    elif action_type == "custom":
        node["action"] = {
            "type": "Custom",
            "custom_action": action.get("custom_action", ""),
            "param": action.get("param", {})
        }

    # Handle error recovery
    if "on_error" in step:
        node["on_error"] = step["on_error"]

    # Handle conditional branching
    if "on_true" in step:
        node["on_true"] = step["on_true"]
    if "on_false" in step:
        node["on_false"] = step["on_false"]

    return step_id, node


def convert_workflow(yaml_path: Path) -> Dict[str, Any]:
    """Convert entire YAML workflow to Pipeline JSON"""
    with open(yaml_path, "r", encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    pipeline = {}
    node_order = []

    # Convert each step to a node
    for i, step in enumerate(workflow.get("steps", [])):
        node_name, node = convert_step_to_node(step, i)
        pipeline[node_name] = node
        node_order.append(node_name)

    # Link nodes (sequential by default)
    for i, node_name in enumerate(node_order):
        node = pipeline[node_name]

        # If node already has on_true/on_error, don't override
        if "on_true" not in node and "on_error" not in node:
            if i + 1 < len(node_order):
                next_node = node_order[i + 1]
                step = workflow["steps"][i]
                explicit_next = step.get("next")

                if explicit_next:
                    node["next"] = [explicit_next]
                else:
                    node["next"] = [next_node]
            else:
                # Last node - no next
                pass

    # Add entry node pointing to first step
    start_step = workflow.get("start_step_id")
    if start_step and node_order:
        entry_name = f"{yaml_path.stem}Main"
        pipeline[entry_name] = {
            "desc": f"{workflow.get('name', 'Task')} main entry",
            "next": [start_step]
        }

    return pipeline


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_yaml_to_pipeline.py <yaml_file>")
        print("  or:  python convert_yaml_to_pipeline.py --all")
        sys.exit(1)

    if sys.argv[1] == "--all":
        # Convert all YAML files in assets/tasks/
        tasks_dir = Path("assets/tasks")
        yaml_files = list(tasks_dir.glob("*.yaml"))

        print(f"Found {len(yaml_files)} YAML files to convert")

        for yaml_file in yaml_files:
            pipeline = convert_workflow(yaml_file)

            output_path = Path("assets/resource/pipeline") / f"{yaml_file.stem}.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(pipeline, f, indent=4, ensure_ascii=False)

            print(f"Converted: {yaml_file} -> {output_path}")
    else:
        # Convert single file
        yaml_file = Path(sys.argv[1])

        if not yaml_file.exists():
            print(f"Error: File not found: {yaml_file}")
            sys.exit(1)

        pipeline = convert_workflow(yaml_file)

        # Output to assets/resource/pipeline/
        output_path = Path("assets/resource/pipeline") / f"{yaml_file.stem}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(pipeline, f, indent=4, ensure_ascii=False)

        print(f"Converted: {yaml_file} -> {output_path}")
        print(f"Nodes: {len(pipeline)}")


if __name__ == "__main__":
    main()
