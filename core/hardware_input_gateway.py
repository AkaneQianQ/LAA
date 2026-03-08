"""
Hardware Input Gateway Module

Provides ACE-compliant hardware-only input abstraction with policy enforcement,
audit logging, and bounded timing jitter. All input actions route through this
gateway to ensure compliance with anti-cheat requirements.

Exports:
    HardwareInputGateway: Single egress point for all hardware input actions
    JitterGenerator: Session-seeded truncated normal jitter generator
    InputPolicyViolation: Exception raised for policy violations
    AuditLogger: Audit trail for blocked/compliant requests
"""

import time
import random
import math
from typing import Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


class InputPolicyViolation(Exception):
    """Raised when an input request violates ACE compliance policy."""
    pass


class ComplianceError(Exception):
    """Raised when compliance validation fails."""
    pass


@dataclass
class AuditEvent:
    """Audit event for input policy enforcement."""
    timestamp: str
    event_type: str  # 'policy_violation', 'compliant_action', 'blocked_request'
    action: str
    detail: dict
    session_seed: int


class AuditLogger:
    """
    Audit trail logger for input policy events.

    Writes structured audit events for compliance verification and debugging.
    """

    def __init__(self, audit_dir: str = "logs/audit"):
        """
        Initialize the audit logger.

        Args:
            audit_dir: Directory for audit log files
        """
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def log_policy_violation(self, action: str, detail: dict, session_seed: int) -> str:
        """
        Log a policy violation event.

        Args:
            action: The action that was blocked
            detail: Additional context about the violation
            session_seed: Current session seed for traceability

        Returns:
            Path to the audit log file
        """
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            event_type='policy_violation',
            action=action,
            detail=detail,
            session_seed=session_seed
        )
        return self._write_event(event)

    def log_compliant_action(self, action: str, detail: dict, session_seed: int) -> str:
        """
        Log a compliant action (optional, for high-security environments).

        Args:
            action: The action that was executed
            detail: Additional context
            session_seed: Current session seed

        Returns:
            Path to the audit log file
        """
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            event_type='compliant_action',
            action=action,
            detail=detail,
            session_seed=session_seed
        )
        return self._write_event(event)

    def _write_event(self, event: AuditEvent) -> str:
        """Write audit event to daily log file."""
        import json

        today = datetime.now().strftime("%Y-%m-%d")
        audit_file = self.audit_dir / f"audit_{today}.jsonl"

        record = {
            "ts": event.timestamp,
            "type": event.event_type,
            "action": event.action,
            "detail": event.detail,
            "session_seed": event.session_seed
        }

        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return str(audit_file)


class JitterGenerator:
    """
    Session-seeded truncated normal jitter generator.

    Generates timing jitter within ±20% bounds using truncated normal distribution.
    Ensures reproducibility with the same session seed while maintaining
    human-like timing variance.
    """

    def __init__(self, session_seed: int):
        """
        Initialize the jitter generator.

        Args:
            session_seed: Session-level seed for reproducible jitter
        """
        self._session_seed = session_seed
        self._rng = random.Random(session_seed)

    def next_delay(self, base_delay_ms: float) -> float:
        """
        Generate next jittered delay.

        Uses truncated normal distribution to keep values within ±20% bounds.
        Most values cluster near the mean (human-like behavior).

        Args:
            base_delay_ms: Base delay in milliseconds

        Returns:
            Jittered delay in milliseconds
        """
        # ±20% bounds
        lower_bound = base_delay_ms * 0.8
        upper_bound = base_delay_ms * 1.2

        # Truncated normal: mean = base_delay, std_dev = 10% of base
        mean = base_delay_ms
        std_dev = base_delay_ms * 0.1

        # Generate truncated normal value
        while True:
            value = self._rng.gauss(mean, std_dev)
            if lower_bound <= value <= upper_bound:
                return value

    def reset(self) -> None:
        """Reset generator to initial state (for testing)."""
        self._rng = random.Random(self._session_seed)


