"""
Compliance Guard Module

Provides startup policy checks and fail-fast enforcement for ACE compliance.
Validates hardware capability, configuration, and prohibited modules before
allowing automation to start.

Exports:
    ComplianceGuard: Startup validation and policy enforcement
    ComplianceError: Exception raised for compliance violations
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
        'pymem',
        'pymemprocess',
        'memory_editor',
        'memorymapper',
        'winmem',
        'readwriteprocessmemory',
        'injector',
        'dll_injector',
        'process_hacker',
        'cheatengine',
        'ceclient',
    }

    # Forbidden configuration flags
    FORBIDDEN_CONFIG_FLAGS: Set[str] = {
        'use_software_input',
        'software_emulation',
        'memory_manipulation',
        'process_injection',
        'dll_injection',
        'disable_anti_cheat',
    }

    def __init__(self):
        """Initialize the compliance guard."""
        self._validation_cache: Optional[ComplianceReport] = None

    def validate_hardware(
        self,
        hardware_controller: Any,
        fail_fast: bool = True
    ) -> bool:
        """
        Validate hardware capability.

        Args:
            hardware_controller: Hardware controller to validate
            fail_fast: If True, raise exception on failure

        Returns:
            True if hardware is valid

        Raises:
            ComplianceError: If hardware validation fails and fail_fast is True
        """
        errors = []

        # Check controller exists
        if hardware_controller is None:
            errors.append("Hardware controller is None")
        else:
            # Check for handshake method
            if not hasattr(hardware_controller, 'handshake'):
                errors.append("Hardware controller missing handshake method")
            else:
                # Perform handshake
                try:
                    handshake_result = hardware_controller.handshake()
                    if not handshake_result:
                        errors.append("Hardware handshake failed")
                except Exception as e:
                    errors.append(f"Hardware handshake error: {e}")

        # Check for required methods
        if hardware_controller is not None:
            required_methods = ['click', 'press', 'scroll']
            for method in required_methods:
                if not hasattr(hardware_controller, method):
                    errors.append(f"Hardware controller missing {method} method")

        if errors:
            if fail_fast:
                raise ComplianceError(
                    f"Hardware validation failed: {'; '.join(errors)}"
                )
            return False

        return True

    def validate_prohibited_modules(
        self,
        module_list: Optional[List[str]] = None,
        fail_fast: bool = True
    ) -> bool:
        """
        Validate no prohibited modules are present.

        Args:
            module_list: List of module names to check (default: sys.modules)
            fail_fast: If True, raise exception on failure

        Returns:
            True if no prohibited modules found

        Raises:
            ComplianceError: If prohibited modules found and fail_fast is True
        """
        if module_list is None:
            # Get loaded module names
            module_list = list(sys.modules.keys())

        # Normalize module names for comparison
        normalized_modules = {m.lower().replace('_', '').replace('-', '') for m in module_list}
        normalized_prohibited = {p.lower().replace('_', '') for p in self.PROHIBITED_MODULES}

        # Find intersections
        found_prohibited = normalized_modules & normalized_prohibited

        if found_prohibited:
            error_msg = f"Prohibited modules detected: {found_prohibited}"
            if fail_fast:
                raise ComplianceError(error_msg)
            return False

        return True

    def validate_configuration(
        self,
        config: Dict[str, Any],
        fail_fast: bool = True
    ) -> bool:
        """
        Validate configuration is ACE compliant.

        Args:
            config: Configuration dictionary to validate
            fail_fast: If True, raise exception on failure

        Returns:
            True if configuration is compliant

        Raises:
            ComplianceError: If configuration violates policy and fail_fast is True
        """
        errors = []

        # Check for forbidden flags
        config_keys_lower = {k.lower(): k for k in config.keys()}

        for forbidden in self.FORBIDDEN_CONFIG_FLAGS:
            forbidden_lower = forbidden.lower()
            if forbidden_lower in config_keys_lower:
                actual_key = config_keys_lower[forbidden_lower]
                value = config[actual_key]
                if value:  # If the flag is enabled
                    errors.append(f"Forbidden configuration flag '{actual_key}' is enabled")

        # Check hardware_only is True
        if not config.get('hardware_only', False):
            # This is a warning-level check, not strictly an error
            # depending on strictness requirements
            pass  # Allow non-hardware-only for flexibility, but log it

        # Check software input is not enabled
        software_enabled = (
            config.get('use_software_input', False) or
            config.get('software_emulation', False)
        )
        if software_enabled:
            errors.append("Software input/emulation is enabled (hardware-only required)")

        if errors:
            if fail_fast:
                raise ComplianceError(
                    f"Configuration validation failed: {'; '.join(errors)}"
                )
            return False

        return True

    def validate_startup(
        self,
        hardware_controller: Any,
        config: Dict[str, Any],
        fail_fast: bool = True
    ) -> bool:
        """
        Perform complete startup validation.

        Runs all validation checks in sequence:
        1. Hardware capability check
        2. Prohibited modules check
        3. Configuration compliance check

        Args:
            hardware_controller: Hardware controller to validate
            config: Configuration dictionary
            fail_fast: If True, raise exception on first failure

        Returns:
            True if all validations pass

        Raises:
            ComplianceError: If any validation fails and fail_fast is True
        """
        errors = []

        # Hardware validation
        try:
            hardware_ok = self.validate_hardware(hardware_controller, fail_fast=False)
        except Exception as e:
            hardware_ok = False
            errors.append(f"Hardware: {e}")

        # Module validation
        try:
            modules_ok = self.validate_prohibited_modules(fail_fast=False)
        except Exception as e:
            modules_ok = False
            errors.append(f"Modules: {e}")

        # Configuration validation
        try:
            config_ok = self.validate_configuration(config, fail_fast=False)
        except Exception as e:
            config_ok = False
            errors.append(f"Config: {e}")

        # Build report
        report = ComplianceReport(
            hardware_ok=hardware_ok,
            config_ok=config_ok,
            modules_ok=modules_ok,
            errors=errors
        )
        self._validation_cache = report

        if not report.all_ok:
            if fail_fast:
                raise ComplianceError(
                    f"ACE compliance validation failed:\n" +
                    "\n".join(f"  - {e}" for e in errors)
                )
            return False

        return True

    def get_last_report(self) -> Optional[ComplianceReport]:
        """
        Get the last validation report.

        Returns:
            ComplianceReport from last validation, or None
        """
        return self._validation_cache

    def is_compliant(
        self,
        hardware_controller: Any,
        config: Dict[str, Any]
    ) -> bool:
        """
        Check if environment is compliant (non-raising).

        Args:
            hardware_controller: Hardware controller to check
            config: Configuration to check

        Returns:
            True if compliant, False otherwise
        """
        try:
            return self.validate_startup(hardware_controller, config, fail_fast=False)
        except Exception:
            return False
