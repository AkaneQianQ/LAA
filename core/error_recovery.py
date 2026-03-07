"""
Error Recovery Module

Provides error taxonomy, classification, and escalation state machine for
workflow execution recovery. Implements deterministic recovery behavior
from network lag, UI timeout, and disconnect scenarios.

Exports:
    ErrorKind: Enum of error classification types
    ErrorContext: Dataclass for error context information
    RecoveryAction: Enum of recovery actions
    RecoveryOrchestrator: State machine for recovery escalation
    classify_error: Function to classify exceptions into ErrorKind
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Set


class ErrorKind(str, Enum):
    """
    Error classification types for recovery routing.

    Each kind maps to a specific recovery strategy and escalation behavior.
    """
    NETWORK_LAG = "network_lag"
    UI_TIMEOUT = "ui_timeout"
    DISCONNECT = "disconnect"
    INPUT_POLICY_VIOLATION = "input_policy_violation"
    UNKNOWN = "unknown"


class RecoveryAction(str, Enum):
    """
    Recovery actions determined by escalation state machine.

    L1_RETRY: Step-level retry (existing retry semantics)
    L2_ROLLBACK: Rollback to anchor step
    L3_SKIP: Skip current role and continue with next
    """
    L1_RETRY = "l1_retry"
    L2_ROLLBACK = "l2_rollback"
    L3_SKIP = "l3_skip"


@dataclass
class ErrorContext:
    """
    Context information for error classification and logging.

    Captures all relevant metadata for debugging and recovery decisions.
    """
    phase: str
    step_id: str
    action_type: str
    attempt: int
    account_id: Optional[str] = None
    screenshot_path: Optional[str] = None
    detail: Dict[str, Any] = field(default_factory=dict)


def classify_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorKind:
    """
    Classify an exception into an ErrorKind for recovery routing.

    Uses error message patterns and context to determine the error type.

    Args:
        error: The exception that occurred
        context: Optional context dictionary with additional metadata

    Returns:
        ErrorKind classification for the error
    """
    context = context or {}
    error_msg = str(error).lower()

    # Check for explicit disconnect markers first
    if context.get("disconnect_detected"):
        return ErrorKind.DISCONNECT

    # Check for network lag patterns
    # Network lag typically shows as extended timeouts
    elapsed_ms = context.get("elapsed_ms", 0)
    if elapsed_ms >= 30000 or "network" in error_msg:
        return ErrorKind.NETWORK_LAG

    # Check for UI timeout patterns
    if "wait_image timeout" in error_msg or "timeout" in error_msg:
        return ErrorKind.UI_TIMEOUT

    # Check for input policy violations
    if "input_policy_violation" in error_msg or "policy" in error_msg:
        return ErrorKind.INPUT_POLICY_VIOLATION

    # Default to unknown
    return ErrorKind.UNKNOWN


class RecoveryOrchestrator:
    """
    State machine for recovery escalation decisions.

    Implements a three-tier escalation policy:
    - L1: Step-level retry (existing retry semantics)
    - L2: Rollback to anchor step after threshold
    - L3: Skip current role after max escalations

    Also implements circuit breaker pattern for same-kind failures.
    """

    def __init__(
        self,
        l1_retry_threshold: int = 3,
        l2_rollback_threshold: int = 3,
        l3_skip_threshold: int = 3
    ):
        """
        Initialize the recovery orchestrator.

        Args:
            l1_retry_threshold: Max retries before L2 escalation
            l2_rollback_threshold: Max rollbacks before L3 escalation
            l3_skip_threshold: Max escalations before role skip
        """
        self.l1_retry_threshold = l1_retry_threshold
        self.l2_rollback_threshold = l2_rollback_threshold
        self.l3_skip_threshold = l3_skip_threshold

        # State tracking
        self._escalation_count = 0
        self._error_kind_counts: Dict[str, int] = {}
        self._circuit_threshold = 3  # Circuit opens after 3 same-kind failures

    def determine_action(
        self,
        error_kind: str,
        step_id: str,
        attempt: int
    ) -> RecoveryAction:
        """
        Determine the recovery action based on current state.

        Args:
            error_kind: The classified error kind
            step_id: Current step ID
            attempt: Current attempt number

        Returns:
            RecoveryAction to take
        """
        # Track error kind for circuit breaker
        self._error_kind_counts[error_kind] = self._error_kind_counts.get(error_kind, 0) + 1

        # Check if we should escalate to L3 (skip role)
        if self._escalation_count >= self.l3_skip_threshold:
            return RecoveryAction.L3_SKIP

        # Check if we should escalate to L2 (rollback)
        if attempt >= self.l2_rollback_threshold:
            self._escalation_count += 1
            return RecoveryAction.L2_ROLLBACK

        # Default to L1 (retry)
        return RecoveryAction.L1_RETRY

    def is_circuit_open(self, error_kind: str) -> bool:
        """
        Check if circuit breaker is open for an error kind.

        Circuit opens when same-kind failures exceed threshold.

        Args:
            error_kind: The error kind to check

        Returns:
            True if circuit is open (should skip role)
        """
        return self._error_kind_counts.get(error_kind, 0) >= self._circuit_threshold

    def get_escalation_count(self) -> int:
        """
        Get current escalation count.

        Returns:
            Number of times recovery has escalated
        """
        return self._escalation_count

    def record_success(self, step_id: str) -> None:
        """
        Record successful step execution.

        Resets escalation state on success.

        Args:
            step_id: The step that succeeded
        """
        self._escalation_count = 0
        self._error_kind_counts.clear()

    def reset(self) -> None:
        """Reset all state (for testing or new role)."""
        self._escalation_count = 0
        self._error_kind_counts.clear()
