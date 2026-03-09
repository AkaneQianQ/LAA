#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow Executor Module

Modular pipeline execution for YAML-defined workflows.
"""

from .executor import execute_pipeline, create_executor

__all__ = ['execute_pipeline', 'create_executor']
