#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workflow runtime regression tests."""

from __future__ import annotations

from types import SimpleNamespace

from agent.py_service.pkg.workflow.runtime import ActionDispatcher
from agent.py_service.pkg.workflow.schema import ClickAction, ClickDetectedAction


def test_dispatch_click_fallback_uses_public_controller_interface_only():
    calls: list[tuple[str, int, int] | tuple[str]] = []

    class FakeController:
        def move_absolute(self, x: int, y: int) -> None:
            calls.append(("move_absolute", x, y))

        def click_current(self) -> None:
            calls.append(("click_current",))

        def _send_command(self, command: str) -> None:
            raise AssertionError(f"runtime should not bypass controller API: {command}")

    dispatcher = ActionDispatcher(controller=FakeController())
    action = ClickAction(type="click", x=321, y=654)

    dispatcher._dispatch_click(action)

    assert calls == [
        ("move_absolute", 321, 654),
        ("click_current",),
    ]


def test_dispatch_click_detected_fallback_uses_public_controller_interface_only(monkeypatch):
    calls: list[tuple[str, int, int] | tuple[str]] = []

    class FakeController:
        def move_absolute(self, x: int, y: int) -> None:
            calls.append(("move_absolute", x, y))

        def click_current(self) -> None:
            calls.append(("click_current",))

        def _send_command(self, command: str) -> None:
            raise AssertionError(f"runtime should not bypass controller API: {command}")

    class FakeVision:
        def find_element(self, screenshot, image, roi, threshold):
            return True, 0.95, (100, 200)

    dispatcher = ActionDispatcher(controller=FakeController(), vision_engine=FakeVision())
    monkeypatch.setattr(dispatcher, "_capture_screenshot", lambda: object())
    monkeypatch.setattr(
        dispatcher,
        "_check_image_present",
        lambda image, roi, threshold=0.8, debug=False: True,
        raising=False,
    )

    import cv2

    monkeypatch.setattr(cv2, "imread", lambda path, mode: None)

    action = ClickDetectedAction(
        type="click_detected",
        image="assets/resource/image/fake.png",
        roi=(10, 20, 110, 220),
        threshold=0.8,
    )
    step = SimpleNamespace(action=action)

    dispatcher._dispatch_click_detected(action, step)

    assert calls == [
        ("move_absolute", 60, 120),
        ("click_current",),
    ]
