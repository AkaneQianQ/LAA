"""
FerrumController 键盘功能测试

测试HID键码映射和按键功能。
注意：此测试需要实际的Ferrum硬件设备连接。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.ferrum_controller import FerrumController, KEY_MAP, MODIFIER_CODES


class TestKeyMap:
    """测试键码映射表"""

    def test_required_keys_present(self):
        """验证所有必需键都存在"""
        required = {
            'esc': 41,
            'u': 24,
            'enter': 40,
            'up': 38,
            'down': 40,
            'alt': 226,
        }
        for key, expected_code in required.items():
            assert key in KEY_MAP, f"缺少必需键: {key}"
            assert KEY_MAP[key] == expected_code, f"键 {key} 的代码错误"

    def test_letters_mapping(self):
        """测试字母键映射 (a-z = 4-29)"""
        for i, letter in enumerate('abcdefghijklmnopqrstuvwxyz'):
            expected_code = 4 + i
            assert KEY_MAP[letter] == expected_code, f"字母 {letter} 映射错误"

    def test_numbers_mapping(self):
        """测试数字键映射 (0-9 = 30-39)"""
        for i, digit in enumerate('0123456789'):
            expected_code = 30 + i
            assert KEY_MAP[digit] == expected_code, f"数字 {digit} 映射错误"

    def test_arrow_keys_mapping(self):
        """测试方向键映射"""
        assert KEY_MAP['up'] == 38
        assert KEY_MAP['down'] == 40
        assert KEY_MAP['left'] == 37
        assert KEY_MAP['right'] == 39

    def test_modifier_keys_mapping(self):
        """测试修饰键映射"""
        assert KEY_MAP['alt'] == 226
        assert KEY_MAP['lalt'] == 226
        assert KEY_MAP['ralt'] == 230
        assert KEY_MAP['ctrl'] == 224
        assert KEY_MAP['lctrl'] == 224
        assert KEY_MAP['rctrl'] == 228
        assert KEY_MAP['shift'] == 225
        assert KEY_MAP['lshift'] == 225
        assert KEY_MAP['rshift'] == 229

    def test_f_keys_mapping(self):
        """测试F键映射 (F1-F12 = 58-69)"""
        for i in range(1, 13):
            key_name = f'f{i}'
            expected_code = 57 + i  # F1 = 58
            assert KEY_MAP[key_name] == expected_code, f"{key_name} 映射错误"

    def test_modifier_codes_set(self):
        """测试修饰键代码集合"""
        expected_modifiers = {224, 225, 226, 228, 229, 230}
        assert MODIFIER_CODES == expected_modifiers


class TestKeyParsing:
    """测试键名解析"""

    @pytest.fixture
    def controller(self):
        """创建控制器实例（不连接实际设备）"""
        # 使用mock方式测试解析功能
        return None

    def test_parse_single_key(self):
        """测试单键解析"""
        from core.ferrum_controller import FerrumController
        # 直接测试解析逻辑
        controller = object.__new__(FerrumController)

        assert controller._parse_key('esc') == [41]
        assert controller._parse_key('u') == [24]
        assert controller._parse_key('enter') == [40]
        assert controller._parse_key('UP') == [38]  # 大小写不敏感
        assert controller._parse_key('Alt') == [226]

    def test_parse_key_combination(self):
        """测试组合键解析"""
        from core.ferrum_controller import FerrumController
        controller = object.__new__(FerrumController)

        assert controller._parse_key('alt+u') == [226, 24]
        assert controller._parse_key('ctrl+shift+a') == [224, 225, 4]
        assert controller._parse_key('ALT+U') == [226, 24]  # 大小写不敏感

    def test_parse_unknown_key_raises(self):
        """测试未知键名抛出异常"""
        from core.ferrum_controller import FerrumController
        controller = object.__new__(FerrumController)

        with pytest.raises(ValueError, match="未知键名"):
            controller._parse_key('unknown_key')

        with pytest.raises(ValueError, match="未知键名"):
            controller._parse_key('alt+unknown')

    def test_parse_with_whitespace(self):
        """测试带空格的键名解析"""
        from core.ferrum_controller import FerrumController
        controller = object.__new__(FerrumController)

        assert controller._parse_key('alt + u') == [226, 24]
        assert controller._parse_key('  esc  ') == [41]


class TestKeyOrdering:
    """测试键码排序"""

    def test_order_codes_puts_modifiers_first(self):
        """测试修饰键排在前面"""
        from core.ferrum_controller import FerrumController
        controller = object.__new__(FerrumController)

        # u+alt 应该变成 alt+u (226, 24)
        ordered = controller._order_codes([24, 226])
        assert ordered == [226, 24]

    def test_order_codes_multiple_modifiers(self):
        """测试多个修饰键排序"""
        from core.ferrum_controller import FerrumController
        controller = object.__new__(FerrumController)

        # a+ctrl+shift 应该变成 ctrl+shift+a
        codes = [4, 224, 225]  # a, ctrl, shift
        ordered = controller._order_codes(codes)
        assert ordered[0] in MODIFIER_CODES
        assert ordered[1] in MODIFIER_CODES
        assert ordered[2] == 4  # a

    def test_order_codes_no_modifiers(self):
        """测试无修饰键时的排序"""
        from core.ferrum_controller import FerrumController
        controller = object.__new__(FerrumController)

        codes = [41, 24, 40]  # esc, u, enter
        ordered = controller._order_codes(codes)
        assert ordered == [41, 24, 40]


@pytest.mark.integration
class TestKeyboardIntegration:
    """
    键盘集成测试 - 需要实际硬件设备

    运行方式: pytest tests/test_ferrum_keyboard.py::TestKeyboardIntegration -v --integration
    """

    @pytest.fixture(scope="module")
    def ferrum(self):
        """创建Ferrum控制器实例"""
        try:
            controller = FerrumController(port="COM2")
            yield controller
            controller.close()
        except Exception as e:
            pytest.skip(f"无法连接Ferrum设备: {e}")

    def test_press_single_key(self, ferrum):
        """测试单键按下"""
        # 这些测试会实际发送按键到设备
        # 请确保有文本输入框可以接收按键

        ferrum.press('esc')
        # 验证设备响应正常（无异常抛出即成功）

    def test_press_key_combination(self, ferrum):
        """测试组合键按下"""
        ferrum.press('alt+u')
        # 验证组合键发送成功

    def test_key_down_up(self, ferrum):
        """测试按住和释放"""
        import time

        ferrum.key_down('alt')
        time.sleep(0.1)
        ferrum.key_up('alt')

    def test_all_required_keys(self, ferrum):
        """测试所有必需键"""
        required_keys = ['esc', 'u', 'enter', 'up', 'down', 'alt']

        for key in required_keys:
            ferrum.press(key)
            import time
            time.sleep(0.05)  # 短暂延迟避免设备过载


if __name__ == '__main__':
    # 运行单元测试（不需要硬件）
    pytest.main([__file__, '-v', '-k', 'not integration'])
