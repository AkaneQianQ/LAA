#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Python keyboard adapter tests."""

from __future__ import annotations

import pytest

from agent.py_service.pkg.input import python_keyboard as python_keyboard_module
from agent.py_service.pkg.input.python_keyboard import PythonKeyboardController


class FakeKeyboardLib:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def press(self, key_name: str) -> None:
        self.calls.append(("press", key_name))

    def release(self, key_name: str) -> None:
        self.calls.append(("release", key_name))


@pytest.fixture
def fake_keyboard(monkeypatch):
    fake = FakeKeyboardLib()
    monkeypatch.setattr(python_keyboard_module, "keyboard_lib", fake)
    return fake


def test_python_keyboard_press_uses_ferrum_key_names_for_single_key(fake_keyboard, monkeypatch):
    sleeps = []
    monkeypatch.setattr(python_keyboard_module.time, "sleep", sleeps.append)

    controller = PythonKeyboardController()
    controller.press("esc")

    assert fake_keyboard.calls == [
        ("press", "esc"),
        ("release", "esc"),
    ]
    assert sleeps == [
        python_keyboard_module.KEY_DOWN_DELAY_S,
        python_keyboard_module.KEY_HOLD_DELAY_S,
        python_keyboard_module.KEY_UP_DELAY_S,
    ]


def test_python_keyboard_press_orders_modifiers_like_ferrum(fake_keyboard, monkeypatch):
    sleeps = []
    monkeypatch.setattr(python_keyboard_module.time, "sleep", sleeps.append)

    controller = PythonKeyboardController()
    controller.press("alt+u")

    assert fake_keyboard.calls == [
        ("press", "alt"),
        ("press", "u"),
        ("release", "u"),
        ("release", "alt"),
    ]
    assert sleeps == [
        python_keyboard_module.KEY_DOWN_DELAY_S,
        python_keyboard_module.KEY_DOWN_DELAY_S,
        python_keyboard_module.KEY_HOLD_DELAY_S,
        python_keyboard_module.KEY_UP_DELAY_S,
        python_keyboard_module.KEY_UP_DELAY_S,
    ]


def test_python_keyboard_maps_ferrum_aliases_to_python_keys(fake_keyboard):
    controller = PythonKeyboardController()

    controller.key_down("lctrl+return")
    controller.key_up("lctrl+return")

    assert fake_keyboard.calls == [
        ("press", "left ctrl"),
        ("press", "enter"),
        ("release", "enter"),
        ("release", "left ctrl"),
    ]


def test_python_keyboard_rejects_unknown_ferrum_key_names(fake_keyboard):
    controller = PythonKeyboardController()

    with pytest.raises(ValueError):
        controller.press("numpad1")
