#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow Executor - High-level API for pipeline execution
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, Optional

from ...pkg.workflow.pipeline_executor import (
    PipelineExecutor,
    ExecutionContext,
    ExecutionResult,
    create_executor_with_defaults,
)
from ...register import Registry


def create_executor(pipeline_path: Path) -> PipelineExecutor:
    """
    Create a PipelineExecutor from a JSON file

    Args:
        pipeline_path: Path to pipeline JSON file

    Returns:
        Configured PipelineExecutor
    """
    with open(pipeline_path, 'r', encoding='utf-8') as f:
        pipeline = json.load(f)

    # Get custom action/recognition registries
    action_registry = {}
    recognition_registry = {}

    # Populate from global Registry
    for name in Registry.list_actions():
        action_registry[name] = Registry.get_action(name)

    for name in Registry.list_recognitions():
        recognition_registry[name] = Registry.get_recognition(name)

    return create_executor_with_defaults(
        pipeline,
        custom_action_registry=action_registry,
        custom_recognition_registry=recognition_registry
    )


def execute_pipeline(
    pipeline_path: Path,
    entry_node: str,
    hardware_controller: Any,
    vision_engine: Any,
    timeout_seconds: float = 300.0
) -> bool:
    """
    Execute a pipeline from start to finish

    Args:
        pipeline_path: Path to pipeline JSON
        entry_node: Entry node name (e.g., "guild_donationMain")
        hardware_controller: FerrumController instance
        vision_engine: VisionEngine instance
        timeout_seconds: Maximum execution time

    Returns:
        True if completed successfully

    Example:
        success = execute_pipeline(
            Path("assets/resource/pipeline/guild_donation.json"),
            "guild_donationMain",
            hardware,
            vision
        )
    """
    executor = create_executor(pipeline_path)

    context = ExecutionContext(
        hardware_controller=hardware_controller,
        vision_engine=vision_engine
    )

    print(f"\n[Workflow] Starting: {pipeline_path.name}")
    print(f"[Workflow] Entry: {entry_node}")

    start_time = time.time()
    success = executor.execute(entry_node, context)
    elapsed = time.time() - start_time

    print(f"[Workflow] Completed in {elapsed:.1f}s: {'SUCCESS' if success else 'FAILED'}")

    return success
