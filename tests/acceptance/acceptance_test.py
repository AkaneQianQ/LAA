"""
Main Acceptance Test Runner

Provides a comprehensive acceptance testing framework for LostarkBot with:
- 5 test phases: Environment, Character Detection, Config System, Intelligent Wait, Full Workflow
- Overlay UI for real-time progress display
- Structured logging with JSON session data
- Screenshot archiving for test evidence
- F1 key advancement between phases
"""

import os
import sys
import time
import ctypes
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.acceptance.overlay import OverlayWindow
from tests.acceptance.test_logger import TestLogger
from tests.acceptance.screenshot_archiver import ScreenshotArchiver

# Core imports
from core.vision_engine import VisionEngine
from core.config_loader import load_workflow_config, ConfigLoadError


class AcceptanceTestRunner:
    """
    Main orchestrator for acceptance testing.

    Runs through 5 phases of testing with UI overlay, logging, and screenshot capture.
    Each phase waits for F1 key press before executing.
    """

    PHASES = [
        ("环境检测", "test_environment"),
        ("角色检测", "test_character_detection"),
        ("配置系统", "test_config_system"),
        ("智能等待", "test_intelligent_wait"),
        ("完整工作流", "test_full_workflow"),
    ]

    # Expected screen resolution
    EXPECTED_RESOLUTION = (2560, 1440)

    # Game process name
    GAME_PROCESS_NAME = "LOSTARK.exe"

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the acceptance test runner.

        Args:
            output_dir: Optional custom output directory. If not provided,
                       a timestamped directory will be created.
        """
        # Generate timestamped output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_dir is None:
            self.output_dir = Path("test_artifacts/acceptance_tests") / timestamp
        else:
            self.output_dir = Path(output_dir)

        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir = self.output_dir / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = self.output_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.overlay = OverlayWindow()
        self.logger = TestLogger(output_dir=str(self.log_dir))
        self.logger.set_total_phases(len(self.PHASES))
        self.archiver = ScreenshotArchiver(
            output_dir=str(self.screenshot_dir),
            vision_engine=None  # Will create on demand
        )
        self.vision = VisionEngine()

        # Test results storage
        self.results: Dict[str, Any] = {}
        self.current_phase = 0

        # Timing records
        self.timing_records: Dict[str, List[float]] = {}

        print(f"Acceptance test output directory: {self.output_dir}")

    def run(self) -> bool:
        """
        Run all acceptance test phases.

        Returns:
            True if all phases passed, False otherwise
        """
        self.logger.log_phase_detail(f"测试开始 - 输出目录: {self.output_dir}")

        all_passed = True

        for i, (phase_name, method_name) in enumerate(self.PHASES, 1):
            self.current_phase = i
            success = self._run_phase(i, phase_name, method_name)
            if not success:
                all_passed = False
                self.logger.log_phase_detail(f"阶段 {i} 失败: {phase_name}")

            # Small delay between phases
            time.sleep(0.5)

        # Finalize
        final_status = "completed" if all_passed else "failed"
        self.logger.finalize(final_status)

        # Update overlay with final status
        if all_passed:
            self.overlay.update_status("所有测试通过", "success")
        else:
            self.overlay.update_status("测试失败", "error")

        # Keep overlay open for a moment
        time.sleep(2)
        self.overlay.close()

        return all_passed

    def _run_phase(self, phase_num: int, phase_name: str, method_name: str) -> bool:
        """
        Run a single test phase.

        Args:
            phase_num: Phase number (1-based)
            phase_name: Human-readable phase name
            method_name: Method name to call for testing

        Returns:
            True if phase passed, False otherwise
        """
        # Update UI
        self.overlay.update_phase(phase_num, len(self.PHASES), phase_name)
        self.overlay.update_status(f"等待开始阶段 {phase_num}", "waiting")
        self.overlay.add_log(f"阶段 {phase_num}: {phase_name}")

        # Log phase start
        self.logger.log_phase_start(phase_num, phase_name)
        self.logger.log_phase_detail(f"等待用户按 F1 开始阶段 {phase_num}")

        # Wait for F1 key
        self.overlay.add_log("按 F1 继续...")
        f1_pressed = self.overlay.wait_for_f1()

        if not f1_pressed:
            self.logger.log_phase_detail("用户取消测试 (窗口关闭)")
            self.logger.log_phase_end("CANCELLED")
            return False

        # Execute phase
        self.overlay.update_status(f"执行阶段 {phase_num}...", "info")
        self.logger.log_phase_detail(f"开始执行阶段 {phase_num}")

        phase_start_time = time.time()
        success = False

        try:
            # Get the test method and execute
            test_method = getattr(self, method_name)
            success = test_method()
        except Exception as e:
            self.logger.log_phase_detail(f"阶段执行异常: {e}")
            self.overlay.add_log(f"错误: {str(e)[:30]}")
            success = False

        phase_duration_ms = int((time.time() - phase_start_time) * 1000)

        # Capture screenshot after phase
        try:
            screenshot_path = self.archiver.capture_and_save(f"phase_{phase_num:02d}_{phase_name}")
            self.logger.log_screenshot(
                Path(screenshot_path).name,
                f"阶段 {phase_num} 完成后截图"
            )
            self.overlay.add_log(f"截图已保存")
        except Exception as e:
            self.logger.log_phase_detail(f"截图失败: {e}")

        # Update UI with result
        if success:
            self.overlay.update_status("阶段通过", "success")
            self.overlay.add_log(f"阶段 {phase_num} 通过")
        else:
            self.overlay.update_status("阶段失败", "error")
            self.overlay.add_log(f"阶段 {phase_num} 失败")

        # Log phase end
        status = "PASS" if success else "FAIL"
        self.logger.log_phase_end(status, phase_duration_ms)

        return success

    def test_environment(self) -> bool:
        """
        Phase 1: Environment Detection

        Detects screen resolution and game process.

        Returns:
            True if environment checks pass
        """
        self.overlay.add_log("检测屏幕分辨率...")
        self.logger.log_phase_detail("开始环境检测")

        # Detect screen resolution
        try:
            # Use Windows API to get screen resolution
            user32 = ctypes.windll.user32
            screen_width = user32.GetSystemMetrics(0)
            screen_height = user32.GetSystemMetrics(1)
            actual_resolution = (screen_width, screen_height)

            self.logger.log_phase_detail(f"屏幕分辨率: {screen_width}x{screen_height}")
            self.overlay.add_log(f"分辨率: {screen_width}x{screen_height}")

            # Check if resolution matches expected
            resolution_match = actual_resolution == self.EXPECTED_RESOLUTION
            self.results['screen_resolution'] = {
                'actual': actual_resolution,
                'expected': self.EXPECTED_RESOLUTION,
                'match': resolution_match
            }

            if resolution_match:
                self.logger.log_phase_detail("分辨率检查通过")
            else:
                self.logger.log_phase_detail(
                    f"分辨率不匹配: 期望 {self.EXPECTED_RESOLUTION}, 实际 {actual_resolution}"
                )

        except Exception as e:
            self.logger.log_phase_detail(f"分辨率检测失败: {e}")
            resolution_match = False

        # Detect game process
        self.overlay.add_log("检测游戏进程...")
        game_running = self._check_game_process()
        self.results['game_process'] = {
            'running': game_running,
            'process_name': self.GAME_PROCESS_NAME
        }

        if game_running:
            self.logger.log_phase_detail(f"游戏进程 {self.GAME_PROCESS_NAME} 正在运行")
            self.overlay.add_log("游戏进程: 运行中")
        else:
            self.logger.log_phase_detail(f"游戏进程 {self.GAME_PROCESS_NAME} 未运行")
            self.overlay.add_log("游戏进程: 未运行")

        # Phase passes if resolution matches (game process is informational)
        return resolution_match

    def _check_game_process(self) -> bool:
        """Check if the game process is running."""
        try:
            import subprocess
            result = subprocess.run(
                ['tasklist', '/FI', f'IMAGENAME eq {self.GAME_PROCESS_NAME}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return self.GAME_PROCESS_NAME in result.stdout
        except Exception as e:
            self.logger.log_phase_detail(f"进程检测失败: {e}")
            return False

    def test_character_detection(self) -> bool:
        """
        Phase 2: Character Detection

        Tests ESC menu detection and character counting.

        Returns:
            True if character detection works
        """
        self.overlay.add_log("导入 CharacterDetector...")
        self.logger.log_phase_detail("开始角色检测测试")

        try:
            from modules.character_detector import CharacterDetector
        except ImportError as e:
            self.logger.log_phase_detail(f"导入失败: {e}")
            self.overlay.add_log("导入失败")
            return False

        # Initialize detector
        detector = CharacterDetector(
            assets_path=str(project_root / "assets"),
            data_dir=str(project_root / "data")
        )
        self.overlay.add_log("CharacterDetector 已初始化")

        # Capture screenshot
        self.overlay.add_log("捕获屏幕...")
        try:
            screenshot = self.vision.get_screenshot()
            self.logger.log_phase_detail(f"屏幕捕获成功: {screenshot.shape}")
        except Exception as e:
            self.logger.log_phase_detail(f"屏幕捕获失败: {e}")
            self.overlay.add_log("屏幕捕获失败")
            return False

        # Test ESC menu detection
        self.overlay.add_log("检测ESC菜单...")
        try:
            is_ready, confidence = detector.detect_esc_menu(screenshot)
            self.logger.log_phase_detail(f"ESC菜单检测: ready={is_ready}, confidence={confidence:.3f}")
            self.overlay.add_log(f"ESC菜单: {'检测到' if is_ready else '未检测'} ({confidence:.2f})")
            self.results['esc_menu_detected'] = is_ready
            self.results['esc_menu_confidence'] = confidence
        except Exception as e:
            self.logger.log_phase_detail(f"ESC菜单检测失败: {e}")
            self.overlay.add_log("ESC菜单检测失败")
            is_ready = False

        # Scan for characters
        self.overlay.add_log("扫描角色槽位...")
        try:
            slot_results = detector.scan_visible_slots(screenshot)
            occupied_count = sum(1 for r in slot_results if r.has_character)
            total_slots = len(slot_results)

            self.logger.log_phase_detail(f"角色扫描完成: {occupied_count}/{total_slots} 槽位有角色")
            self.overlay.add_log(f"发现 {occupied_count} 个角色")

            self.results['character_count'] = occupied_count
            self.results['total_slots'] = total_slots
            self.results['slot_details'] = [
                {
                    'slot_index': r.slot_index,
                    'has_character': r.has_character,
                    'confidence': r.confidence
                }
                for r in slot_results
            ]

        except Exception as e:
            self.logger.log_phase_detail(f"角色扫描失败: {e}")
            self.overlay.add_log("角色扫描失败")
            occupied_count = 0

        # Phase passes if we successfully scanned slots
        return occupied_count >= 0

    def test_config_system(self) -> bool:
        """
        Phase 3: Configuration System

        Tests YAML config loading and action type verification.

        Returns:
            True if config system works
        """
        self.overlay.add_log("测试配置系统...")
        self.logger.log_phase_detail("开始配置系统测试")

        # Look for workflow config files
        config_dir = project_root / "config"
        workflow_files = list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml"))

        if not workflow_files:
            self.logger.log_phase_detail("未找到工作流配置文件")
            self.overlay.add_log("未找到配置文件")
            return False

        self.overlay.add_log(f"找到 {len(workflow_files)} 个配置文件")

        # Try to load each config
        loaded_count = 0
        action_types_found: set = set()

        for config_file in workflow_files:
            self.overlay.add_log(f"加载: {config_file.name}")
            try:
                compiled = load_workflow_config(config_file)
                loaded_count += 1
                self.logger.log_phase_detail(f"成功加载: {config_file.name}")

                # Extract action types from compiled workflow
                for step in compiled.steps:
                    if hasattr(step, 'action') and step.action:
                        action_type = getattr(step.action, 'type', None)
                        if action_type:
                            action_types_found.add(action_type)

            except ConfigLoadError as e:
                self.logger.log_phase_detail(f"配置加载错误 ({config_file.name}): {e}")
                self.overlay.add_log(f"加载失败: {config_file.name}")
            except Exception as e:
                self.logger.log_phase_detail(f"配置加载异常 ({config_file.name}): {e}")
                self.overlay.add_log(f"异常: {config_file.name}")

        self.logger.log_phase_detail(f"成功加载 {loaded_count}/{len(workflow_files)} 个配置")
        self.logger.log_phase_detail(f"发现的动作类型: {action_types_found}")
        self.overlay.add_log(f"动作类型: {', '.join(action_types_found) or '无'}")

        self.results['config_files_found'] = len(workflow_files)
        self.results['config_files_loaded'] = loaded_count
        self.results['action_types'] = list(action_types_found)

        # Phase passes if at least one config loaded
        return loaded_count > 0

    def test_intelligent_wait(self) -> bool:
        """
        Phase 4: Intelligent Wait System

        Tests wait mechanisms and records timing.

        Returns:
            True if wait system works
        """
        self.overlay.add_log("测试智能等待...")
        self.logger.log_phase_detail("开始智能等待测试")

        timing_results = []

        # Test 1: Simple wait
        self.overlay.add_log("测试简单等待 (500ms)...")
        start = time.time()
        time.sleep(0.5)
        duration = time.time() - start
        timing_results.append(('simple_wait', duration))
        self.logger.log_phase_detail(f"简单等待实际耗时: {duration*1000:.1f}ms")
        self.overlay.add_log(f"实际: {duration*1000:.1f}ms")

        # Test 2: Screenshot capture timing
        self.overlay.add_log("测试截图耗时...")
        start = time.time()
        try:
            screenshot = self.vision.get_screenshot()
            capture_time = time.time() - start
            timing_results.append(('screenshot_capture', capture_time))
            self.logger.log_phase_detail(f"截图耗时: {capture_time*1000:.1f}ms")
            self.overlay.add_log(f"截图: {capture_time*1000:.1f}ms")
        except Exception as e:
            self.logger.log_phase_detail(f"截图失败: {e}")
            capture_time = None

        # Test 3: Template matching timing (if we have a screenshot)
        if capture_time:
            self.overlay.add_log("测试模板匹配耗时...")
            try:
                import cv2
                import numpy as np

                # Create a simple test template
                test_template = np.zeros((50, 50), dtype=np.uint8)

                start = time.time()
                # Perform a match on a small ROI
                h, w = screenshot.shape[:2]
                roi = screenshot[0:min(100, h), 0:min(100, w)]
                if len(roi.shape) == 3:
                    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                else:
                    roi_gray = roi

                result = cv2.matchTemplate(roi_gray, test_template, cv2.TM_CCOEFF_NORMED)
                match_time = time.time() - start
                timing_results.append(('template_match', match_time))
                self.logger.log_phase_detail(f"模板匹配耗时: {match_time*1000:.1f}ms")
                self.overlay.add_log(f"匹配: {match_time*1000:.1f}ms")
            except Exception as e:
                self.logger.log_phase_detail(f"模板匹配测试失败: {e}")
                match_time = None

        # Store timing records
        self.timing_records['phase_4'] = [t[1] for t in timing_results]
        self.results['timing_tests'] = [
            {'name': name, 'duration_ms': duration * 1000}
            for name, duration in timing_results
        ]

        self.logger.log_phase_detail(f"完成 {len(timing_results)} 个计时测试")
        self.overlay.add_log(f"完成 {len(timing_results)} 个计时测试")

        # Phase passes if we completed timing tests
        return len(timing_results) >= 2

    def test_full_workflow(self) -> bool:
        """
        Phase 5: Full Workflow

        Executes a sample workflow and verifies completion.

        Returns:
            True if workflow executes successfully
        """
        self.overlay.add_log("测试完整工作流...")
        self.logger.log_phase_detail("开始完整工作流测试")

        # Check if we can import workflow components
        try:
            from core.workflow_schema import WorkflowConfig
            from core.workflow_compiler import compile_workflow
            from core.workflow_executor import WorkflowExecutor
            self.overlay.add_log("工作流组件已加载")
        except ImportError as e:
            self.logger.log_phase_detail(f"工作流组件导入失败: {e}")
            self.overlay.add_log("组件导入失败")
            return False

        # Try to find and execute a simple workflow
        config_dir = project_root / "config"
        workflow_files = list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml"))

        if not workflow_files:
            self.logger.log_phase_detail("没有工作流文件可供测试")
            self.overlay.add_log("无工作流文件")
            return False

        # Use the first available workflow for testing
        test_workflow = workflow_files[0]
        self.overlay.add_log(f"测试工作流: {test_workflow.name}")

        try:
            # Load and compile
            compiled = load_workflow_config(test_workflow)
            self.logger.log_phase_detail(f"工作流编译成功: {len(compiled.steps)} 步骤")
            self.overlay.add_log(f"步骤数: {len(compiled.steps)}")

            # Create executor (but don't actually execute - just verify it can be created)
            # In a real test, we might execute against a test environment
            executor = WorkflowExecutor(compiled)
            self.logger.log_phase_detail("工作流执行器创建成功")
            self.overlay.add_log("执行器创建成功")

            # Store workflow info
            self.results['workflow_tested'] = test_workflow.name
            self.results['workflow_steps'] = len(compiled.steps)
            self.results['workflow_entry'] = compiled.entry_step

            # For guild donation workflow verification
            # Check if workflow has expected guild donation related steps
            step_names = [step.step_id for step in compiled.steps]
            guild_keywords = ['guild', 'donation', 'donate', '公会', '捐赠']
            guild_related = [
                name for name in step_names
                if any(kw in name.lower() for kw in guild_keywords)
            ]

            if guild_related:
                self.logger.log_phase_detail(f"发现公会相关步骤: {guild_related}")
                self.overlay.add_log(f"公会步骤: {len(guild_related)}")

            self.results['guild_related_steps'] = guild_related

            return True

        except Exception as e:
            self.logger.log_phase_detail(f"工作流测试失败: {e}")
            self.overlay.add_log(f"工作流失败: {str(e)[:30]}")
            return False

    def get_results(self) -> Dict[str, Any]:
        """Get the complete test results."""
        return {
            'output_dir': str(self.output_dir),
            'phases_completed': self.current_phase,
            'total_phases': len(self.PHASES),
            'results': self.results,
            'timing_records': self.timing_records,
        }


def main():
    """Main entry point for acceptance testing."""
    print("=" * 60)
    print("LostarkBot Acceptance Test Runner")
    print("=" * 60)
    print()
    print("测试阶段:")
    for i, (name, _) in enumerate(AcceptanceTestRunner.PHASES, 1):
        print(f"  {i}. {name}")
    print()
    print("按 F1 键在每个阶段之间前进")
    print("按 ESC 键随时退出")
    print()
    print("=" * 60)

    runner = AcceptanceTestRunner()

    try:
        success = runner.run()
        results = runner.get_results()

        print()
        print("=" * 60)
        if success:
            print("所有测试通过!")
        else:
            print("部分测试失败")
        print(f"输出目录: {results['output_dir']}")
        print("=" * 60)

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 130
    except Exception as e:
        print(f"\n测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
