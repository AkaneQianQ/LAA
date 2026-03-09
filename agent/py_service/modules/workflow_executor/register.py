#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow Executor Module Registration
"""

from ...register import action, recognition
from .executor import execute_pipeline, create_executor


@action("ExecutePipeline")
def execute_pipeline_action(context: dict):
    """
    Execute a pipeline by path.

    Usage:
    {
        "action": {
            "type": "Custom",
            "custom_action": "ExecutePipeline",
            "param": {
                "pipeline_path": "assets/resource/pipeline/guild_donation.json",
                "entry_node": "guild_donationMain"
            }
        }
    }
    """
    import os
    from pathlib import Path

    hardware = context.get('hardware_controller')
    vision = context.get('vision_engine')
    param = context.get('param', {})

    pipeline_path = param.get('pipeline_path', '')
    entry_node = param.get('entry_node', '')

    if not hardware or not vision:
        print("[Workflow] Error: Hardware or Vision not available")
        return

    # Convert to absolute path if relative
    if not os.path.isabs(pipeline_path):
        pipeline_path = Path(pipeline_path)

    success = execute_pipeline(
        pipeline_path=Path(pipeline_path),
        entry_node=entry_node,
        hardware_controller=hardware,
        vision_engine=vision
    )

    return success


def register():
    """Module registration entry"""
    print("[模块] workflow_executor 已注册")
