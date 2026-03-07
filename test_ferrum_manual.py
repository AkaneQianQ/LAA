"""
Ferrum Hardware Manual Test Launcher

手动测试启动器，用于交互式验证FerrumController和HardwareInputGateway。

使用方法:
    python test_ferrum_manual.py

测试流程:
    1. 连接Ferrum设备
    2. 执行鼠标点击测试
    3. 执行按键测试
    4. 执行组合键测试
    5. 执行滚轮测试
    6. 关闭连接

注意: 需要Ferrum硬件连接到COM2端口
"""

import sys
import time


def main():
    """主测试函数"""
    print("=" * 60)
    print("Ferrum Hardware Manual Test")
    print("=" * 60)
    print()

    # 导入模块
    try:
        from core.ferrum_controller import FerrumController, FerrumConnectionError
        from core.hardware_input_gateway import HardwareInputGateway
        print("[✓] 模块导入成功")
    except ImportError as e:
        print(f"[✗] 模块导入失败: {e}")
        sys.exit(1)

    # 创建FerrumController
    print("\n[1] 连接Ferrum设备...")
    try:
        ferrum = FerrumController(port="COM2")
        print(f"[✓] 设备已连接: {ferrum.port}")
    except FerrumConnectionError as e:
        print(f"[✗] 连接失败: {e}")
        print("    请检查:")
        print("    - Ferrum设备是否已连接到COM2端口")
        print("    - 设备驱动是否正确安装")
        sys.exit(1)

    # 包装在HardwareInputGateway中
    print("\n[2] 初始化HardwareInputGateway...")
    gateway = HardwareInputGateway(hardware_controller=ferrum)
    print("[✓] Gateway初始化完成")
    print(f"    Session Seed: {gateway._session_seed}")

    # 测试鼠标点击
    print("\n[3] 测试鼠标点击...")
    print("    将在3秒后在当前鼠标位置进行点击")
    print("    请将鼠标移动到安全位置")
    for i in range(3, 0, -1):
        print(f"    {i}...")
        time.sleep(1)

    try:
        # 注意：这里使用相对坐标(0, 0)表示在当前位置点击
        # 实际使用中应该计算从当前位置到目标位置的delta
        gateway.click(0, 0, base_delay_ms=100)
        print("[✓] 点击测试完成")
    except Exception as e:
        print(f"[✗] 点击测试失败: {e}")

    # 测试按键
    print("\n[4] 测试按键 (ESC)...")
    print("    将发送ESC键（不会关闭此窗口）")
    time.sleep(1)
    try:
        gateway.press("esc", base_delay_ms=100)
        print("[✓] 按键测试完成")
    except Exception as e:
        print(f"[✗] 按键测试失败: {e}")

    # 测试组合键
    print("\n[5] 测试组合键 (Alt+U)...")
    print("    将发送Alt+U组合键（Lost Ark中打开公会界面）")
    print("    请确保Lost Ark正在运行，或观察按键是否生效")
    time.sleep(1)
    try:
        gateway.press("alt+u", base_delay_ms=100)
        print("[✓] 组合键测试完成")
    except Exception as e:
        print(f"[✗] 组合键测试失败: {e}")

    # 测试滚轮
    print("\n[6] 测试滚轮 (向下滚动3次)...")
    print("    将向下滚动鼠标滚轮3次")
    time.sleep(1)
    try:
        gateway.scroll("down", 3, base_delay_ms=50)
        print("[✓] 滚轮测试完成")
    except Exception as e:
        print(f"[✗] 滚轮测试失败: {e}")

    # 显示统计信息
    print("\n[7] 统计信息...")
    stats = gateway.get_stats()
    print(f"    动作次数: {stats['action_count']}")
    print(f"    违规次数: {stats['violation_count']}")
    print(f"    抖动启用: {stats['jitter_enabled']}")
    print(f"    Session Seed: {stats['session_seed']}")

    # 关闭连接
    print("\n[8] 关闭连接...")
    gateway.wait(500)  # 等待500ms确保所有命令执行完成
    ferrum.close()
    print("[✓] 连接已关闭")

    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
