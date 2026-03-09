#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pytest Configuration for FerrumBot Tests

Provides shared fixtures and command-line options for all tests.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Global flags (set via command-line options)
HARDWARE_MODE = False
STARTUP_DELAY_SECONDS = 3


def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--hardware",
        action="store_true",
        default=False,
        help="Enable hardware mode with real Ferrum device"
    )
    parser.addoption(
        "--delay",
        type=int,
        default=3,
        help="Startup delay in seconds (default: 3)"
    )


def pytest_configure(config):
    """Configure global settings based on pytest options."""
    global HARDWARE_MODE, STARTUP_DELAY_SECONDS
    HARDWARE_MODE = config.getoption("--hardware")
    STARTUP_DELAY_SECONDS = config.getoption("--delay")
