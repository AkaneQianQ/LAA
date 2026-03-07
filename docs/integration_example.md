# Ferrum Hardware Integration Example

This document shows how to integrate FerrumController with the existing workflow system.

## Architecture Overview

```
WorkflowExecutor
    └── ActionDispatcher
            └── HardwareInputGateway
                    └── FerrumController
                            └── Serial Connection (COM2)
```

## Integration Code Example

```python
"""
Ferrum Hardware Integration Example

展示如何将FerrumController与现有的Workflow系统集成。
"""

from core.ferrum_controller import FerrumController
from core.hardware_input_gateway import HardwareInputGateway
from core.vision_engine import VisionEngine
from core.workflow_bootstrap import create_workflow_executor


def create_ferrum_workflow_executor(workflow_path: str):
    """
    创建配置Ferrum硬件的Workflow执行器

    Args:
        workflow_path: YAML工作流配置文件路径

    Returns:
        配置好的WorkflowExecutor实例
    """
    # 1. 创建Ferrum硬件控制器
    # 默认使用COM2端口，波特率115200
    ferrum = FerrumController(
        port="COM2",
        baudrate=115200,
        timeout=1.0
    )

    # 2. 包装在HardwareInputGateway中
    # Gateway提供ACE合规策略执行和时序抖动
    gateway = HardwareInputGateway(
        hardware_controller=ferrum,
        session_seed=None,  # 随机生成session seed
        enable_jitter=True   # 启用±20%时序抖动
    )

    # 3. 创建视觉引擎
    vision = VisionEngine()

    # 4. 创建工作流执行器
    executor = create_workflow_executor(
        workflow_path=workflow_path,
        controller=gateway,
        vision_engine=vision
    )

    return executor


def run_guild_donation_workflow():
    """运行公会捐赠工作流示例"""
    # 创建工作流执行器
    executor = create_ferrum_workflow_executor(
        "config/workflows/guild_donation.yaml"
    )

    # 执行工作流
    result = executor.execute()

    # 检查结果
    if result.success:
        print(f"[任务] 工作流执行成功，完成 {result.steps_executed} 步")
    else:
        print(f"[错误] 工作流执行失败: {result.error_message}")

    return result


def run_with_context_manager():
    """使用上下文管理器确保资源清理"""
    with FerrumController(port="COM2") as ferrum:
        gateway = HardwareInputGateway(hardware_controller=ferrum)
        vision = VisionEngine()

        executor = create_workflow_executor(
            "config/workflows/guild_donation.yaml",
            controller=gateway,
            vision_engine=vision
        )

        result = executor.execute()

    # 退出上下文后，ferrum连接已自动关闭
    return result


def check_hardware_status():
    """检查硬件连接状态"""
    try:
        ferrum = FerrumController(port="COM2")

        if ferrum.is_connected():
            print("[✓] Ferrum硬件已连接")

            # 创建gateway并检查统计
            gateway = HardwareInputGateway(hardware_controller=ferrum)
            stats = gateway.get_stats()
            print(f"    Session Seed: {stats['session_seed']}")
            print(f"    Jitter Enabled: {stats['jitter_enabled']}")
        else:
            print("[✗] Ferrum硬件未连接")

        ferrum.close()

    except Exception as e:
        print(f"[错误] 硬件检查失败: {e}")


# 直接测试硬件输入
if __name__ == "__main__":
    print("Ferrum Hardware Integration Example")
    print("=" * 50)

    # 检查硬件状态
    check_hardware_status()

    # 简单输入测试
    print("\n执行简单输入测试...")
    with FerrumController(port="COM2") as ferrum:
        gateway = HardwareInputGateway(hardware_controller=ferrum)

        # 测试按键 (ESC)
        print("发送 ESC 键...")
        gateway.press("esc")

        # 测试组合键 (Alt+U - Lost Ark公会界面)
        print("发送 Alt+U 组合键...")
        gateway.press("alt+u")

        # 显示统计
        stats = gateway.get_stats()
        print(f"\n执行统计: {stats['action_count']} 个动作")

    print("\n测试完成，连接已关闭")
```

## Method Compatibility

FerrumController实现了ActionDispatcher期望的所有方法：

| Method | Signature | Description |
|--------|-----------|-------------|
| `click` | `click(x: int, y: int)` | 相对移动并点击左键 |
| `press` | `press(key_name: str)` | 按键或组合键 |
| `scroll` | `scroll(direction: str, ticks: int)` | 滚轮滚动 |
| `wait` | `wait(seconds: float)` | 等待指定时间 |

## Key Mapping

支持的键名（不区分大小写）：

**字母**: a-z (codes 4-29)
**数字**: 0-9 (codes 30-39)
**功能键**: f1-f12 (codes 58-69)
**方向键**: up, down, left, right
**修饰键**: alt, lalt, ralt, ctrl, lctrl, rctrl, shift, lshift, rshift
**特殊键**: esc, enter, return, space, tab, backspace

**组合键示例**:
- `"alt+u"` - 打开公会界面
- `"ctrl+shift+a"` - 多修饰键组合
- `"esc"` - 单键

## Hardware Requirements

- Ferrum设备通过USB连接
- 默认COM端口: COM2
- 波特率: 115200
- 需要设备驱动程序

## Error Handling

```python
from core.ferrum_controller import FerrumConnectionError

try:
    ferrum = FerrumController(port="COM2")
except FerrumConnectionError as e:
    print(f"连接失败: {e}")
    # 处理连接失败
```

## ACE Compliance

HardwareInputGateway确保ACE合规：
- 仅硬件输入路径（无软件注入）
- ±20%截断正态分布时序抖动
- 审计日志记录策略违规
- 会话种子保证可重复性
