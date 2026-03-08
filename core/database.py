"""
Database Module

Provides SQLite persistence for account and character metadata.
Uses stdlib sqlite3 with explicit timeout and short transactions.

Schema:
- accounts: Stores account identity (hash-based) and creation timestamp
- characters: Maps account to slot_index with screenshot path
- character_progress: Tracks daily donation completion per character slot
"""

import sqlite3
import os
from typing import Optional, List, Dict, Any
from datetime import datetime


# =============================================================================
# SCHEMA DEFINITION
# =============================================================================

# SQL to create the accounts table
CREATE_ACCOUNTS_TABLE = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_hash TEXT UNIQUE NOT NULL,
    tag_screenshot_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# SQL to create the characters table
CREATE_CHARACTERS_TABLE = """
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    slot_index INTEGER NOT NULL,
    screenshot_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    UNIQUE(account_id, slot_index)
);
"""

# Create index for faster account lookups
CREATE_ACCOUNT_HASH_INDEX = """
CREATE INDEX IF NOT EXISTS idx_account_hash ON accounts(account_hash);
"""

# Create index for character lookups by account
CREATE_CHARACTER_ACCOUNT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_character_account ON characters(account_id);
"""

# =============================================================================
# PROGRESS TRACKING SCHEMA
# =============================================================================

# SQL to create the character_progress table
CREATE_CHARACTER_PROGRESS_TABLE = """
CREATE TABLE IF NOT EXISTS character_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_index INTEGER NOT NULL,
    character_name TEXT,
    last_donation_date TEXT NOT NULL,
    donation_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(slot_index)
);
"""

# Create index for slot lookups
CREATE_PROGRESS_SLOT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_progress_slot ON character_progress(slot_index);
"""

