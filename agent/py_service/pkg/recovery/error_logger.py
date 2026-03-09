"""
Error Logger Module

Provides structured JSONL logging for error events with failure evidence capture.
Implements ERR-04 requirements for complete debug evidence.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from .orchestrator import ErrorKind, ErrorContext


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
        timestamp = datetime.now(timezone.utc).isoformat()

        log_entry = {
            "timestamp": timestamp,
            "error_kind": error_kind.value if hasattr(error_kind, 'value') else str(error_kind),
            "message": message,
            "context": context.to_dict() if hasattr(context, 'to_dict') else str(context)
        }

        # Daily log file
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self.log_dir / f"errors_{date_str}.jsonl"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        return str(log_file)
