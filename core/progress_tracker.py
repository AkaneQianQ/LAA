"""
Progress Tracker Module

Provides per-account progress persistence for daily donation tracking.
Uses SQLite with per-account database files for isolation.

Exports:
    ProgressTracker: Tracks daily donation completion per character
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, Any, List


# =============================================================================
# SCHEMA DEFINITION
# =============================================================================

CREATE_PROGRESS_TABLE = """
CREATE TABLE IF NOT EXISTS character_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_index INTEGER NOT NULL,
    character_name TEXT,
    last_donation_date TEXT NOT NULL,  -- YYYY-MM-DD format
    donation_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(slot_index)
);
"""

CREATE_PROGRESS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_progress_date ON character_progress(last_donation_date);
"""


class ProgressTracker:
    """
    Per-account progress persistence for daily donation tracking.

    Tracks which characters have completed donations for the current day,
    with support for historical donation counts and summary statistics.

    Usage:
        tracker = ProgressTracker("data/accounts/abc/progress.db")
        tracker.mark_done(0, "CharacterName")
        if tracker.is_done(0):
            print("Already completed today")
    """

    def __init__(self, db_path: str):
        """
        Initialize progress tracker with database path.

        Args:
            db_path: Path to the SQLite database file for this account
        """
        self.db_path = db_path
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize the progress tracking schema if not exists."""
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        conn = sqlite3.connect(self.db_path, timeout=5.0)
        try:
            cursor = conn.cursor()
            cursor.execute(CREATE_PROGRESS_TABLE)
            cursor.execute(CREATE_PROGRESS_INDEX)
            conn.commit()
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _today(self) -> str:
        """Get today's date in ISO format (YYYY-MM-DD)."""
        return datetime.now().strftime('%Y-%m-%d')

    def mark_done(self, slot_index: int, character_name: Optional[str] = None) -> None:
        """
        Mark a character's donation as complete for today.

        Args:
            slot_index: The slot index (0-8) of the character
            character_name: Optional character name for reference
        """
        today = self._today()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO character_progress
                    (slot_index, character_name, last_donation_date, donation_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(slot_index) DO UPDATE SET
                    character_name = COALESCE(EXCLUDED.character_name, character_progress.character_name),
                    last_donation_date = EXCLUDED.last_donation_date,
                    donation_count = character_progress.donation_count + 1,
                    updated_at = CURRENT_TIMESTAMP
            """, (slot_index, character_name, today))
            conn.commit()
        finally:
            conn.close()

    def is_done(self, slot_index: int) -> bool:
        """
        Check if a character has completed donation today.

        Args:
            slot_index: The slot index (0-8) to check

        Returns:
            True if character completed donation today, False otherwise
        """
        today = self._today()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT last_donation_date FROM character_progress WHERE slot_index = ?",
                (slot_index,)
            )
            row = cursor.fetchone()

            if row is None:
                return False

            return row['last_donation_date'] == today
        finally:
            conn.close()

    def get_character_status(self, slot_index: int) -> Optional[Dict[str, Any]]:
        """
        Get full status for a character.

        Args:
            slot_index: The slot index (0-8) to query

        Returns:
            Dictionary with character status or None if not found
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT slot_index, character_name, last_donation_date,
                          donation_count, updated_at
                   FROM character_progress WHERE slot_index = ?""",
                (slot_index,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return {
                'slot_index': row['slot_index'],
                'character_name': row['character_name'],
                'last_donation_date': row['last_donation_date'],
                'donation_count': row['donation_count'],
                'updated_at': row['updated_at'],
            }
        finally:
            conn.close()

    def get_summary(self) -> Dict[str, Any]:
        """
        Get progress summary for the account.

        Returns:
            Dictionary with:
                - total_tracked: Total number of characters tracked
                - completed_today: Number completed today
                - remaining_today: Number remaining for today
                - completion_percentage: Percentage complete (0.0-100.0)
                - total_donations: Total donations across all time
        """
        today = self._today()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) as total_tracked,
                    SUM(CASE WHEN last_donation_date = ? THEN 1 ELSE 0 END) as completed_today,
                    SUM(donation_count) as total_donations
                FROM character_progress
            """, (today,))
            row = cursor.fetchone()

            total = row['total_tracked'] or 0
            completed = row['completed_today'] or 0
            remaining = total - completed
            percentage = (completed / total * 100) if total > 0 else 0.0

            return {
                'total_tracked': total,
                'completed_today': completed,
                'remaining_today': remaining,
                'completion_percentage': percentage,
                'total_donations': row['total_donations'] or 0,
            }
        finally:
            conn.close()

    def get_remaining_characters(self, total_slots: int) -> List[int]:
        """
        Get list of slot indices not yet completed today.

        Args:
            total_slots: Total number of slots to check (typically character_count)

        Returns:
            List of slot indices (0-based) that haven't completed donation today
        """
        today = self._today()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT slot_index FROM character_progress WHERE last_donation_date = ?",
                (today,)
            )
            completed = {row['slot_index'] for row in cursor.fetchall()}

            return [i for i in range(total_slots) if i not in completed]
        finally:
            conn.close()

    def reset_progress(self) -> int:
        """
        Reset all progress (for testing or manual reset).

        Returns:
            Number of records deleted
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM character_progress")
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
