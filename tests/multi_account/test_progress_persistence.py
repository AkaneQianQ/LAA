"""
Progress Persistence Tests

Tests for progress tracking schema and ProgressTracker class.
Verifies daily donation completion tracking with proper date handling.
"""

import pytest
import sqlite3
import os
from datetime import datetime, timedelta
from unittest.mock import patch


# =============================================================================
# DATABASE SCHEMA TESTS (Task 1)
# =============================================================================

class TestProgressSchema:
    """Tests for progress tracking database schema."""

    def test_character_progress_table_created(self, tmp_path):
        """Test that character_progress table is created with correct schema."""
        from core.database import init_progress_schema

        db_path = str(tmp_path / "test_progress.db")
        conn = sqlite3.connect(db_path)

        try:
            init_progress_schema(conn)

            # Verify table exists
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='character_progress'"
            )
            assert cursor.fetchone() is not None, "character_progress table should exist"

            # Verify schema
            cursor.execute("PRAGMA table_info(character_progress)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

            assert columns['id'] == 'INTEGER'
            assert columns['slot_index'] == 'INTEGER'
            assert columns['character_name'] == 'TEXT'
            assert columns['last_donation_date'] == 'TEXT'
            assert columns['donation_count'] == 'INTEGER'
            assert columns['updated_at'] == 'TIMESTAMP'
        finally:
            conn.close()

    def test_upsert_progress_marks_character_done(self, tmp_path):
        """Test that upsert progress marks character as done for today."""
        from core.database import init_progress_schema, mark_character_done, get_character_progress

        db_path = str(tmp_path / "test_progress.db")
        conn = sqlite3.connect(db_path)

        try:
            init_progress_schema(conn)
            conn.close()

            # Mark character as done
            today = datetime.now().strftime('%Y-%m-%d')
            mark_character_done(db_path, slot_index=0, character_name="TestChar")

            # Verify progress was recorded
            progress = get_character_progress(db_path, slot_index=0)
            assert progress is not None
            assert progress['slot_index'] == 0
            assert progress['character_name'] == "TestChar"
            assert progress['last_donation_date'] == today
            assert progress['donation_count'] == 1
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_is_character_done_today_returns_true_only_for_today(self, tmp_path):
        """Test that is_character_done_today returns True only for today's date."""
        from core.database import init_progress_schema, mark_character_done, is_character_done_today

        db_path = str(tmp_path / "test_progress.db")
        conn = sqlite3.connect(db_path)

        try:
            init_progress_schema(conn)
            conn.close()

            # Mark character as done today
            mark_character_done(db_path, slot_index=0, character_name="TestChar")

            # Should return True for today
            assert is_character_done_today(db_path, slot_index=0) is True

            # Should return False for different slot
            assert is_character_done_today(db_path, slot_index=1) is False
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_daily_reset_works(self, tmp_path):
        """Test that yesterday's completion doesn't count for today."""
        from core.database import init_progress_schema, mark_character_done, is_character_done_today

        db_path = str(tmp_path / "test_progress.db")
        conn = sqlite3.connect(db_path)

        try:
            init_progress_schema(conn)
            conn.close()

            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

            # Manually insert yesterday's record
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO character_progress (slot_index, character_name, last_donation_date, donation_count)
                VALUES (?, ?, ?, ?)
                """,
                (0, "TestChar", yesterday, 1)
            )
            conn.commit()
            conn.close()

            # Should return False for today (yesterday's completion)
            assert is_character_done_today(db_path, slot_index=0) is False
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_progress_stats_aggregate_correctly(self, tmp_path):
        """Test that progress stats aggregate correctly per account."""
        from core.database import init_progress_schema, mark_character_done, get_account_progress_summary

        db_path = str(tmp_path / "test_progress.db")
        conn = sqlite3.connect(db_path)

        try:
            init_progress_schema(conn)
            conn.close()

            today = datetime.now().strftime('%Y-%m-%d')
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

            # Mark some characters done today
            mark_character_done(db_path, slot_index=0, character_name="Char1")
            mark_character_done(db_path, slot_index=1, character_name="Char2")

            # Mark one done yesterday
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO character_progress (slot_index, character_name, last_donation_date, donation_count)
                VALUES (?, ?, ?, ?)
                """,
                (2, "Char3", yesterday, 5)
            )
            conn.commit()
            conn.close()

            # Get summary
            summary = get_account_progress_summary(db_path)

            assert summary['total_tracked'] == 3
            assert summary['completed_today'] == 2
            assert summary['total_donations'] == 7  # 1 + 1 + 5
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_donation_count_increments_on_multiple_completions(self, tmp_path):
        """Test that donation_count increments correctly on multiple completions."""
        from core.database import init_progress_schema, mark_character_done, get_character_progress

        db_path = str(tmp_path / "test_progress.db")
        conn = sqlite3.connect(db_path)

        try:
            init_progress_schema(conn)
            conn.close()

            # Mark same character done multiple times
            mark_character_done(db_path, slot_index=0, character_name="TestChar")
            mark_character_done(db_path, slot_index=0, character_name="TestChar")
            mark_character_done(db_path, slot_index=0, character_name="TestChar")

            progress = get_character_progress(db_path, slot_index=0)
            assert progress['donation_count'] == 3
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


# =============================================================================
# PROGRESS TRACKER TESTS (Task 2)
# =============================================================================

