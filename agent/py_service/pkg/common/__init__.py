#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Common utilities and shared components.

Provides database access, logging, and other shared infrastructure.
"""

from .database import (
    init_database,
    create_account,
    get_or_create_account,
    upsert_character,
    list_characters_by_account,
    list_all_accounts,
)

__all__ = [
    "init_database",
    "create_account",
    "get_or_create_account",
    "upsert_character",
    "list_characters_by_account",
    "list_all_accounts",
]
