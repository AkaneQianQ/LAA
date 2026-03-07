"""
Workflow Bootstrap Module

Provides a bootstrap entrypoint to load compiled workflow and create executor.
Integrates config loading, runtime creation, executor instantiation, and
ACE compliance validation.

Exports:
    create_workflow_executor: Create a WorkflowExecutor from a workflow YAML file
    ConfigLoadError: Re-exported from config_loader for convenience
    ComplianceError: Re-exported from compliance_guard for convenience
"""

from pathlib import Path
from typing import Union, Any, Optional, Dict

from core.config_loader import load_workflow_config, ConfigLoadError
from core.workflow_executor import WorkflowExecutor
from core.workflow_runtime import ActionDispatcher, ConditionEvaluator
from core.compliance_guard import ComplianceGuard, ComplianceError
from core.hardware_input_gateway import HardwareInputGateway


def create_workflow_executor(
    workflow_path: Union[str, Path],
    controller: Any,
    vision_engine: Any,
    enable_compliance_guard: bool = True,
    compliance_config: Optional[Dict[str, Any]] = None
) -> WorkflowExecutor:
    """
    Create a WorkflowExecutor from a workflow YAML file.

    This is the main bootstrap entrypoint for config-driven workflow execution.
    It performs the full pipeline:
    1. Run ACE compliance validation (if enabled)
    2. Load workflow config from YAML file
    3. Compile for semantic validation
    4. Create ActionDispatcher with controller
    5. Create ConditionEvaluator with vision engine
    6. Create and return WorkflowExecutor

    Args:
        workflow_path: Path to the YAML workflow configuration file
        controller: Hardware controller with click, wait, press, scroll methods
        vision_engine: Vision engine with find_element method for image detection
        enable_compliance_guard: Whether to run ACE compliance validation
        compliance_config: Optional configuration for compliance validation

    Returns:
        WorkflowExecutor ready to execute the workflow

    Raises:
        ConfigLoadError: If workflow config loading or validation fails
        FileNotFoundError: If the workflow file does not exist
        WorkflowCompilationError: If semantic validation fails
        ComplianceError: If ACE compliance validation fails
    """
    # Step 1: ACE compliance validation
    if enable_compliance_guard:
        guard = ComplianceGuard()
        config = compliance_config or {"hardware_only": True}

        # Validate startup compliance (fail-fast)
        guard.validate_startup(
            hardware_controller=controller,
            config=config,
            fail_fast=True
        )

    # Step 2: Load and compile workflow config
    compiled = load_workflow_config(workflow_path)

    # Step 3: Create runtime components
    dispatcher = ActionDispatcher(controller, vision_engine)
    condition_evaluator = ConditionEvaluator(vision_engine)

    # Step 4: Create and return executor
    executor = WorkflowExecutor(
        workflow=compiled,
        action_dispatcher=dispatcher,
        condition_evaluator=condition_evaluator
    )

    return executor


# Re-export for convenience
__all__ = ['create_workflow_executor', 'ConfigLoadError', 'ComplianceError']