class TestProgressTracker:
    """Tests for ProgressTracker class."""

    def test_tracker_mark_done_updates_database(self, tmp_path):
        """Test that mark_done updates database correctly."""
        from core.progress_tracker import ProgressTracker

        db_path = str(tmp_path / "test_tracker.db")
        tracker = ProgressTracker(db_path)

        tracker.mark_done(slot_index=0, character_name="TestChar")

        progress = tracker.get_character_status(slot_index=0)
        assert progress is not None
        assert progress['slot_index'] == 0
        assert progress['character_name'] == "TestChar"

    def test_tracker_is_done_returns_true_only_for_completed(self, tmp_path):
        """Test that is_done returns True only for completed characters today."""
        from core.progress_tracker import ProgressTracker

        db_path = str(tmp_path / "test_tracker.db")
        tracker = ProgressTracker(db_path)

        # Initially not done
        assert tracker.is_done(slot_index=0) is False

        # Mark as done
        tracker.mark_done(slot_index=0, character_name="TestChar")

        # Now should be done
        assert tracker.is_done(slot_index=0) is True

        # Different slot should not be done
        assert tracker.is_done(slot_index=1) is False

    def test_tracker_get_summary_returns_accurate_stats(self, tmp_path):
        """Test that get_summary returns accurate account statistics."""
        from core.progress_tracker import ProgressTracker

        db_path = str(tmp_path / "test_tracker.db")
        tracker = ProgressTracker(db_path)

        # Mark some characters done
        tracker.mark_done(slot_index=0, character_name="Char1")
        tracker.mark_done(slot_index=1, character_name="Char2")
        tracker.mark_done(slot_index=3, character_name="Char4")

        summary = tracker.get_summary()

        assert summary['total_tracked'] == 3
        assert summary['completed_today'] == 3
        assert summary['completion_percentage'] == 100.0

    def test_tracker_get_remaining_characters_filters_completed(self, tmp_path):
        """Test that get_remaining_characters filters out completed."""
        from core.progress_tracker import ProgressTracker

        db_path = str(tmp_path / "test_tracker.db")
        tracker = ProgressTracker(db_path)

        # Mark slots 0 and 2 as done
        tracker.mark_done(slot_index=0, character_name="Char1")
        tracker.mark_done(slot_index=2, character_name="Char3")

        # Get remaining from 6 total slots
        remaining = tracker.get_remaining_characters(total_slots=6)

        assert 0 not in remaining
        assert 2 not in remaining
        assert 1 in remaining
        assert 3 in remaining
        assert 4 in remaining
        assert 5 in remaining
        assert len(remaining) == 4

    def test_tracker_multiple_donations_same_day_increment_count(self, tmp_path):
        """Test that multiple donations same day increment count correctly."""
        from core.progress_tracker import ProgressTracker

        db_path = str(tmp_path / "test_tracker.db")
        tracker = ProgressTracker(db_path)

        # Multiple donations for same character
        tracker.mark_done(slot_index=0, character_name="TestChar")
        tracker.mark_done(slot_index=0, character_name="TestChar")
        tracker.mark_done(slot_index=0, character_name="TestChar")

        status = tracker.get_character_status(slot_index=0)
        assert status['donation_count'] == 3
        assert tracker.is_done(slot_index=0) is True

    def test_tracker_daily_reset_behavior(self, tmp_path):
        """Test daily reset behavior with date change."""
        from core.progress_tracker import ProgressTracker
        from datetime import datetime, timedelta

        db_path = str(tmp_path / "test_tracker.db")
        tracker = ProgressTracker(db_path)

        # Mark as done
        tracker.mark_done(slot_index=0, character_name="TestChar")
        assert tracker.is_done(slot_index=0) is True

        # Simulate date change by directly updating the database
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE character_progress SET last_donation_date = ? WHERE slot_index = ?",
            (yesterday, 0)
        )
        conn.commit()
        conn.close()

        # Should not be done today anymore
        assert tracker.is_done(slot_index=0) is False


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestProgressIntegration:
    """Integration tests for progress tracking."""

    def test_full_workflow_mark_and_check(self, tmp_path):
        """Test full workflow of marking and checking progress."""
        from core.progress_tracker import ProgressTracker

        db_path = str(tmp_path / "test_integration.db")
        tracker = ProgressTracker(db_path)

        # Simulate workflow: process characters 0, 1, 2
        for i in range(3):
            tracker.mark_done(slot_index=i, character_name=f"Char{i}")

        # Check remaining
        remaining = tracker.get_remaining_characters(total_slots=6)
        assert len(remaining) == 3
        assert all(i in remaining for i in [3, 4, 5])

        # Complete remaining
        for i in remaining:
            tracker.mark_done(slot_index=i, character_name=f"Char{i}")

        # All done
        summary = tracker.get_summary()
        assert summary['completed_today'] == 6
        assert summary['completion_percentage'] == 100.0

    def test_persistence_across_connections(self, tmp_path):
        """Test that progress persists across database reconnections."""
        from core.progress_tracker import ProgressTracker

        db_path = str(tmp_path / "test_persistence.db")

        # First tracker instance
        tracker1 = ProgressTracker(db_path)
        tracker1.mark_done(slot_index=0, character_name="TestChar")

        # Second tracker instance (new connection)
        tracker2 = ProgressTracker(db_path)

        # Progress should persist
        assert tracker2.is_done(slot_index=0) is True
        assert tracker2.get_character_status(slot_index=0)['character_name'] == "TestChar"