# Create index for date lookups
CREATE_PROGRESS_DATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_progress_date ON character_progress(last_donation_date);
"""


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

def init_database(db_path: str) -> None:
    """
    Initialize the SQLite database with required tables and indexes.

    This function is idempotent - it can be called multiple times without
    changing state unexpectedly.

    Args:
        db_path: Path to the SQLite database file
    """
    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        cursor = conn.cursor()

        # Create tables
        cursor.execute(CREATE_ACCOUNTS_TABLE)
        cursor.execute(CREATE_CHARACTERS_TABLE)

        # Create indexes
        cursor.execute(CREATE_ACCOUNT_HASH_INDEX)
        cursor.execute(CREATE_CHARACTER_ACCOUNT_INDEX)

        conn.commit()
    finally:
        conn.close()


# =============================================================================
# ACCOUNT REPOSITORY
# =============================================================================

def create_account(db_path: str, account_hash: str) -> int:
    """
    Create a new account record.

    Args:
        db_path: Path to the SQLite database file
        account_hash: Unique hash identifier for the account

    Returns:
        The ID of the created account

    Raises:
        sqlite3.IntegrityError: If account_hash already exists
    """
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO accounts (account_hash) VALUES (?)",
            (account_hash,)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def find_account_by_hash(db_path: str, account_hash: str) -> Optional[Dict[str, Any]]:
    """
    Find an account by its hash.

    Args:
        db_path: Path to the SQLite database file
        account_hash: The account hash to search for

    Returns:
        Account dictionary with id, account_hash, tag_screenshot_path, created_at, or None if not found
    """
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, account_hash, tag_screenshot_path, created_at FROM accounts WHERE account_hash = ?",
            (account_hash,)
        )
        row = cursor.fetchone()

        if row is None:
            return None

        return {
            'id': row['id'],
            'account_hash': row['account_hash'],
            'tag_screenshot_path': row['tag_screenshot_path'],
            'created_at': row['created_at'],
        }
    finally:
        conn.close()


def get_or_create_account(db_path: str, account_hash: str) -> int:
    """
    Get existing account ID or create new account if not exists.

    Args:
        db_path: Path to the SQLite database file
        account_hash: The account hash identifier

    Returns:
        The account ID (existing or newly created)
    """
    existing = find_account_by_hash(db_path, account_hash)
    if existing:
        return existing['id']
    return create_account(db_path, account_hash)


def update_account_tag(db_path: str, account_id: int, tag_screenshot_path: str) -> bool:
    """
    Update account tag screenshot path.

    Args:
        db_path: Path to the SQLite database file
        account_id: The account ID to update
        tag_screenshot_path: Path to the tag screenshot

    Returns:
        True if successful, False otherwise
    """
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE accounts SET tag_screenshot_path = ? WHERE id = ?",
            (tag_screenshot_path, account_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def get_account_tag_path(db_path: str, account_id: int) -> Optional[str]:
    """
    Get account tag screenshot path.

    Args:
        db_path: Path to the SQLite database file
        account_id: The account ID

    Returns:
        Path to tag screenshot or None if not found
    """
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tag_screenshot_path FROM accounts WHERE id = ?",
            (account_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def list_all_accounts(db_path: str) -> List[Dict[str, Any]]:
    """
    List all accounts in the database.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        List of account dictionaries
    """
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, account_hash, tag_screenshot_path, created_at FROM accounts ORDER BY created_at")
        rows = cursor.fetchall()

        return [
            {
                'id': row['id'],
                'account_hash': row['account_hash'],
                'tag_screenshot_path': row['tag_screenshot_path'],
                'created_at': row['created_at'],
            }
            for row in rows
        ]
    finally:
        conn.close()


# =============================================================================
# CHARACTER REPOSITORY
# =============================================================================

def upsert_character(
    db_path: str,
    account_id: int,
    slot_index: int,
    screenshot_path: str
) -> int:
    """
    Insert or update a character record.

    If a character already exists for the given account_id and slot_index,
    it will be updated with the new screenshot_path. Otherwise, a new
    record is created.

    Args:
        db_path: Path to the SQLite database file
        account_id: The account ID this character belongs to
        slot_index: The slot index (0-8) of the character
        screenshot_path: Path to the character screenshot

    Returns:
        The ID of the character record
    """
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        cursor = conn.cursor()

        # Try to update existing record
        cursor.execute(
            """
            UPDATE characters
            SET screenshot_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE account_id = ? AND slot_index = ?
            """,
            (screenshot_path, account_id, slot_index)
        )

        if cursor.rowcount > 0:
            # Record was updated, fetch its ID
            cursor.execute(
                "SELECT id FROM characters WHERE account_id = ? AND slot_index = ?",
                (account_id, slot_index)
            )
            row = cursor.fetchone()
            conn.commit()
            return row[0]

        # Insert new record
        cursor.execute(
            """
            INSERT INTO characters (account_id, slot_index, screenshot_path)
            VALUES (?, ?, ?)
            """,
            (account_id, slot_index, screenshot_path)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def find_character_by_slot(
    db_path: str,
    account_id: int,
    slot_index: int
) -> Optional[Dict[str, Any]]:
    """
    Find a character by account ID and slot index.

    Args:
        db_path: Path to the SQLite database file
        account_id: The account ID to search within
        slot_index: The slot index to search for

    Returns:
        Character dictionary or None if not found
    """
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, account_id, slot_index, screenshot_path, created_at, updated_at
            FROM characters
            WHERE account_id = ? AND slot_index = ?
            """,
            (account_id, slot_index)
        )
        row = cursor.fetchone()

        if row is None:
            return None

        return {
            'id': row['id'],
            'account_id': row['account_id'],
            'slot_index': row['slot_index'],
            'screenshot_path': row['screenshot_path'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }
    finally:
        conn.close()


def list_characters_by_account(
    db_path: str,
    account_id: int
) -> List[Dict[str, Any]]:
    """
    List all characters for a given account.

    Args:
        db_path: Path to the SQLite database file
        account_id: The account ID to list characters for

    Returns:
        List of character dictionaries ordered by slot_index
    """
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, account_id, slot_index, screenshot_path, created_at, updated_at
            FROM characters
            WHERE account_id = ?
            ORDER BY slot_index
            """,
            (account_id,)
        )
        rows = cursor.fetchall()

        return [
            {
                'id': row['id'],
                'account_id': row['account_id'],
                'slot_index': row['slot_index'],
                'screenshot_path': row['screenshot_path'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
            }
            for row in rows
        ]
    finally:
        conn.close()


def delete_character(db_path: str, character_id: int) -> bool:
    """
    Delete a character record by ID.

    Args:
        db_path: Path to the SQLite database file
        character_id: The character ID to delete

    Returns:
        True if a record was deleted, False if not found
    """
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM characters WHERE id = ?", (character_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_characters_by_account(db_path: str, account_id: int) -> int:
    """
    Delete all characters for a given account.

    Args:
        db_path: Path to the SQLite database file
        account_id: The account ID to delete characters for

    Returns:
        Number of characters deleted
    """
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM characters WHERE account_id = ?", (account_id,))
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


# =============================================================================
# DATABASE UTILITIES
# =============================================================================

def get_database_stats(db_path: str) -> Dict[str, int]:
    """
    Get basic statistics about the database.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        Dictionary with account_count and character_count
    """
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM accounts")
        account_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM characters")
        character_count = cursor.fetchone()[0]

        return {
            'account_count': account_count,
            'character_count': character_count,
        }
    finally:
        conn.close()


def vacuum_database(db_path: str) -> None:
    """
    Run VACUUM to optimize database file size.

    Args:
        db_path: Path to the SQLite database file
    """
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        conn.execute("VACUUM")
    finally:
        conn.close()


# =============================================================================
# PROGRESS TRACKING FUNCTIONS
# =============================================================================

def init_progress_schema(conn: sqlite3.Connection) -> None:
    """
    Initialize the progress tracking schema in the given connection.

    This function creates the character_progress table and indexes
    if they don't already exist.

    Args:
        conn: SQLite connection object
    """
    cursor = conn.cursor()

    # Create progress table
    cursor.execute(CREATE_CHARACTER_PROGRESS_TABLE)

    # Create indexes
    cursor.execute(CREATE_PROGRESS_SLOT_INDEX)
    cursor.execute(CREATE_PROGRESS_DATE_INDEX)

    conn.commit()


def mark_character_done(db_path: str, slot_index: int, character_name: str = None) -> bool:
    """
    Mark a character's donation as complete for today.

    Uses UPSERT pattern to either insert a new record or update an existing one.
    Increments donation_count on each completion.

    Args:
        db_path: Path to the SQLite database file
        slot_index: The slot index (0-8) of the character
        character_name: Optional character name for display

    Returns:
        True if successful, False on error
    """
    today = datetime.now().strftime('%Y-%m-%d')

    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        cursor = conn.cursor()

        # Ensure table exists
        cursor.execute(CREATE_CHARACTER_PROGRESS_TABLE)

        # UPSERT: Insert or update progress
        cursor.execute(
            """
            INSERT INTO character_progress (slot_index, character_name, last_donation_date, donation_count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(slot_index) DO UPDATE SET
                last_donation_date = EXCLUDED.last_donation_date,
                donation_count = character_progress.donation_count + 1,
                updated_at = CURRENT_TIMESTAMP
            """,
            (slot_index, character_name, today)
        )

        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def is_character_done_today(db_path: str, slot_index: int) -> bool:
    """
    Check if a character has completed donation today.

    Args:
        db_path: Path to the SQLite database file
        slot_index: The slot index (0-8) to check

    Returns:
        True if character completed donation today, False otherwise
    """
    today = datetime.now().strftime('%Y-%m-%d')

    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        cursor = conn.cursor()

        # Ensure table exists
        cursor.execute(CREATE_CHARACTER_PROGRESS_TABLE)
        conn.commit()

        cursor.execute(
            """
            SELECT last_donation_date FROM character_progress
            WHERE slot_index = ?
            """,
            (slot_index,)
        )
        row = cursor.fetchone()

        if row is None:
            return False

        return row[0] == today
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def get_character_progress(db_path: str, slot_index: int) -> Optional[Dict[str, Any]]:
    """
    Get full progress record for a character.

    Args:
        db_path: Path to the SQLite database file
        slot_index: The slot index (0-8) to retrieve

    Returns:
        Dictionary with progress data or None if not found
    """
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()

        # Ensure table exists
        cursor.execute(CREATE_CHARACTER_PROGRESS_TABLE)
        conn.commit()

        cursor.execute(
            """
            SELECT id, slot_index, character_name, last_donation_date,
                   donation_count, updated_at
            FROM character_progress
            WHERE slot_index = ?
            """,
            (slot_index,)
        )
        row = cursor.fetchone()

        if row is None:
            return None

        return {
            'id': row['id'],
            'slot_index': row['slot_index'],
            'character_name': row['character_name'],
            'last_donation_date': row['last_donation_date'],
            'donation_count': row['donation_count'],
            'updated_at': row['updated_at'],
        }
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def get_account_progress_summary(db_path: str) -> Dict[str, Any]:
    """
    Get aggregate progress statistics for the account.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        Dictionary with summary statistics
    """
    today = datetime.now().strftime('%Y-%m-%d')

    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        cursor = conn.cursor()

        # Ensure table exists
        cursor.execute(CREATE_CHARACTER_PROGRESS_TABLE)
        conn.commit()

        # Total tracked characters
        cursor.execute("SELECT COUNT(*) FROM character_progress")
        total_tracked = cursor.fetchone()[0]

        # Completed today
        cursor.execute(
            "SELECT COUNT(*) FROM character_progress WHERE last_donation_date = ?",
            (today,)
        )
        completed_today = cursor.fetchone()[0]

        # Total donations across all characters
        cursor.execute(
            "SELECT COALESCE(SUM(donation_count), 0) FROM character_progress"
        )
        total_donations = cursor.fetchone()[0]

        return {
            'total_tracked': total_tracked,
            'completed_today': completed_today,
            'total_donations': total_donations,
        }
    except sqlite3.Error:
        return {
            'total_tracked': 0,
            'completed_today': 0,
            'total_donations': 0,
        }
    finally:
        conn.close()
