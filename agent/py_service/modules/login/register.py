#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Login Module Registration

Registers character switching and login actions with the global registry.
Note: Workflow implementation will be migrated from legacy auto_login.py
"""

from ...register import action, recognition, RecognitionResult


@action("SwitchCharacter")
def switch_character(context: dict):
    """
    Switch to the next character.

    Usage in Pipeline JSON:
    {
        "action": {
            "type": "Custom",
            "custom_action": "SwitchCharacter",
            "param": {
                "slot_index": 0
            }
        }
    }
    """
    hardware = context.get('hardware_controller')
    param = context.get('param', {})
    slot_index = param.get('slot_index', 0)

    # TODO: Migrate full character switching logic from legacy implementation
    # For now, this is a placeholder that will be extended

    if hardware:
        print(f"[Login] Switching to character slot {slot_index}...")


@action("EnterCharacterSelection")
def enter_character_selection(context: dict):
    """
    Enter character selection screen.

    Usage in Pipeline JSON:
    {
        "action": {
            "type": "Custom",
            "custom_action": "EnterCharacterSelection"
        }
    }
    """
    hardware = context.get('hardware_controller')
    if hardware:
        # Click quick switch button position
        # From CLAUDE.md: Quick switch button: (500, 850, 950, 1000)
        hardware.click(750, 925)


@action("ClickCharacterSlot")
def click_character_slot(context: dict):
    """
    Click on a specific character slot.

    Usage in Pipeline JSON:
    {
        "action": {
            "type": "Custom",
            "custom_action": "ClickCharacterSlot",
            "param": {
                "slot_index": 0
            }
        }
    }
    """
    hardware = context.get('hardware_controller')
    param = context.get('param', {})
    slot_index = param.get('slot_index', 0)

    if hardware:
        # Calculate slot position based on 3x3 grid
        # From CLAUDE.md SLOT_CONFIGS:
        slot_rois = [
            (904, 557, 1152, 624),   # Slot 0
            (1164, 557, 1412, 624),  # Slot 1
            (1425, 557, 1673, 624),  # Slot 2
            (904, 674, 1152, 741),   # Slot 3
            (1164, 674, 1412, 741),  # Slot 4
            (1425, 674, 1673, 741),  # Slot 5
            (904, 791, 1152, 858),   # Slot 6
            (1164, 791, 1412, 858),  # Slot 7
            (1425, 791, 1673, 858),  # Slot 8
        ]

        if 0 <= slot_index < len(slot_rois):
            roi = slot_rois[slot_index]
            # Click center of ROI
            x = (roi[0] + roi[2]) // 2
            y = (roi[1] + roi[3]) // 2
            hardware.click(x, y)


@action("ConfirmCharacterLogin")
def confirm_character_login(context: dict):
    """
    Confirm character login (yellow login button).

    Usage in Pipeline JSON:
    {
        "action": {
            "type": "Custom",
            "custom_action": "ConfirmCharacterLogin"
        }
    }
    """
    hardware = context.get('hardware_controller')
    if hardware:
        # From CLAUDE.md: Login button: (1200, 880, 1700, 960)
        # Click center of login button
        hardware.click(1450, 920)


@recognition("OnCharacterSelectionScreen")
def check_character_selection_screen(context: dict) -> RecognitionResult:
    """
    Check if currently on character selection screen.

    Usage in Pipeline JSON:
    {
        "recognition": "Custom",
        "custom_recognition": "OnCharacterSelectionScreen",
        "next": ["_OnSelectionScreen", "_NotOnSelectionScreen"]
    }
    """
    screenshot = context.get('screenshot')
    vision = context.get('vision_engine')

    if screenshot is None or vision is None:
        return RecognitionResult(matched=False)

    import os

    # Check for quick switch button (indicates character selection)
    template_path = os.path.join('assets', 'resource', 'image', 'btn_quick_switch.png')
    if not os.path.exists(template_path):
        return RecognitionResult(matched=False)

    # Quick switch button ROI (from CLAUDE.md)
    roi = (500, 850, 950, 1000)

    result = vision.find_element(
        template_path=template_path,
        roi=roi,
        threshold=0.8
    )

    return RecognitionResult(
        matched=result is not None,
        box=result if result else None,
        score=1.0 if result else 0.0
    )


@recognition("LoginConfirmationDialog")
def check_login_confirmation(context: dict) -> RecognitionResult:
    """
    Check if login confirmation dialog is shown.

    Usage in Pipeline JSON:
    {
        "recognition": "Custom",
        "custom_recognition": "LoginConfirmationDialog",
        "next": ["_ShowDialog", "_NoDialog"]
    }
    """
    screenshot = context.get('screenshot')
    vision = context.get('vision_engine')

    if screenshot is None or vision is None:
        return RecognitionResult(matched=False)

    import os

    # Check for login confirmation popup
    template_path = os.path.join('assets', 'resource', 'image', 'login_popup_confirm.png')
    if not os.path.exists(template_path):
        return RecognitionResult(matched=False)

    # Login confirm popup ROI (from CLAUDE.md)
    roi = (1100, 700, 1500, 1100)

    result = vision.find_element(
        template_path=template_path,
        roi=roi,
        threshold=0.8
    )

    return RecognitionResult(
        matched=result is not None,
        box=result if result else None,
        score=1.0 if result else 0.0
    )


def register():
    """Module registration entry - called by register_all_modules()"""
    print("[模块] login 已注册")
