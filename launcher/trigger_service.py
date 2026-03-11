#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent trigger-task runtime helpers."""

from __future__ import annotations

import cv2
import os
import sys
import time
from pathlib import Path
from threading import Event
from typing import Callable, Optional

from agent.py_service import main as service_main
from agent.py_service.pkg.vision.engine import VisionEngine
from agent.py_service.pkg.vision.frame_cache import FrameCache

from launcher.service import (
    apply_controller_override,
    append_probe_log,
    build_controller_override,
    resolve_controller_config,
    resolve_controller_name,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRIGGER_LOG_PATH = PROJECT_ROOT / "logs" / "trigger_runtime.log"


DEFAULT_TRIGGER_CONFIG = {
    "TASK_A": {
        "IMAGE": "assets/resource/image/target_a.png",
        "ROI": (1088, 700, 1482, 846),
        "COOLDOWN": 0.3,
    },
    "TASK_B": {
        "IMAGES": [
            "assets/resource/image/target_b_1.png",
            "assets/resource/image/target_b_2.png",
        ],
        "ROI": (1280, 0, 2560, 1440),
        "OFFSETS": [(7, 0), (127, 0)],
        "COOLDOWN": 0.3,
    },
}

TRIGGER_MATCH_STABILIZE_S = 0.15
TRIGGER_MOVE_SETTLE_S = 0.05
TRIGGER_ENTER_SETTLE_S = 0.05


def append_trigger_log(message: str) -> None:
    TRIGGER_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with TRIGGER_LOG_PATH.open("a", encoding="utf-8") as fp:
        fp.write(f"[{timestamp}] {message}\n")


def resolve_trigger_asset_path(relative_path: str) -> str:
    candidate = Path(relative_path)
    if candidate.is_absolute() and candidate.exists():
        return str(candidate)

    search_roots = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        search_roots.append(Path(meipass))
    search_roots.append(PROJECT_ROOT)
    search_roots.append(PROJECT_ROOT / "_internal")

    normalized = Path(relative_path)
    for root in search_roots:
        resolved = root / normalized
        if resolved.exists():
            return str(resolved)

    return str((search_roots[0] / normalized) if search_roots else normalized)


def resolve_trigger_config_paths(config: dict) -> dict:
    resolved = {
        "TASK_A": dict(config["TASK_A"]),
        "TASK_B": dict(config["TASK_B"]),
    }
    resolved["TASK_A"]["IMAGE"] = resolve_trigger_asset_path(str(config["TASK_A"]["IMAGE"]))
    resolved["TASK_B"]["IMAGES"] = [
        resolve_trigger_asset_path(str(image_path))
        for image_path in config["TASK_B"]["IMAGES"]
    ]
    return resolved


def get_template_center_point(template_path: str, match_top_left: tuple[int, int]) -> tuple[int, int]:
    """Convert a template-match top-left point into a template center point."""
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        return int(match_top_left[0]), int(match_top_left[1])

    height, width = template.shape[:2]
    return int(match_top_left[0] + (width / 2)), int(match_top_left[1] + (height / 2))


def press_up_up_down(hardware_controller) -> None:
    hardware_controller.press("up")
    time.sleep(0.05)
    hardware_controller.press("up")
    time.sleep(0.05)
    hardware_controller.press("down")


def execute_offset_clicks(
    hardware_controller,
    detected_pos,
    offsets,
    click_delay_ms: int,
) -> None:
    cx, cy = int(detected_pos[0]), int(detected_pos[1])
    for dx, dy in offsets:
        hardware_controller.move_absolute(cx + int(dx), cy + int(dy))
        time.sleep(TRIGGER_MOVE_SETTLE_S)
        hardware_controller.click_current()
        time.sleep(click_delay_ms / 1000.0)
    time.sleep(TRIGGER_ENTER_SETTLE_S)
    hardware_controller.press("enter")


def run_trigger_cycle(
    vision_engine,
    hardware_controller,
    screenshot,
    config: Optional[dict] = None,
    log_writer: Optional[Callable[[str], None]] = None,
) -> bool:
    """Run one trigger scan cycle. Returns True if any trigger fired."""
    config = config or DEFAULT_TRIGGER_CONFIG
    writer = log_writer or (lambda message: None)

    matched, _, box = vision_engine.find_element(
        screenshot,
        template_path=config["TASK_A"]["IMAGE"],
        roi=tuple(config["TASK_A"]["ROI"]),
        threshold=0.8,
    )
    if matched:
        writer(f"[Trigger] Task A matched at {box}")
        press_up_up_down(hardware_controller)
        time.sleep(float(config["TASK_A"].get("COOLDOWN", 0.3)))
        return True

    for image_path in config["TASK_B"]["IMAGES"]:
        matched, _, box = vision_engine.find_element(
            screenshot,
            template_path=image_path,
            roi=tuple(config["TASK_B"]["ROI"]),
            threshold=0.8,
        )
        if matched:
            writer(f"[Trigger] Task B matched at {box} using {image_path}")
            click_anchor = get_template_center_point(image_path, box)
            time.sleep(TRIGGER_MATCH_STABILIZE_S)
            execute_offset_clicks(
                hardware_controller=hardware_controller,
                detected_pos=click_anchor,
                offsets=config["TASK_B"]["OFFSETS"],
                click_delay_ms=int(float(config["TASK_B"].get("COOLDOWN", 0.3)) * 1000),
            )
            time.sleep(float(config["TASK_B"].get("COOLDOWN", 0.3)))
            return True

    return False


def run_independent_trigger(
    interface_config: dict,
    driver_backend: str,
    port: str,
    baudrate: int | None,
    stop_event: Event,
    keyboard_via_python: bool = False,
    config: Optional[dict] = None,
    log_writer: Optional[Callable[[str], None]] = None,
) -> None:
    """Long-running trigger loop for independent launcher usage."""
    os.chdir(project_root := service_main.project_root)
    config = resolve_trigger_config_paths(config or DEFAULT_TRIGGER_CONFIG)

    def writer(message: str) -> None:
        append_trigger_log(message)
        append_probe_log(message)
        if log_writer is not None:
            log_writer(message)
        else:
            print(message)

    controller_name = resolve_controller_name(interface_config, driver_backend)
    controller_config = resolve_controller_config(interface_config, controller_name)
    controller_config = apply_controller_override(
        controller_config,
        build_controller_override(port, baudrate, keyboard_via_python=keyboard_via_python),
    )

    hardware_controller = service_main.create_hardware_controller(controller_config)
    vision_engine = VisionEngine(frame_cache=FrameCache(ttl_ms=50.0))

    writer(f"[Trigger] start independent trigger on {driver_backend}:{port}")
    try:
        while not stop_event.is_set():
            screenshot = vision_engine.get_screenshot(force_fresh=True)
            run_trigger_cycle(
                vision_engine=vision_engine,
                hardware_controller=hardware_controller,
                screenshot=screenshot,
                config=config,
                log_writer=writer,
            )
            time.sleep(0.02)
    except Exception as exc:
        writer(f"[ERROR] trigger runtime failed: {exc}")
        raise
    finally:
        hardware_controller.close()
        writer("[Trigger] independent trigger stopped")
