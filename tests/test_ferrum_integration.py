"""
Ferrum Hardware Integration Tests

集成测试脚本，验证FerrumController与HardwareInputGateway的兼容性。
需要实际Ferrum硬件连接才能运行完整测试。
"""

import pytest
import time
from unittest.mock import MagicMock, patch

# Skip all tests if serial module not available
try:
    import serial
    from core.ferrum_controller import FerrumController, FerrumConnectionError
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

from core.hardware_input_gateway import HardwareInputGateway


@pytest.fixture(scope="module")
def ferrum_available():
    """检查Ferrum硬件是否可用"""
    if not SERIAL_AVAILABLE:
        pytest.skip("pyserial not available")

    # 尝试连接COM2，如果失败则跳过测试
    try:
        controller = FerrumController(port="COM2", timeout=0.5)
        controller.close()
        return True
    except FerrumConnectionError:
        pytest.skip("Ferrum hardware not available on COM2")


@pytest.fixture
def ferrum(ferrum_available):
    """
    创建FerrumController实例

    如果硬件不可用，使用mock对象代替
    """
    if ferrum_available:
        controller = FerrumController(port="COM2")
        yield controller
        controller.close()
    else:
        # 创建mock controller用于测试接口
        mock_controller = MagicMock()
        mock_controller.is_connected.return_value = True
        yield mock_controller


@pytest.fixture
def gateway(ferrum):
    """创建HardwareInputGateway实例，包装FerrumController"""
    return HardwareInputGateway(hardware_controller=ferrum)


class TestFerrumIntegration:
    """Ferrum硬件集成测试类"""

    def test_connection(self, ferrum):
        """测试设备连接状态"""
        assert ferrum.is_connected() is True

    def test_click_method_exists(self, ferrum):
        """验证click方法存在且可调用"""
        assert hasattr(ferrum, 'click')
        assert callable(ferrum.click)

    def test_press_method_exists(self, ferrum):
        """验证press方法存在且可调用"""
        assert hasattr(ferrum, 'press')
        assert callable(ferrum.press)

    def test_scroll_method_exists(self, ferrum):
        """验证scroll方法存在且可调用"""
        assert hasattr(ferrum, 'scroll')
        assert callable(ferrum.scroll)

    def test_wait_method_exists(self, ferrum):
        """验证wait方法存在且可调用"""
        assert hasattr(ferrum, 'wait')
        assert callable(ferrum.wait)

    def test_close_method_exists(self, ferrum):
        """验证close方法存在且可调用"""
        assert hasattr(ferrum, 'close')
        assert callable(ferrum.close)


class TestHardwareInputGatewayIntegration:
    """HardwareInputGateway集成测试类"""

    def test_gateway_click(self, gateway, ferrum):
        """测试Gateway的click方法调用FerrumController"""
        # 使用mock时验证调用
        if isinstance(ferrum, MagicMock):
            gateway.click(100, 200)
            ferrum.click.assert_called_once_with(100, 200)
        else:
            # 真实硬件：只验证不抛出异常
            gateway.click(100, 200, base_delay_ms=50)

    def test_gateway_press(self, gateway, ferrum):
        """测试Gateway的press方法调用FerrumController"""
        if isinstance(ferrum, MagicMock):
            gateway.press("esc")
            ferrum.press.assert_called_once_with("esc")
        else:
            gateway.press("esc", base_delay_ms=50)

    def test_gateway_press_combo(self, gateway, ferrum):
        """测试Gateway的组合键press"""
        if isinstance(ferrum, MagicMock):
            gateway.press("alt+u")
            ferrum.press.assert_called_once_with("alt+u")
        else:
            gateway.press("alt+u", base_delay_ms=50)

    def test_gateway_scroll(self, gateway, ferrum):
        """测试Gateway的scroll方法调用FerrumController"""
        if isinstance(ferrum, MagicMock):
            gateway.scroll("down", 3)
            ferrum.scroll.assert_called_once_with("down", 3)
        else:
            gateway.scroll("down", 3, base_delay_ms=50)

    def test_gateway_stats(self, gateway):
        """测试Gateway统计信息"""
        stats = gateway.get_stats()
        assert "action_count" in stats
        assert "violation_count" in stats
        assert "session_seed" in stats
        assert "jitter_enabled" in stats


class TestFerrumControllerSignatures:
    """验证FerrumController方法签名符合ActionDispatcher期望"""

    def test_click_signature(self):
        """验证click方法签名: click(x: int, y: int)"""
        import inspect
        sig = inspect.signature(FerrumController.click)
        params = list(sig.parameters.keys())
        assert 'x' in params
        assert 'y' in params

    def test_press_signature(self):
        """验证press方法签名: press(key_name: str)"""
        import inspect
        sig = inspect.signature(FerrumController.press)
        params = list(sig.parameters.keys())
        assert 'key_name' in params

    def test_scroll_signature(self):
        """验证scroll方法签名: scroll(direction: str, ticks: int)"""
        import inspect
        sig = inspect.signature(FerrumController.scroll)
        params = list(sig.parameters.keys())
        assert 'direction' in params
        assert 'ticks' in params

    def test_wait_signature(self):
        """验证wait方法签名: wait(seconds: float)"""
        import inspect
        sig = inspect.signature(FerrumController.wait)
        params = list(sig.parameters.keys())
        assert 'seconds' in params


class TestContextManager:
    """测试上下文管理器"""

    def test_context_manager_enter_exit(self):
        """测试上下文管理器正确进入和退出"""
        # 使用mock避免实际串口连接
        with patch('core.ferrum_controller.serial.Serial') as mock_serial:
            mock_instance = MagicMock()
            mock_instance.is_open = True
            mock_serial.return_value = mock_instance

            with FerrumController(port="COM2") as controller:
                assert controller.is_connected()

            # 退出上下文后应该关闭
            assert not controller.is_connected()

    def test_close_method(self):
        """测试close方法正确关闭连接"""
        with patch('core.ferrum_controller.serial.Serial') as mock_serial:
            mock_instance = MagicMock()
            mock_instance.is_open = True
            mock_serial.return_value = mock_instance

            controller = FerrumController(port="COM2")
            assert controller.is_connected()

            controller.close()
            assert not controller.is_connected()


if __name__ == "__main__":
    # 手动运行测试
    print("=" * 60)
    print("Ferrum Hardware Integration Tests")
    print("=" * 60)
    print()
    print("运行测试需要Ferrum硬件连接到COM2端口")
    print("如果没有硬件，测试将使用mock对象运行")
    print()

    # 尝试检测硬件
    try:
        test_controller = FerrumController(port="COM2", timeout=0.5)
        test_controller.close()
        print("[✓] Ferrum硬件已检测到 (COM2)")
    except Exception as e:
        print(f"[!] Ferrum硬件未检测到: {e}")
        print("    测试将使用mock对象运行")
    print()

    # 运行pytest
    pytest.main([__file__, "-v", "--tb=short"])
