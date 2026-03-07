"""
Account Switcher Module

Provides safe runtime account switching without application restart.
Integrates with WorkflowExecutor for lifecycle management and ensures
the workflow is stopped before switching accounts.

Exports:
    AccountSwitcher: Manages safe account switching during runtime
"""

import threading
from typing import Optional, Callable, List, TYPE_CHECKING

import numpy as np

from core.account_manager import AccountManager, AccountContext

if TYPE_CHECKING:
    from core.workflow_executor import WorkflowExecutor


class AccountSwitcher:
    """
    Manages safe account switching during runtime.

    This class provides thread-safe account switching with workflow lifecycle
    management. It ensures workflows are stopped before switching and provides
    callbacks for switch events.

    Safety mechanisms:
    - Lock prevents concurrent switch attempts
    - Workflow must be stopped before switch
    - Immutable context prevents mid-switch corruption
    - Clear error messages for switch failures

    Usage:
        switcher = AccountSwitcher(account_manager)
        switcher.attach_workflow(executor)

        # Check if switch is allowed
        if switcher.can_switch():
            switcher.switch_to_account("account_hash", screenshot)

        # Or auto-detect from screenshot
        new_context = switcher.switch_to_detected(screenshot)
    """

    def __init__(self, account_manager: AccountManager):
        """
        Initialize the account switcher.

        Args:
            account_manager: AccountManager instance for account operations
        """
        self.account_manager = account_manager
        self._workflow_executor: Optional['WorkflowExecutor'] = None
        self._is_running: bool = False
        self._lock = threading.Lock()
        self._on_switch_callbacks: List[Callable[[AccountContext, AccountContext], None]] = []

    def attach_workflow(self, executor: 'WorkflowExecutor') -> None:
        """
        Register workflow executor for lifecycle management.

        This allows the switcher to check running state and stop
        the workflow safely before account switching.

        Args:
            executor: WorkflowExecutor instance to manage
        """
        self._workflow_executor = executor

    def can_switch(self) -> bool:
        """
        Check if account switch is currently allowed.

        Returns True only if no workflow is currently running.
        This is a thread-safe check.

        Returns:
            True if switch is allowed, False if workflow is running
        """
        with self._lock:
            # Check if we have an attached workflow
            if self._workflow_executor is None:
                return True  # No workflow, can always switch

            # Check if workflow is running
            # WorkflowExecutor doesn't have is_running(), so we track it ourselves
            return not self._is_running

    def _stop_workflow(self, timeout: float = 5.0) -> bool:
        """
        Stop the current workflow gracefully.

        Args:
            timeout: Maximum time to wait for stop (seconds)

        Returns:
            True if stopped successfully, False if timeout
        """
        if self._workflow_executor is None:
            return True

        # Signal stop via stop_event if available
        # The executor should have a stop_event passed during creation
        import threading
        stop_event = getattr(self._workflow_executor, '_stop_event', None)

        if stop_event is not None and isinstance(stop_event, threading.Event):
            stop_event.set()
            # Wait for stop with timeout
            return stop_event.wait(timeout)

        return True

    def switch_to_account(self, account_hash: str, screenshot: np.ndarray) -> bool:
        """
        Switch to a specific account by hash.

        This method will:
        1. Check if switch is allowed (no running workflow)
        2. Stop current workflow if running
        3. Use AccountManager to switch context
        4. Fire switch callbacks

        Args:
            account_hash: The account hash to switch to
            screenshot: Screenshot for verification/context

        Returns:
            True on success, False if switch not allowed

        Raises:
            RuntimeError: If workflow cannot be stopped
        """
        with self._lock:
            # Check if we can switch
            if not self.can_switch():
                # Try to stop the workflow
                if not self._stop_workflow():
                    raise RuntimeError("Could not stop running workflow for account switch")
                self._is_running = False

            # Get old context for callbacks
            old_context = self.account_manager.current_context

            # Perform the switch
            try:
                new_context = self.account_manager.switch_account(account_hash)
            except ValueError as e:
                raise RuntimeError(f"Account switch failed: {e}")

            # Fire callbacks outside lock to prevent deadlocks
            callbacks = self._on_switch_callbacks.copy()

        # Fire callbacks (outside lock)
        if old_context is not None:
            for callback in callbacks:
                try:
                    callback(old_context, new_context)
                except Exception:
                    # Callback errors shouldn't break switching
                    pass

        return True

    def switch_to_detected(self, screenshot: np.ndarray) -> Optional[AccountContext]:
        """
        Auto-detect account from screenshot and switch to it.

        Args:
            screenshot: Screenshot of current screen

        Returns:
            New AccountContext or None if detection/switch failed
        """
        with self._lock:
            # Check if we can switch
            if not self.can_switch():
                if not self._stop_workflow():
                    return None
                self._is_running = False

            # Get old context for callbacks
            old_context = self.account_manager.current_context

            # Use AccountManager to detect and create context
            try:
                new_context = self.account_manager.get_or_create_context(screenshot)
            except Exception:
                return None

            # Fire callbacks outside lock
            callbacks = self._on_switch_callbacks.copy()

        # Fire callbacks (outside lock)
        if old_context is not None:
            for callback in callbacks:
                try:
                    callback(old_context, new_context)
                except Exception:
                    pass

        return new_context

    def on_switch(self, callback: Callable[[AccountContext, AccountContext], None]) -> None:
        """
        Register a callback for account switch events.

        The callback receives (old_context, new_context) and is fired
        after a successful switch.

        Args:
            callback: Function(old_context, new_context) to call on switch
        """
        self._on_switch_callbacks.append(callback)

    def set_running_state(self, is_running: bool) -> None:
        """
        Set the running state of the workflow.

        This should be called by the workflow launcher to indicate
        whether a workflow is currently executing.

        Args:
            is_running: True if workflow is running, False otherwise
        """
        with self._lock:
            self._is_running = is_running

    @property
    def is_running(self) -> bool:
        """Check if a workflow is currently running."""
        with self._lock:
            return self._is_running
