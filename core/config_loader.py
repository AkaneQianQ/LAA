"""
Configuration Loader Module

Provides YAML-only workflow configuration loading with strict validation.
Implements fail-fast startup behavior - any validation error blocks execution.

Exports:
    load_workflow_config: Load and compile a workflow from a YAML file
    ConfigLoadError: Exception raised for configuration loading failures
"""

import os
from pathlib import Path
from typing import Union

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from core.workflow_schema import WorkflowConfig
from core.workflow_compiler import compile_workflow, CompiledWorkflow, WorkflowCompilationError


class ConfigLoadError(ValueError):
    """Raised when configuration loading fails."""
    pass


def load_workflow_config(path: Union[str, Path]) -> CompiledWorkflow:
    """
    Load and compile a workflow configuration from a YAML file.

    This is the single public entrypoint for workflow configuration loading.
    It implements a strict pipeline:
    1. Validate file extension (.yaml or .yml)
    2. Read file contents
    3. Parse YAML safely (yaml.safe_load)
    4. Validate against WorkflowConfig schema
    5. Compile for semantic validation (step references)

    Args:
        path: Path to the YAML workflow configuration file

    Returns:
        CompiledWorkflow ready for execution

    Raises:
        ConfigLoadError: If file extension is invalid
        FileNotFoundError: If the file does not exist
        yaml.YAMLError: If YAML parsing fails
        ValidationError: If schema validation fails
        WorkflowCompilationError: If semantic validation fails
    """
    path = Path(path)

    # Validate file extension (YAML only)
    if path.suffix.lower() not in ('.yaml', '.yml'):
        raise ConfigLoadError(
            f"Invalid file extension '{path.suffix}'. "
            f"Workflow config must be a YAML file (.yaml or .yml). "
            f"Path: {path}"
        )

    # Check file exists
    if not path.exists():
        raise FileNotFoundError(f"Workflow config file not found: {path}")

    # Check PyYAML is available
    if not HAS_YAML:
        raise ConfigLoadError(
            "PyYAML is required but not installed. "
            "Install with: pip install pyyaml"
        )

    # Read and parse YAML safely
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigLoadError(f"Failed to parse YAML from {path}: {e}") from e

    # Handle empty file
    if raw_config is None:
        raise ConfigLoadError(f"Workflow config file is empty: {path}")

    # Validate against schema
    try:
        workflow_config = WorkflowConfig.model_validate(raw_config)
    except Exception as e:
        raise ConfigLoadError(
            f"Workflow schema validation failed for {path}: {e}"
        ) from e

    # Compile for semantic validation
    try:
        compiled = compile_workflow(workflow_config)
    except WorkflowCompilationError:
        raise  # Re-raise compilation errors as-is
    except Exception as e:
        raise ConfigLoadError(
            f"Workflow compilation failed for {path}: {e}"
        ) from e

    return compiled


def load_workflow_config_safe(
    path: Union[str, Path],
    default: CompiledWorkflow = None
) -> CompiledWorkflow:
    """
    Load workflow config with fallback to default on any error.

    This is a convenience wrapper for cases where you want to
    optionally load a config without raising exceptions.

    Args:
        path: Path to the YAML workflow configuration file
        default: Default value to return if loading fails

    Returns:
        CompiledWorkflow if successful, default otherwise
    """
    try:
        return load_workflow_config(path)
    except Exception:
        return default
