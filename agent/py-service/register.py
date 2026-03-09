#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组件注册表 - 类似 MaaEnd 的 agent/go-service/register.go

所有自定义识别器和动作在此集中注册，实现模块化加载。
"""

from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass
import importlib
import pkgutil

# 全局注册表
_custom_recognitions: Dict[str, Callable] = {}
_custom_actions: Dict[str, Callable] = {}
_registered_modules: set = set()


@dataclass
class RecognitionResult:
    """识别结果结构 - MaaEnd 风格"""
    matched: bool
    box: Optional[tuple] = None  # [x, y, w, h]
    score: float = 0.0
    payload: Optional[dict] = None


class Registry:
    """组件注册表"""

    @staticmethod
    def register_recognition(name: str, func: Callable) -> Callable:
        """
        注册自定义识别器

        Args:
            name: 识别器名称，Pipeline JSON 中通过此名称引用
            func: 识别函数，接收 context 字典，返回 RecognitionResult
        """
        _custom_recognitions[name] = func
        print(f"[注册] 识别器: {name}")
        return func

    @staticmethod
    def register_action(name: str, func: Callable) -> Callable:
        """
        注册自定义动作

        Args:
            name: 动作名称，Pipeline JSON 中通过此名称引用
            func: 动作函数，接收 context 字典
        """
        _custom_actions[name] = func
        print(f"[注册] 动作: {name}")
        return func

    @staticmethod
    def get_recognition(name: str) -> Optional[Callable]:
        return _custom_recognitions.get(name)

    @staticmethod
    def get_action(name: str) -> Optional[Callable]:
        return _custom_actions.get(name)

    @staticmethod
    def list_recognitions() -> Dict[str, Callable]:
        return _custom_recognitions.copy()

    @staticmethod
    def list_actions() -> Dict[str, Callable]:
        return _custom_actions.copy()


# 便捷装饰器
def recognition(name: str):
    """识别器装饰器"""
    def decorator(func: Callable) -> Callable:
        return Registry.register_recognition(name, func)
    return decorator


def action(name: str):
    """动作装饰器"""
    def decorator(func: Callable) -> Callable:
        return Registry.register_action(name, func)
    return decorator


def register_all_modules():
    """
    自动发现并注册所有模块

    扫描 modules/ 目录下的所有 register.py 并执行
    """
    from . import modules

    for importer, modname, ispkg in pkgutil.iter_modules(modules.__path__):
        if ispkg:
            try:
                register_module = importlib.import_module(
                    f'.modules.{modname}.register',
                    package=__package__
                )
                if hasattr(register_module, 'register'):
                    register_module.register()
                    _registered_modules.add(modname)
            except Exception as e:
                print(f"[警告] 模块 {modname} 注册失败: {e}")

    print(f"[注册] 已完成 {len(_registered_modules)} 个模块加载")
