#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent trigger service tests."""

import sys
from pathlib import Path

import pytest

import launcher.trigger_service as trigger_service
from launcher.trigger_service import execute_offset_clicks, press_up_up_down, run_trigger_cycle
from launcher.trigger_service import DEFAULT_TRIGGER_CONFIG


def test_press_up_up_down_uses_string_key_names():
    calls = []

    class FakeHardware:
        def press(self, key_name):
            calls.append(key_name)

    press_up_up_down(FakeHardware())
    assert calls == ["up", "up", "down"]


def test_execute_offset_clicks_uses_last_detection_box():
    moves = []
    clicks = []
    presses = []
    sleeps = []

    class FakeHardware:
        def move_absolute(self, x, y):
            moves.append((x, y))

        def click_current(self):
            clicks.append("click")

        def press(self, key_name):
            presses.append(key_name)

    original_sleep = trigger_service.time.sleep
    trigger_service.time.sleep = sleeps.append
    try:
        execute_offset_clicks(
            hardware_controller=FakeHardware(),
            detected_pos=(500, 600),
            offsets=[[7, 0], [127, 0]],
            click_delay_ms=0,
        )
    finally:
        trigger_service.time.sleep = original_sleep

    assert moves == [(507, 600), (627, 600)]
    assert clicks == ["click", "click"]
    assert presses == ["enter"]
    assert sleeps == [0.05, 0.0, 0.05, 0.0, 0.05]


def test_run_trigger_cycle_executes_task_a_and_stops_before_task_b():
    calls = []

    class FakeVision:
        def find_element(self, screenshot, template_path, roi, threshold):
            if template_path.endswith("target_a.png"):
                return True, 0.95, (100, 200)
            return False, 0.0, (0, 0)

    class FakeHardware:
        def press(self, key_name):
            calls.append(("press", key_name))

        def move_absolute(self, x, y):
            calls.append(("move", x, y))

        def click_current(self):
            calls.append(("click",))

    run_trigger_cycle(FakeVision(), FakeHardware(), screenshot="frame", config={
        "TASK_A": {"IMAGE": "assets/target_a.png", "ROI": (1, 2, 3, 4), "COOLDOWN": 0},
        "TASK_B": {"IMAGES": ["assets/target_b_1.png"], "ROI": (1, 2, 3, 4), "OFFSETS": [(7, 0), (127, 0)], "COOLDOWN": 0},
    })

    assert calls == [("press", "up"), ("press", "up"), ("press", "down")]


def test_run_trigger_cycle_executes_task_b_when_task_a_not_matched():
    calls = []
    sleeps = []

    class FakeVision:
        def find_element(self, screenshot, template_path, roi, threshold):
            if template_path.endswith("target_b_2.png"):
                return True, 0.88, (300, 400)
            return False, 0.0, (0, 0)

    class FakeHardware:
        def press(self, key_name):
            calls.append(("press", key_name))

        def move_absolute(self, x, y):
            calls.append(("move", x, y))

        def click_current(self):
            calls.append(("click",))

    original_sleep = trigger_service.time.sleep
    original_get_template_center_point = trigger_service.get_template_center_point
    trigger_service.time.sleep = sleeps.append
    trigger_service.get_template_center_point = lambda path, box: (498, 420)
    try:
        run_trigger_cycle(FakeVision(), FakeHardware(), screenshot="frame", config={
            "TASK_A": {"IMAGE": "assets/resource/image/target_a.png", "ROI": (1, 2, 3, 4), "COOLDOWN": 0},
            "TASK_B": {
                "IMAGES": [
                    "assets/resource/image/target_b_1.png",
                    "assets/resource/image/target_b_2.png",
                ],
                "ROI": (1, 2, 3, 4),
                "OFFSETS": [(7, 0), (127, 0)],
                "COOLDOWN": 0,
            },
        })
    finally:
        trigger_service.time.sleep = original_sleep
        trigger_service.get_template_center_point = original_get_template_center_point

    assert calls == [
        ("move", 505, 420),
        ("click",),
        ("move", 625, 420),
        ("click",),
        ("press", "enter"),
    ]
    assert sleeps[0] == 0.15


def test_default_trigger_config_contains_expected_targets():
    assert DEFAULT_TRIGGER_CONFIG["TASK_A"]["IMAGE"] == "assets/resource/image/target_a.png"
    assert DEFAULT_TRIGGER_CONFIG["TASK_B"]["IMAGES"] == [
        "assets/resource/image/target_b_1.png",
        "assets/resource/image/target_b_2.png",
    ]


def test_resolve_trigger_asset_path_uses_internal_assets_for_frozen_bundle(tmp_path, monkeypatch):
    bundle_root = tmp_path / "bundle"
    internal_asset = bundle_root / "_internal" / "assets" / "resource" / "image" / "target_a.png"
    internal_asset.parent.mkdir(parents=True)
    internal_asset.write_bytes(b"fake")

    monkeypatch.setattr(trigger_service, "PROJECT_ROOT", bundle_root)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_root / "_internal"), raising=False)

    resolved = trigger_service.resolve_trigger_asset_path("assets/resource/image/target_a.png")

    assert resolved == str(internal_asset)


def test_resolve_trigger_asset_path_uses_project_assets_in_source_tree(tmp_path, monkeypatch):
    project_root = tmp_path / "repo"
    source_asset = project_root / "assets" / "resource" / "image" / "target_b_1.png"
    source_asset.parent.mkdir(parents=True)
    source_asset.write_bytes(b"fake")

    monkeypatch.setattr(trigger_service, "PROJECT_ROOT", project_root)
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    resolved = trigger_service.resolve_trigger_asset_path("assets/resource/image/target_b_1.png")

    assert resolved == str(source_asset)
