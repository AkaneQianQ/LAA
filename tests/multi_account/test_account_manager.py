"""
Account Manager Tests

Tests for AccountManager class with per-account database isolation.
Verifies account lifecycle, context management, and callback functionality.
"""

import pytest
import numpy as np
import os
import sqlite3
from unittest.mock import Mock, MagicMock


# =============================================================================
# ACCOUNT MANAGER TESTS
# =============================================================================

class TestAccountManager:
    """Tests for AccountManager class."""

    def test_create_account_generates_consistent_hash(self, tmp_path):
        """Test that create_account generates consistent hash for same screenshot."""
        from core.account_manager import AccountManager

        # Create a mock detector that returns consistent hash
        mock_detector = Mock()
        mock_detector.discover_account.return_value = {
            'account_id': 1,
            'account_hash': 'abc123def456',
            'character_count': 6,
        }

        data_dir = str(tmp_path / "data")
        manager = AccountManager(base_data_dir=data_dir, detector=mock_detector)

        # Create sample screenshot
        screenshot = np.zeros((1440, 2560, 3), dtype=np.uint8)

        # Discover/create account
        context1 = manager.discover_and_create(screenshot)

        # Same screenshot should produce same hash (via detector)
        context2 = manager.discover_and_create(screenshot)

        assert context1.account_hash == context2.account_hash
        assert context1.account_hash == 'abc123def456'

    def test_switch_account_loads_correct_database(self, tmp_path):
        """Test that switch_account loads correct database."""
        from core.account_manager import AccountManager

        mock_detector = Mock()
        mock_detector.discover_account.return_value = {
            'account_id': 1,
            'account_hash': 'account_a',
            'character_count': 6,
        }

        data_dir = str(tmp_path / "data")
        manager = AccountManager(base_data_dir=data_dir, detector=mock_detector)

        screenshot = np.zeros((1440, 2560, 3), dtype=np.uint8)

        # Create first account
        context1 = manager.discover_and_create(screenshot)

        # Mark progress in first account
        context1.progress_tracker.mark_done(0, "Char1")

        # Switch to same account (should load same database)
        context2 = manager.switch_account('account_a')

        # Progress should persist
        assert context2.progress_tracker.is_done(0) is True

    def test_per_account_databases_are_isolated(self, tmp_path):
        """Test that per-account databases are isolated (no data leak)."""
        from core.account_manager import AccountManager

        data_dir = str(tmp_path / "data")
        manager = AccountManager(base_data_dir=data_dir)

        # Manually create two account contexts
        os.makedirs(os.path.join(data_dir, "accounts", "account_a"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "accounts", "account_b"), exist_ok=True)

        # Create contexts for both accounts
        from core.account_manager import AccountContext
        from core.progress_tracker import ProgressTracker

        db_path_a = os.path.join(data_dir, "accounts", "account_a", "progress.db")
        db_path_b = os.path.join(data_dir, "accounts", "account_b", "progress.db")

        tracker_a = ProgressTracker(db_path_a)
        tracker_b = ProgressTracker(db_path_b)

        # Mark progress in account A
        tracker_a.mark_done(0, "CharA")

        # Account B should not see account A's progress
        assert tracker_b.is_done(0) is False
        assert tracker_a.is_done(0) is True

    def test_account_context_contains_required_fields(self, tmp_path):
        """Test that AccountContext contains all required fields."""
        from core.account_manager import AccountManager, AccountContext

        mock_detector = Mock()
        mock_detector.discover_account.return_value = {
            'account_hash': 'test_hash_123',
            'character_count': 9,
        }

        data_dir = str(tmp_path / "data")
        manager = AccountManager(base_data_dir=data_dir, detector=mock_detector)

        screenshot = np.zeros((1440, 2560, 3), dtype=np.uint8)
        context = manager.discover_and_create(screenshot)

        # Verify all required fields
        assert isinstance(context.account_hash, str)
        assert isinstance(context.account_id, int)
        assert isinstance(context.character_count, int)
        assert isinstance(context.db_path, str)
        assert context.progress_tracker is not None

        assert context.account_hash == 'test_hash_123'
        assert context.account_id > 0  # Database-assigned ID
        assert context.character_count == 9

    def test_callbacks_fire_on_account_switch(self, tmp_path):
        """Test that callbacks fire on account switch."""
        from core.account_manager import AccountManager

        mock_detector = Mock()
        mock_detector.discover_account.return_value = {
            'account_id': 1,
            'account_hash': 'test_account',
            'character_count': 6,
        }

        data_dir = str(tmp_path / "data")
        manager = AccountManager(base_data_dir=data_dir, detector=mock_detector)

        # Register mock callback
        callback_mock = Mock()
        manager.on_switch(callback_mock)

        screenshot = np.zeros((1440, 2560, 3), dtype=np.uint8)

        # Discover account (should trigger callback)
        context = manager.discover_and_create(screenshot)

        # Callback should have been called
        callback_mock.assert_called_once()
        assert callback_mock.call_args[0][0] == context

    def test_get_or_create_context_returns_existing(self, tmp_path):
        """Test that get_or_create_context returns existing account if found."""
        from core.account_manager import AccountManager

        mock_detector = Mock()
        mock_detector.discover_account.return_value = {
            'account_id': 1,
            'account_hash': 'existing_account',
            'character_count': 6,
        }

        data_dir = str(tmp_path / "data")
        manager = AccountManager(base_data_dir=data_dir, detector=mock_detector)

        screenshot = np.zeros((1440, 2560, 3), dtype=np.uint8)

        # First call creates
        context1 = manager.get_or_create_context(screenshot)

        # Second call should get existing (same hash)
        context2 = manager.get_or_create_context(screenshot)

        # Both should have same hash
        assert context1.account_hash == context2.account_hash

    def test_list_accounts_returns_all_accounts(self, tmp_path):
        """Test that list_accounts returns all known accounts."""
        from core.account_manager import AccountManager
        from core.database import init_database, create_account

        data_dir = str(tmp_path / "data")
        manager = AccountManager(base_data_dir=data_dir)

        # Initialize main database and add accounts
        main_db = os.path.join(data_dir, "accounts.db")
        init_database(main_db)
        create_account(main_db, "acc1")
        create_account(main_db, "acc2")

        # Create account directories manually
        os.makedirs(os.path.join(data_dir, "accounts", "acc1"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "accounts", "acc2"), exist_ok=True)

        # Create progress databases
        from core.progress_tracker import ProgressTracker
        tracker1 = ProgressTracker(os.path.join(data_dir, "accounts", "acc1", "progress.db"))
        tracker2 = ProgressTracker(os.path.join(data_dir, "accounts", "acc2", "progress.db"))

        # Add some progress
        tracker1.mark_done(0, "Char1")
        tracker2.mark_done(0, "Char2")
        tracker2.mark_done(1, "Char3")

        accounts = manager.list_accounts()

        assert len(accounts) == 2
        hashes = {acc['account_hash'] for acc in accounts}
        assert 'acc1' in hashes
        assert 'acc2' in hashes

    def test_context_immutability(self, tmp_path):
        """Test that AccountContext is immutable (frozen dataclass)."""
        from core.account_manager import AccountContext
        from core.progress_tracker import ProgressTracker
        from dataclasses import FrozenInstanceError

        tracker = ProgressTracker(str(tmp_path / "test.db"))

        context = AccountContext(
            account_hash='test_hash',
            account_id=1,
            character_count=6,
            db_path=str(tmp_path / "test.db"),
            progress_tracker=tracker,
        )

        # Attempting to modify should raise error
        with pytest.raises(FrozenInstanceError):
            context.account_id = 2

    def test_error_handling_for_invalid_account(self, tmp_path):
        """Test error handling for invalid account hash."""
        from core.account_manager import AccountManager, AccountManagerError

        data_dir = str(tmp_path / "data")
        manager = AccountManager(base_data_dir=data_dir)

        # Switching to non-existent account should raise error
        with pytest.raises(AccountManagerError):
            manager.switch_account('nonexistent_account')

    def test_multiple_callbacks_all_fire(self, tmp_path):
        """Test that multiple callbacks all fire on account switch."""
        from core.account_manager import AccountManager

        mock_detector = Mock()
        mock_detector.discover_account.return_value = {
            'account_id': 1,
            'account_hash': 'test_account',
            'character_count': 6,
        }

        data_dir = str(tmp_path / "data")
        manager = AccountManager(base_data_dir=data_dir, detector=mock_detector)

        # Register multiple callbacks
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()

        manager.on_switch(callback1)
        manager.on_switch(callback2)
        manager.on_switch(callback3)

        screenshot = np.zeros((1440, 2560, 3), dtype=np.uint8)
        manager.discover_and_create(screenshot)

        # All callbacks should have been called
        callback1.assert_called_once()
        callback2.assert_called_once()
        callback3.assert_called_once()

    def test_database_path_management(self, tmp_path):
        """Test that database paths are correctly managed."""
        from core.account_manager import AccountManager

        mock_detector = Mock()
        mock_detector.discover_account.return_value = {
            'account_id': 1,
            'account_hash': 'path_test_account',
            'character_count': 6,
        }

        data_dir = str(tmp_path / "data")
        manager = AccountManager(base_data_dir=data_dir, detector=mock_detector)

        screenshot = np.zeros((1440, 2560, 3), dtype=np.uint8)
        context = manager.discover_and_create(screenshot)

        # Path should be in correct location
        expected_path = os.path.join(data_dir, "accounts", "path_test_account", "progress.db")
        assert context.db_path == expected_path
        assert os.path.exists(os.path.dirname(context.db_path))

    def test_thread_safety_context_switching(self, tmp_path):
        """Test thread safety of context switching."""
        import threading
        from core.account_manager import AccountManager

        mock_detector = Mock()
        mock_detector.discover_account.return_value = {
            'account_id': 1,
            'account_hash': 'thread_test',
            'character_count': 6,
        }

        data_dir = str(tmp_path / "data")
        manager = AccountManager(base_data_dir=data_dir, detector=mock_detector)

        screenshot = np.zeros((1440, 2560, 3), dtype=np.uint8)

        results = []

        def discover():
            ctx = manager.discover_and_create(screenshot)
            results.append(ctx.account_hash)

        # Run multiple threads
        threads = [threading.Thread(target=discover) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should have same hash (consistent)
        assert all(r == 'thread_test' for r in results)
