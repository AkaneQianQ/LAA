#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Guild Donation Workflow Test Script
基于 guild_donation.yaml 的工作流测试工具

功能:
1. 加载和验证工作流配置
2. 模拟执行工作流（不实际操作硬件）
3. 单步调试模式
4. 流程图可视化

Usage:
    python test.py --validate    # 验证工作流配置
    python test.py --simulate    # 模拟执行工作流
    python test.py --step        # 单步调试模式
    python test.py --graph       # 输出流程图
    python test.py --full        # 完整测试（验证+模拟）
"""

import sys
import io
import time
import argparse
from pathlib import Path
from typing import Optional, Tuple, Any
from dataclasses import dataclass

# Fix Windows console encoding for Chinese output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config_loader import load_workflow_config, ConfigLoadError
from core.workflow_compiler import WorkflowCompilationError
from core.workflow_schema import WorkflowStep, CompiledWorkflow


@dataclass
class MockScreenshot:
    """模拟截图数据"""
    width: int = 2560
    height: int = 1440


class MockController:
    """
    模拟硬件控制器 - 只打印操作不实际执行
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.action_log = []

    def _log(self, action: str, details: str = ""):
        """记录操作日志"""
        entry = f"[Controller] {action} {details}".strip()
        self.action_log.append(entry)
        if self.verbose:
            print(f"  → {entry}")

    def click(self, x: int, y: int):
        self._log("CLICK", f"坐标: ({x}, {y})")

    def move_and_click(self, x: int, y: int):
        self._log("MOVE_AND_CLICK", f"坐标: ({x}, {y})")

    def move_absolute(self, x: int, y: int):
        self._log("MOVE", f"绝对坐标: ({x}, {y})")

    def press(self, key: str):
        self._log("PRESS", f"按键: {key}")

    def scroll(self, direction: str, ticks: int):
        self._log("SCROLL", f"方向: {direction},  ticks: {ticks}")

    def wait(self, seconds: float):
        self._log("WAIT", f"时长: {seconds:.3f}s")

    def _send_command(self, cmd: str):
        self._log("SERIAL", f"命令: {cmd}")


