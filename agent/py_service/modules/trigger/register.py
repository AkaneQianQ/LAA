#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trigger Module Registration

Registers trigger actions with the global registry.
Implements Task A (Up-Up-Down) and Task B (Offset Clicks + Enter) logic.
"""

import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import time
from pathlib import Path
from typing import List, Tuple, Optional
from ...register import action, recognition, RecognitionResult


# Default configurations matching trigger_action.py
DEFAULT_CONFIG = {
    "TASK_A": {
        "IMAGE": "assets/target_a.png",
        "ROI": (1088, 700, 1482, 846),
        "COOLDOWN": 0.3,
    },
    "TASK_B": {
        "IMAGES": ["assets/target_b_1.png", "assets/target_b_2.png"],
        "ROI": (1280, 0, 2560, 1440),
        "OFFSETS": [(7, 0), (127, 0)],
        "COOLDOWN": 0.3,
    }
}


@recognition("TriggerTargetADetection")
def detect_target_a(context: dict) -> RecognitionResult:
    """
    Detect target_a.png in specified ROI.

    Usage in Pipeline JSON:
    {
        "recognition": {
            "type": "Custom",
            "custom_recognition": "TriggerTargetADetection",
            "param": {
                "image": "assets/target_a.png",
                "roi": [1088, 700, 1482, 846],
                "threshold": 0.8
            }
        }
    }
    """
    screenshot = context.get('screenshot')
    vision = context.get('vision_engine')
    param = context.get('param', {})

    if screenshot is None or vision is None:
        return RecognitionResult(matched=False)

    # Get parameters with defaults
    image_path = param.get('image', DEFAULT_CONFIG["TASK_A"]["IMAGE"])
    roi = param.get('roi', DEFAULT_CONFIG["TASK_A"]["ROI"])
    threshold = param.get('threshold', 0.8)

    # Perform template matching
    result = vision.find_element(
        template_path=image_path,
        roi=tuple(roi),
        threshold=threshold
    )

    if result:
        print(f"[Trigger] Task A target detected at {result}")
        return RecognitionResult(
            matched=True,
            box=result,
            payload={'position': result}
        )

    return RecognitionResult(matched=False)


@recognition("TriggerTargetBDetection")
def detect_target_b(context: dict) -> RecognitionResult:
    """
    Detect target_b_1.png or target_b_2.png in specified ROI.
    Returns the best match if found.

    Usage in Pipeline JSON:
    {
        "recognition": {
            "type": "Custom",
            "custom_recognition": "TriggerTargetBDetection",
            "param": {
                "images": ["assets/target_b_1.png", "assets/target_b_2.png"],
                "roi": [1280, 0, 2560, 1440],
                "threshold": 0.8
            }
        }
    }
    """
    screenshot = context.get('screenshot')
    vision = context.get('vision_engine')
    param = context.get('param', {})

    if screenshot is None or vision is None:
        return RecognitionResult(matched=False)

    # Get parameters with defaults
    images = param.get('images', DEFAULT_CONFIG["TASK_B"]["IMAGES"])
    roi = param.get('roi', DEFAULT_CONFIG["TASK_B"]["ROI"])
    threshold = param.get('threshold', 0.8)

    best_match = None
    best_score = 0.0

    # Try each image and return the best match
    for image_path in images:
        result = vision.find_element(
            template_path=image_path,
            roi=tuple(roi),
            threshold=threshold
        )

        if result:
            # Calculate score based on match quality (if available from vision engine)
            score = result[2] if len(result) > 2 else 1.0
            if score > best_score:
                best_score = score
                best_match = result
                print(f"[Trigger] Task B target detected: {image_path} at {result[:2]}")

    if best_match:
        return RecognitionResult(
            matched=True,
            box=best_match[:2],
            payload={
                'position': best_match[:2],
                'score': best_score
            }
        )

    return RecognitionResult(matched=False)


@action("PressUpUpDown")
def press_up_up_down(context: dict):
    """
    Execute Task A key sequence: Up, Up, Down.
    This matches the original trigger_action.py Task A behavior.

    Usage in Pipeline JSON:
    {
        "action": {
            "type": "Custom",
            "custom_action": "PressUpUpDown"
        }
    }
    """
    hardware = context.get('hardware_controller')

    if not hardware:
        print("[Trigger] Error: Hardware controller not available")
        return

    # HID codes: 38 = Up Arrow, 40 = Down Arrow
    UP_KEY = 38
    DOWN_KEY = 40

    print("[Trigger] Task A: Executing Up-Up-Down sequence")

    # Press Up, Up, Down with 50ms delays
    hardware.press(UP_KEY)
    time.sleep(0.05)
    hardware.press(UP_KEY)
    time.sleep(0.05)
    hardware.press(DOWN_KEY)

    print("[Trigger] Task A: Sequence complete")


@action("ExecuteOffsetClicks")
def execute_offset_clicks(context: dict):
    """
    Execute Task B offset click sequence.
    Move to detected position + offset, click, repeat, then press Enter.

    Usage in Pipeline JSON:
    {
        "action": {
            "type": "Custom",
            "custom_action": "ExecuteOffsetClicks",
            "param": {
                "offsets": [[7, 0], [127, 0]],
                "click_delay_ms": 300
            }
        }
    }

    Note: Position is retrieved from recognition result in context.
    """
    hardware = context.get('hardware_controller')
    vision = context.get('vision_engine')
    param = context.get('param', {})

    if not hardware or not vision:
        print("[Trigger] Error: Hardware or Vision not available")
        return

    # Get offsets and delays from parameters or defaults
    offsets = param.get('offsets', DEFAULT_CONFIG["TASK_B"]["OFFSETS"])
    click_delay_ms = param.get('click_delay_ms', 300)
    click_delay_sec = click_delay_ms / 1000.0

    # Get detected position from previous recognition result
    # The position should be in the runtime context
    detected_pos = None
    if hasattr(vision, '_last_detection'):
        detected_pos = vision._last_detection

    if detected_pos is None:
        # Try to get from context if available
        last_result = context.get('last_recognition_result')
        if last_result and 'box' in last_result:
            detected_pos = last_result['box']

    if detected_pos is None:
        print("[Trigger] Error: No detection position available for offset clicks")
        return

    cx, cy = detected_pos[:2] if isinstance(detected_pos, (list, tuple)) else (0, 0)

    print(f"[Trigger] Task B: Executing offset clicks from position ({cx}, {cy})")

    # Execute offset clicks
    for i, (dx, dy) in enumerate(offsets):
        target_x = cx + dx
        target_y = cy + dy

        print(f"[Trigger] Task B: Click {i+1} at ({target_x}, {target_y})")

        # Move and click (using hardware controller's move_to if available)
        if hasattr(hardware, 'move_to'):
            hardware.move_to(target_x, target_y)
        else:
            # Fallback: direct move command
            hardware.move(target_x - hardware.get_cursor_pos()[0] if hasattr(hardware, 'get_cursor_pos') else 0,
                         target_y - hardware.get_cursor_pos()[1] if hasattr(hardware, 'get_cursor_pos') else 0)

        hardware.click()
        time.sleep(click_delay_sec)

    # Press Enter (HID 40)
    ENTER_KEY = 40
    hardware.press(ENTER_KEY)
    print("[Trigger] Task B: Offset clicks complete, Enter pressed")


@action("TriggerTaskA")
def execute_task_a(context: dict):
    """
    Full Task A execution: Detect + Press sequence.
    Convenience action for direct Task A execution.

    Usage in Pipeline JSON:
    {
        "action": {
            "type": "Custom",
            "custom_action": "TriggerTaskA"
        }
    }
    """
    vision = context.get('vision_engine')
    hardware = context.get('hardware_controller')

    if not vision or not hardware:
        print("[Trigger] Error: Required components not available")
        return

    # Detect
    result = vision.find_element(
        template_path=DEFAULT_CONFIG["TASK_A"]["IMAGE"],
        roi=DEFAULT_CONFIG["TASK_A"]["ROI"]
    )

    if result:
        print("[Trigger] Task A target found, executing sequence")
        press_up_up_down(context)
        time.sleep(DEFAULT_CONFIG["TASK_A"]["COOLDOWN"])
    else:
        print("[Trigger] Task A target not detected")


@action("TriggerTaskB")
def execute_task_b(context: dict):
    """
    Full Task B execution: Detect + Offset clicks + Enter.
    Convenience action for direct Task B execution.

    Usage in Pipeline JSON:
    {
        "action": {
            "type": "Custom",
            "custom_action": "TriggerTaskB"
        }
    }
    """
    vision = context.get('vision_engine')
    hardware = context.get('hardware_controller')

    if not vision or not hardware:
        print("[Trigger] Error: Required components not available")
        return

    # Try each target image
    for img_path in DEFAULT_CONFIG["TASK_B"]["IMAGES"]:
        result = vision.find_element(
            template_path=img_path,
            roi=DEFAULT_CONFIG["TASK_B"]["ROI"]
        )

        if result:
            print(f"[Trigger] Task B target found in {img_path}, executing clicks")
            # Store position for offset clicks
            if hasattr(vision, '_last_detection'):
                vision._last_detection = result
            execute_offset_clicks(context)
            time.sleep(DEFAULT_CONFIG["TASK_B"]["COOLDOWN"])
            return

    print("[Trigger] Task B target not detected")


def register():
    """Module registration entry - called by register_all_modules()"""
    print("[Module] trigger 已注册")
