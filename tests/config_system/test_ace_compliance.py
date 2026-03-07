"""
ACE Compliance Tests

Tests for ACE (Anti-Cheat Engine) compliance enforcement.
Covers ACE-01 (hardware-only input), ACE-02 (timing jitter), ACE-03 (audit),
and ACE-04 (startup validation) requirements.
"""

import pytest
import json
import tempfile
import time
import statistics
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch


# =============================================================================
# Hardware Input Gateway Tests
# =============================================================================

class TestHardwareInputGateway:
    """Test hardware-only input gateway with policy enforcement."""

    def test_gateway_initializes_with_session_seed(self):
        """Gateway initializes with session-level random seed for jitter."""
        from core.hardware_input_gateway import HardwareInputGateway

        gateway = HardwareInputGateway(session_seed=12345)

        assert gateway._session_seed == 12345
        assert gateway._jitter is not None

    def test_gateway_requires_hardware_controller(self):
        """Gateway requires a hardware controller for initialization."""
        from core.hardware_input_gateway import HardwareInputGateway

        mock_controller = Mock()
        mock_controller.click = Mock()
        mock_controller.press = Mock()
        mock_controller.scroll = Mock()

        gateway = HardwareInputGateway(
            hardware_controller=mock_controller,
            session_seed=12345
        )

        assert gateway._hardware is mock_controller

    def test_gateway_click_routes_through_hardware(self):
        """Click action routes through hardware controller."""
        from core.hardware_input_gateway import HardwareInputGateway

        mock_controller = Mock()
        mock_controller.click = Mock()

        gateway = HardwareInputGateway(
            hardware_controller=mock_controller,
            session_seed=12345
        )

        gateway.click(100, 200)

        mock_controller.click.assert_called_once()
        args = mock_controller.click.call_args
        assert args[0][0] == 100
        assert args[0][1] == 200

    def test_gateway_press_routes_through_hardware(self):
        """Press action routes through hardware controller."""
        from core.hardware_input_gateway import HardwareInputGateway

        mock_controller = Mock()
        mock_controller.press = Mock()

        gateway = HardwareInputGateway(
            hardware_controller=mock_controller,
            session_seed=12345
        )

        gateway.press('alt+u')

        mock_controller.press.assert_called_once_with('alt+u')

    def test_gateway_scroll_routes_through_hardware(self):
        """Scroll action routes through hardware controller."""
        from core.hardware_input_gateway import HardwareInputGateway

        mock_controller = Mock()
        mock_controller.scroll = Mock()

        gateway = HardwareInputGateway(
            hardware_controller=mock_controller,
            session_seed=12345
        )

        gateway.scroll('down', 3)

        mock_controller.scroll.assert_called_once_with('down', 3)

    def test_gateway_rejects_software_input_paths(self):
        """Gateway rejects non-hardware input paths with policy violation."""
        from core.hardware_input_gateway import HardwareInputGateway, InputPolicyViolation

        gateway = HardwareInputGateway(
            hardware_controller=Mock(),
            session_seed=12345
        )

        # Attempt to use software-only path (simulated)
        with pytest.raises(InputPolicyViolation) as exc_info:
            gateway._validate_hardware_only(use_software=True)

        assert "software input path blocked" in str(exc_info.value).lower()

    def test_gateway_audit_logs_blocked_requests(self):
        """Gateway writes audit event when blocking non-compliant request."""
        from core.hardware_input_gateway import HardwareInputGateway, InputPolicyViolation

        mock_controller = Mock()
        mock_audit_logger = Mock()

        gateway = HardwareInputGateway(
            hardware_controller=mock_controller,
            session_seed=12345,
            audit_logger=mock_audit_logger
        )

        try:
            gateway._validate_hardware_only(use_software=True)
        except InputPolicyViolation:
            pass

        mock_audit_logger.log_policy_violation.assert_called_once()

    def test_gateway_preserves_current_action_api(self):
        """Gateway maintains same API as existing controller for compatibility."""
        from core.hardware_input_gateway import HardwareInputGateway

        mock_controller = Mock()
        gateway = HardwareInputGateway(
            hardware_controller=mock_controller,
            session_seed=12345
        )

        # Verify all expected methods exist
        assert hasattr(gateway, 'click')
        assert hasattr(gateway, 'press')
        assert hasattr(gateway, 'scroll')
        assert hasattr(gateway, 'wait')


