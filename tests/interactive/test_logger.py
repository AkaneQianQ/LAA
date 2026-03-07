"""
Test Logger Module - JSON persistence for interactive test results.

This module provides TestLogger class for recording test execution results
to JSON files with timestamps and step-by-step feedback.
"""

import json
import os
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class StepResult:
    """Result of a single test step."""
    step_number: int
    instruction: str
    expected_result: str
    user_feedback: str  # "Y", "N", or "SKIP"
    timestamp: str  # ISO format
    notes: str = ""  # Optional user notes


@dataclass
class TestResult:
    """Complete test result with all steps."""
    test_id: str  # UUID or timestamp-based
    scenario_name: str
    start_time: str
    end_time: Optional[str]
    steps: List[StepResult] = field(default_factory=list)
    overall_result: str = "INCOMPLETE"  # "PASS", "FAIL", "INCOMPLETE"


class TestLogger:
    """
    Logger for interactive test results.

    Persists test results to JSON files with thread-safe atomic writes.
    File naming: {timestamp}_{scenario_name}_{test_id}.json
    """

    def __init__(self, log_dir: str = "logs/tests"):
        """
        Initialize TestLogger.

        Args:
            log_dir: Directory for test result JSON files.
                     Auto-created if not exists.
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._active_tests: dict[str, TestResult] = {}

    def _generate_test_id(self) -> str:
        """Generate unique test ID."""
        return f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def _get_filename(self, test_id: str, scenario_name: str) -> str:
        """Generate filename for test result."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_scenario = scenario_name.replace(' ', '_').replace('/', '_')
        return f"{timestamp}_{safe_scenario}_{test_id}.json"

    def _get_filepath(self, test_id: str) -> Optional[Path]:
        """Find filepath for existing test by ID."""
        for file_path in self.log_dir.glob(f"*_{test_id}.json"):
            return file_path
        return None

    def _atomic_write(self, file_path: Path, data: dict) -> None:
        """
        Atomically write JSON data to file.

        Writes to temp file then renames for thread safety.
        """
        temp_path = file_path.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp_path.replace(file_path)

    def start_test(self, scenario_name: str) -> str:
        """
        Begin a new test session.

        Args:
            scenario_name: Name of the test scenario.

        Returns:
            test_id: Unique identifier for this test session.
        """
        test_id = self._generate_test_id()
        start_time = datetime.now().isoformat()

        test_result = TestResult(
            test_id=test_id,
            scenario_name=scenario_name,
            start_time=start_time,
            end_time=None,
            steps=[],
            overall_result="INCOMPLETE"
        )

        with self._lock:
            self._active_tests[test_id] = test_result

        # Create initial file
        file_path = self.log_dir / self._get_filename(test_id, scenario_name)
        self._atomic_write(file_path, asdict(test_result))

        return test_id

    def log_step(self, test_id: str, step: StepResult) -> None:
        """
        Record a step result.

        Args:
            test_id: Test session ID from start_test().
            step: StepResult to record.

        Raises:
            KeyError: If test_id not found.
        """
        with self._lock:
            if test_id not in self._active_tests:
                raise KeyError(f"Test {test_id} not found")

            self._active_tests[test_id].steps.append(step)
            test_result = self._active_tests[test_id]

        # Write outside lock to minimize contention
        file_path = self._get_filepath(test_id)
        if file_path:
            self._atomic_write(file_path, asdict(test_result))

    def end_test(self, test_id: str, overall_result: str) -> None:
        """
        Finalize a test session.

        Args:
            test_id: Test session ID from start_test().
            overall_result: "PASS", "FAIL", or "INCOMPLETE".

        Raises:
            KeyError: If test_id not found.
        """
        end_time = datetime.now().isoformat()

        with self._lock:
            if test_id not in self._active_tests:
                raise KeyError(f"Test {test_id} not found")

            self._active_tests[test_id].end_time = end_time
            self._active_tests[test_id].overall_result = overall_result
            test_result = self._active_tests[test_id]

            # Remove from active tests
            del self._active_tests[test_id]

        # Write final result
        file_path = self._get_filepath(test_id)
        if file_path:
            self._atomic_write(file_path, asdict(test_result))

    def get_test_result(self, test_id: str) -> Optional[TestResult]:
        """
        Load test result from file.

        Args:
            test_id: Test session ID.

        Returns:
            TestResult if found, None otherwise.
        """
        # Check active tests first
        with self._lock:
            if test_id in self._active_tests:
                return self._active_tests[test_id]

        # Load from file
        file_path = self._get_filepath(test_id)
        if not file_path or not file_path.exists():
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Convert steps to StepResult objects
        steps = [StepResult(**step) for step in data.get('steps', [])]

        return TestResult(
            test_id=data['test_id'],
            scenario_name=data['scenario_name'],
            start_time=data['start_time'],
            end_time=data.get('end_time'),
            steps=steps,
            overall_result=data.get('overall_result', 'INCOMPLETE')
        )

    def list_tests(self) -> List[str]:
        """
        List all test result files.

        Returns:
            List of test IDs from all JSON files in log_dir.
        """
        test_ids = []
        for file_path in self.log_dir.glob("*.json"):
            # Extract test_id from filename: {timestamp}_{scenario}_{test_id}.json
            parts = file_path.stem.split('_')
            if len(parts) >= 3:
                # Last part is the test_id (after timestamp and scenario)
                test_id = parts[-1]
                test_ids.append(test_id)
        return test_ids


