"""
Test Runner Module - Main test runner with scenario selection.

Provides the TestRunner class that integrates overlay, logger, and test flow
with scenario selection UI.
"""

import tkinter as tk
from typing import Optional
import logging
import threading

from tests.interactive.overlay import TestOverlay
from tests.interactive.test_logger import TestLogger
from tests.interactive.test_flow import TestFlow
from tests.interactive.scenarios import (
    ALL_SCENARIOS,
    list_scenario_names,
    get_scenario_by_name,
)

logger = logging.getLogger(__name__)


class TestRunner:
    """
    Main test runner that orchestrates the interactive test flow.

    Manages overlay UI, scenario selection, hotkey registration,
    and test execution lifecycle.
    """

    def __init__(self):
        """Initialize the test runner."""
        self.overlay: Optional[TestOverlay] = None
        self.logger: Optional[TestLogger] = None
        self.flow: Optional[TestFlow] = None
        self.root: Optional[tk.Tk] = None
        self.selected_scenario = None
        self._number_hotkeys_registered = False
        self._selection_callbacks = {}

    def initialize(self) -> None:
        """Initialize all components."""
        self.root = tk.Tk()
        self.root.withdraw()  # Hide root window

        self.overlay = TestOverlay(self.root)
        self.logger = TestLogger()
        self.flow = TestFlow(self.overlay, self.logger)

        logger.info("TestRunner initialized")

    def show_scenario_selection(self) -> None:
        """Show scenario selection UI in overlay."""
        scenario_names = list_scenario_names()

        if not scenario_names:
            self.overlay.set_instruction("错误: 没有可用的测试场景")
            return

        # Build selection text
        selection_text = "选择测试场景:\n"
        for i, name in enumerate(scenario_names):
            scenario = get_scenario_by_name(name)
            desc = scenario.description if scenario else name
            selection_text += f"{i+1}. {desc}\n"

        selection_text += f"\n按数字键 1-{len(scenario_names)} 选择"

        self.overlay.set_instruction(selection_text)

        # Register number key hotkeys for selection
        self._register_selection_hotkeys(scenario_names)

    def _register_selection_hotkeys(self, scenario_names: list) -> None:
        """Register hotkeys for scenario selection."""
        try:
            import keyboard

            self._selection_callbacks = {}
            for i, name in enumerate(scenario_names):
                # Use default argument to capture name correctly
                def make_callback(n=name):
                    return lambda: self._select_scenario(n)

                callback = make_callback()
                self._selection_callbacks[str(i+1)] = callback
                keyboard.add_hotkey(str(i+1), callback)

            self._number_hotkeys_registered = True
            logger.debug(f"Registered {len(scenario_names)} selection hotkeys")

        except ImportError:
            logger.warning("keyboard library not available")
        except Exception as e:
            logger.warning(f"Failed to register selection hotkeys: {e}")

    def _unregister_selection_hotkeys(self) -> None:
        """Unregister selection hotkeys."""
        if not self._number_hotkeys_registered:
            return

        try:
            import keyboard

            for key in self._selection_callbacks:
                try:
                    keyboard.remove_hotkey(key)
                except Exception:
                    pass

            self._selection_callbacks = {}
            self._number_hotkeys_registered = False
            logger.debug("Unregistered selection hotkeys")

        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Failed to unregister selection hotkeys: {e}")

    def _select_scenario(self, scenario_name: str) -> None:
        """Handle scenario selection."""
        # Use root.after for thread safety (hotkeys run in separate thread)
        if self.root:
            self.root.after(0, lambda: self._do_select_scenario(scenario_name))

    def _do_select_scenario(self, scenario_name: str) -> None:
        """Actually perform scenario selection (called from main thread)."""
        self.selected_scenario = get_scenario_by_name(scenario_name)

        if self.selected_scenario:
            # Unregister number keys
            self._unregister_selection_hotkeys()

            # Show selection confirmation
            confirm_text = (
                f"已选择: {self.selected_scenario.description}\n"
                f"步骤数: {len(self.selected_scenario.steps)}\n\n"
                f"按 F1 开始测试"
            )
            self.overlay.set_instruction(confirm_text)

            # Register F1 to start
            self._register_start_hotkey()

            logger.info(f"Selected scenario: {scenario_name}")

    def _register_start_hotkey(self) -> None:
        """Register F1 hotkey to start the test."""
        try:
            import keyboard
            keyboard.add_hotkey('f1', self._start_selected_scenario)
            logger.debug("Registered F1 start hotkey")
        except Exception as e:
            logger.warning(f"Failed to register F1 hotkey: {e}")

    def _start_selected_scenario(self) -> None:
        """Start the selected scenario."""
        if self.root:
            self.root.after(0, self._do_start_scenario)

    def _do_start_scenario(self) -> None:
        """Actually start the scenario (called from main thread)."""
        if not self.selected_scenario:
            return

        # Remove F1 start hotkey
        try:
            import keyboard
            keyboard.remove_hotkey('f1')
        except Exception:
            pass

        # Setup flow hotkeys
        self.flow.setup_hotkeys()

        # Load and start scenario
        self.flow.load_scenario(self.selected_scenario)
        self.flow.start()

        logger.info(f"Started scenario: {self.selected_scenario.name}")

    def run(self) -> None:
        """Main run loop."""
        self.initialize()
        self.show_scenario_selection()

        # Keep main thread alive
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Cleanup resources."""
        logger.info("Cleaning up TestRunner")

        # Unregister hotkeys
        self._unregister_selection_hotkeys()

        try:
            import keyboard
            keyboard.remove_hotkey('f1')
        except Exception:
            pass

        # Cleanup flow
        if self.flow:
            self.flow.terminate()

        # Cleanup overlay
        if self.overlay:
            self.overlay.close()

        # Destroy root
        if self.root:
            self.root.destroy()


# =============================================================================
# Unit Tests
# =============================================================================

import pytest


class TestTestRunner:
    """Unit tests for TestRunner class."""

    @pytest.fixture
    def runner(self):
        """Provide TestRunner instance."""
        return TestRunner()

    def test_initialization(self, runner):
        """Test runner initialization."""
        runner.initialize()
        assert runner.overlay is not None
        assert runner.logger is not None
        assert runner.flow is not None
        assert runner.root is not None
        runner.cleanup()

    def test_scenario_selection_text(self, runner):
        """Test that scenario selection shows correct text."""
        runner.initialize()
        runner.show_scenario_selection()

        # Check that overlay shows selection text
        # Note: We can't directly check the label text without accessing internals
        # but we can verify the runner is in correct state
        assert runner._number_hotkeys_registered
        runner.cleanup()

    def test_select_scenario(self, runner):
        """Test scenario selection."""
        runner.initialize()
        runner._do_select_scenario("guild_donation")

        assert runner.selected_scenario is not None
        assert runner.selected_scenario.name == "guild_donation"
        runner.cleanup()

    def test_invalid_scenario(self, runner):
        """Test selecting invalid scenario."""
        runner.initialize()
        runner._do_select_scenario("nonexistent")

        # Should not crash, just not set scenario
        assert runner.selected_scenario is None
        runner.cleanup()
