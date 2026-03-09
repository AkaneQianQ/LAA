#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兼容层 - 转发到新位置

此模块提供向后兼容性，将旧导入路径转发到新的 MaaEnd 风格结构。
新项目代码应直接使用 agent.py_service.modules 中的模块。
"""

# Forward imports to new locations
from agent.py_service.modules.character.detector import CharacterDetector

__all__ = [
    "CharacterDetector",
]
