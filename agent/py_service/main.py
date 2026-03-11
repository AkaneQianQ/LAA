#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FerrumBot Service Entry Point

MaaEnd 风格的服务入口，负责：
1. 加载 interface.json 配置
2. 初始化所有组件
3. 注册自定义识别器和动作
4. 提供任务执行入口
"""

import json
import sys
import os
import argparse
import time
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

# 项目根目录处理
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 核心导入
try:
    from agent.py_service.register import register_all_modules, Registry, RecognitionResult
    from agent.py_service.pkg.ferrum.controller import FerrumController
    from agent.py_service.pkg.makcu.controller import MakcuController
    from agent.py_service.pkg.input import HybridMakcuController
    from agent.py_service.pkg.vision.engine import VisionEngine
    from agent.py_service.pkg.vision.frame_cache import FrameCache
except ImportError as e:
    print(f"[错误] 模块导入失败: {e}")
    print(f"[调试] Python路径: {sys.path}")
    print(f"[调试] 当前文件: {__file__}")
    raise

# 版本信息
VERSION = "1.0.05"


class ServiceError(Exception):
    """服务错误基类"""
    pass


class ConfigError(ServiceError):
    """配置错误"""
    pass


class InitializationError(ServiceError):
    """初始化错误"""
    pass


def configure_debug_mode(enabled: bool) -> None:
    """
    Configure global debug logging mode.

    When enabled, turns on verbose logger output and sets env flags
    that downstream modules can read.
    """
    if enabled:
        os.environ["FERRUMBOT_DEBUG"] = "1"
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            force=True,
        )
        print("[调试] DEBUG 模式已开启（全日志）")
    else:
        os.environ.pop("FERRUMBOT_DEBUG", None)


def load_interface_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载 interface.json 配置文件

    Args:
        config_path: 配置文件路径，默认为 assets/interface.json

    Returns:
        解析后的配置字典

    Raises:
        ConfigError: 配置文件不存在或格式错误
    """
    if config_path is None:
        config_path = project_root / "assets" / "interface.json"
    else:
        config_path = Path(config_path)

    print(f"[配置] 加载配置文件: {config_path}")

    if not config_path.exists():
        raise ConfigError(f"配置文件不存在: {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"配置文件格式错误: {e}")
    except Exception as e:
        raise ConfigError(f"读取配置文件失败: {e}")

    # 验证必要字段
    required_fields = ['interface_version', 'name', 'controller', 'resource', 'task']
    for field in required_fields:
        if field not in config:
            raise ConfigError(f"配置缺少必要字段: {field}")

    print(f"[配置] 项目名称: {config['name']}")
    print(f"[配置] 版本: {config.get('version', 'unknown')}")
    print(f"[配置] 控制器数量: {len(config['controller'])}")
    print(f"[配置] 资源数量: {len(config['resource'])}")
    print(f"[配置] 任务数量: {len(config['task'])}")

    return config


def get_controller_config(config: Dict[str, Any], controller_name: Optional[str] = None) -> Dict[str, Any]:
    """
    获取控制器配置

    Args:
        config: interface.json 配置
        controller_name: 控制器名称，默认为第一个控制器

    Returns:
        控制器配置字典

    Raises:
        ConfigError: 未找到指定控制器
    """
    controllers = config.get('controller', [])

    if not controllers:
        raise ConfigError("配置中没有定义控制器")

    if controller_name is None:
        return controllers[0]

    for ctrl in controllers:
        if ctrl.get('name') == controller_name:
            return ctrl

    raise ConfigError(f"未找到控制器: {controller_name}")


def get_resource_config(config: Dict[str, Any], resource_name: Optional[str] = None) -> Dict[str, Any]:
    """
    获取资源配置

    Args:
        config: interface.json 配置
        resource_name: 资源名称，默认为第一个资源

    Returns:
        资源配置字典

    Raises:
        ConfigError: 未找到指定资源
    """
    resources = config.get('resource', [])

    if not resources:
        raise ConfigError("配置中没有定义资源")

    if resource_name is None:
        return resources[0]

    for res in resources:
        if res.get('name') == resource_name:
            return res

    raise ConfigError(f"未找到资源: {resource_name}")


def get_task_config(config: Dict[str, Any], task_name: str) -> Dict[str, Any]:
    """
    获取任务配置

    Args:
        config: interface.json 配置
        task_name: 任务名称

    Returns:
        任务配置字典

    Raises:
        ConfigError: 未找到指定任务
    """
    tasks = config.get('task', [])

    for task in tasks:
        if task.get('name') == task_name:
            return task

    raise ConfigError(f"未找到任务: {task_name}")


def list_available_tasks(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    列出所有可用任务

    Args:
        config: interface.json 配置

    Returns:
        任务列表，每项包含 name, label, description
    """
    tasks = config.get('task', [])
    return [
        {
            'name': task.get('name', ''),
            'label': task.get('label', ''),
            'description': task.get('description', '')
        }
        for task in tasks
    ]


@dataclass
class InitializedComponents:
    """初始化后的组件容器"""
    config: Dict[str, Any]
    controller_config: Dict[str, Any]
    resource_config: Dict[str, Any]
    hardware_controller: Optional[FerrumController] = None
    vision_engine: Optional[VisionEngine] = None
    frame_cache: Optional[FrameCache] = None


def create_hardware_controller(controller_config: Dict[str, Any]):
    """Create hardware controller from interface config."""
    serial_config = controller_config.get("serial", {})
    driver = str(controller_config.get("driver", "ferrum")).lower()
    input_config = controller_config.get("input", {})
    keyboard_via_python = bool(input_config.get("keyboard_via_python", False))

    controller_cls = FerrumController
    if driver == "makcu":
        controller_cls = HybridMakcuController if keyboard_via_python else MakcuController

    return controller_cls(
        port=serial_config.get("port", "COM2"),
        baudrate=serial_config.get("baudrate", 115200),
        timeout=serial_config.get("timeout", 1.0),
    )


def initialize(
    config_path: Optional[str] = None,
    controller_name: Optional[str] = None,
    controller_override: Optional[Dict[str, Any]] = None,
    resource_name: Optional[str] = None,
    skip_hardware: bool = False,
    test_mode: bool = False,
    debug_mode: bool = False
) -> InitializedComponents:
    """
    初始化所有组件

    Args:
        config_path: 配置文件路径
        controller_name: 控制器名称
        resource_name: 资源名称
        skip_hardware: 是否跳过硬件初始化（用于测试）
        test_mode: 测试模式，不实际连接硬件

    Returns:
        InitializedComponents 组件容器

    Raises:
        InitializationError: 初始化失败
    """
    print(f"\n{'='*50}")
    print(f"[服务] 启动 FerrumBot v{VERSION}")
    if debug_mode:
        print("[调试] 初始化阶段启用调试日志")
    print(f"{'='*50}\n")

    # Normalize runtime base directory so relative assets/data paths behave
    # the same in source runs and in PyInstaller portable builds.
    os.chdir(project_root)

    # 1. 加载配置
    try:
        config = load_interface_config(config_path)
    except ConfigError as e:
        raise InitializationError(f"配置加载失败: {e}")

    # 2. 获取控制器和资源配置
    controller_config = get_controller_config(config, controller_name)
    if controller_override:
        controller_config = json.loads(json.dumps(controller_config))
        serial_override = controller_override.get("serial", {})
        controller_config.setdefault("serial", {}).update(serial_override)
    resource_config = get_resource_config(config, resource_name)

    print(f"[配置] 使用控制器: {controller_config.get('name')}")
    print(f"[配置] 使用资源: {resource_config.get('name')}")

    # 3. 注册所有模块
    print("\n[注册] 开始加载模块...")
    try:
        register_all_modules()
        recognitions = Registry.list_recognitions()
        actions = Registry.list_actions()
        print(f"[注册] 已加载 {len(recognitions)} 个识别器, {len(actions)} 个动作")
        if debug_mode:
            print("[调试] 已注册识别器:")
            for name in sorted(recognitions.keys()):
                print(f"  - {name}")
            print("[调试] 已注册动作:")
            for name in sorted(actions.keys()):
                print(f"  - {name}")
    except Exception as e:
        print(f"[警告] 模块注册过程中出现错误: {e}")
        # 非致命错误，继续初始化

    # 4. 初始化视觉引擎
    print("\n[视觉] 初始化视觉引擎...")
    try:
        frame_cache = FrameCache()
        vision_engine = VisionEngine(frame_cache=frame_cache)
        print("[视觉] 视觉引擎已初始化")
    except Exception as e:
        raise InitializationError(f"视觉引擎初始化失败: {e}")

    # 5. 初始化硬件控制器
    hardware_controller = None
    if not skip_hardware and not test_mode:
        print("\n[硬件] 初始化硬件控制器...")
        try:
            serial_config = controller_config.get('serial', {})
            hardware_controller = create_hardware_controller(controller_config)
            print(f"[硬件] 已连接到 {serial_config.get('port', 'COM2')}")
        except Exception as e:
            if test_mode:
                print(f"[警告] 硬件连接失败（测试模式，继续）: {e}")
            else:
                raise InitializationError(f"硬件控制器初始化失败: {e}")
    else:
        print("[硬件] 跳过硬件初始化" + (" (测试模式)" if test_mode else ""))

    print(f"\n{'='*50}")
    print("[服务] 初始化完成")
    print(f"{'='*50}\n")

    return InitializedComponents(
        config=config,
        controller_config=controller_config,
        resource_config=resource_config,
        hardware_controller=hardware_controller,
        vision_engine=vision_engine,
        frame_cache=frame_cache
    )


def execute_recognition(
    name: str,
    screenshot: Any,
    vision_engine: VisionEngine,
    hardware_controller: Optional[FerrumController] = None,
    param: Optional[Dict] = None
) -> RecognitionResult:
    """
    执行已注册的自定义识别器

    Args:
        name: 识别器名称
        screenshot: 屏幕截图
        vision_engine: 视觉引擎实例
        hardware_controller: 硬件控制器实例（可选）
        param: 额外参数（可选）

    Returns:
        RecognitionResult 识别结果

    Raises:
        ValueError: 识别器未找到
    """
    func = Registry.get_recognition(name)
    if func is None:
        raise ValueError(f"未找到识别器: {name}")

    context = {
        'screenshot': screenshot,
        'vision_engine': vision_engine,
        'hardware_controller': hardware_controller,
        'param': param or {}
    }

    result = func(context)

    # 确保返回 RecognitionResult
    if not isinstance(result, RecognitionResult):
        # 兼容旧式返回
        if isinstance(result, bool):
            return RecognitionResult(matched=result)
        elif isinstance(result, dict):
            return RecognitionResult(
                matched=result.get('matched', False),
                box=result.get('box'),
                score=result.get('score', 0.0),
                payload=result.get('payload')
            )

    return result


def execute_action(
    name: str,
    screenshot: Any,
    vision_engine: VisionEngine,
    hardware_controller: Optional[FerrumController] = None,
    param: Optional[Dict] = None
) -> Any:
    """
    执行已注册的自定义动作

    Args:
        name: 动作名称
        screenshot: 屏幕截图
        vision_engine: 视觉引擎实例
        hardware_controller: 硬件控制器实例（可选）
        param: 额外参数（可选）

    Returns:
        动作执行结果

    Raises:
        ValueError: 动作未找到
    """
    func = Registry.get_action(name)
    if func is None:
        raise ValueError(f"未找到动作: {name}")

    context = {
        'screenshot': screenshot,
        'vision_engine': vision_engine,
        'hardware_controller': hardware_controller,
        'param': param or {}
    }

    return func(context)


def load_pipeline(pipeline_path: str) -> Dict[str, Any]:
    """
    加载 Pipeline JSON 文件

    Args:
        pipeline_path: Pipeline 文件路径

    Returns:
        Pipeline 节点字典

    Raises:
        ConfigError: 文件不存在或格式错误
    """
    # 处理相对路径
    full_path = project_root / pipeline_path

    if not full_path.exists():
        raise ConfigError(f"Pipeline 文件不存在: {full_path}")

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            pipeline = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Pipeline 格式错误: {e}")

    print(f"[Pipeline] 已加载: {pipeline_path} ({len(pipeline)} 个节点)")
    return pipeline


def _to_snake_case(name: str) -> str:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(name))
    return text.replace("-", "_").lower()


def resolve_entry_node(task_name: str, configured_entry: str, pipeline: Dict[str, Any]) -> str:
    """Resolve the real entry node name present in the pipeline."""
    if configured_entry in pipeline:
        return configured_entry

    normalized_keys = {str(key).lower(): str(key) for key in pipeline.keys()}
    configured_lower = str(configured_entry).lower()
    if configured_lower in normalized_keys:
        return normalized_keys[configured_lower]

    fallback_candidates = [
        f"{_to_snake_case(task_name)}Main",
        f"{_to_snake_case(configured_entry.removesuffix('Main'))}Main" if configured_entry.endswith("Main") else "",
    ]
    for candidate in fallback_candidates:
        if candidate and candidate in pipeline:
            return candidate
        candidate_lower = candidate.lower()
        if candidate_lower in normalized_keys:
            return normalized_keys[candidate_lower]

    return configured_entry


@dataclass
class ExecutionContext:
    """Pipeline 执行上下文"""
    vision_engine: VisionEngine
    hardware_controller: Optional[FerrumController]
    screenshot: Optional[Any] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    current_node: Optional[str] = None


def run_task(
    task_name: str,
    context: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None,
    controller_name: Optional[str] = None,
    controller_override: Optional[Dict[str, Any]] = None,
    test_mode: bool = False,
    debug_mode: bool = False,
    stop_event: Any = None,
) -> bool:
    """
    执行指定任务

    Args:
        task_name: 任务名称 (如 "GuildDonation", "CharacterSwitch")
        context: 可选执行上下文参数
        config_path: 配置文件路径
        test_mode: 测试模式，不实际执行硬件操作

    Returns:
        任务是否成功完成
    """
    print(f"\n[任务] 开始执行: {task_name}")

    # 1. 初始化组件
    try:
        components = initialize(
            config_path=config_path,
            controller_name=controller_name,
            controller_override=controller_override,
            test_mode=test_mode,
            skip_hardware=test_mode,
            debug_mode=debug_mode
        )
    except InitializationError as e:
        print(f"[错误] 初始化失败: {e}")
        return False

    # 2. 获取任务配置
    try:
        task_config = get_task_config(components.config, task_name)
        entry_node = task_config.get('entry', f'{task_name}Main')
        pipeline_path = task_config.get('pipeline')

        if not pipeline_path:
            print(f"[错误] 任务 {task_name} 没有定义 pipeline")
            return False

        print(f"[任务] 入口节点: {entry_node}")
        print(f"[任务] Pipeline: {pipeline_path}")
        if debug_mode:
            print(f"[调试] task config: {json.dumps(task_config, ensure_ascii=False)}")
    except ConfigError as e:
        print(f"[错误] 获取任务配置失败: {e}")
        return False

    # 3. 加载 Pipeline
    try:
        pipeline = load_pipeline(pipeline_path)
        resolved_entry_node = resolve_entry_node(task_name, entry_node, pipeline)
        if resolved_entry_node != entry_node:
            print(f"[任务] 入口节点已解析: {entry_node} -> {resolved_entry_node}")
            entry_node = resolved_entry_node
        if debug_mode:
            print(f"[调试] pipeline nodes ({len(pipeline)}): {', '.join(list(pipeline.keys())[:20])}")
    except ConfigError as e:
        print(f"[错误] 加载 Pipeline 失败: {e}")
        return False

    # 4. 执行 Pipeline (简化版本)
    if test_mode:
        print("\n[测试] 测试模式 - 跳过实际执行")
        print(f"[测试] 可用节点: {list(pipeline.keys())[:5]}...")
        return True

    # 5. 执行 Pipeline
    try:
        from agent.py_service.modules.workflow_executor.executor import execute_pipeline

        full_pipeline_path = project_root / pipeline_path
        return bool(
            execute_pipeline(
                pipeline_path=full_pipeline_path,
                entry_node=entry_node,
                hardware_controller=components.hardware_controller,
                vision_engine=components.vision_engine,
                stop_event=stop_event,
            )
        )
    except Exception as e:
        print(f"[错误] Pipeline 执行失败: {e}")
        return False


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        prog='FerrumBot',
        description='Lost Ark 公会捐赠自动化助手 - MaaEnd 风格服务入口'
    )

    parser.add_argument(
        '--version', '-v',
        action='version',
        version=f'FerrumBot {VERSION}'
    )

    parser.add_argument(
        '--config', '-c',
        type=str,
        default=None,
        help='interface.json 配置文件路径'
    )

    parser.add_argument(
        '--task', '-t',
        type=str,
        help='执行指定任务 (如 GuildDonation)'
    )

    parser.add_argument(
        '--list-tasks', '-l',
        action='store_true',
        help='列出所有可用任务'
    )

    parser.add_argument(
        '--test-init',
        action='store_true',
        help='测试初始化流程 (不连接硬件)'
    )

    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='测试模式 (不执行实际操作)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='开启调试模式（全日志输出）'
    )

    args = parser.parse_args()
    configure_debug_mode(args.debug)

    try:
        if args.list_tasks:
            # 列出任务
            config = load_interface_config(args.config)
            tasks = list_available_tasks(config)

            print(f"\n可用任务 ({len(tasks)} 个):")
            print("-" * 60)
            for task in tasks:
                print(f"  {task['name']:20s} - {task['label']}")
                if task['description']:
                    print(f"  {'':20s}   {task['description']}")
            print("-" * 60)
            return 0

        elif args.test_init:
            # 测试初始化
            print("[测试] 测试模式初始化...")
            components = initialize(
                config_path=args.config,
                test_mode=True,
                skip_hardware=True,
                debug_mode=args.debug
            )
            print("\n[成功] 初始化测试通过")
            print(f"  - 配置项: {len(components.config)} 项")
            print(f"  - 控制器: {components.controller_config.get('name')}")
            print(f"  - 资源: {components.resource_config.get('name')}")
            print(f"  - 视觉引擎: {'已初始化' if components.vision_engine else '未初始化'}")
            return 0

        elif args.task:
            # 执行任务
            success = run_task(
                task_name=args.task,
                config_path=args.config,
                controller_name=None,
                test_mode=args.test_mode,
                debug_mode=args.debug
            )
            return 0 if success else 1

        else:
            parser.print_help()
            return 0

    except KeyboardInterrupt:
        print("\n\n[用户] 操作已取消")
        return 130

    except Exception as e:
        print(f"\n[错误] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
