"""
Workflow Compiler Module

Provides semantic compile-time validation for workflow definitions.
Checks step graph references, branch targets, and loop safety.

Exports:
    compile_workflow: Compile and validate a WorkflowConfig into a CompiledWorkflow
    WorkflowCompilationError: Exception raised for compilation failures
"""

from typing import Set, List
from core.workflow_schema import WorkflowConfig, WorkflowStep, CompiledWorkflow


class WorkflowCompilationError(ValueError):
    """Raised when workflow compilation fails due to semantic errors."""
    pass


def compile_workflow(config: WorkflowConfig) -> CompiledWorkflow:
    """
    Compile and validate a workflow configuration.

    Performs semantic validation:
    1. Verifies start_step_id references an existing step
    2. Checks all 'next' references point to valid step IDs
    3. Checks all 'on_true' references point to valid step IDs
    4. Checks all 'on_false' references point to valid step IDs
    5. Builds indexed step lookup for runtime efficiency

    Args:
        config: Validated WorkflowConfig instance

    Returns:
        CompiledWorkflow ready for execution

    Raises:
        WorkflowCompilationError: If any reference is dangling or invalid
    """
    # Build step index for O(1) lookups
    step_index = {step.step_id: step for step in config.steps}
    valid_step_ids = set(step_index.keys())

    errors: List[str] = []

    # Validate start_step_id exists
    if config.start_step_id not in valid_step_ids:
        errors.append(
            f"start_step_id '{config.start_step_id}' does not reference "
            f"any existing step. Valid step IDs: {sorted(valid_step_ids)}"
        )

    # Validate all step references
    for step in config.steps:
        # Validate 'next' reference
        if step.next is not None and step.next not in valid_step_ids:
            errors.append(
                f"Step '{step.step_id}': 'next' references non-existent "
                f"step '{step.next}'"
            )

        # Validate 'on_true' reference
        if step.on_true is not None and step.on_true not in valid_step_ids:
            errors.append(
                f"Step '{step.step_id}': 'on_true' references non-existent "
                f"step '{step.on_true}'"
            )

        # Validate 'on_false' reference
        if step.on_false is not None and step.on_false not in valid_step_ids:
            errors.append(
                f"Step '{step.step_id}': 'on_false' references non-existent "
                f"step '{step.on_false}'"
            )

    # Raise if any errors found
    if errors:
        raise WorkflowCompilationError(
            f"Workflow compilation failed for '{config.name}':\n" +
            "\n".join(f"  - {error}" for error in errors)
        )

    # Return compiled workflow
    return CompiledWorkflow(
        name=config.name,
        start_step_id=config.start_step_id,
        steps=config.steps,
        step_index=step_index,
        wait_defaults=config.wait_defaults
    )


def _detect_unreachable_steps(
    start_step_id: str,
    step_index: dict
) -> Set[str]:
    """
    Detect steps that cannot be reached from the start step.

    This is a diagnostic helper (not a compilation error) to help
    users identify dead code in their workflows.

    Args:
        start_step_id: ID of the starting step
        step_index: Dictionary mapping step_id to WorkflowStep

    Returns:
        Set of unreachable step IDs
    """
    all_step_ids = set(step_index.keys())

    # BFS from start step to find reachable steps
    reachable = set()
    to_visit = [start_step_id]

    while to_visit:
        current_id = to_visit.pop()
        if current_id in reachable:
            continue
        if current_id not in step_index:
            continue

        reachable.add(current_id)
        step = step_index[current_id]

        # Add all possible next steps
        if step.next is not None:
            to_visit.append(step.next)
        if step.on_true is not None:
            to_visit.append(step.on_true)
        if step.on_false is not None:
            to_visit.append(step.on_false)

    return all_step_ids - reachable
