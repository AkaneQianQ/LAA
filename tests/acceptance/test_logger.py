"""
Structured test logger for acceptance tests.

Provides logging to both file and console with structured session data in JSON format,
daily log rotation, phase tracking, screenshot tracking, and summary report generation.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class TestLogger:
    """Structured logger for acceptance tests with JSON session data and summary reports."""

    def __init__(self, output_dir: str = "logs/acceptance_tests"):
        """
        Initialize the test logger.

        Args:
            output_dir: Directory for log output (will be created if not exists)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate session timestamp and ID
        self.session_start = datetime.now()
        self.session_id = self.session_start.strftime("%Y%m%d_%H%M%S")

        # Create daily subdirectory for log rotation/partitioning
        self.daily_dir = self.output_dir / self.session_start.strftime("%Y-%m-%d")
        self.daily_dir.mkdir(parents=True, exist_ok=True)

        # Session data structure
        self.session_data: Dict[str, Any] = {
            "start_time": self.session_start.isoformat(),
            "end_time": None,
            "status": "running",
            "phases": [],
            "screenshots": []
        }

        # Current phase tracking
        self.current_phase: Optional[Dict[str, Any]] = None
        self.phase_counter = 0
        self.total_phases = 0

        # Setup logging
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Setup file and console logging handlers."""
        log_file = self.daily_dir / f"test_{self.session_id}.log"

        # Create formatter
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # File handler
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        # Configure logger
        self.logger = logging.getLogger(f"TestLogger_{self.session_id}")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Prevent propagation to avoid duplicate logs
        self.logger.propagate = False

    def set_total_phases(self, total: int) -> None:
        """
        Set the total number of phases for progress tracking.

        Args:
            total: Total number of phases in the test
        """
        self.total_phases = total

    def log_phase_start(self, phase_num: int, phase_name: str) -> None:
        """
        Log the start of a test phase.

        Args:
            phase_num: Phase number (1-indexed)
            phase_name: Human-readable phase name
        """
        self.phase_counter = phase_num

        # End any existing phase
        if self.current_phase is not None:
            self.log_phase_end("INTERRUPTED", 0)

        # Create new phase record
        self.current_phase = {
            "num": phase_num,
            "name": phase_name,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "status": "running",
            "duration_ms": 0,
            "details": []
        }

        # Log to file and console
        phase_indicator = f"[{phase_num}/{self.total_phases}]" if self.total_phases > 0 else f"[{phase_num}]"
        self.logger.info(f"[Phase {phase_indicator}] {phase_name} START")

    def log_phase_detail(self, message: str) -> None:
        """
        Log a detail message within the current phase.

        Args:
            message: Detail message to log
        """
        if self.current_phase is not None:
            self.current_phase["details"].append({
                "timestamp": datetime.now().isoformat(),
                "message": message
            })

        self.logger.info(message)

    def log_phase_end(self, status: str, duration_ms: Optional[int] = None) -> None:
        """
        Log the end of the current phase.

        Args:
            status: Phase status (e.g., "PASS", "FAIL", "SKIP")
            duration_ms: Phase duration in milliseconds (calculated if not provided)
        """
        if self.current_phase is None:
            self.logger.warning("log_phase_end called but no phase is active")
            return

        # Calculate duration if not provided
        end_time = datetime.now()
        start_time = datetime.fromisoformat(self.current_phase["start_time"])

        if duration_ms is None:
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Update phase record
        self.current_phase["end_time"] = end_time.isoformat()
        self.current_phase["status"] = status
        self.current_phase["duration_ms"] = duration_ms

        # Add to session data
        self.session_data["phases"].append(self.current_phase)

        # Log to file and console
        phase_num = self.current_phase["num"]
        phase_indicator = f"[{phase_num}/{self.total_phases}]" if self.total_phases > 0 else f"[{phase_num}]"
        self.logger.info(f"[Phase {phase_indicator}] END - {status} ({duration_ms}ms)")

        # Clear current phase
        self.current_phase = None

    def log_screenshot(self, filename: str, description: str) -> None:
        """
        Log a screenshot with description.

        Args:
            filename: Screenshot file path or name
            description: Human-readable description of the screenshot
        """
        screenshot_record = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename,
            "description": description
        }

        self.session_data["screenshots"].append(screenshot_record)

        # Also log to current phase if active
        if self.current_phase is not None:
            self.current_phase["details"].append({
                "timestamp": screenshot_record["timestamp"],
                "message": f"Screenshot: {description} ({filename})"
            })

        self.logger.info(f"Screenshot captured: {description}")

    def _save_session_json(self) -> None:
        """Save session data to JSON file."""
        json_file = self.daily_dir / "session.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self.session_data, f, indent=2, ensure_ascii=False)

    def _generate_summary(self) -> str:
        """Generate human-readable summary text."""
        lines = []
        lines.append("=" * 60)
        lines.append("ACCEPTANCE TEST SUMMARY")
        lines.append("=" * 60)
        lines.append("")

        # Session info
        lines.append(f"Session ID: {self.session_id}")
        lines.append(f"Start Time: {self.session_data['start_time']}")
        if self.session_data['end_time']:
            lines.append(f"End Time: {self.session_data['end_time']}")
        lines.append(f"Final Status: {self.session_data['status']}")
        lines.append("")

        # Phase summary
        lines.append("-" * 60)
        lines.append("PHASE RESULTS")
        lines.append("-" * 60)

        total_duration = 0
        for phase in self.session_data["phases"]:
            status_symbol = "✓" if phase["status"] == "PASS" else "✗" if phase["status"] == "FAIL" else "○"
            lines.append(f"{status_symbol} Phase {phase['num']}: {phase['name']}")
            lines.append(f"  Status: {phase['status']}")
            lines.append(f"  Duration: {phase['duration_ms']}ms")
            total_duration += phase["duration_ms"]

            if phase["details"]:
                lines.append("  Details:")
                for detail in phase["details"]:
                    lines.append(f"    - {detail['message']}")
            lines.append("")

        lines.append("-" * 60)
        lines.append(f"Total Duration: {total_duration}ms ({total_duration / 1000:.2f}s)")
        lines.append("-" * 60)
        lines.append("")

        # Screenshots
        if self.session_data["screenshots"]:
            lines.append("-" * 60)
            lines.append("SCREENSHOTS")
            lines.append("-" * 60)
            for screenshot in self.session_data["screenshots"]:
                lines.append(f"  [{screenshot['timestamp']}] {screenshot['filename']}")
                lines.append(f"    Description: {screenshot['description']}")
            lines.append("")

        lines.append("=" * 60)
        lines.append("END OF SUMMARY")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _save_summary(self) -> None:
        """Save summary to text file."""
        summary_file = self.daily_dir / "summary.txt"
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(self._generate_summary())

    def finalize(self, status: str) -> None:
        """
        Finalize the test session and save all outputs.

        Args:
            status: Final session status (e.g., "completed", "failed", "aborted")
        """
        # End any active phase
        if self.current_phase is not None:
            self.log_phase_end("INCOMPLETE")

        # Update session data
        self.session_data["end_time"] = datetime.now().isoformat()
        self.session_data["status"] = status

        # Save outputs
        self._save_session_json()
        self._save_summary()

        self.logger.info(f"Test session finalized with status: {status}")
        self.logger.info(f"Session data saved to: {self.daily_dir}")


# =============================================================================
# Self-Tests
# =============================================================================

def test_logger_creation():
    """Test logger initialization and directory creation."""
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp()
    try:
        logger = TestLogger(output_dir=temp_dir)

        # Check directory was created
        assert Path(temp_dir).exists()
        assert logger.output_dir.exists()
        assert logger.daily_dir.exists()

        # Check session data structure
        assert "start_time" in logger.session_data
        assert logger.session_data["status"] == "running"
        assert logger.session_data["phases"] == []
        assert logger.session_data["screenshots"] == []

        print("✓ test_logger_creation passed")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_phase_logging():
    """Test phase start, detail, and end logging."""
    import tempfile
    import shutil
    import time

    temp_dir = tempfile.mkdtemp()
    try:
        logger = TestLogger(output_dir=temp_dir)
        logger.set_total_phases(2)

        # Phase 1
        logger.log_phase_start(1, "环境检测")
        time.sleep(0.01)  # Small delay for duration testing
        logger.log_phase_detail("分辨率: 2560x1440")
        logger.log_phase_end("PASS")

        # Check phase was recorded
        assert len(logger.session_data["phases"]) == 1
        phase = logger.session_data["phases"][0]
        assert phase["num"] == 1
        assert phase["name"] == "环境检测"
        assert phase["status"] == "PASS"
        assert phase["duration_ms"] >= 0
        assert len(phase["details"]) == 1
        assert phase["details"][0]["message"] == "分辨率: 2560x1440"

        # Phase 2
        logger.log_phase_start(2, "功能测试")
        logger.log_phase_detail("Starting test")
        logger.log_phase_end("FAIL", duration_ms=500)

        assert len(logger.session_data["phases"]) == 2
        assert logger.session_data["phases"][1]["status"] == "FAIL"
        assert logger.session_data["phases"][1]["duration_ms"] == 500

        print("✓ test_phase_logging passed")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_screenshot_logging():
    """Test screenshot logging."""
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp()
    try:
        logger = TestLogger(output_dir=temp_dir)

        logger.log_screenshot("screenshot_001.png", "Initial state")
        logger.log_screenshot("screenshot_002.png", "After action")

        assert len(logger.session_data["screenshots"]) == 2
        assert logger.session_data["screenshots"][0]["filename"] == "screenshot_001.png"
        assert logger.session_data["screenshots"][0]["description"] == "Initial state"
        assert logger.session_data["screenshots"][1]["filename"] == "screenshot_002.png"

        print("✓ test_screenshot_logging passed")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_finalize():
    """Test session finalization and file output."""
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp()
    try:
        logger = TestLogger(output_dir=temp_dir)
        logger.set_total_phases(1)

        logger.log_phase_start(1, "Test Phase")
        logger.log_phase_detail("Some detail")
        logger.log_screenshot("test.png", "Test screenshot")
        logger.log_phase_end("PASS")

        logger.finalize("completed")

        # Check files were created
        assert (logger.daily_dir / "session.json").exists()
        assert (logger.daily_dir / "summary.txt").exists()
        # Log file has session ID in name
        log_files = list(logger.daily_dir.glob("test_*.log"))
        assert len(log_files) == 1

        # Check session.json content
        with open(logger.daily_dir / "session.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["status"] == "completed"
            assert "end_time" in data
            assert len(data["phases"]) == 1
            assert len(data["screenshots"]) == 1

        # Check summary.txt content
        with open(logger.daily_dir / "summary.txt", "r", encoding="utf-8") as f:
            summary = f.read()
            assert "ACCEPTANCE TEST SUMMARY" in summary
            assert "Test Phase" in summary
            assert "PASS" in summary
            assert "test.png" in summary

        print("✓ test_finalize passed")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_daily_rotation():
    """Test daily log rotation creates separate directories."""
    import tempfile
    import shutil
    import time

    temp_dir = tempfile.mkdtemp()
    try:
        # Create two loggers with delay to ensure different session IDs
        logger1 = TestLogger(output_dir=temp_dir)
        logger1.finalize("completed")

        time.sleep(1.1)  # Wait for timestamp to change

        logger2 = TestLogger(output_dir=temp_dir)
        logger2.finalize("completed")

        # Both should be in the same daily directory (same day)
        daily_dirs = [d for d in Path(temp_dir).iterdir() if d.is_dir()]
        assert len(daily_dirs) == 1  # Same day = same directory

        # Should have separate log files per session
        log_files = list(daily_dirs[0].glob("test_*.log"))
        assert len(log_files) == 2  # Two separate log files

        print("✓ test_daily_rotation passed")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_phase_interruption():
    """Test that starting a new phase ends the previous one."""
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp()
    try:
        logger = TestLogger(output_dir=temp_dir)
        logger.set_total_phases(2)

        # Start phase 1 but don't end it
        logger.log_phase_start(1, "Phase 1")
        logger.log_phase_detail("Detail 1")

        # Start phase 2 - should auto-end phase 1
        logger.log_phase_start(2, "Phase 2")

        # Phase 1 should be recorded as interrupted
        assert len(logger.session_data["phases"]) == 1
        assert logger.session_data["phases"][0]["status"] == "INTERRUPTED"

        # Complete phase 2
        logger.log_phase_end("PASS")

        assert len(logger.session_data["phases"]) == 2

        print("✓ test_phase_interruption passed")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("Running TestLogger self-tests...\n")
    test_logger_creation()
    test_phase_logging()
    test_screenshot_logging()
    test_finalize()
    test_daily_rotation()
    test_phase_interruption()
    print("\n✅ All self-tests passed!")
