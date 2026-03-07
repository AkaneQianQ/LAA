"""
Account Manager Module

Provides account lifecycle management with per-account database isolation.
Supports automatic account discovery, context switching, and progress tracking.

Exports:
    AccountManager: Manages account lifecycle and context switching
    AccountContext: Immutable runtime context for a specific account
"""

import os
import threading
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, TYPE_CHECKING
from pathlib import Path

import numpy as np

from core.progress_tracker import ProgressTracker

if TYPE_CHECKING:
    from modules.character_detector import CharacterDetector


# =============================================================================
# ACCOUNT CONTEXT
# =============================================================================

@dataclass(frozen=True)
class AccountContext:
    """
    Immutable runtime context for a specific account.

    This context is created when an account is discovered or switched to,
    and remains unchanged throughout the account's active session.

    Attributes:
        account_hash: Unique SHA-256 hash identifying the account
        account_id: Database ID for the account
        character_count: Number of characters in this account
        db_path: Path to the per-account progress database
        progress_tracker: ProgressTracker instance for this account
    """
    account_hash: str
    account_id: int
    character_count: int
    db_path: str
    progress_tracker: ProgressTracker = field(compare=False)

    def __repr__(self) -> str:
        return f"AccountContext(hash={self.account_hash[:8]}..., chars={self.character_count})"


# =============================================================================
# ACCOUNT MANAGER
# =============================================================================

class AccountManager:
    """
    Manages account lifecycle, discovery, and context switching.

    Provides automatic account identification using CharacterDetector,
    per-account database isolation, and callback-based switch notifications.

    Usage:
        manager = AccountManager(base_data_dir="data")
        context = manager.get_or_create_context(screenshot)
        # ... use context.progress_tracker ...
        manager.switch_account("different_hash")
    """

    def __init__(
        self,
        base_data_dir: str = "data",
        detector: Optional['CharacterDetector'] = None
    ):
        """
        Initialize the account manager.

        Args:
            base_data_dir: Base directory for all account data
            detector: Optional CharacterDetector for account discovery
        """
        self.base_data_dir = Path(base_data_dir)
        self.detector = detector
        self._current_context: Optional[AccountContext] = None
        self._on_switch_callbacks: List[Callable[[AccountContext], None]] = []
        self._lock = threading.Lock()

        # Ensure base directories exist
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create base directory structure if not exists."""
        self.base_data_dir.mkdir(parents=True, exist_ok=True)
        (self.base_data_dir / "accounts").mkdir(exist_ok=True)

    def _get_account_db_path(self, account_hash: str) -> str:
        """Get the database path for a specific account."""
        account_dir = self.base_data_dir / "accounts" / account_hash
        account_dir.mkdir(parents=True, exist_ok=True)
        return str(account_dir / "progress.db")

    def _get_main_db_path(self) -> str:
        """Get the main accounts database path."""
        return str(self.base_data_dir / "accounts.db")

    def _discover_account(self, screenshot: np.ndarray) -> Dict[str, Any]:
        """
        Discover account from screenshot using detector.

        Args:
            screenshot: Screenshot of character selection screen

        Returns:
            Dictionary with account_hash, character_count, etc.
        """
        if self.detector is None:
            raise RuntimeError("No CharacterDetector provided for account discovery")

        # Use detector to discover account
        result = self.detector.discover_account(screenshot)
        return {
            'account_hash': result.account_hash,
            'character_count': result.character_count,
        }

    def _create_context(
        self,
        account_hash: str,
        account_id: int,
        character_count: int
    ) -> AccountContext:
        """
        Create a new AccountContext.

        Args:
            account_hash: Unique account hash
            account_id: Database account ID
            character_count: Number of characters

        Returns:
            New AccountContext instance
        """
        db_path = self._get_account_db_path(account_hash)
        progress_tracker = ProgressTracker(db_path)

        return AccountContext(
            account_hash=account_hash,
            account_id=account_id,
            character_count=character_count,
            db_path=db_path,
            progress_tracker=progress_tracker
        )

    def get_or_create_context(self, screenshot: np.ndarray) -> AccountContext:
        """
        Get existing account context or create new one from screenshot.

        This is the main entry point for launcher integration. It will:
        1. Detect the account from the screenshot
        2. Look up or create the account in the database
        3. Return an AccountContext with progress tracker

        Args:
            screenshot: Screenshot of character selection screen

        Returns:
            AccountContext for the detected account
        """
        # Discover account from screenshot
        discovery = self._discover_account(screenshot)
        account_hash = discovery['account_hash']
        character_count = discovery['character_count']

        # Get or create account in main database
        from core.database import get_or_create_account
        main_db = self._get_main_db_path()
        account_id = get_or_create_account(main_db, account_hash)

        # Create context
        with self._lock:
            self._current_context = self._create_context(
                account_hash=account_hash,
                account_id=account_id,
                character_count=character_count
            )
            return self._current_context

    def switch_account(self, account_hash: str) -> AccountContext:
        """
        Switch to an existing account by hash.

        Args:
            account_hash: The account hash to switch to

        Returns:
            AccountContext for the switched account

        Raises:
            ValueError: If account not found in database
        """
        from core.database import find_account_by_hash

        main_db = self._get_main_db_path()
        account = find_account_by_hash(main_db, account_hash)

        if account is None:
            raise ValueError(f"Account with hash '{account_hash}' not found")

        # Get character count from detector or default
        character_count = 9  # Default, could be stored in DB

        with self._lock:
            old_context = self._current_context

            # Create new context
            new_context = self._create_context(
                account_hash=account_hash,
                account_id=account['id'],
                character_count=character_count
            )

            self._current_context = new_context

            # Fire callbacks (outside lock to prevent deadlocks)
            if old_context is not None:
                for callback in self._on_switch_callbacks:
                    try:
                        callback(new_context)
                    except Exception:
                        # Callback errors shouldn't break switching
                        pass

            return new_context

    def list_accounts(self) -> List[Dict[str, Any]]:
        """
        List all known accounts.

        Returns:
            List of account dictionaries with id, account_hash, created_at
        """
        from core.database import list_all_accounts
        main_db = self._get_main_db_path()
        return list_all_accounts(main_db)

    def on_switch(self, callback: Callable[[AccountContext], None]) -> None:
        """
        Register a callback for account switch events.

        The callback will be called with the new AccountContext after
        a successful account switch.

        Args:
            callback: Function to call on account switch
        """
        self._on_switch_callbacks.append(callback)

    @property
    def current_context(self) -> Optional[AccountContext]:
        """Get the current active account context."""
        with self._lock:
            return self._current_context

    def get_account_by_hash(self, account_hash: str) -> Optional[Dict[str, Any]]:
        """
        Look up an account by its hash.

        Args:
            account_hash: The account hash to look up

        Returns:
            Account dictionary or None if not found
        """
        from core.database import find_account_by_hash
        main_db = self._get_main_db_path()
        return find_account_by_hash(main_db, account_hash)
