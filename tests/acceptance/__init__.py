"""
Acceptance testing module for LostarkBot.

Provides comprehensive acceptance testing infrastructure including:
- OverlayWindow: Transparent UI for test progress display
- TestLogger: Structured logging with JSON session data
- ScreenshotArchiver: Automated screenshot capture and archiving
- AcceptanceTestRunner: Main orchestrator for multi-phase acceptance tests
"""

from tests.acceptance.overlay import OverlayWindow, create_overlay
from tests.acceptance.test_logger import TestLogger
from tests.acceptance.screenshot_archiver import ScreenshotArchiver

try:
    from tests.acceptance.acceptance_test import AcceptanceTestRunner
except ImportError:
    # AcceptanceTestRunner may not be available if dependencies are missing
    AcceptanceTestRunner = None

__all__ = [
    'OverlayWindow',
    'create_overlay',
    'TestLogger',
    'ScreenshotArchiver',
    'AcceptanceTestRunner',
]