# =============================================================================
# Compliance Guard Tests
# =============================================================================

class TestComplianceGuard:
    """Test compliance guard fail-fast checks at startup."""

    def test_guard_validates_hardware_capability(self):
        """Guard validates hardware capability before allowing startup."""
        from core.compliance_guard import ComplianceGuard, ComplianceError

        guard = ComplianceGuard()

        # Mock hardware check passing
        mock_hardware = Mock()
        mock_hardware.handshake = Mock(return_value=True)

        result = guard.validate_hardware(mock_hardware)

        assert result is True

    def test_guard_fails_fast_on_missing_hardware(self):
        """Guard fails fast when hardware capability is missing."""
        from core.compliance_guard import ComplianceGuard, ComplianceError

        guard = ComplianceGuard()

        # Mock hardware check failing
        mock_hardware = Mock()
        mock_hardware.handshake = Mock(return_value=False)

        with pytest.raises(ComplianceError) as exc_info:
            guard.validate_hardware(mock_hardware, fail_fast=True)

        assert "hardware" in str(exc_info.value).lower()

    def test_guard_validates_no_memory_injection_modules(self):
        """Guard checks for forbidden memory/process injection modules."""
        from core.compliance_guard import ComplianceGuard, ComplianceError

        guard = ComplianceGuard()

        # Simulate forbidden module detected
        forbidden_modules = ['pymem', 'pymemprocess', 'memory_editor']

        with pytest.raises(ComplianceError) as exc_info:
            guard.validate_prohibited_modules(forbidden_modules)

        assert "prohibited" in str(exc_info.value).lower() or "forbidden" in str(exc_info.value).lower()

    def test_guard_validates_no_software_injection_flags(self):
        """Guard validates absence of software injection feature flags."""
        from core.compliance_guard import ComplianceGuard, ComplianceError

        guard = ComplianceGuard()

        config_with_injection = {
            'use_software_input': True,
            'hardware_only': False
        }

        with pytest.raises(ComplianceError) as exc_info:
            guard.validate_configuration(config_with_injection)

        assert "software" in str(exc_info.value).lower() or "configuration" in str(exc_info.value).lower()

    def test_guard_passes_with_compliant_config(self):
        """Guard passes when configuration is ACE compliant."""
        from core.compliance_guard import ComplianceGuard

        guard = ComplianceGuard()

        compliant_config = {
            'use_hardware_input': True,
            'hardware_only': True,
            'timing_jitter_enabled': True
        }

        result = guard.validate_configuration(compliant_config)

        assert result is True

    def test_guard_full_startup_validation(self):
        """Guard performs complete startup validation sequence."""
        from core.compliance_guard import ComplianceGuard

        guard = ComplianceGuard()

        mock_hardware = Mock()
        mock_hardware.handshake = Mock(return_value=True)

        config = {'hardware_only': True}

        result = guard.validate_startup(mock_hardware, config)

        assert result is True


# =============================================================================
# Timing Jitter Policy Tests
# =============================================================================

