#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Donation Module Registration

Registers guild donation actions with the global registry.
Note: Workflow implementation will be migrated from legacy guild_donation.py
"""

from ...register import action, recognition, RecognitionResult


@action("ExecuteDonation")
def execute_donation(context: dict):
    """
    Execute a single guild donation.

    Usage in Pipeline JSON:
    {
        "action": {
            "type": "Custom",
            "custom_action": "ExecuteDonation"
        }
    }
    """
    hardware = context.get('hardware_controller')
    vision = context.get('vision_engine')

    # TODO: Migrate full donation workflow from legacy implementation
    # For now, this is a placeholder that will be extended

    if hardware and vision:
        print("[Donation] Executing donation workflow...")
        # Legacy steps:
        # 1. Open ESC menu (Alt+U or ESC + click)
        # 2. Click guild button
        # 3. Click donation tab
        # 4. Execute silver donation
        # 5. Confirm donation
        # 6. Close UI


@action("OpenGuildMenu")
def open_guild_menu(context: dict):
    """
    Open guild menu via Alt+U shortcut.

    Usage in Pipeline JSON:
    {
        "action": {
            "type": "Custom",
            "custom_action": "OpenGuildMenu"
        }
    }
    """
    hardware = context.get('hardware_controller')
    if hardware:
        # Alt+U shortcut for guild menu
        hardware.press_key('alt+u')


@action("CloseGuildMenu")
def close_guild_menu(context: dict):
    """
    Close guild menu via ESC key.

    Usage in Pipeline JSON:
    {
        "action": {
            "type": "Custom",
            "custom_action": "CloseGuildMenu"
        }
    }
    """
    hardware = context.get('hardware_controller')
    if hardware:
        hardware.press_key('esc')


@recognition("GuildMenuOpen")
def check_guild_menu_open(context: dict) -> RecognitionResult:
    """
    Check if guild menu is currently open.

    Usage in Pipeline JSON:
    {
        "recognition": "Custom",
        "custom_recognition": "GuildMenuOpen",
        "next": ["_GuildMenuOpen", "_GuildMenuClosed"]
    }
    """
    screenshot = context.get('screenshot')
    vision = context.get('vision_engine')

    if screenshot is None or vision is None:
        return RecognitionResult(matched=False)

    import os

    # Check for guild flag mark (indicates guild UI is open)
    template_path = os.path.join('assets', 'resource', 'image', 'guild_flag_mark.png')
    if not os.path.exists(template_path):
        return RecognitionResult(matched=False)

    # Guild flag mark ROI (from CLAUDE.md)
    roi = (1000, 200, 1600, 400)

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
    print("[模块] donation 已注册")
