"""
Compliance Guard Module

Provides startup policy checks and fail-fast enforcement for ACE compliance.
Validates hardware capability, configuration, and prohibited modules before
allowing automation to start.
"""

import sys
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass


class ComplianceError(Exception):
    """Raised when ACE compliance validation fails."""
    pass


@dataclass
class ComplianceReport:
    """Report of compliance validation results."""
    hardware_ok: bool
    config_ok: bool
    modules_ok: bool
    errors: List[str]

    @property
    def all_ok(self) -> bool:
        """Check if all validations passed."""
        return self.hardware_ok and self.config_ok and self.modules_ok


class ComplianceGuard:
    """
    ACE compliance guard with fail-fast validation.

    Performs startup checks to ensure:
    - Hardware capability is available and responsive
    - Configuration prohibits software injection paths
    - No forbidden memory/process manipulation modules are loaded

    Non-compliant environments are blocked from starting automation.
    """

    # Prohibited modules that indicate memory/process manipulation
    PROHIBITED_MODULES: Set[str] = {
        'pymem', 'pymem.process', 'ReadWriteMemory', 'mem_edit',
        'ctypes.windll.kernel32', 'ctypes.windll.user32',
        'win32process', 'win32con', 'win32gui.SendMessage',
    }

    def __init__(self):
        self.errors: List[str] = []

    def validate_all(self) -> ComplianceReport:
        """Run all compliance validations."""
        self.errors = []

        hardware_ok = self._validate_hardware()
        config_ok = self._validate_config()
        modules_ok = self._validate_modules()

        return ComplianceReport(
            hardware_ok=hardware_ok,
            config_ok=config_ok,
            modules_ok=modules_ok,
            errors=self.errors
        )

    def _validate_hardware(self) -> bool:
        """Validate hardware capability is available."""
        # TODO: Implement hardware validation
        return True

    def _validate_config(self) -> bool:
        """Validate configuration compliance."""
        # TODO: Implement config validation
        return True

    def _validate_modules(self) -> bool:
        """Validate no prohibited modules are loaded."""
        found = []
        for module in self.PROHIBITED_MODULES:
            if module in sys.modules:
                found.append(module)

        if found:
            self.errors.append(f"Prohibited modules detected: {found}")
            return False

        return True
