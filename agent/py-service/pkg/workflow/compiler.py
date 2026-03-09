"""
Workflow Compiler Module

Provides semantic compile-time validation for workflow definitions.
Checks step graph references, branch targets, loop safety, and recovery graph integrity.

Exports:
    compile_workflow: Compile and validate a WorkflowConfig into a CompiledWorkflow
    WorkflowCompilationError: Exception raised for compilation failures
"""

from typing import Set, List, Dict
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
    5. Validates recovery on_timeout references point to valid step IDs
    6. Detects recovery-only cycles (no normal path forward)
    7. Builds indexed step lookup for runtime efficiency

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

        # Validate recovery on_timeout reference
        if step.recovery.on_timeout is not None:
            if step.recovery.on_timeout not in valid_step_ids:
                errors.append(
                    f"Step '{step.step_id}': recovery.on_timeout references "
                    f"non-existent step '{step.recovery.on_timeout}'"
                )

    # Detect recovery-only cycles
    cycle_errors = _detect_recovery_cycles(step_index, valid_step_ids)
    errors.extend(cycle_errors)

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


def _detect_recovery_cycles(
    step_index: Dict[str, WorkflowStep],
    valid_step_ids: Set[str]
) -> List[str]:
    """
    Detect cycles formed exclusively by recovery on_timeout references.

    A recovery-only cycle occurs when steps form a closed loop using only
    on_timeout references without any normal path (next/on_true/on_false)
    leading out of the cycle. This would cause infinite recovery loops.

    Args:
        step_index: Dictionary mapping step_id to WorkflowStep
        valid_step_ids: Set of all valid step IDs

    Returns:
        List of error messages for detected cycles
    """
    errors: List[str] = []

    # Build recovery-only graph
    recovery_graph: Dict[str, str] = {}
    for step_id, step in step_index.items():
        if step.recovery.on_timeout is not None:
            recovery_graph[step_id] = step.recovery.on_timeout

    # Find cycles in recovery graph using DFS
    visited: Set[str] = set()
    rec_stack: Set[str] = set()

    def has_cycle_from(node: str, path: List[str]) -> bool:
        visited.add(node)
        rec_stack.add(node)

        if node in recovery_graph:
            neighbor = recovery_graph[node]
            if neighbor not in visited:
                if has_cycle_from(neighbor, path + [neighbor]):
                    return True
            elif neighbor in rec_stack:
                # Found a cycle - report it
                cycle_start = path.index(neighbor)
                cycle_path = path[cycle_start:] + [neighbor]
                errors.append(
                    f"Recovery-only cycle detected: {' -> '.join(cycle_path)}. "
                    f"Steps form a closed loop using only on_timeout references."
                )
                return True

        rec_stack.remove(node)
        return False

    for step_id in valid_step_ids:
        if step_id not in visited and step_id in recovery_graph:
            has_cycle_from(step_id, [step_id])

    return errors


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
