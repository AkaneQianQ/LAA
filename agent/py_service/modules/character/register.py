#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Character Detection Module Registration

Registers character detection recognizers and actions with the global registry.
"""

from ...register import recognition, action, RecognitionResult
from .detector import CharacterDetector


@recognition("CharacterSlotDetection")
def detect_slots(context: dict) -> RecognitionResult:
    """
    Detect character slots on the character selection screen.

    Usage in Pipeline JSON:
    {
        "recognition": "Custom",
        "custom_recognition": "CharacterSlotDetection",
        "next": ["_HasCharacters", "_NoCharacters"]
    }
    """
    screenshot = context.get('screenshot')
    vision = context.get('vision_engine')

    if screenshot is None:
        return RecognitionResult(matched=False)

    detector = CharacterDetector(vision)
    slots = detector.detect_character_slots(screenshot)

    return RecognitionResult(
        matched=len(slots) > 0,
        box=None,
        score=1.0 if slots else 0.0,
        payload={'slots': slots, 'count': len(slots)}
    )


@recognition("AccountIdentification")
def identify_account(context: dict) -> RecognitionResult:
    """
    Identify account by screenshot of the account tag area.

    Usage in Pipeline JSON:
    {
        "recognition": "Custom",
        "custom_recognition": "AccountIdentification",
        "next": ["_KnownAccount", "_NewAccount"]
    }
    """
    screenshot = context.get('screenshot')
    vision = context.get('vision_engine')

    if screenshot is None:
        return RecognitionResult(matched=False)

    detector = CharacterDetector(vision)
    account_id = detector.identify_by_screenshot(screenshot)

    return RecognitionResult(
        matched=bool(account_id),
        box=None,
        score=1.0 if account_id else 0.0,
        payload={'account_id': account_id}
    )


@recognition("ScrollbarBottomDetection")
def detect_scrollbar_bottom(context: dict) -> RecognitionResult:
    """
    Detect if scrollbar is at bottom position.

    Usage in Pipeline JSON:
    {
        "recognition": "Custom",
        "custom_recognition": "ScrollbarBottomDetection",
        "next": ["_AtBottom", "_CanScrollMore"]
    }
    """
    screenshot = context.get('screenshot')
    vision = context.get('vision_engine')

    if screenshot is None or vision is None:
        return RecognitionResult(matched=False)

    from .detector import SCROLLBAR_BOTTOM_ROI, SCROLLBAR_BOTTOM_TEMPLATE
    import os

    template_path = os.path.join('assets', SCROLLBAR_BOTTOM_TEMPLATE)
    if not os.path.exists(template_path):
        return RecognitionResult(matched=False)

    result = vision.find_element(
        template_path=template_path,
        roi=SCROLLBAR_BOTTOM_ROI,
        threshold=0.8
    )

    return RecognitionResult(
        matched=result is not None,
        box=result if result else None,
        score=1.0 if result else 0.0,
        payload={'at_bottom': result is not None}
    )


@action("ScrollToNextRow")
def scroll_next_row(context: dict):
    """
    Scroll down to next row of characters.

    Usage in Pipeline JSON:
    {
        "action": {
            "type": "Custom",
            "custom_action": "ScrollToNextRow"
        }
    }
    """
    hardware = context.get('hardware_controller')
    if hardware:
        # Move to scroll area and scroll down 3 ticks
        hardware.move_to(1425, 826)
        hardware.scroll(-3)


@action("MoveToSafePosition")
def move_to_safe_position(context: dict):
    """
    Move mouse to safe position to avoid UI color changes.

    Usage in Pipeline JSON:
    {
        "action": {
            "type": "Custom",
            "custom_action": "MoveToSafePosition"
        }
    }
    """
    hardware = context.get('hardware_controller')
    if hardware:
        from .detector import MOUSE_SAFE_POSITION
        hardware.move_to(MOUSE_SAFE_POSITION[0], MOUSE_SAFE_POSITION[1])


def register():
    """Module registration entry - called by register_all_modules()"""
    # Decorators have already registered functions on import
    print("[模块] character 已注册")
