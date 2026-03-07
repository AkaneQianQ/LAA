"""
Account indexing and screenshot cache tests for character detection system.

Tests validate:
- First character screenshot hashing for account identity
- Account directory structure creation
- Cache persistence and repeat-run recognition
- Database integration for account/character metadata
"""

import pytest
import sys
import os
import hashlib
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestFirstCharacterAccountIndexing:
    """Validate first-character screenshot creates stable account identity."""

    def test_create_or_get_account_index_exists(self):
        """CharacterDetector has create_or_get_account_index method."""
        from modules.character_detector import CharacterDetector

        assert hasattr(CharacterDetector, 'create_or_get_account_index')

    def test_first_character_creates_account_index(self, tmp_path):
        """First run captures first character screenshot and creates account."""
        from modules.character_detector import CharacterDetector
        from core.database import init_database

        # Setup test environment
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "accounts.db"
        init_database(str(db_path))

        detector = CharacterDetector(
            assets_path="assets",
            data_dir=str(data_dir),
            db_path=str(db_path)
        )

        # Create a mock screenshot with a unique pattern
        screenshot = np.random.randint(0, 255, (1440, 2560, 3), dtype=np.uint8)

        # Mock slot detection to return first slot as occupied
        mock_result = Mock()
        mock_result.has_character = True
        mock_result.slot_index = 0
        mock_result.roi = (904, 557, 1152, 624)
        mock_result.confidence = 0.95

        with patch.object(detector, 'scan_visible_slots', return_value=[mock_result]):
            account_id, account_hash = detector.create_or_get_account_index(screenshot)

        # Should return valid account info
        assert account_id is not None
        assert isinstance(account_id, int)
        assert account_hash is not None
        assert isinstance(account_hash, str)
        assert len(account_hash) == 64  # SHA-256 hex string

    def test_account_hash_is_deterministic(self, tmp_path):
        """Same screenshot produces same account hash (deterministic)."""
        from modules.character_detector import CharacterDetector
        from core.database import init_database

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "accounts.db"
        init_database(str(db_path))

        detector = CharacterDetector(
            assets_path="assets",
            data_dir=str(data_dir),
            db_path=str(db_path)
        )

        # Create identical screenshots
        screenshot1 = np.ones((1440, 2560, 3), dtype=np.uint8) * 128
        screenshot2 = np.ones((1440, 2560, 3), dtype=np.uint8) * 128

        mock_result = Mock()
        mock_result.has_character = True
        mock_result.slot_index = 0
        mock_result.roi = (904, 557, 1152, 624)
        mock_result.confidence = 0.95

        with patch.object(detector, 'scan_visible_slots', return_value=[mock_result]):
            _, hash1 = detector.create_or_get_account_index(screenshot1)
            _, hash2 = detector.create_or_get_account_index(screenshot2)

        # Same input should produce same hash
        assert hash1 == hash2

    def test_account_hash_is_unique_per_screenshot(self, tmp_path):
        """Different screenshots produce different account hashes."""
        from modules.character_detector import CharacterDetector
        from core.database import init_database

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "accounts.db"
        init_database(str(db_path))

        detector = CharacterDetector(
            assets_path="assets",
            data_dir=str(data_dir),
            db_path=str(db_path)
        )

        # Create different screenshots
        screenshot1 = np.ones((1440, 2560, 3), dtype=np.uint8) * 100
        screenshot2 = np.ones((1440, 2560, 3), dtype=np.uint8) * 200

        mock_result = Mock()
        mock_result.has_character = True
        mock_result.slot_index = 0
        mock_result.roi = (904, 557, 1152, 624)
        mock_result.confidence = 0.95

        with patch.object(detector, 'scan_visible_slots', return_value=[mock_result]):
            _, hash1 = detector.create_or_get_account_index(screenshot1)
            _, hash2 = detector.create_or_get_account_index(screenshot2)

        # Different input should produce different hash
        assert hash1 != hash2

    def test_account_directory_structure_created(self, tmp_path):
        """Account directory structure is created on first run."""
        from modules.character_detector import CharacterDetector
        from core.database import init_database

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "accounts.db"
        init_database(str(db_path))

        detector = CharacterDetector(
            assets_path="assets",
            data_dir=str(data_dir),
            db_path=str(db_path)
        )

        screenshot = np.ones((1440, 2560, 3), dtype=np.uint8) * 128

        mock_result = Mock()
        mock_result.has_character = True
        mock_result.slot_index = 0
        mock_result.roi = (904, 557, 1152, 624)
        mock_result.confidence = 0.95

        with patch.object(detector, 'scan_visible_slots', return_value=[mock_result]):
            account_id, account_hash = detector.create_or_get_account_index(screenshot)

        # Check directory structure exists
        account_dir = data_dir / "accounts" / account_hash
        chars_dir = account_dir / "characters"

        assert account_dir.exists(), f"Account directory not created: {account_dir}"
        assert chars_dir.exists(), f"Characters directory not created: {chars_dir}"

    def test_first_character_screenshot_saved(self, tmp_path):
        """First character screenshot is saved to account directory."""
        from modules.character_detector import CharacterDetector
        from core.database import init_database

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "accounts.db"
        init_database(str(db_path))

        detector = CharacterDetector(
            assets_path="assets",
            data_dir=str(data_dir),
            db_path=str(db_path)
        )

        screenshot = np.random.randint(0, 255, (1440, 2560, 3), dtype=np.uint8)

        mock_result = Mock()
        mock_result.has_character = True
        mock_result.slot_index = 0
        mock_result.roi = (904, 557, 1152, 624)
        mock_result.confidence = 0.95

        with patch.object(detector, 'scan_visible_slots', return_value=[mock_result]):
            account_id, account_hash = detector.create_or_get_account_index(screenshot)

        # Check screenshot was saved
        chars_dir = data_dir / "accounts" / account_hash / "characters"
        screenshot_files = list(chars_dir.glob("*.png"))

        assert len(screenshot_files) > 0, "No screenshot files saved"
        assert (chars_dir / "0.png").exists(), "Slot 0 screenshot not saved"

    def test_account_created_exactly_once(self, tmp_path):
        """Same account hash creates record exactly once (idempotent)."""
        from modules.character_detector import CharacterDetector
        from core.database import init_database, list_all_accounts

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "accounts.db"
        init_database(str(db_path))

        detector = CharacterDetector(
            assets_path="assets",
            data_dir=str(data_dir),
            db_path=str(db_path)
        )

        screenshot = np.ones((1440, 2560, 3), dtype=np.uint8) * 128

        mock_result = Mock()
        mock_result.has_character = True
        mock_result.slot_index = 0
        mock_result.roi = (904, 557, 1152, 624)
        mock_result.confidence = 0.95

        # First call - should create account
        with patch.object(detector, 'scan_visible_slots', return_value=[mock_result]):
            account_id1, _ = detector.create_or_get_account_index(screenshot)

        # Second call with same screenshot - should return existing
        with patch.object(detector, 'scan_visible_slots', return_value=[mock_result]):
            account_id2, _ = detector.create_or_get_account_index(screenshot)

        # Should return same account ID
        assert account_id1 == account_id2

        # Should only have one account in database
        accounts = list_all_accounts(str(db_path))
        assert len(accounts) == 1


