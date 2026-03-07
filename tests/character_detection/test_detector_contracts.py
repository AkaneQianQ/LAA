"""
Contract and schema tests for character detection system.

Tests validate:
- Detector API contracts and ROI constants
- SQLite schema bootstrap and repository behaviors
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestDetectorContracts:
    """Validate CharacterDetector API surface and configuration constants."""

    def test_detector_module_importable(self):
        """Detector module can be imported without side effects."""
        from modules import character_detector
        assert hasattr(character_detector, 'CharacterDetector')

    def test_detector_class_exists(self):
        """CharacterDetector class is defined with expected methods."""
        from modules.character_detector import CharacterDetector

        # Check required methods exist
        assert hasattr(CharacterDetector, 'detect_esc_menu')
        assert hasattr(CharacterDetector, 'scan_slots_occupancy')
        assert hasattr(CharacterDetector, 'detect_scroll_bottom')
        assert hasattr(CharacterDetector, 'discover_characters')

    def test_detector_roi_constants_exist(self):
        """All 9 slot ROIs are defined as module constants."""
        from modules import character_detector as cd

        # Check slot ROI constants exist (3x3 grid)
        assert hasattr(cd, 'SLOT_1_1_ROI')
        assert hasattr(cd, 'SLOT_1_2_ROI')
        assert hasattr(cd, 'SLOT_1_3_ROI')
        assert hasattr(cd, 'SLOT_2_1_ROI')
        assert hasattr(cd, 'SLOT_2_2_ROI')
        assert hasattr(cd, 'SLOT_2_3_ROI')
        assert hasattr(cd, 'SLOT_3_1_ROI')
        assert hasattr(cd, 'SLOT_3_2_ROI')
        assert hasattr(cd, 'SLOT_3_3_ROI')

    def test_detector_slot_roi_values(self):
        """Slot ROI values match locked phase specifications (248x67 each)."""
        from modules.character_detector import (
            SLOT_1_1_ROI, SLOT_1_2_ROI, SLOT_1_3_ROI,
            SLOT_2_1_ROI, SLOT_2_2_ROI, SLOT_2_3_ROI,
            SLOT_3_1_ROI, SLOT_3_2_ROI, SLOT_3_3_ROI,
        )

        # Expected ROIs from phase context
        expected_rois = {
            'SLOT_1_1_ROI': (904, 557, 1152, 624),
            'SLOT_1_2_ROI': (1164, 557, 1412, 624),
            'SLOT_1_3_ROI': (1425, 557, 1673, 624),
            'SLOT_2_1_ROI': (904, 674, 1152, 741),
            'SLOT_2_2_ROI': (1164, 674, 1412, 741),
            'SLOT_2_3_ROI': (1425, 674, 1673, 741),
            'SLOT_3_1_ROI': (904, 791, 1152, 858),
            'SLOT_3_2_ROI': (1164, 791, 1412, 858),
            'SLOT_3_3_ROI': (1425, 791, 1673, 858),
        }

        actual_rois = {
            'SLOT_1_1_ROI': SLOT_1_1_ROI,
            'SLOT_1_2_ROI': SLOT_1_2_ROI,
            'SLOT_1_3_ROI': SLOT_1_3_ROI,
            'SLOT_2_1_ROI': SLOT_2_1_ROI,
            'SLOT_2_2_ROI': SLOT_2_2_ROI,
            'SLOT_2_3_ROI': SLOT_2_3_ROI,
            'SLOT_3_1_ROI': SLOT_3_1_ROI,
            'SLOT_3_2_ROI': SLOT_3_2_ROI,
            'SLOT_3_3_ROI': SLOT_3_3_ROI,
        }

        for name, expected in expected_rois.items():
            actual = actual_rois[name]
            assert actual == expected, f"{name}: expected {expected}, got {actual}"

            # Verify dimensions: 248x67
            x1, y1, x2, y2 = actual
            width = x2 - x1
            height = y2 - y1
            assert width == 248, f"{name} width should be 248, got {width}"
            assert height == 67, f"{name} height should be 67, got {height}"

    def test_detector_scrollbar_roi_exists(self):
        """Scrollbar bottom detection ROI is defined."""
        from modules import character_detector as cd

        assert hasattr(cd, 'SCROLLBAR_BOTTOM_ROI')

    def test_detector_scrollbar_roi_value(self):
        """Scrollbar ROI matches locked phase specification (14x32)."""
        from modules.character_detector import SCROLLBAR_BOTTOM_ROI

        expected = (1683, 828, 1697, 860)
        assert SCROLLBAR_BOTTOM_ROI == expected

        # Verify dimensions: 14x32
        x1, y1, x2, y2 = SCROLLBAR_BOTTOM_ROI
        width = x2 - x1
        height = y2 - y1
        assert width == 14, f"Width should be 14, got {width}"
        assert height == 32, f"Height should be 32, got {height}"

    def test_detector_threshold_constants(self):
        """Detection thresholds are centralized with correct values."""
        from modules import character_detector as cd

        assert hasattr(cd, 'SLOT_DETECTION_THRESHOLD')
        assert hasattr(cd, 'MAX_DETECTION_RETRIES')

        # Threshold must be >= 0.8 per locked decision
        assert cd.SLOT_DETECTION_THRESHOLD >= 0.8
        assert cd.SLOT_DETECTION_THRESHOLD <= 1.0

        # Retries should be 3 per specification
        assert cd.MAX_DETECTION_RETRIES == 3

    def test_detector_matching_method_locked(self):
        """Template matching method is TM_CCOEFF_NORMED (locked decision)."""
        from modules import character_detector as cd

        assert hasattr(cd, 'TEMPLATE_MATCH_METHOD')
        import cv2
        assert cd.TEMPLATE_MATCH_METHOD == cv2.TM_CCOEFF_NORMED

    def test_detector_return_types_documented(self):
        """Detector methods have typed return annotations."""
        from modules.character_detector import CharacterDetector
        import inspect

        methods = ['detect_esc_menu', 'scan_slots_occupancy', 'detect_scroll_bottom', 'discover_characters']
        for method_name in methods:
            method = getattr(CharacterDetector, method_name)
            sig = inspect.signature(method)
            assert sig.return_annotation != inspect.Signature.empty, f"{method_name} missing return type"


class TestDatabaseSchema:
    """Validate SQLite schema and repository behaviors."""

    def test_database_module_importable(self):
        """Database module can be imported without side effects."""
        from core import database
        assert hasattr(database, 'init_database')

    def test_database_init_creates_tables(self, tmp_path):
        """Schema initialization creates required tables."""
        from core.database import init_database
        import sqlite3

        db_path = tmp_path / "test.db"
        init_database(str(db_path))

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check accounts table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'")
        assert cursor.fetchone() is not None, "accounts table not found"

        # Check characters table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='characters'")
        assert cursor.fetchone() is not None, "characters table not found"

        conn.close()

    def test_database_schema_columns(self, tmp_path):
        """Tables have required columns."""
        from core.database import init_database
        import sqlite3

        db_path = tmp_path / "test.db"
        init_database(str(db_path))

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check accounts columns
        cursor.execute("PRAGMA table_info(accounts)")
        account_columns = {row[1] for row in cursor.fetchall()}
        required_account_cols = {'id', 'account_hash', 'created_at'}
        assert required_account_cols.issubset(account_columns), f"Missing columns in accounts: {required_account_cols - account_columns}"

        # Check characters columns
        cursor.execute("PRAGMA table_info(characters)")
        character_columns = {row[1] for row in cursor.fetchall()}
        required_character_cols = {'id', 'account_id', 'slot_index', 'screenshot_path', 'created_at'}
        assert required_character_cols.issubset(character_columns), f"Missing columns in characters: {required_character_cols - character_columns}"

        conn.close()

    def test_database_account_operations(self, tmp_path):
        """Account repository operations work correctly."""
        from core.database import init_database, create_account, find_account_by_hash
        import sqlite3

        db_path = tmp_path / "test.db"
        init_database(str(db_path))

        # Create account
        account_id = create_account(str(db_path), "test_hash_123")
        assert account_id is not None
        assert isinstance(account_id, int)

        # Find account by hash
        found = find_account_by_hash(str(db_path), "test_hash_123")
        assert found is not None
        assert found['id'] == account_id
        assert found['account_hash'] == "test_hash_123"

        # Non-existent hash returns None
        not_found = find_account_by_hash(str(db_path), "non_existent")
        assert not_found is None

    def test_database_character_upsert(self, tmp_path):
        """Character upsert creates or updates without duplicates."""
        from core.database import init_database, create_account, upsert_character, list_characters_by_account

        db_path = tmp_path / "test.db"
        init_database(str(db_path))

        # Create account
        account_id = create_account(str(db_path), "account_hash_456")

        # Upsert character
        upsert_character(str(db_path), account_id, 0, "/path/to/char_0.png")

        # List characters
        chars = list_characters_by_account(str(db_path), account_id)
        assert len(chars) == 1
        assert chars[0]['slot_index'] == 0
        assert chars[0]['screenshot_path'] == "/path/to/char_0.png"

        # Upsert same slot (should update, not create duplicate)
        upsert_character(str(db_path), account_id, 0, "/path/to/char_0_updated.png")
        chars = list_characters_by_account(str(db_path), account_id)
        assert len(chars) == 1, "Upsert should not create duplicates"
        assert chars[0]['screenshot_path'] == "/path/to/char_0_updated.png"

        # Upsert different slot
        upsert_character(str(db_path), account_id, 1, "/path/to/char_1.png")
        chars = list_characters_by_account(str(db_path), account_id)
        assert len(chars) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
