"""
Hardware Check Module - Ferrum硬件连接检测

提供Ferrum硬件设备的连接预检测功能，确保测试前硬件可用。
"""

from typing import Optional, List, Dict
import logging

# 配置日志
logger = logging.getLogger(__name__)


def check_ferrum_connection(port: str = "COM2", baudrate: int = 115200, timeout: float = 1.0) -> bool:
    """
    检测Ferrum硬件设备是否已连接

    尝试创建FerrumController实例来验证设备连接状态。
    成功检测后会自动关闭连接，避免占用串口。

    Args:
        port: 串口名称，默认COM2
        baudrate: 波特率，默认115200
        timeout: 超时时间（秒），默认1.0

    Returns:
        True如果设备连接成功，False如果连接失败
    """
    try:
        # 延迟导入以避免循环依赖
        from core.ferrum_controller import FerrumController, FerrumConnectionError

        print(f"[Ferrum] 正在检测设备连接 ({port} @ {baudrate})...")

        # 尝试创建控制器实例（会自动连接）
        controller = FerrumController(port=port, baudrate=baudrate, timeout=timeout)

        # 验证连接状态
        if controller.is_connected():
            print(f"[Ferrum] 设备连接成功，串口{port}可用")
            # 关闭连接，避免占用串口
            controller.close()
            return True
        else:
            print(f"[错误] 设备连接状态异常")
            controller.close()
            return False

    except FerrumConnectionError as e:
        print(f"[错误] Ferrum设备未连接: {e}")
        return False
    except Exception as e:
        print(f"[错误] 检测过程中发生异常: {e}")
        return False


class FerrumHardwareCheck:
    """
    Ferrum硬件检测类

    提供更详细的硬件检测功能，支持多端口检测和详细错误报告。
    """

    # 默认检测的端口列表
    DEFAULT_PORTS = ["COM2", "COM3"]

    def __init__(self, ports: Optional[List[str]] = None, baudrate: int = 115200, timeout: float = 1.0):
        """
        初始化硬件检测器

        Args:
            ports: 要检测的端口列表，默认检测COM2和COM3
            baudrate: 波特率，默认115200
            timeout: 超时时间（秒），默认1.0
        """
        self.ports = ports or self.DEFAULT_PORTS
        self.baudrate = baudrate
        self.timeout = timeout
        self.results: Dict[str, Dict] = {}

    def check_all_ports(self) -> Dict[str, Dict]:
        """
        检测所有配置的端口

        Returns:
            端口检测结果字典，键为端口名，值为包含status和error的字典
        """
        self.results = {}

        for port in self.ports:
            result = self._check_single_port(port)
            self.results[port] = result

        return self.results

    def _check_single_port(self, port: str) -> Dict:
        """
        检测单个端口

        Args:
            port: 串口名称

        Returns:
            包含status和error信息的字典
        """
        try:
            from core.ferrum_controller import FerrumController, FerrumConnectionError

            controller = FerrumController(
                port=port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )

            if controller.is_connected():
                controller.close()
                return {
                    "status": "connected",
                    "error": None
                }
            else:
                controller.close()
                return {
                    "status": "disconnected",
                    "error": "设备未响应"
                }

        except FerrumConnectionError as e:
            return {
                "status": "error",
                "error": str(e)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"未知错误: {e}"
            }

    def is_any_connected(self) -> bool:
        """
        检查是否有任何端口连接成功

        Returns:
            True如果至少有一个端口连接成功
        """
        if not self.results:
            self.check_all_ports()

        return any(
            result["status"] == "connected"
            for result in self.results.values()
        )

    def get_first_connected_port(self) -> Optional[str]:
        """
        获取第一个连接成功的端口

        Returns:
            连接成功的端口名，如果没有则返回None
        """
        if not self.results:
            self.check_all_ports()

        for port, result in self.results.items():
            if result["status"] == "connected":
                return port
        return None

    def get_error_summary(self) -> str:
        """
        获取错误摘要

        Returns:
            格式化的错误信息字符串
        """
        if not self.results:
            self.check_all_ports()

        errors = []
        for port, result in self.results.items():
            if result["status"] != "connected" and result["error"]:
                errors.append(f"{port}: {result['error']}")

        if errors:
            return "; ".join(errors)
        return "无错误"


# =============================================================================
# Unit Tests
# =============================================================================

import pytest
from unittest.mock import patch, MagicMock


