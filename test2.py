# -*- coding: utf-8 -*-
"""
公会捐献工作流 Step 5 测试脚本

功能：
1. 连接 Ferrum 硬件设备（KMBox）
2. 初始化 VisionEngine 视觉引擎
3. 测试 Step 5: 检测并点击支援金捐献
"""

import time
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.ferrum_controller import FerrumController, FerrumConnectionError
from core.vision_engine import VisionEngine
from core.workflow_bootstrap import create_workflow_executor


def main():
    print("=" * 50)
    print("公会捐献工作流 Step 5 测试")
    print("=" * 50)
    print()

    ferrum = None
    vision = None
    executor = None

    try:
        # Step 1: 连接 Ferrum 设备
        print("[1/3] 正在连接 Ferrum 硬件设备...")
        print(f"      端口: COM2, 波特率: 115200")

        try:
            ferrum = FerrumController(port="COM2", baudrate=115200, timeout=1.0)
            if ferrum.is_connected():
                print(f"      [OK] Ferrum 设备连接成功!")
            else:
                print(f"      [FAIL] Ferrum 设备连接失败: 未知状态")
                return
        except FerrumConnectionError as e:
            print(f"      [FAIL] Ferrum 设备连接失败: {e}")
            print(f"\n      请检查:")
            print(f"        - KMBox 设备是否已连接到电脑")
            print(f"        - 设备管理器中是否显示 COM 端口")
            print(f"        - 端口号是否正确 (默认 COM2)")
            return
        except Exception as e:
            print(f"      [FAIL] 连接过程中发生错误: {e}")
            return

        print()

        # Step 2: 初始化 VisionEngine
        print("[2/3] 正在初始化 VisionEngine...")
        vision = VisionEngine()
        print(f"      [OK] VisionEngine 初始化完成")

        print()

        # Step 3: 加载工作流执行器
        print("[3/3] 正在加载公会捐献工作流...")
        workflow_path = "config/workflows/guild_donation.yaml"

        if not os.path.exists(workflow_path):
            print(f"      [FAIL] 工作流文件不存在: {workflow_path}")
            return

        try:
            executor = create_workflow_executor(
                workflow_path=workflow_path,
                controller=ferrum,
                vision_engine=vision,
                enable_compliance_guard=True
            )
            print(f"      [OK] 工作流加载成功: {executor.workflow.name}")
            print(f"      [OK] 起始步骤: {executor.workflow.start_step_id}")
            print(f"      [OK] 总步骤数: {len(executor.workflow.steps)}")
        except Exception as e:
            print(f"      [FAIL] 工作流加载失败: {e}")
            import traceback
            traceback.print_exc()
            return

        print()
        print("=" * 50)
        print("准备执行 Step 5 测试")
        print("=" * 50)
        print()
        print("请在 2 秒内切换到游戏窗口...")
        time.sleep(2)

        # Step 5 测试: 检测 guild_sec_donation1
        print()
        print("[执行] 开始执行 Step 5: check_sec_donation...")
        print("       检测 guild_sec_donation1.bmp (ROI: 1551,606,1693,635)")
        print()

        # 获取 step5
        step5 = executor.workflow.get_step("check_sec_donation")
        if step5 is None:
            print("[FAIL] Step 5 不存在于工作流中")
            return

        # 使用 ConditionEvaluator 检测 guild_sec_donation1
        from core.workflow_runtime import ConditionEvaluator
        evaluator = ConditionEvaluator(vision)
        condition_result = evaluator.evaluate(step5)

        print(f"[结果] 检测状态: {'检测到' if condition_result else '未检测到'}")

        if condition_result:
            print("[执行] 执行 click_sec_donation1 (点击检测位置)...")
            click_step = executor.workflow.get_step("click_sec_donation1")
            if click_step:
                from core.workflow_runtime import ActionDispatcher
                dispatcher = ActionDispatcher(ferrum, vision)
                try:
                    dispatcher.dispatch(click_step)
                    print("[OK] guild_sec_donation1 点击完成")
                except Exception as e:
                    print(f"[FAIL] guild_sec_donation1 点击失败: {e}")
                    print("[执行] 按下 ESC 键...")
                    ferrum.press("esc")
                    return

            # Step 5b: 等待 guild_sec_donation2 出现
            print()
            print("[Step 5b] 等待 guild_sec_donation2.bmp 出现 (ROI: 1010,602,1253,795)...")

            wait_step = executor.workflow.get_step("wait_sec_donation2")
            donation2_success = False
            if wait_step:
                try:
                    dispatcher = ActionDispatcher(ferrum, vision)
                    dispatcher.dispatch(wait_step)
                    print("[OK] guild_sec_donation2 已检测到")
                    donation2_success = True
                except Exception as e:
                    print(f"[FAIL] 等待 guild_sec_donation2 失败: {e}")

            # Step 5c: 点击检测到的 guild_sec_donation2 位置
            if donation2_success:
                print()
                print("[Step 5c] 点击检测到的 guild_sec_donation2 位置...")
                click_step2 = executor.workflow.get_step("click_sec_donation2")
                if click_step2:
                    try:
                        dispatcher = ActionDispatcher(ferrum, vision)
                        dispatcher.dispatch(click_step2)
                        print("[OK] 检测位置点击完成")
                    except Exception as e:
                        print(f"[FAIL] 检测位置点击失败: {e}")

                # Step 5d: 点击固定坐标 (1229, 937) Y随机+/-5像素
                print()
                print("[Step 5d] 点击固定坐标 (1229, 937) Y随机+/-5像素...")
                click_step2_fixed = executor.workflow.get_step("click_sec_donation2_fixed")
                if click_step2_fixed:
                    try:
                        dispatcher = ActionDispatcher(ferrum, vision)
                        dispatcher.dispatch(click_step2_fixed)
                        print("[OK] 固定坐标点击完成")
                    except Exception as e:
                        print(f"[FAIL] 固定坐标点击失败: {e}")

                # 输出最终结果（不触发ESC）
                print()
                print("=" * 50)
                print("支援金捐献完成!")
                print("=" * 50)
            else:
                # 检测失败时才按ESC
                print()
                print("[执行] 检测失败，按下 ESC 键关闭界面...")
                ferrum.press("esc")
                print("[OK] ESC 已发送")
        else:
            # 未检测到 - 当日无支援
            print()
            print("[信息] 当日无支援")
            print("[执行] 按下 ESC 键...")
            ferrum.press("esc")
            print("[OK] ESC 已发送")

            print()
            print("=" * 50)
            print("当日无支援，流程中断")
            print("=" * 50)

    except KeyboardInterrupt:
        print("\n\n[!] 用户中断测试")
    except Exception as e:
        print(f"\n[!] 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        if ferrum:
            print("\n[清理] 关闭 Ferrum 设备连接...")
            ferrum.close()
            print("       [OK] 设备已关闭")


if __name__ == "__main__":
    main()
    input("\n按 Enter 键退出...")