# =============================================================================
# Unit Tests
# =============================================================================

import pytest


class TestTestLogger:
    """Unit tests for TestLogger class."""

    @pytest.fixture
    def temp_log_dir(self, tmp_path):
        """Provide temporary log directory."""
        return tmp_path / "test_logs"

    @pytest.fixture
    def logger(self, temp_log_dir):
        """Provide TestLogger instance with temp directory."""
        return TestLogger(str(temp_log_dir))

    def test_start_test_creates_file(self, logger, temp_log_dir):
        """Test that start_test creates a JSON file."""
        test_id = logger.start_test("test_scenario")

        # Check that a file was created
        files = list(temp_log_dir.glob("*.json"))
        assert len(files) == 1
        assert test_id in files[0].name

    def test_log_step_records_data(self, logger):
        """Test that log_step records step data correctly."""
        test_id = logger.start_test("test_scenario")
        step = StepResult(
            step_number=1,
            instruction="Test instruction",
            expected_result="Expected",
            user_feedback="Y",
            timestamp="2026-03-08T14:30:00"
        )
        logger.log_step(test_id, step)

        result = logger.get_test_result(test_id)
        assert len(result.steps) == 1
        assert result.steps[0].user_feedback == "Y"
        assert result.steps[0].instruction == "Test instruction"

    def test_end_test_sets_result(self, logger):
        """Test that end_test finalizes test with result."""
        test_id = logger.start_test("test_scenario")
        logger.end_test(test_id, "PASS")

        result = logger.get_test_result(test_id)
        assert result.overall_result == "PASS"
        assert result.end_time is not None

    def test_multiple_steps(self, logger):
        """Test recording multiple steps."""
        test_id = logger.start_test("multi_step_scenario")

        for i in range(3):
            step = StepResult(
                step_number=i + 1,
                instruction=f"Step {i + 1}",
                expected_result=f"Expected {i + 1}",
                user_feedback="Y" if i < 2 else "N",
                timestamp=f"2026-03-08T14:30:0{i}"
            )
            logger.log_step(test_id, step)

        logger.end_test(test_id, "FAIL")

        result = logger.get_test_result(test_id)
        assert len(result.steps) == 3
        assert result.steps[2].user_feedback == "N"
        assert result.overall_result == "FAIL"

    def test_list_tests(self, logger):
        """Test listing all test files."""
        test_ids = [logger.start_test(f"scenario_{i}") for i in range(3)]

        listed = logger.list_tests()
        assert len(listed) == 3
        for test_id in test_ids:
            assert test_id.split('_')[-1] in listed

    def test_invalid_test_id_raises(self, logger):
        """Test that invalid test_id raises KeyError."""
        step = StepResult(
            step_number=1,
            instruction="Test",
            expected_result="Expected",
            user_feedback="Y",
            timestamp="2026-03-08T14:30:00"
        )
        with pytest.raises(KeyError):
            logger.log_step("invalid_id", step)

    def test_skip_feedback(self, logger):
        """Test SKIP feedback recording."""
        test_id = logger.start_test("test_scenario")
        step = StepResult(
            step_number=1,
            instruction="Test instruction",
            expected_result="Expected",
            user_feedback="SKIP",
            timestamp="2026-03-08T14:30:00",
            notes="User skipped this step"
        )
        logger.log_step(test_id, step)

        result = logger.get_test_result(test_id)
        assert result.steps[0].user_feedback == "SKIP"
        assert result.steps[0].notes == "User skipped this step"
