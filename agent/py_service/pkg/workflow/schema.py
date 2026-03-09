"""
Workflow Schema Module

Provides strict Pydantic v2 models for workflow configuration validation.
Enforces locked field and action constraints at startup.

Exports:
    WorkflowConfig: Top-level workflow configuration model
    WorkflowStep: Individual step with action and routing
    ActionConfig: Discriminated union of all action types
    RecoveryConfig: Step-level recovery and audit configuration
"""

from typing import Literal, Optional, Union, Tuple, List, Dict, Any
from pydantic import BaseModel, Field, model_validator


class ConfigLoadError(ValueError):
    """Raised when workflow configuration fails to load."""
    pass


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
    random_y: int = Field(
        0,
        ge=0,
        description="Random Y offset range (+/- pixels) for vertical randomization"
    )


class MoveAction(BaseModel):
    """Move mouse to absolute coordinates without clicking."""
    type: Literal["move"]
    x: int = Field(..., description="X coordinate (absolute)")
    y: int = Field(..., description="Y coordinate (absolute)")


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


class WaitImageAction(BaseModel):
    """
    Intelligent wait action based on image appearance/disappearance.

    Replaces hardcoded sleep with state-driven waits for UI synchronization.
    Supports both 'appear' (wait for image to show) and 'disappear' (wait for image to hide).
    """
    type: Literal["wait_image"]
    state: Literal["appear", "disappear"] = Field(
        ...,
        description="Wait condition: 'appear' waits for image to appear, 'disappear' waits for it to vanish"
    )
    image: str = Field(
        ...,
        min_length=1,
        description="Template image filename for matching (e.g., 'btn_login.png')"
    )
    roi: Tuple[int, int, int, int] = Field(
        ...,
        description="Region of interest as (x1, y1, x2, y2) for template matching"
    )
    timeout_ms: Optional[int] = Field(
        None,
        ge=1,
        description="Override timeout in milliseconds (uses workflow default if not set)"
    )
    poll_interval_ms: Optional[int] = Field(
        None,
        ge=1,
        description="Override polling interval in milliseconds (uses workflow default if not set)"
    )
    stability_hits: int = Field(
        1,
        ge=1,
        le=5,
        description="Required consecutive hits for stability confirmation (default 1, max 5)"
    )
    threshold: float = Field(
        0.8,
        ge=0.0,
        le=1.0,
        description="Matching confidence threshold (default 0.8)"
    )


class ClickDetectedAction(BaseModel):
    """
    Click action at detected image position with safe-area randomization.

    Detects image in ROI, then clicks at a random position within a
    "safe area" (ROI shrunk by shrink_percent) to avoid clicking edges
    and provide anti-detection randomization.
    """
    type: Literal["click_detected"]
    image: str = Field(
        ...,
        description="Template image filename to detect and click"
    )
    roi: Tuple[int, int, int, int] = Field(
        ...,
        description="Region of interest as (x1, y1, x2, y2) for template matching"
    )
    threshold: float = Field(
        0.8,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for match"
    )
    shrink_percent: float = Field(
        0.10,
        ge=0.0,
        le=0.5,
        description="Shrink percentage for safe click area (default 10%, e.g., 0.10)"
    )
    y_offset: float = Field(
        0.0,
        ge=0.0,
        le=0.9,
        description="Vertical offset from top of ROI for clickable area (0.0-0.9, e.g., 0.33 skips top 33%)"
    )


class CaptureROIAction(BaseModel):
    """
    Capture ROI action for screenshot-based account indexing.

    Extracts a region from the current screenshot and stores it in the
    workflow context for later processing (e.g., perceptual hash comparison).
    Optionally saves the captured image to a file path.
    """
    type: Literal["capture_roi"]
    roi: Tuple[int, int, int, int] = Field(
        ...,
        description="Region of interest as (x1, y1, x2, y2) to capture"
    )
    output_key: str = Field(
        ...,
        description="Key to store captured image in workflow context"
    )
    save_path: Optional[str] = Field(
        None,
        description="Optional path to save captured screenshot"
    )


# Discriminated union for all action types
ActionConfig = Union[ClickAction, ClickDetectedAction, CaptureROIAction, MoveAction, PressAction, ScrollAction, WaitAction, WaitImageAction]


# =============================================================================
# RECOVERY CONFIG MODEL
# =============================================================================

class RecoveryConfig(BaseModel):
    """
    Step-level recovery and audit configuration.

    Defines error recovery behavior for workflow steps, including anchor markers,
    timeout rollback targets, escalation limits, and optional audit context.
    This enables deterministic recovery logic that can be validated at compile time.
    """
    anchor: bool = Field(
        False,
        description="If True, this step is a stable recovery anchor point"
    )
    on_timeout: Optional[str] = Field(
        None,
        description="Step ID to rollback to when timeout occurs (must reference an anchor)"
    )
    max_escalations: int = Field(
        3,
        ge=0,
        description="Maximum number of recovery escalations before session-level failure"
    )
    audit_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional audit metadata for error logging and debugging"
    )


# =============================================================================
# WAIT DEFAULTS MODEL
# =============================================================================

class WaitDefaults(BaseModel):
    """
    Global wait configuration defaults for a workflow.

    Provides tiered timeout/poll/retry settings that can be overridden
    at the step or action level. Uses sensible defaults for typical automation.
    """
    timeout_ms: int = Field(
        10000,
        ge=1,
        description="Default timeout for wait operations in milliseconds (default: 10s)"
    )
    poll_interval_ms: int = Field(
        50,
        ge=1,
        description="Default polling interval for image checks in milliseconds (default: 50ms)"
    )
    retry_interval_ms: int = Field(
        1000,
        ge=0,
        description="Default interval between retry attempts in milliseconds (default: 1s)"
    )


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
    retry_interval_ms: Optional[int] = Field(
        None,
        ge=0,
        description="Override retry interval in milliseconds (uses workflow default if not set)"
    )
    # Condition configuration for branching
    condition: Optional[dict] = Field(
        None,
        description="Condition configuration for conditional branching"
    )
    # Recovery configuration
    recovery: RecoveryConfig = Field(
        default_factory=RecoveryConfig,
        description="Recovery and audit configuration for error handling"
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
    wait_defaults: WaitDefaults = Field(
        default_factory=WaitDefaults,
        description="Global wait configuration defaults with per-step override support"
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
        step_index: dict,
        wait_defaults: Optional[WaitDefaults] = None
    ):
        self.name = name
        self.start_step_id = start_step_id
        self.steps = steps
        self.step_index = step_index
        self.wait_defaults = wait_defaults or WaitDefaults()

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a step by its ID."""
        return self.step_index.get(step_id)

    def __repr__(self) -> str:
        return f"CompiledWorkflow(name='{self.name}', steps={len(self.steps)})"
