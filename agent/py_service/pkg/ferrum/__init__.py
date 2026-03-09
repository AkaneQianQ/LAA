#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ferrum hardware controller package.

Provides KMBox serial device communication for ACE-compliant
hardware-based input simulation.
"""

from .controller import FerrumController, ControllerConfig

__all__ = ["FerrumController", "ControllerConfig"]