class MockVisionEngine:
    """
    模拟视觉引擎 - 模拟图像检测结果
    """

    def __init__(self, mock_detection_results: dict = None):
        """
        Args:
            mock_detection_results: 模拟检测结果字典 {image_name: (found, confidence)}
        """
        self.mock_results = mock_detection_results or {}
        self.detection_log = []

    def find_element(self, screenshot: Any, template_path: str, roi: Tuple[int, int, int, int] = None,
                     threshold: float = 0.8) -> Tuple[bool, float, Optional[Tuple[int, int]]]:
        """模拟图像检测"""

        # 从路径中提取图像名称
        image_name = template_path.split('/')[-1].split('\\')[-1]

        # 查找模拟结果，默认未找到
        found, confidence = self.mock_results.get(image_name, (False, 0.0))

        # 生成模拟位置（ROI中心）
        if roi and found:
            x1, y1, x2, y2 = roi
            location = ((x1 + x2) // 2, (y1 + y2) // 2)
        else:
            location = None

        self.detection_log.append({
            'image': image_name,
            'roi': roi,
            'threshold': threshold,
            'found': found,
            'confidence': confidence
        })

        return found, confidence, location

    def set_mock_result(self, image_name: str, found: bool, confidence: float = 0.85):
        """设置模拟检测结果"""
        self.mock_results[image_name] = (found, confidence)


def validate_workflow(workflow_path: str) -> bool:
    """验证工作流配置"""
    print(f"\n{'='*60}")
    print(f"[验证] 加载工作流配置: {workflow_path}")
    print(f"{'='*60}")

    try:
        compiled = load_workflow_config(workflow_path)
        print(f"[OK] 工作流名称: {compiled.name}")
        print(f"[OK] 起始步骤: {compiled.start_step_id}")
        print(f"[OK] 步骤数量: {len(compiled.steps)}")
        print(f"[OK] 默认超时: {compiled.wait_defaults.timeout_ms}ms")
        print(f"[OK] 轮询间隔: {compiled.wait_defaults.poll_interval_ms}ms")
        print(f"\n[SUCCESS] 工作流配置验证通过！")
        return True

    except FileNotFoundError as e:
        print(f"\n[ERROR] 文件未找到: {e}")
        return False
    except ConfigLoadError as e:
        print(f"\n[ERROR] 配置加载错误: {e}")
        return False
    except WorkflowCompilationError as e:
        print(f"\n[ERROR] 工作流编译错误: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] 未知错误: {type(e).__name__}: {e}")
        return False


def simulate_workflow(workflow_path: str, mock_results: dict = None, use_real_hardware: bool = False, port: str = "COM2"):
    """执行工作流（模拟或真实硬件）"""
    mode_str = "[真实硬件执行]" if use_real_hardware else "[模拟执行]"
    print(f"\n{'='*60}")
    print(f"{mode_str} 工作流: {workflow_path}")
    print(f"{'='*60}")

    try:
        from core.workflow_bootstrap import create_workflow_executor
    except ImportError as e:
        print(f"[ERROR] 无法导入 workflow_bootstrap: {e}")
        return

    if use_real_hardware:
        # 使用真实硬件
        try:
            from core.ferrum_controller import FerrumController
            from core.vision_engine import VisionEngine
            print(f"[硬件] 正在连接 Ferrum 设备 (端口: {port})...")
            controller = FerrumController(port=port, baudrate=115200)
            print(f"[硬件] 设备连接成功!")
            vision = VisionEngine()
        except Exception as e:
            print(f"[ERROR] 硬件连接失败: {e}")
            return
    else:
        # 创建模拟组件
        controller = MockController(verbose=True)
        vision = MockVisionEngine(mock_detection_results=mock_results)

    try:
        # 创建工作流执行器
        executor = create_workflow_executor(
            workflow_path=workflow_path,
            controller=controller,
            vision_engine=vision,
            enable_compliance_guard=False  # 测试时禁用合规检查
        )

        # 3秒启动延迟，便于切换游戏窗口
        print(f"\n[等待] 3秒后执行工作流，请切换到游戏窗口...")
        for i in range(3, 0, -1):
            print(f"  {i}...")
            time.sleep(1)
        print("  开始执行!")
        print(f"{'-'*60}")

        # 执行工作流
        result = executor.execute()

        print(f"{'-'*60}")
        print(f"\n执行结果:")
        print(f"  成功: {'[YES]' if result.success else '[NO]'}")
        print(f"  执行步骤数: {result.steps_executed}")
        print(f"  最终步骤: {result.final_step_id}")
        print(f"  耗时: {result.duration_ms:.2f}ms" if result.duration_ms else "  耗时: N/A")

        if result.error:
            print(f"  错误: {type(result.error).__name__}: {result.error}")

    except Exception as e:
        print(f"\n[ERROR] 执行失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def step_through_workflow(workflow_path: str):
    """单步调试工作流"""
    print(f"\n{'='*60}")
    print(f"[单步调试] 工作流: {workflow_path}")
    print(f"{'='*60}")

    try:
        compiled = load_workflow_config(workflow_path)
    except Exception as e:
        print(f"[ERROR] 加载失败: {e}")
        return

    steps = compiled.steps
    step_index = {step.step_id: step for step in steps}

    current_step_id = compiled.start_step_id
    step_history = []

    print(f"\n工作流: {compiled.name}")
    print(f"总步骤数: {len(steps)}")
    print(f"\n可用命令:")
    print(f"  [Enter] - 执行当前步骤")
    print(f"  n       - 跳到下一步")
    print(f"  p       - 跳到上一步")
    print(f"  s       - 显示所有步骤")
    print(f"  i       - 显示当前步骤详情")
    print(f"  q       - 退出调试\n")

    while current_step_id:
        step = step_index.get(current_step_id)
        if not step:
            print(f"[ERROR] 步骤 {current_step_id} 不存在")
            break

        print(f"\n当前步骤: [{step.step_id}] {step.action.type}")

        cmd = input("  命令 (Enter/n/p/s/i/q): ").strip().lower()

        if cmd == 'q':
            print("退出调试")
            break
        elif cmd == 's':
            print(f"\n所有步骤:")
            for i, s in enumerate(steps, 1):
                marker = " →" if s.step_id == current_step_id else "  "
                print(f"{marker} {i}. [{s.step_id}] {s.action.type}")
        elif cmd == 'i':
            print_step_details(step)
        elif cmd == 'p' and step_history:
            current_step_id = step_history.pop()
        elif cmd == 'n':
            step_history.append(current_step_id)
            current_step_id = step.next
        elif cmd == '' or cmd == 'n':
            step_history.append(current_step_id)
            print_step_execution(step)
            current_step_id = step.next
        else:
            print("未知命令")

        if current_step_id is None:
            print(f"\n[DONE] 工作流执行完毕")
            break


def print_step_details(step: WorkflowStep):
    """打印步骤详情"""
    print(f"\n  步骤ID: {step.step_id}")
    print(f"  动作类型: {step.action.type}")

    action = step.action
    if hasattr(action, 'key_name'):
        print(f"  按键: {action.key_name}")
    if hasattr(action, 'x') and hasattr(action, 'y'):
        print(f"  坐标: ({action.x}, {action.y})")
    if hasattr(action, 'roi') and action.roi:
        print(f"  ROI: {action.roi}")
    if hasattr(action, 'image') and action.image:
        print(f"  图像: {action.image}")
    if hasattr(action, 'duration_ms'):
        print(f"  等待时长: {action.duration_ms}ms")
    if hasattr(action, 'timeout_ms') and action.timeout_ms:
        print(f"  超时: {action.timeout_ms}ms")

    if step.next:
        print(f"  下一步: {step.next}")
    if step.on_true:
        print(f"  条件为真: {step.on_true}")
    if step.on_false:
        print(f"  条件为假: {step.on_false}")
    if step.condition:
        print(f"  条件: {step.condition}")


def print_step_execution(step: WorkflowStep):
    """打印步骤执行信息"""
    action = step.action
    print(f"  执行: {action.type}", end="")

    if action.type == 'press':
        print(f" → 按键 '{action.key_name}'")
    elif action.type == 'click':
        print(f" → 点击 ({action.x}, {action.y})")
    elif action.type == 'click_detected':
        print(f" → 检测并点击 {action.image}")
    elif action.type == 'wait':
        print(f" → 等待 {action.duration_ms}ms")
    elif action.type == 'wait_image':
        print(f" → 等待图像 '{action.image}' {action.state}")
    elif action.type == 'scroll':
        print(f" → 滚动 {action.direction} {action.ticks}")
    else:
        print()


def print_workflow_graph(workflow_path: str):
    """打印工作流流程图（Mermaid格式）"""
    print(f"\n{'='*60}")
    print(f"[流程图] 工作流: {workflow_path}")
    print(f"{'='*60}")

    try:
        compiled = load_workflow_config(workflow_path)
    except Exception as e:
        print(f"[ERROR] 加载失败: {e}")
        return

    print("\n```mermaid")
    print("flowchart TD")

    steps = compiled.steps
    step_index = {step.step_id: step for step in steps}

    # 定义节点
    for step in steps:
        action_type = step.action.type
        node_label = f"{step.step_id}<br/>{action_type}"

        if step.step_id == compiled.start_step_id:
            print(f"    Start([开始]) --> {step.step_id}")

        # 根据类型使用不同形状
        if step.on_true or step.on_false:
            print(f"    {step.step_id}{{{node_label}}}")  # 菱形判断
        else:
            print(f"    {step.step_id}[{node_label}]")  # 矩形

    # 定义连接
    for step in steps:
        if step.next:
            print(f"    {step.step_id} --> {step.next}")
        if step.on_true:
            print(f"    {step.step_id} -->|是| {step.on_true}")
        if step.on_false:
            print(f"    {step.step_id} -->|否| {step.on_false}")

        # 恢复路径
        if step.recovery and step.recovery.on_timeout:
            print(f"    {step.step_id} -.->|超时恢复| {step.recovery.on_timeout}")

    print("    workflow_complete --> End([结束])")
    print("    no_support_today --> End")
    print("```")


def run_full_test(workflow_path: str):
    """运行完整测试"""
    print(f"\n{'#'*60}")
    print(f"# Guild Donation Workflow 完整测试")
    print(f"{'#'*60}")

    # 1. 验证配置
    if not validate_workflow(workflow_path):
        return

    # 2. 显示流程图
    print_workflow_graph(workflow_path)

    # 3. 模拟执行（场景1：有支援金）
    print(f"\n{'='*60}")
    print("[场景1] 模拟执行 - 有支援金捐献")
    print(f"{'='*60}")
    mock_results_with_support = {
        'guild_first_confirm.bmp': (False, 0.0),  # 无首次确认弹窗
        'guild_first_donation.bmp': (True, 0.92),  # 找到首次捐赠按钮
        'guild_first_donation2.bmp': (True, 0.91),  # 找到二次捐赠按钮
        'guild_sec_donation1.bmp': (True, 0.88),  # 找到支援金捐献
        'guild_sec_donation2.bmp': (True, 0.87),  # 找到支援选项
        'guild_ui.bmp': (True, 0.95),  # 公会UI存在
    }
    simulate_workflow(workflow_path, mock_results_with_support, use_real_hardware=False)

    # 4. 模拟执行（场景2：无支援金）
    print(f"\n{'='*60}")
    print("[场景2] 模拟执行 - 无支援金捐献")
    print(f"{'='*60}")
    mock_results_no_support = {
        'guild_first_confirm.bmp': (False, 0.0),
        'guild_first_donation.bmp': (True, 0.92),
        'guild_first_donation2.bmp': (True, 0.91),
        'guild_sec_donation1.bmp': (False, 0.3),  # 未找到支援金捐献
        'guild_ui.bmp': (True, 0.95),
    }
    simulate_workflow(workflow_path, mock_results_no_support, use_real_hardware=False)

    print(f"\n{'#'*60}")
    print(f"# 测试完成")
    print(f"{'#'*60}")


def main():
    parser = argparse.ArgumentParser(
        description='Guild Donation Workflow Test Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python test.py --validate
    python test.py --simulate
    python test.py --real
    python test.py --real --port COM3
    python test.py --step
    python test.py --graph
    python test.py --full
        """
    )

    parser.add_argument('--validate', action='store_true',
                        help='验证工作流配置')
    parser.add_argument('--simulate', action='store_true',
                        help='模拟执行工作流（不操作硬件）')
    parser.add_argument('--real', action='store_true',
                        help='使用真实 Ferrum 硬件执行工作流')
    parser.add_argument('--port', type=str, default='COM2',
                        help='Ferrum 设备串口 (默认: COM2)')
    parser.add_argument('--step', action='store_true',
                        help='单步调试模式')
    parser.add_argument('--graph', action='store_true',
                        help='输出流程图')
    parser.add_argument('--full', action='store_true',
                        help='完整测试')
    parser.add_argument('--workflow', type=str,
                        default='config/workflows/guild_donation.yaml',
                        help='工作流配置文件路径 (默认: config/workflows/guild_donation.yaml)')

    args = parser.parse_args()

    # 如果没有指定任何参数，默认显示帮助
    if not any([args.validate, args.simulate, args.real, args.step, args.graph, args.full]):
        parser.print_help()
        return

    workflow_path = args.workflow

    if args.validate:
        validate_workflow(workflow_path)

    if args.simulate:
        simulate_workflow(workflow_path, use_real_hardware=False)

    if args.real:
        simulate_workflow(workflow_path, use_real_hardware=True, port=args.port)

    if args.step:
        step_through_workflow(workflow_path)

    if args.graph:
        print_workflow_graph(workflow_path)

    if args.full:
        run_full_test(workflow_path)


if __name__ == '__main__':
    main()