class HardwareInputGateway:
    """
    ACE-compliant hardware input gateway.

    Single egress point for all input actions with:
    - Hardware-only policy enforcement
    - Bounded timing jitter (±20% truncated normal)
    - Audit logging for policy violations
    - Session-seeded reproducibility

    All click/press/scroll actions must route through this gateway.
    """

    def __init__(
        self,
        hardware_controller: Optional[Any] = None,
        session_seed: Optional[int] = None,
        enable_jitter: bool = True,
        audit_logger: Optional[AuditLogger] = None,
        compliance_guard: Optional[Any] = None
    ):
        """
        Initialize the hardware input gateway.

        Args:
            hardware_controller: Hardware controller with click/press/scroll methods
            session_seed: Seed for jitter reproducibility (default: random)
            enable_jitter: Whether to apply timing jitter
            audit_logger: Optional audit logger for policy events
            compliance_guard: Optional compliance guard for validation
        """
        self._hardware = hardware_controller
        self._session_seed = session_seed or random.randint(0, 2**31 - 1)
        self._enable_jitter = enable_jitter
        self._audit_logger = audit_logger or AuditLogger()
        self._compliance_guard = compliance_guard

        # Initialize jitter generator
        self._jitter = JitterGenerator(self._session_seed)

        # Track action statistics
        self._action_count = 0
        self._violation_count = 0

    def _validate_hardware_only(self, use_software: bool = False) -> None:
        """
        Validate that only hardware input paths are used.

        Args:
            use_software: Whether software path is requested (must be False)

        Raises:
            InputPolicyViolation: If software input is requested
        """
        if use_software:
            self._violation_count += 1
            detail = {
                "violation_type": "software_input_requested",
                "action_count": self._action_count,
                "violation_count": self._violation_count
            }
            self._audit_logger.log_policy_violation(
                "input_validation", detail, self._session_seed
            )
            raise InputPolicyViolation(
                "Software input path blocked by ACE compliance policy. "
                "Only hardware input is permitted."
            )

    def _apply_jitter(self, base_delay_ms: float) -> float:
        """
        Apply timing jitter if enabled.

        Args:
            base_delay_ms: Base delay in milliseconds

        Returns:
            Jittered delay in milliseconds
        """
        if not self._enable_jitter:
            return base_delay_ms
        return self._jitter.next_delay(base_delay_ms)

    def _sleep_with_jitter(self, base_delay_ms: float) -> None:
        """
        Sleep with jitter applied.

        Args:
            base_delay_ms: Base delay in milliseconds
        """
        jittered_delay = self._apply_jitter(base_delay_ms)
        # timing_jitter: ACE-02 compliance delay (not UI polling)
        time.sleep(jittered_delay / 1000.0)

    def click(self, x: int, y: int, base_delay_ms: float = 100) -> None:
        """
        Execute click action through hardware controller.

        Args:
            x: X coordinate
            y: Y coordinate
            base_delay_ms: Base delay after click (jittered)

        Raises:
            InputPolicyViolation: If hardware controller is not available
        """
        self._validate_hardware_only()

        if self._hardware is None:
            raise InputPolicyViolation("No hardware controller available for click action")

        self._action_count += 1

        # Execute through hardware
        self._hardware.click(x, y)

        # Apply jittered delay
        self._sleep_with_jitter(base_delay_ms)

    def press(self, key_name: str, base_delay_ms: float = 100) -> None:
        """
        Execute key press action through hardware controller.

        Args:
            key_name: Key name or combination (e.g., 'alt+u', 'enter')
            base_delay_ms: Base delay after press (jittered)

        Raises:
            InputPolicyViolation: If hardware controller is not available
        """
        self._validate_hardware_only()

        if self._hardware is None:
            raise InputPolicyViolation("No hardware controller available for press action")

        self._action_count += 1

        # Execute through hardware
        self._hardware.press(key_name)

        # Apply jittered delay
        self._sleep_with_jitter(base_delay_ms)

    def scroll(self, direction: str, ticks: int, base_delay_ms: float = 100) -> None:
        """
        Execute scroll action through hardware controller.

        Args:
            direction: 'up' or 'down'
            ticks: Number of scroll ticks
            base_delay_ms: Base delay after scroll (jittered)

        Raises:
            InputPolicyViolation: If hardware controller is not available
        """
        self._validate_hardware_only()

        if self._hardware is None:
            raise InputPolicyViolation("No hardware controller available for scroll action")

        self._action_count += 1

        # Execute through hardware
        self._hardware.scroll(direction, ticks)

        # Apply jittered delay
        self._sleep_with_jitter(base_delay_ms)

    def wait(self, duration_ms: float) -> None:
        """
        Wait for specified duration (jittered).

        Args:
            duration_ms: Base wait duration in milliseconds
        """
        self._action_count += 1
        self._sleep_with_jitter(duration_ms)

    def get_polling_interval(self, base_ms: float) -> float:
        """
        Get polling interval (unaffected by jitter policy).

        wait_image polling cadence should remain constant for reliable detection.

        Args:
            base_ms: Base polling interval in milliseconds

        Returns:
            Unmodified base polling interval
        """
        # Polling intervals are NOT jittered - they need to remain constant
        # for reliable image detection
        return base_ms

    def get_stats(self) -> dict:
        """
        Get gateway statistics.

        Returns:
            Dictionary with action count, violation count, session seed
        """
        return {
            "action_count": self._action_count,
            "violation_count": self._violation_count,
            "session_seed": self._session_seed,
            "jitter_enabled": self._enable_jitter
        }

    def reset_jitter(self) -> None:
        """Reset jitter generator (for testing reproducibility)."""
        self._jitter.reset()

    def move_mouse(self, x: int, y: int, base_delay_ms: float = 50) -> None:
        """
        移动鼠标到指定绝对坐标位置

        通过硬件控制器移动鼠标到绝对坐标位置。
        使用win32api获取当前位置并计算相对位移。

        Args:
            x: 目标X坐标（绝对位置）
            y: 目标Y坐标（绝对位置）
            base_delay_ms: 移动后的基础延迟（带抖动）

        Raises:
            InputPolicyViolation: 如果没有可用的硬件控制器
        """
        self._validate_hardware_only()

        if self._hardware is None:
            raise InputPolicyViolation("No hardware controller available for mouse move action")

        self._action_count += 1

        # 通过硬件执行绝对移动
        self._hardware.move_absolute(x, y)

        # 应用抖动延迟
        self._sleep_with_jitter(base_delay_ms)
