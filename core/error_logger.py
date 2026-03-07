"""
Error Logger Module

Provides structured JSONL logging for error events with failure evidence capture.
Implements ERR-04 requirements for complete debug evidence.

Exports:
    ErrorLogger: Structured JSONL logger with daily file partitioning
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from core.error_recovery import ErrorKind, ErrorContext


class ErrorLogger:
    """
    Structured JSONL error logger with daily file partitioning.

    Logs error events with complete context for debugging and auditing.
    Creates daily log files under the configured log directory.
    """

    def __init__(self, log_dir: str = "logs/errors"):
        """
        Initialize the error logger.

        Args:
            log_dir: Directory for log files (created if not exists)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_error(
        self,
        error_kind: ErrorKind,
        message: str,
        context: ErrorContext
    ) -> str:
        """
        Log an error event as JSONL.

        Args:
            error_kind: Classification of the error
            message: Human-readable error message
            context: Error context with all metadata

        Returns:
            Path to the log file written
        """
        # Build log record with required fields
        record = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "phase": context.phase,
            "step_id": context.step_id,
            "error_kind": error_kind.value,
            "message": message,
            "attempt": context.attempt,
            "account": context.account_id,
            "screenshot_path": context.screenshot_path,
            "context": context.detail
        }

        # Determine log file path (daily partitioning)
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"errors_{today}.jsonl"

        # Append to log file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # Console summary (concise)
        print(f"[ERROR] {error_kind.value}: {message} (step={context.step_id}, attempt={context.attempt})")

        return str(log_file)

    def log_failure_with_screenshot(
        self,
        error_kind: ErrorKind,
        message: str,
        context: ErrorContext,
        screenshot_data: Optional[Any] = None
    ) -> str:
        """
        Log an error with screenshot capture.

        Args:
            error_kind: Classification of the error
            message: Human-readable error message
            context: Error context
            screenshot_data: Optional screenshot data to save

        Returns:
            Path to the log file written
        """
        # Capture screenshot if data provided
        if screenshot_data is not None:
            screenshot_path = self._save_screenshot(screenshot_data, context.step_id)
            context.screenshot_path = screenshot_path

        return self.log_error(error_kind, message, context)

    def _save_screenshot(self, screenshot_data: Any, step_id: str) -> str:
        """
        Save screenshot to disk and return path.

        Args:
            screenshot_data: Screenshot image data
            step_id: Current step ID for filename

        Returns:
            Path to saved screenshot
        """
        # Create screenshots subdirectory
        screenshot_dir = self.log_dir / "screenshots"
        screenshot_dir.mkdir(exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{step_id}_{timestamp}.png"
        screenshot_path = screenshot_dir / filename

        # Save screenshot (implementation depends on data type)
        try:
            import cv2
            if hasattr(screenshot_data, 'shape'):
                cv2.imwrite(str(screenshot_path), screenshot_data)
        except Exception:
            # If screenshot save fails, return None path
            return None

        return str(screenshot_path)

    def get_log_file_for_date(self, date: Optional[datetime] = None) -> Path:
        """
        Get log file path for a specific date.

        Args:
            date: Date to get log file for (default: today)

        Returns:
            Path to log file
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")
        return self.log_dir / f"errors_{date_str}.jsonl"
