"""
Workflow Bootstrap Module

Provides a bootstrap entrypoint to load compiled workflow and create executor.
Integrates config loading, runtime creation, and executor instantiation.

Exports:
    create_workflow_executor: Create a WorkflowExecutor from a workflow YAML file
    ConfigLoadError: Re-exported from config_loader for convenience
"""

from pathlib import Path
from typing import Union, Any

from core.config_loader import load_workflow_config, ConfigLoadError
from core.workflow_executor import WorkflowExecutor
from core.workflow_runtime import ActionDispatcher, ConditionEvaluator


def create_workflow_executor(
    workflow_path: Union[str, Path],
    controller: Any,
    vision_engine: Any
) -> WorkflowExecutor:
    """
    Create a WorkflowExecutor from a workflow YAML file.

    This is the main bootstrap entrypoint for config-driven workflow execution.
    It performs the full pipeline:
    1. Load workflow config from YAML file
    2. Compile for semantic validation
    3. Create ActionDispatcher with controller
    4. Create ConditionEvaluator with vision engine
    5. Create and return WorkflowExecutor

    Args:
        workflow_path: Path to the YAML workflow configuration file
        controller: Hardware controller with click, wait, press, scroll methods
        vision_engine: Vision engine with find_element method for image detection

    Returns:
        WorkflowExecutor ready to execute the workflow

    Raises:
        ConfigLoadError: If workflow config loading or validation fails
        FileNotFoundError: If the workflow file does not exist
        WorkflowCompilationError: If semantic validation fails
    """
    # Load and compile workflow config
    compiled = load_workflow_config(workflow_path)

    # Create runtime components
    dispatcher = ActionDispatcher(controller)
    condition_evaluator = ConditionEvaluator(vision_engine)

    # Create and return executor
    executor = WorkflowExecutor(
        workflow=compiled,
        action_dispatcher=dispatcher,
        condition_evaluator=condition_evaluator
    )

    return executor


# Re-export for convenience
__all__ = ['create_workflow_executor', 'ConfigLoadError']