class TestTimingJitterPolicy:
    """Test bounded timing jitter policy for hardware actions."""

    def test_jitter_generator_uses_session_seed(self):
        """Jitter generator uses session seed for reproducibility."""
        from core.hardware_input_gateway import JitterGenerator

        gen1 = JitterGenerator(session_seed=12345)
        gen2 = JitterGenerator(session_seed=12345)

        values1 = [gen1.next_delay(1000) for _ in range(10)]
        values2 = [gen2.next_delay(1000) for _ in range(10)]

        assert values1 == values2

    def test_jitter_stays_within_plus_minus_20_percent(self):
        """Jitter values stay within ±20% bounds."""
        from core.hardware_input_gateway import JitterGenerator

        gen = JitterGenerator(session_seed=12345)

        base_delay = 1000  # 1 second
        min_expected = 800  # -20%
        max_expected = 1200  # +20%

        for _ in range(100):
            delay = gen.next_delay(base_delay)
            assert min_expected <= delay <= max_expected

    def test_jitter_distribution_is_truncated_normal(self):
        """Jitter follows truncated normal distribution (majority near mean)."""
        from core.hardware_input_gateway import JitterGenerator

        gen = JitterGenerator(session_seed=12345)

        base_delay = 1000
        samples = [gen.next_delay(base_delay) for _ in range(1000)]

        # Calculate statistics
        mean = statistics.mean(samples)
        std_dev = statistics.stdev(samples)

        # Mean should be close to base_delay (within 5%)
        assert abs(mean - base_delay) < base_delay * 0.05

        # Most values should be within 1 standard deviation (68% rule approx)
        within_one_std = sum(1 for s in samples if abs(s - mean) < std_dev)
        assert within_one_std > 500  # At least 50% within 1 std dev

    def test_jitter_applied_to_click_actions(self):
        """Jitter is applied to click action delays."""
        from core.hardware_input_gateway import HardwareInputGateway

        mock_controller = Mock()
        mock_controller.click = Mock()

        gateway = HardwareInputGateway(
            hardware_controller=mock_controller,
            session_seed=12345,
            enable_jitter=True
        )

        # Mock the jitter generator
        gateway._jitter = Mock()
        gateway._jitter.next_delay = Mock(return_value=1100)

        gateway.click(100, 200, base_delay_ms=1000)

        # Verify jitter was consulted
        gateway._jitter.next_delay.assert_called_once_with(1000)

    def test_jitter_applied_to_press_actions(self):
        """Jitter is applied to press action delays."""
        from core.hardware_input_gateway import HardwareInputGateway

        mock_controller = Mock()
        mock_controller.press = Mock()

        gateway = HardwareInputGateway(
            hardware_controller=mock_controller,
            session_seed=12345,
            enable_jitter=True
        )

        gateway._jitter = Mock()
        gateway._jitter.next_delay = Mock(return_value=900)

        gateway.press('enter', base_delay_ms=1000)

        gateway._jitter.next_delay.assert_called_once_with(1000)

    def test_jitter_applied_to_scroll_actions(self):
        """Jitter is applied to scroll action delays."""
        from core.hardware_input_gateway import HardwareInputGateway

        mock_controller = Mock()
        mock_controller.scroll = Mock()

        gateway = HardwareInputGateway(
            hardware_controller=mock_controller,
            session_seed=12345,
            enable_jitter=True
        )

        gateway._jitter = Mock()
        gateway._jitter.next_delay = Mock(return_value=1050)

        gateway.scroll('down', 3, base_delay_ms=1000)

        gateway._jitter.next_delay.assert_called_once_with(1000)

    def test_wait_image_polling_unaffected_by_jitter(self):
        """wait_image polling cadence is not affected by jitter policy."""
        from core.hardware_input_gateway import HardwareInputGateway

        mock_controller = Mock()

        gateway = HardwareInputGateway(
            hardware_controller=mock_controller,
            session_seed=12345,
            enable_jitter=True
        )

        # Polling interval should remain constant
        poll_interval = gateway.get_polling_interval(base_ms=50)

        assert poll_interval == 50


# =============================================================================
# Integration Tests
# =============================================================================

class TestACEComplianceIntegration:
    """Integration tests for ACE compliance components."""

    def test_gateway_uses_guard_for_validation(self):
        """Gateway uses compliance guard for policy validation."""
        from core.hardware_input_gateway import HardwareInputGateway
        from core.compliance_guard import ComplianceGuard

        mock_controller = Mock()
        mock_guard = Mock(spec=ComplianceGuard)
        mock_guard.validate_hardware = Mock(return_value=True)

        gateway = HardwareInputGateway(
            hardware_controller=mock_controller,
            session_seed=12345,
            compliance_guard=mock_guard
        )

        # Guard should be called during initialization or operation
        assert gateway._compliance_guard is mock_guard

    def test_full_compliance_pipeline(self):
        """Complete compliance pipeline from validation to execution."""
        from core.hardware_input_gateway import HardwareInputGateway
        from core.compliance_guard import ComplianceGuard

        # Setup
        mock_controller = Mock()
        mock_controller.handshake = Mock(return_value=True)
        mock_controller.click = Mock()

        guard = ComplianceGuard()

        # Validate startup
        assert guard.validate_startup(mock_controller, {'hardware_only': True})

        # Create gateway
        gateway = HardwareInputGateway(
            hardware_controller=mock_controller,
            session_seed=12345,
            compliance_guard=guard
        )

        # Execute action
        gateway.click(100, 200)

        mock_controller.click.assert_called_once()
