"""
Database Isolation Tests

Tests to verify that per-account databases are properly isolated.
Ensures no data leakage between accounts.
"""

import pytest
import os
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor


class TestDatabaseIsolation:
    """Tests for per-account database isolation."""

    def test_account_a_progress_not_visible_to_account_b(self, tmp_path):
        """Test that Account A progress is not visible to Account B."""
        from core.progress_tracker import ProgressTracker

        # Create two separate progress trackers (simulating two accounts)
        db_path_a = str(tmp_path / "account_a" / "progress.db")
        db_path_b = str(tmp_path / "account_b" / "progress.db")

        tracker_a = ProgressTracker(db_path_a)
        tracker_b = ProgressTracker(db_path_b)

        # Mark progress in account A
        tracker_a.mark_done(0, "CharA")
        tracker_a.mark_done(1, "CharA2")

        # Account B should not see any progress
        assert tracker_b.is_done(0) is False
        assert tracker_b.is_done(1) is False
        assert tracker_b.get_summary()['total_tracked'] == 0

        # Account A should see its progress
        assert tracker_a.is_done(0) is True
        assert tracker_a.is_done(1) is True
        assert tracker_a.get_summary()['total_tracked'] == 2

    def test_separate_database_files_created_per_account(self, tmp_path):
        """Test that separate database files are created per account."""
        from core.progress_tracker import ProgressTracker

        db_path_a = str(tmp_path / "account_a" / "progress.db")
        db_path_b = str(tmp_path / "account_b" / "progress.db")

        tracker_a = ProgressTracker(db_path_a)
        tracker_b = ProgressTracker(db_path_b)

        # Mark progress to ensure databases are created
        tracker_a.mark_done(0, "CharA")
        tracker_b.mark_done(0, "CharB")

        # Verify both database files exist
        assert os.path.exists(db_path_a), f"Database A should exist at {db_path_a}"
        assert os.path.exists(db_path_b), f"Database B should exist at {db_path_b}"

        # Verify they are different files
        assert db_path_a != db_path_b

    def test_deleting_one_account_doesnt_affect_others(self, tmp_path):
        """Test that deleting one account doesn't affect others."""
        from core.progress_tracker import ProgressTracker

        db_path_a = str(tmp_path / "account_a" / "progress.db")
        db_path_b = str(tmp_path / "account_b" / "progress.db")

        tracker_a = ProgressTracker(db_path_a)
        tracker_b = ProgressTracker(db_path_b)

        # Mark progress in both accounts
        tracker_a.mark_done(0, "CharA")
        tracker_b.mark_done(0, "CharB")

        # Delete account A's database
        os.remove(db_path_a)

        # Account B should still have its progress
        assert tracker_b.is_done(0) is True
        assert os.path.exists(db_path_b) is True

    def test_concurrent_access_to_different_accounts_safe(self, tmp_path):
        """Test that concurrent access to different accounts is safe."""
        from core.progress_tracker import ProgressTracker

        db_path_a = str(tmp_path / "account_a" / "progress.db")
        db_path_b = str(tmp_path / "account_b" / "progress.db")

        tracker_a = ProgressTracker(db_path_a)
        tracker_b = ProgressTracker(db_path_b)

        results = {'a': 0, 'b': 0}

        def update_account_a():
            for i in range(10):
                tracker_a.mark_done(i % 3, f"CharA{i}")
                results['a'] += 1
                time.sleep(0.01)

        def update_account_b():
            for i in range(10):
                tracker_b.mark_done(i % 3, f"CharB{i}")
                results['b'] += 1
                time.sleep(0.01)

        # Run both updates concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(update_account_a)
            future_b = executor.submit(update_account_b)
            future_a.result()
            future_b.result()

        # Verify both accounts have their own data
        assert results['a'] == 10
        assert results['b'] == 10

        # Verify isolation - each should only see their own 3 slots
        summary_a = tracker_a.get_summary()
        summary_b = tracker_b.get_summary()

        assert summary_a['total_tracked'] == 3
        assert summary_b['total_tracked'] == 3

    def test_database_isolation_with_account_manager(self, tmp_path):
        """Test database isolation using AccountManager."""
        from core.account_manager import AccountManager
        from core.database import init_database, create_account

        data_dir = str(tmp_path / "data")
        manager = AccountManager(base_data_dir=data_dir)

        # Initialize main database and create two accounts
        main_db = os.path.join(data_dir, "accounts.db")
        init_database(main_db)
        create_account(main_db, "account_a")
        create_account(main_db, "account_b")

        # Create directories and progress databases
        os.makedirs(os.path.join(data_dir, "accounts", "account_a"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "accounts", "account_b"), exist_ok=True)

        # Switch to account A and mark progress
        context_a = manager.switch_account("account_a")
        context_a.progress_tracker.mark_done(0, "CharA")
        context_a.progress_tracker.mark_done(1, "CharA2")

        # Switch to account B
        context_b = manager.switch_account("account_b")

        # Account B should not see account A's progress
        assert context_b.progress_tracker.is_done(0) is False
        assert context_b.progress_tracker.is_done(1) is False

        # Mark progress in account B
        context_b.progress_tracker.mark_done(0, "CharB")

        # Switch back to account A
        context_a2 = manager.switch_account("account_a")

        # Account A should still have its original progress
        assert context_a2.progress_tracker.is_done(0) is True
        assert context_a2.progress_tracker.is_done(1) is True
        # But not account B's progress
        assert context_a2.progress_tracker.is_done(2) is False

    def test_database_paths_are_unique_per_account(self, tmp_path):
        """Test that database paths are unique per account hash."""
        from core.account_manager import AccountManager

        data_dir = str(tmp_path / "data")
        manager = AccountManager(base_data_dir=data_dir)

        # Get database paths for different accounts
        path_a = manager._get_account_db_path("hash_a")
        path_b = manager._get_account_db_path("hash_b")
        path_c = manager._get_account_db_path("hash_a")  # Same as A

        # Different accounts should have different paths
        assert path_a != path_b

        # Same hash should return same path
        assert path_a == path_c

        # Paths should contain account hash
        assert "hash_a" in path_a
        assert "hash_b" in path_b

    def test_isolation_persists_across_sessions(self, tmp_path):
        """Test that isolation persists across tracker sessions."""
        from core.progress_tracker import ProgressTracker

        db_path_a = str(tmp_path / "account_a" / "progress.db")
        db_path_b = str(tmp_path / "account_b" / "progress.db")

        # Session 1: Create trackers and mark progress
        tracker_a1 = ProgressTracker(db_path_a)
        tracker_b1 = ProgressTracker(db_path_b)

        tracker_a1.mark_done(0, "CharA")
        tracker_b1.mark_done(0, "CharB")

        # Session 2: Create new tracker instances
        tracker_a2 = ProgressTracker(db_path_a)
        tracker_b2 = ProgressTracker(db_path_b)

        # Verify isolation persists - each tracker sees its own data
        assert tracker_a2.is_done(0) is True  # Account A has slot 0 done
        assert tracker_b2.is_done(0) is True  # Account B has slot 0 done

        # Verify they are tracking different databases by checking paths
        assert tracker_a2.db_path != tracker_b2.db_path

        # Verify they don't see each other's data
        summary_a = tracker_a2.get_summary()
        summary_b = tracker_b2.get_summary()

        assert summary_a['total_tracked'] == 1
        assert summary_b['total_tracked'] == 1

    def test_no_cross_contamination_in_summary_stats(self, tmp_path):
        """Test that summary stats don't cross-contaminate between accounts."""
        from core.progress_tracker import ProgressTracker

        db_path_a = str(tmp_path / "account_a" / "progress.db")
        db_path_b = str(tmp_path / "account_b" / "progress.db")

        tracker_a = ProgressTracker(db_path_a)
        tracker_b = ProgressTracker(db_path_b)

        # Add different amounts of progress to each account
        for i in range(5):
            tracker_a.mark_done(i, f"CharA{i}")

        for i in range(3):
            tracker_b.mark_done(i, f"CharB{i}")

        # Get summaries
        summary_a = tracker_a.get_summary()
        summary_b = tracker_b.get_summary()

        # Verify counts are isolated
        assert summary_a['total_tracked'] == 5
        assert summary_b['total_tracked'] == 3
        assert summary_a['completed_today'] == 5
        assert summary_b['completed_today'] == 3

        # Verify donation counts are isolated
        assert summary_a['total_donations'] == 5
        assert summary_b['total_donations'] == 3
