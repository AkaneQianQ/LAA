"""
Workflow Bootstrap Module

Provides a bootstrap entrypoint to load compiled workflow and create executor.
Integrates config loading, runtime creation, executor instantiation, and
ACE compliance validation.

Exports:
    create_workflow_executor: Create a WorkflowExecutor from a workflow YAML file
    create_workflow_executor_with_account: Create executor with account context
    ConfigLoadError: Re-exported from config_loader for convenience
    ComplianceError: Re-exported from compliance_guard for convenience
"""

from pathlib import Path
from typing import Union, Any, Optional, Dict

from .executor import WorkflowExecutor
from .runtime import ActionDispatcher, ConditionEvaluator
from .schema import WorkflowConfig, ConfigLoadError
from ..recovery.compliance import ComplianceGuard, ComplianceError
from ..ferrum.controller import FerrumController

# AccountContext placeholder - to be implemented in database module
class AccountContext:
    def __init__(self, account_id: str):
        self.account_id = account_id

def load_workflow_config(path: Union[str, Path]) -> dict:
    """Load workflow configuration from YAML file"""
    import yaml
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def create_workflow_executor(
    workflow_path: Union[str, Path],
    controller: Any,
    vision_engine: Any,
    enable_compliance_guard: bool = True,
    compliance_config: Optional[Dict[str, Any]] = None,
    account_context: Optional[AccountContext] = None
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
        account_context: Optional account context for account-aware execution

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
    # Pass account_id from context if provided
    account_id = account_context.account_hash if account_context else None

    executor = WorkflowExecutor(
        workflow=compiled,
        action_dispatcher=dispatcher,
        condition_evaluator=condition_evaluator,
        account_id=account_id
    )

    return executor


def create_workflow_executor_with_account(
    workflow_path: Union[str, Path],
    account_context: AccountContext,
    controller: Any,
    vision_engine: Any,
    enable_compliance_guard: bool = True,
    compliance_config: Optional[Dict[str, Any]] = None
) -> WorkflowExecutor:
    """
    Create a WorkflowExecutor with account-specific configuration.

    This factory function creates an executor configured for a specific
    account context, using account-specific settings for loop limits,
    progress tracking, and error logging context.

    Args:
        workflow_path: Path to the YAML workflow configuration file
        account_context: Account context with character count and progress tracker
        controller: Hardware controller with click, wait, press, scroll methods
        vision_engine: Vision engine with find_element method for image detection
        enable_compliance_guard: Whether to run ACE compliance validation
        compliance_config: Optional configuration for compliance validation

    Returns:
        WorkflowExecutor configured for the specified account

    Example:
        context = account_manager.get_or_create_context(screenshot)
        executor = create_workflow_executor_with_account(
            "config/workflow.yaml",
            context,
            controller,
            vision_engine
        )
    """
    return create_workflow_executor(
        workflow_path=workflow_path,
        controller=controller,
        vision_engine=vision_engine,
        enable_compliance_guard=enable_compliance_guard,
        compliance_config=compliance_config,
        account_context=account_context
    )


# Re-export for convenience
__all__ = [
    'create_workflow_executor',
    'create_workflow_executor_with_account',
    'ConfigLoadError',
    'ComplianceError'
]
