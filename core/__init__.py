#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兼容层 - 转发到新位置

此模块提供向后兼容性，将旧导入路径转发到新的 MaaEnd 风格结构。
新项目代码应直接使用 agent.py_service.pkg 中的模块。
"""

# Forward imports to new locations
from agent.py_service.pkg.ferrum.controller import FerrumController
from agent.py_service.pkg.vision.engine import VisionEngine
from agent.py_service.pkg.workflow.bootstrap import WorkflowBootstrap
from agent.py_service.pkg.workflow.compiler import WorkflowCompiler
from agent.py_service.pkg.workflow.executor import WorkflowExecutor
from agent.py_service.pkg.workflow.runtime import ActionDispatcher, ConditionEvaluator
from agent.py_service.pkg.workflow.schema import WorkflowSchema
from agent.py_service.pkg.recovery.orchestrator import RecoveryOrchestrator
from agent.py_service.pkg.common.database import Database

__all__ = [
    "FerrumController",
    "VisionEngine",
    "WorkflowBootstrap",
    "WorkflowCompiler",
    "WorkflowExecutor",
    "ActionDispatcher",
    "ConditionEvaluator",
    "WorkflowSchema",
    "RecoveryOrchestrator",
    "Database",
]
