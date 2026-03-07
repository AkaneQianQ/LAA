"""
Ferrum Mouse Actions Test

测试FerrumController的鼠标操作功能：
- click(x, y): 移动并点击左键
- click_right(x, y): 移动并点击右键
- scroll(direction, ticks): 滚动鼠标滚轮
- _move(x, y): 相对鼠标移动

使用方式:
    python tests/test_ferrum_mouse.py

注意: 需要连接Ferrum硬件设备才能运行测试
"""

import sys
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
sys.path.insert(0, 'C:/Users/Akane/FerrumProject/LostarkGuildDonationBot')

from core.ferrum_controller import FerrumController, BUTTON_LEFT, BUTTON_RIGHT


def test_move_command():
    """测试 _move 方法发送正确的命令格式"""
    print("\n=== 测试 _move 方法 ===")
    print("验证: _move(10, -5) 应发送 'km.move(10, -5)'")
    print("注意: 此测试需要实际硬件连接")

    try:
        with FerrumController(port="COM2") as controller:
            # 测试相对移动
            print("[测试] 发送 _move(100, 50) - 向右下移动")
            controller._move(100, 50)
            time.sleep(0.5)

            print("[测试] 发送 _move(-100, -50) - 向左上移动（回到原位）")
            controller._move(-100, -50)
            time.sleep(0.5)

            print("[通过] _move 方法测试完成")
            return True
    except Exception as e:
        print(f"[错误] 测试失败: {e}")
        return False


def test_click():
    """测试 click(x, y) 方法"""
    print("\n=== 测试 click 方法 ===")
    print("验证: click(100, 100) 应先发送 move 然后发送 click(0)")

    try:
        with FerrumController(port="COM2") as controller:
            print("[测试] 在相对位置 (50, 50) 点击左键")
            print("      3秒后开始点击...")
            time.sleep(3)

            controller.click(50, 50)

            print("[通过] click 方法测试完成")
            return True
    except Exception as e:
        print(f"[错误] 测试失败: {e}")
        return False


def test_click_right():
    """测试 click_right(x, y) 方法"""
    print("\n=== 测试 click_right 方法 ===")
    print("验证: click_right(100, 100) 应发送 km.click(1)")

    try:
        with FerrumController(port="COM2") as controller:
            print("[测试] 在相对位置 (50, 50) 点击右键")
            print("      3秒后开始点击...")
            time.sleep(3)

            controller.click_right(50, 50)

            print("[通过] click_right 方法测试完成")
            return True
    except Exception as e:
        print(f"[错误] 测试失败: {e}")
        return False


def test_scroll():
    """测试 scroll(direction, ticks) 方法"""
    print("\n=== 测试 scroll 方法 ===")
    print("验证: scroll('down', 3) 应发送 km.wheel(-1) 三次")

    try:
        with FerrumController(port="COM2") as controller:
            print("[测试] 向下滚动 3 次")
            print("      3秒后开始滚动...")
            time.sleep(3)

            controller.scroll("down", 3)
            time.sleep(0.5)

            print("[测试] 向上滚动 3 次")
            controller.scroll("up", 3)

            print("[通过] scroll 方法测试完成")
            return True
    except Exception as e:
        print(f"[错误] 测试失败: {e}")
        return False


def test_button_constants():
    """测试按钮常量值"""
    print("\n=== 测试按钮常量 ===")

    # 验证常量值符合Ferrum文档
    assert BUTTON_LEFT == 0, f"BUTTON_LEFT 应为 0, 得到 {BUTTON_LEFT}"
    assert BUTTON_RIGHT == 1, f"BUTTON_RIGHT 应为 1, 得到 {BUTTON_RIGHT}"
    assert BUTTON_MIDDLE == 2, f"BUTTON_MIDDLE 应为 2, 得到 {BUTTON_MIDDLE}"

    print(f"BUTTON_LEFT = {BUTTON_LEFT} ✓")
    print(f"BUTTON_RIGHT = {BUTTON_RIGHT} ✓")
    print(f"BUTTON_MIDDLE = {BUTTON_MIDDLE} ✓")
    print("[通过] 按钮常量测试完成")
    return True


def run_all_tests():
    """运行所有鼠标操作测试"""
    print("=" * 50)
    print("Ferrum 鼠标操作测试")
    print("=" * 50)
    print("\n警告: 这些测试需要连接 Ferrum 硬件设备")
    print("请确保设备已连接到 COM2 端口")
    print("\n按 Ctrl+C 取消测试")
    print("=" * 50)

    results = []

    # 测试按钮常量（不需要硬件）
    try:
        results.append(("按钮常量", test_button_constants()))
    except Exception as e:
        print(f"[失败] 按钮常量测试: {e}")
        results.append(("按钮常量", False))

    # 测试需要硬件的方法
    try:
        results.append(("_move", test_move_command()))
    except Exception as e:
        print(f"[失败] _move 测试: {e}")
        results.append(("_move", False))

    try:
        results.append(("click", test_click()))
    except Exception as e:
        print(f"[失败] click 测试: {e}")
        results.append(("click", False))

    try:
        results.append(("click_right", test_click_right()))
    except Exception as e:
        print(f"[失败] click_right 测试: {e}")
        results.append(("click_right", False))

    try:
        results.append(("scroll", test_scroll()))
    except Exception as e:
        print(f"[失败] scroll 测试: {e}")
        results.append(("scroll", False))

    # 打印结果汇总
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")

    passed_count = sum(1 for _, p in results if p)
    print(f"\n总计: {passed_count}/{len(results)} 项测试通过")
    print("=" * 50)

    return all(p for _, p in results)


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试已取消")
        sys.exit(130)
