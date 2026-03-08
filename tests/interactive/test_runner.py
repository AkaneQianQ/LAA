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
from tests.interactive.test_flow import TestFlow, TestState
from tests.interactive.scenarios import (
    ALL_SCENARIOS,
    list_scenario_names,
    get_scenario_by_name,
)
from tests.interactive.hardware_check import check_ferrum_connection

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
        self._selection_handles = {}
        self._menu_hotkey_registered = False
        self._menu_hotkey_handle = None
        self._retry_hotkey_handle = None
        self._start_hotkey_handle = None
        self.hardware_available = False
        self.hardware_check_result = None

    def initialize(self) -> None:
        """Initialize all components including hardware check."""
        self.root = tk.Tk()
        self.root.withdraw()  # Hide root window

        self.overlay = TestOverlay(self.root)
        self.logger = TestLogger()
        self.flow = TestFlow(self.overlay, self.logger)

        # 执行硬件检测（仅打印信息到终端，不阻塞测试）
        self._perform_hardware_check_async()

        # 直接显示场景选择
        self.root.after(500, self.show_scenario_selection)

        logger.info("TestRunner initialized")

    def _perform_hardware_check_async(self) -> None:
        """
        在后台线程执行硬件检测，避免阻塞UI

        检测结果仅打印到终端，不影响测试流程。
        """
        def check_in_thread():
            try:
                print("=" * 50)
                print("[Ferrum] 正在检测硬件连接...")
                self.hardware_check_result = check_ferrum_connection()
                self.hardware_available = self.hardware_check_result.get("success", False)

                if self.hardware_available:
                    port_info = self.hardware_check_result.get("message", "")
                    print(f"[Ferrum] ✓ 连接成功 - {port_info}")
                else:
                    error_msg = self.hardware_check_result.get("error", "未知错误")
                    print(f"[Ferrum] ✗ 连接失败 - {error_msg}")
                    print("[Ferrum] 提示: 测试可以继续，但硬件操作将失败")
                print("=" * 50)
            except Exception as e:
                print(f"[Ferrum] 检测异常: {e}")
                self.hardware_available = False

        # 在后台线程执行检测
        import threading
        threading.Thread(target=check_in_thread, daemon=True).start()

    def _perform_hardware_check(self) -> None:
        """
        执行硬件预检测（已弃用，改用 _perform_hardware_check_async）

        检测Ferrum设备是否已连接。无论成功与否都显示详细信息。
        用户可以通过按R键重试检测。
        """
        self._perform_hardware_check_async()

    def _register_retry_hotkey(self) -> None:
        """注册R键重试硬件检测的热键"""
        try:
            import keyboard
            self._retry_hotkey_handle = keyboard.add_hotkey('r', self._retry_hardware_check)
            logger.debug("Registered R key for hardware check retry")
        except Exception as e:
            logger.warning(f"Failed to register retry hotkey: {e}")

    def _unregister_retry_hotkey(self) -> None:
        """注销R键重试热键"""
        if self._retry_hotkey_handle is None:
            return
        try:
            import keyboard
            keyboard.remove_hotkey(self._retry_hotkey_handle)
            self._retry_hotkey_handle = None
            logger.debug("Unregistered R key for hardware check retry")
        except Exception:
            pass

    def _retry_hardware_check(self) -> None:
        """
        重试硬件检测

        用户按R键时调用，重新检测设备连接状态。
        成功后自动继续到场景选择。
        """
        if self.root:
            self.root.after(0, self._do_retry_hardware_check)

    def _do_retry_hardware_check(self) -> None:
        """实际执行重试（在主线程中调用）"""
        print("[Ferrum] 正在重试硬件检测...")
        self._unregister_retry_hotkey()
        self._unregister_menu_hotkey()
        self._perform_hardware_check()

    def _register_menu_hotkey(self) -> None:
        """注册M键返回主菜单的热键"""
        if self._menu_hotkey_registered:
            return
        try:
            import keyboard
            self._menu_hotkey_handle = keyboard.add_hotkey('m', self._return_to_menu)
            self._menu_hotkey_registered = True
            logger.debug("Registered M key for returning to menu")
        except Exception as e:
            logger.warning(f"Failed to register menu hotkey: {e}")

    def _unregister_menu_hotkey(self) -> None:
        """注销M键返回主菜单的热键"""
        if not self._menu_hotkey_registered or self._menu_hotkey_handle is None:
            return
        try:
            import keyboard
            keyboard.remove_hotkey(self._menu_hotkey_handle)
            self._menu_hotkey_registered = False
            self._menu_hotkey_handle = None
            logger.debug("Unregistered M key for returning to menu")
        except Exception:
            pass

    def _return_to_menu(self) -> None:
        """返回主菜单（按M键时调用）"""
        if self.root:
            self.root.after(0, self._do_return_to_menu)

    def _do_return_to_menu(self) -> None:
        """实际返回主菜单（在主线程中调用）"""
        logger.info("Returning to main menu")

        # 清理当前测试状态
        if self.flow:
            self.flow.state = TestState.IDLE
            self.flow.scenario = None
            self.flow.current_step_index = -1
            self.flow.test_id = None
            self.selected_scenario = None

        # 注销测试热键，重新注册菜单热键
        self._unregister_test_hotkeys()
        self._register_menu_hotkey()

        # 显示场景选择
        self.show_scenario_selection()

    def show_scenario_selection(self) -> None:
        """Show scenario selection UI in overlay."""
        scenario_names = list_scenario_names()

        if not scenario_names:
            self.overlay.set_instruction("错误: 没有可用的测试场景")
            return

        # 获取硬件连接信息显示
        hw_info = ""
        if self.hardware_check_result and self.hardware_check_result.get("success"):
            hw_info = f"[Ferrum已连接: {self.hardware_check_result.get('message', '')}] "

        # Build selection text (compact for horizontal layout)
        selection_text = f"{hw_info}选择场景: "
        for i, name in enumerate(scenario_names):
            scenario = get_scenario_by_name(name)
            desc = scenario.description if scenario else name
            selection_text += f"{i+1}.{desc} "
        selection_text += f"| 按 1-{len(scenario_names)} 选择"

        self.overlay.set_instruction(selection_text)

        # Register number key hotkeys for selection and M key for menu
        self._register_selection_hotkeys(scenario_names)
        self._register_menu_hotkey()

    def _register_selection_hotkeys(self, scenario_names: list) -> None:
        """Register hotkeys for scenario selection."""
        try:
            import keyboard

            self._selection_callbacks = {}
            self._selection_handles = {}
            for i, name in enumerate(scenario_names):
                # Use default argument to capture name correctly
                def make_callback(n=name):
                    return lambda: self._select_scenario(n)

                callback = make_callback()
                key = str(i+1)
                self._selection_callbacks[key] = callback
                self._selection_handles[key] = keyboard.add_hotkey(key, callback)

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

            for key, handle in self._selection_handles.items():
                try:
                    keyboard.remove_hotkey(handle)
                except Exception:
                    pass

            self._selection_callbacks = {}
            self._selection_handles = {}
            self._number_hotkeys_registered = False
            logger.debug("Unregistered selection hotkeys")

        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Failed to unregister selection hotkeys: {e}")

    def _unregister_test_hotkeys(self) -> None:
        """Unregister test flow hotkeys (F1, Y, N, END)."""
        try:
            import keyboard
            # Use overlay's unregister if available (it tracks handles properly)
            if self.overlay:
                self.overlay.unregister_hotkeys()
            logger.debug("Unregistered test hotkeys")
        except Exception:
            pass

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
            confirm_text = f"已选择: {self.selected_scenario.description} ({len(self.selected_scenario.steps)}步) | 按 F1 开始"
            self.overlay.set_instruction(confirm_text)

            # Register F1 to start
            self._register_start_hotkey()

            logger.info(f"Selected scenario: {scenario_name}")

    def _register_start_hotkey(self) -> None:
        """Register F1 hotkey to start the test."""
        try:
            import keyboard
            self._start_hotkey_handle = keyboard.add_hotkey('f1', self._start_selected_scenario)
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
        if self._start_hotkey_handle is not None:
            try:
                import keyboard
                keyboard.remove_hotkey(self._start_hotkey_handle)
                self._start_hotkey_handle = None
            except Exception:
                pass

        # Setup flow hotkeys
        self.flow.setup_hotkeys()

        # Load and start scenario
        self.flow.load_scenario(self.selected_scenario)
        self.flow.start()

        # Start polling for test completion
        self._poll_test_completion()

        logger.info(f"Started scenario: {self.selected_scenario.name}")

    def _poll_test_completion(self) -> None:
        """Poll for test completion and show return to menu option."""
        if not self.flow or not self.root:
            return

        # Check if test is completed or terminated
        if self.flow.state in (TestState.COMPLETED, TestState.TERMINATED):
            # Test finished, show return to menu prompt
            self._show_return_to_menu_prompt()
        else:
            # Continue polling
            self.root.after(500, self._poll_test_completion)

    def _show_return_to_menu_prompt(self) -> None:
        """Show prompt to return to main menu after test completion."""
        if not self.flow or not self.overlay:
            return

        # Get test result
        result_text = "已完成"
        if self.flow.state == TestState.COMPLETED and self.flow.test_id:
            result = self.logger.get_test_result(self.flow.test_id)
            if result:
                result_text = result.overall_result

        # Show return to menu prompt with M key
        prompt_text = f"测试{result_text}！按 M 返回主菜单 | 按 END 关闭"
        self.overlay.set_instruction(prompt_text)

        # Ensure menu hotkey is registered
        self._unregister_test_hotkeys()
        self._register_menu_hotkey()

    def run(self) -> None:
        """Main run loop."""
        self.initialize()
        # 硬件检测在initialize中已执行，成功后自动显示场景选择
        # 如果硬件检测失败，initialize会显示错误信息并等待重试

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
        self._unregister_retry_hotkey()
        self._unregister_menu_hotkey()
        self._unregister_test_hotkeys()

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
