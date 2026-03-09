#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Donation Module Registration

Registers guild donation actions with the global registry.
Uses Pipeline Executor for modular workflow execution.
"""

from pathlib import Path
from ...register import action, recognition, RecognitionResult


# Pipeline path
PIPELINE_PATH = Path("assets/resource/pipeline/guild_donation.json")


@action("ExecuteDonation")
def execute_donation(context: dict):
    """
    Execute full guild donation workflow using Pipeline Executor.

    This action loads and executes the complete guild_donation.json pipeline,
    including all steps: open menu, detect UI, click donations, close UI.

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

    if not hardware or not vision:
        print("[Donation] Error: Hardware or Vision not available")
        return

    # Import here to avoid circular dependencies
    from ...modules.workflow_executor.executor import execute_pipeline

    # Execute the full pipeline
    success = execute_pipeline(
        pipeline_path=PIPELINE_PATH,
        entry_node="guild_donationMain",
        hardware_controller=hardware,
        vision_engine=vision,
        timeout_seconds=60.0
    )

    if success:
        print("[Donation] Workflow completed successfully")
    else:
        print("[Donation] Workflow failed or timed out")


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
        hardware.press('alt+u')
        print("[Action] OpenGuildMenu: Alt+U pressed")


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
        hardware.press('esc')
        print("[Action] CloseGuildMenu: ESC pressed")


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