class TestCharacterCacheReuse:
    """Validate screenshot cache persistence and repeat-run recognition."""

    def test_cache_character_screenshot_exists(self):
        """CharacterDetector has cache_character_screenshot method."""
        from modules.character_detector import CharacterDetector

        assert hasattr(CharacterDetector, 'cache_character_screenshot')

    def test_load_cached_characters_exists(self):
        """CharacterDetector has load_cached_characters method."""
        from modules.character_detector import CharacterDetector

        assert hasattr(CharacterDetector, 'load_cached_characters')

    def test_character_cache_reused_on_subsequent_runs(self, tmp_path):
        """Repeat run resolves account from cached screenshot identity."""
        from modules.character_detector import CharacterDetector
        from core.database import init_database

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "accounts.db"
        init_database(str(db_path))

        # First run - create account and cache
        detector1 = CharacterDetector(
            assets_path="assets",
            data_dir=str(data_dir),
            db_path=str(db_path)
        )

        screenshot = np.random.randint(0, 255, (1440, 2560, 3), dtype=np.uint8)

        mock_result = Mock()
        mock_result.has_character = True
        mock_result.slot_index = 0
        mock_result.roi = (904, 557, 1152, 624)
        mock_result.confidence = 0.95

        with patch.object(detector1, 'scan_visible_slots', return_value=[mock_result]):
            account_id1, account_hash1 = detector1.create_or_get_account_index(screenshot)

        # Second run - new detector instance, same data directory
        detector2 = CharacterDetector(
            assets_path="assets",
            data_dir=str(data_dir),
            db_path=str(db_path)
        )

        # Should resolve same account from cache
        with patch.object(detector2, 'scan_visible_slots', return_value=[mock_result]):
            account_id2, account_hash2 = detector2.create_or_get_account_index(screenshot)

        assert account_id1 == account_id2
        assert account_hash1 == account_hash2

    def test_screenshot_saved_to_correct_slot_path(self, tmp_path):
        """Screenshots stored under data/accounts/{hash}/characters/{slot_index}.png."""
        from modules.character_detector import CharacterDetector
        from core.database import init_database

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "accounts.db"
        init_database(str(db_path))

        detector = CharacterDetector(
            assets_path="assets",
            data_dir=str(data_dir),
            db_path=str(db_path)
        )

        screenshot = np.random.randint(0, 255, (1440, 2560, 3), dtype=np.uint8)

        # Create multiple slot results
        mock_results = []
        for i in range(3):
            mock_result = Mock()
            mock_result.has_character = True
            mock_result.slot_index = i
            mock_result.roi = (904, 557, 1152, 624)
            mock_result.confidence = 0.95
            mock_results.append(mock_result)

        with patch.object(detector, 'scan_visible_slots', return_value=mock_results):
            account_id, account_hash = detector.create_or_get_account_index(screenshot)

        # Check all screenshots saved with correct naming
        chars_dir = data_dir / "accounts" / account_hash / "characters"

        for i in range(3):
            expected_path = chars_dir / f"{i}.png"
            assert expected_path.exists(), f"Screenshot for slot {i} not found at {expected_path}"

    def test_metadata_links_slot_to_screenshot_path(self, tmp_path):
        """Database metadata links slot index to image path and timestamp."""
        from modules.character_detector import CharacterDetector
        from core.database import init_database, list_characters_by_account

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "accounts.db"
        init_database(str(db_path))

        detector = CharacterDetector(
            assets_path="assets",
            data_dir=str(data_dir),
            db_path=str(db_path)
        )

        screenshot = np.random.randint(0, 255, (1440, 2560, 3), dtype=np.uint8)

        mock_result = Mock()
        mock_result.has_character = True
        mock_result.slot_index = 0
        mock_result.roi = (904, 557, 1152, 624)
        mock_result.confidence = 0.95

        with patch.object(detector, 'scan_visible_slots', return_value=[mock_result]):
            account_id, _ = detector.create_or_get_account_index(screenshot)

        # Check database has character record with correct metadata
        characters = list_characters_by_account(str(db_path), account_id)
        assert len(characters) == 1

        char = characters[0]
        assert char['slot_index'] == 0
        assert char['screenshot_path'].endswith("0.png")
        assert 'created_at' in char
        assert 'updated_at' in char

    def test_idempotent_upsert_for_slot_records(self, tmp_path):
        """Upserting same slot updates rather than duplicates."""
        from modules.character_detector import CharacterDetector
        from core.database import init_database, list_characters_by_account

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "accounts.db"
        init_database(str(db_path))

        detector = CharacterDetector(
            assets_path="assets",
            data_dir=str(data_dir),
            db_path=str(db_path)
        )

        screenshot1 = np.random.randint(0, 255, (1440, 2560, 3), dtype=np.uint8)
        screenshot2 = np.random.randint(0, 255, (1440, 2560, 3), dtype=np.uint8)

        mock_result = Mock()
        mock_result.has_character = True
        mock_result.slot_index = 0
        mock_result.roi = (904, 557, 1152, 624)
        mock_result.confidence = 0.95

        # First cache
        with patch.object(detector, 'scan_visible_slots', return_value=[mock_result]):
            account_id, _ = detector.create_or_get_account_index(screenshot1)

        # Get initial character count
        chars_before = list_characters_by_account(str(db_path), account_id)
        assert len(chars_before) == 1

        # Cache again (should update, not create new)
        with patch.object(detector, 'scan_visible_slots', return_value=[mock_result]):
            detector.cache_character_screenshot(account_id, 0, screenshot2)

        chars_after = list_characters_by_account(str(db_path), account_id)
        assert len(chars_after) == 1, "Upsert should not create duplicates"

        # updated_at should be different (or at least not earlier)
        assert chars_after[0]['updated_at'] >= chars_before[0]['updated_at']

    def test_stale_files_checked_on_load(self, tmp_path):
        """Cache load verifies file existence and handles missing files."""
        from modules.character_detector import CharacterDetector
        from core.database import init_database

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "accounts.db"
        init_database(str(db_path))

        detector = CharacterDetector(
            assets_path="assets",
            data_dir=str(data_dir),
            db_path=str(db_path)
        )

        screenshot = np.random.randint(0, 255, (1440, 2560, 3), dtype=np.uint8)

        mock_result = Mock()
        mock_result.has_character = True
        mock_result.slot_index = 0
        mock_result.roi = (904, 557, 1152, 624)
        mock_result.confidence = 0.95

        with patch.object(detector, 'scan_visible_slots', return_value=[mock_result]):
            account_id, account_hash = detector.create_or_get_account_index(screenshot)

        # Delete the screenshot file to simulate staleness
        chars_dir = data_dir / "accounts" / account_hash / "characters"
        screenshot_file = chars_dir / "0.png"
        screenshot_file.unlink()

        # Load cached characters should handle missing file gracefully
        cached = detector.load_cached_characters(account_id)

        # Should return empty or filtered list (no valid cached characters)
        assert isinstance(cached, list)


class TestLauncherIntegration:
    """Validate launcher workflow integration."""

    def test_discover_account_method_exists(self):
        """CharacterDetector has discover_account method for launcher."""
        from modules.character_detector import CharacterDetector

        assert hasattr(CharacterDetector, 'discover_account')

    def test_discover_account_returns_account_info(self, tmp_path):
        """discover_account returns account ID and hash for launcher."""
        from modules.character_detector import CharacterDetector
        from core.database import init_database

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "accounts.db"
        init_database(str(db_path))

        detector = CharacterDetector(
            assets_path="assets",
            data_dir=str(data_dir),
            db_path=str(db_path)
        )

        screenshot = np.random.randint(0, 255, (1440, 2560, 3), dtype=np.uint8)

        mock_result = Mock()
        mock_result.has_character = True
        mock_result.slot_index = 0
        mock_result.roi = (904, 557, 1152, 624)
        mock_result.confidence = 0.95

        with patch.object(detector, 'scan_visible_slots', return_value=[mock_result]):
            result = detector.discover_account(screenshot)

        assert result is not None
        assert 'account_id' in result
        assert 'account_hash' in result
        assert 'character_count' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