class TestCheckFerrumConnection:
    """Tests for check_ferrum_connection function."""

    @patch('tests.interactive.hardware_check.FerrumController')
    def test_successful_connection(self, mock_controller_class):
        """Test successful hardware connection detection."""
        # 设置mock
        mock_controller = MagicMock()
        mock_controller.is_connected.return_value = True
        mock_controller_class.return_value = mock_controller

        # 执行测试
        result = check_ferrum_connection(port="COM2")

        # 验证结果
        assert result is True
        mock_controller_class.assert_called_once_with(port="COM2", baudrate=115200, timeout=1.0)
        mock_controller.close.assert_called_once()

    @patch('tests.interactive.hardware_check.FerrumController')
    def test_failed_connection_not_connected(self, mock_controller_class):
        """Test connection detection when device reports not connected."""
        mock_controller = MagicMock()
        mock_controller.is_connected.return_value = False
        mock_controller_class.return_value = mock_controller

        result = check_ferrum_connection(port="COM2")

        assert result is False
        mock_controller.close.assert_called_once()

    @patch('tests.interactive.hardware_check.FerrumController')
    def test_connection_error(self, mock_controller_class):
        """Test connection detection when FerrumConnectionError is raised."""
        from core.ferrum_controller import FerrumConnectionError
        mock_controller_class.side_effect = FerrumConnectionError("Device not found")

        result = check_ferrum_connection(port="COM2")

        assert result is False

    @patch('tests.interactive.hardware_check.FerrumController')
    def test_unexpected_exception(self, mock_controller_class):
        """Test connection detection when unexpected exception occurs."""
        mock_controller_class.side_effect = RuntimeError("Unexpected error")

        result = check_ferrum_connection(port="COM2")

        assert result is False


class TestFerrumHardwareCheck:
    """Tests for FerrumHardwareCheck class."""

    @patch('tests.interactive.hardware_check.FerrumController')
    def test_check_all_ports(self, mock_controller_class):
        """Test checking multiple ports."""
        mock_controller = MagicMock()
        mock_controller.is_connected.return_value = True
        mock_controller_class.return_value = mock_controller

        checker = FerrumHardwareCheck(ports=["COM2", "COM3"])
        results = checker.check_all_ports()

        assert len(results) == 2
        assert results["COM2"]["status"] == "connected"
        assert results["COM3"]["status"] == "connected"

    @patch('tests.interactive.hardware_check.FerrumController')
    def test_is_any_connected_true(self, mock_controller_class):
        """Test is_any_connected returns True when at least one port works."""
        mock_controller = MagicMock()
        mock_controller.is_connected.return_value = True
        mock_controller_class.return_value = mock_controller

        checker = FerrumHardwareCheck(ports=["COM2", "COM3"])
        assert checker.is_any_connected() is True

    @patch('tests.interactive.hardware_check.FerrumController')
    def test_is_any_connected_false(self, mock_controller_class):
        """Test is_any_connected returns False when no ports work."""
        from core.ferrum_controller import FerrumConnectionError
        mock_controller_class.side_effect = FerrumConnectionError("Not found")

        checker = FerrumHardwareCheck(ports=["COM2", "COM3"])
        assert checker.is_any_connected() is False

    @patch('tests.interactive.hardware_check.FerrumController')
    def test_get_first_connected_port(self, mock_controller_class):
        """Test getting first connected port."""
        mock_controller = MagicMock()
        mock_controller.is_connected.return_value = True
        mock_controller_class.return_value = mock_controller

        checker = FerrumHardwareCheck(ports=["COM2", "COM3"])
        port = checker.get_first_connected_port()

        assert port == "COM2"

    @patch('tests.interactive.hardware_check.FerrumController')
    def test_get_first_connected_port_none(self, mock_controller_class):
        """Test getting first connected port when none available."""
        from core.ferrum_controller import FerrumConnectionError
        mock_controller_class.side_effect = FerrumConnectionError("Not found")

        checker = FerrumHardwareCheck(ports=["COM2", "COM3"])
        port = checker.get_first_connected_port()

        assert port is None

    def test_default_ports(self):
        """Test default ports configuration."""
        checker = FerrumHardwareCheck()
        assert checker.ports == ["COM2", "COM3"]

    def test_custom_ports(self):
        """Test custom ports configuration."""
        checker = FerrumHardwareCheck(ports=["COM4", "COM5"])
        assert checker.ports == ["COM4", "COM5"]
