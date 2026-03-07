"""
Multi-Account Test Fixtures

Provides shared fixtures for multi-account testing including:
- Temporary data directories
- Mock CharacterDetector
- Sample account contexts
- AccountManager and ProgressTracker instances
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock

from core.account_manager import AccountManager, AccountContext
from core.progress_tracker import ProgressTracker
from core.account_switcher import AccountSwitcher


@pytest.fixture
def temp_data_dir(tmp_path):
    """Provide a temporary directory for test databases."""
    return tmp_path / "test_data"


@pytest.fixture
def sample_account_hash():
    """Provide a consistent test account hash."""
    return "abc123def456"


@pytest.fixture
def sample_account_hash_b():
    """Provide a second consistent test account hash."""
    return "xyz789uvw012"


@pytest.fixture
def mock_detector():
    """Provide a mock CharacterDetector for testing."""
    detector = MagicMock()

    # Configure discover_account to return a mock result
    mock_result = MagicMock()
    mock_result.account_hash = "abc123def456"
    mock_result.character_count = 6
    detector.discover_account.return_value = mock_result

    return detector


@pytest.fixture
def mock_detector_b():
    """Provide a mock CharacterDetector that returns account B."""
    detector = MagicMock()

    mock_result = MagicMock()
    mock_result.account_hash = "xyz789uvw012"
    mock_result.character_count = 9
    detector.discover_account.return_value = mock_result

    return detector


@pytest.fixture
def sample_screenshot():
    """Provide a dummy screenshot for testing."""
    # Create a small dummy image (100x100 RGB)
    return np.zeros((100, 100, 3), dtype=np.uint8)


@pytest.fixture
def account_manager(temp_data_dir, mock_detector):
    """Provide an AccountManager with temp directory and mock detector."""
    return AccountManager(
        base_data_dir=str(temp_data_dir),
        detector=mock_detector
    )


@pytest.fixture
def progress_tracker(temp_data_dir):
    """Provide a ProgressTracker with temp database."""
    db_path = temp_data_dir / "test_progress.db"
    return ProgressTracker(str(db_path))


@pytest.fixture
def mock_workflow_executor():
    """Provide a mock WorkflowExecutor for testing."""
    executor = MagicMock()
    executor._stop_event = MagicMock()
    executor._stop_event.set.return_value = True
    executor._stop_event.wait.return_value = True
    return executor


@pytest.fixture
def account_switcher(account_manager, mock_workflow_executor):
    """Provide an AccountSwitcher with mock executor."""
    switcher = AccountSwitcher(account_manager)
    switcher.attach_workflow(mock_workflow_executor)
    return switcher


@pytest.fixture
def sample_context_a(temp_data_dir):
    """Provide a sample AccountContext for account A."""
    db_path = temp_data_dir / "accounts" / "abc123" / "progress.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tracker = ProgressTracker(str(db_path))

    return AccountContext(
        account_hash="abc123def456",
        account_id=1,
        character_count=6,
        db_path=str(db_path),
        progress_tracker=tracker
    )


@pytest.fixture
def sample_context_b(temp_data_dir):
    """Provide a sample AccountContext for account B."""
    db_path = temp_data_dir / "accounts" / "xyz789" / "progress.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tracker = ProgressTracker(str(db_path))

    return AccountContext(
        account_hash="xyz789uvw012",
        account_id=2,
        character_count=9,
        db_path=str(db_path),
        progress_tracker=tracker
    )
