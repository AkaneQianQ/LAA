#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recovery and error handling package.

Provides three-tier error recovery (L1 retry, L2 rollback, L3 skip)
and orchestration for automation workflows.
"""

from .orchestrator import RecoveryOrchestrator

__all__ = ["RecoveryOrchestrator"]
