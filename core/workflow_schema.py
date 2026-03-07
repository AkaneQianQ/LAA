"""
Workflow Schema Module

Provides strict Pydantic v2 models for workflow configuration validation.
Enforces locked field and action constraints at startup.

Exports:
    WorkflowConfig: Top-level workflow configuration model
    WorkflowStep: Individual step with action and routing
    ActionConfig: Discriminated union of all action types
"""

from typing import Literal, Optional, Union, Tuple, List
from pydantic import BaseModel, Field, model_validator


# =============================================================================
# ACTION MODELS (Discriminated Union)
# =============================================================================

class ClickAction(BaseModel):
    """Click action at absolute or ROI-relative coordinates."""
    type: Literal["click"]
    x: int = Field(..., description="X coordinate (absolute or relative to ROI)")
    y: int = Field(..., description="Y coordinate (absolute or relative to ROI)")
    roi: Optional[Tuple[int, int, int, int]] = Field(
        None,
        description="Optional ROI as (x1, y1, x2, y2) for relative coordinates"
    )


class WaitAction(BaseModel):
    """Wait action with millisecond duration."""
    type: Literal["wait"]
    duration_ms: int = Field(
        ...,
        ge=0,
        description="Wait duration in milliseconds"
    )


class PressAction(BaseModel):
    """Press action with readable key name."""
    type: Literal["press"]
    key_name: str = Field(
        ...,
        description="Key name (e.g., 'enter', 'esc', 'alt+u')"
    )


class ScrollAction(BaseModel):
    """Scroll action with direction and ticks."""
    type: Literal["scroll"]
    direction: Literal["up", "down"] = Field(
        ...,
        description="Scroll direction"
    )
    ticks: int = Field(
        ...,
        ge=1,
        description="Number of scroll ticks"
    )


# Discriminated union for all action types
ActionConfig = Union[ClickAction, WaitAction, PressAction, ScrollAction]


# =============================================================================
# STEP MODEL
# =============================================================================

class WorkflowStep(BaseModel):
    """
    Single workflow step with action and routing.

    Each step must have a unique step_id and an action.
    Routing can be:
    - Simple: next -> step_id or None (end workflow)
    - Conditional: on_true/on_false for branching
    """
    step_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this step"
    )
    action: ActionConfig = Field(
        ...,
        discriminator="type",
        description="Action to execute in this step"
    )
    # Simple routing
    next: Optional[str] = Field(
        None,
        description="Next step ID, or None to end workflow"
    )
    # Conditional branching
    on_true: Optional[str] = Field(
        None,
        description="Step ID to go to if condition is true"
    )
    on_false: Optional[str] = Field(
        None,
        description="Step ID to go to if condition is false"
    )
    # Retry policy
    retry: int = Field(
        0,
        ge=0,
        description="Number of retry attempts on failure (0 = no retries)"
    )
    # Condition configuration for branching
    condition: Optional[dict] = Field(
        None,
        description="Condition configuration for conditional branching"
    )

    @model_validator(mode='after')
    def validate_routing(self):
        """Ensure routing is valid (not both simple and conditional)."""
        has_next = self.next is not None
        has_conditional = self.on_true is not None or self.on_false is not None

        if has_next and has_conditional:
            raise ValueError(
                f"Step '{self.step_id}' cannot have both 'next' and conditional routing "
                f"(on_true/on_false). Use one or the other."
            )

        return self


# =============================================================================
# WORKFLOW CONFIG MODEL
# =============================================================================

class WorkflowConfig(BaseModel):
    """
    Top-level workflow configuration.

    Defines a complete automation workflow with steps, actions,
    and routing. Enforces strict validation at load time.
    """
    name: str = Field(
        ...,
        min_length=1,
        description="Workflow name for identification"
    )
    start_step_id: str = Field(
        ...,
        min_length=1,
        description="ID of the first step to execute"
    )
    steps: List[WorkflowStep] = Field(
        ...,
        min_length=1,
        description="List of workflow steps"
    )

    @model_validator(mode='after')
    def validate_unique_step_ids(self):
        """Ensure all step_ids are unique."""
        step_ids = [step.step_id for step in self.steps]
        duplicates = set()
        seen = set()

        for step_id in step_ids:
            if step_id in seen:
                duplicates.add(step_id)
            seen.add(step_id)

        if duplicates:
            raise ValueError(
                f"Duplicate step IDs found: {sorted(duplicates)}. "
                f"Each step must have a unique step_id."
            )

        return self


# =============================================================================
# COMPILED WORKFLOW (Runtime representation)
# =============================================================================

class CompiledWorkflow:
    """
    Compiled workflow ready for execution.

    Contains validated workflow data with indexed steps for efficient
    runtime lookup. Created by workflow_compiler.compile_workflow().
    """

    def __init__(
        self,
        name: str,
        start_step_id: str,
        steps: List[WorkflowStep],
        step_index: dict
    ):
        self.name = name
        self.start_step_id = start_step_id
        self.steps = steps
        self.step_index = step_index

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a step by its ID."""
        return self.step_index.get(step_id)

    def __repr__(self) -> str:
        return f"CompiledWorkflow(name='{self.name}', steps={len(self.steps)})"
