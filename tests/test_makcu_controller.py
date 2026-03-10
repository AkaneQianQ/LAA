#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAKCU controller tests.
"""

from pathlib import Path

import pytest

from agent.py_service import main as service_main
from agent.py_service.main import load_interface_config
from agent.py_service.pkg.makcu.controller import BUTTON_LEFT, BUTTON_RIGHT, MakcuController


class DummySerial:
    def __init__(self, *args, **kwargs):
        self.is_open = True
        self.writes = []
        self.in_waiting = 0
        self._response = bytearray()

    def write(self, data):
        self.writes.append(data.decode("utf-8"))
        self._response = bytearray(b"OK\r\n>>>")
        self.in_waiting = len(self._response)

    def read(self, size):
        chunk = bytes(self._response[:size])
        self._response = self._response[size:]
        self.in_waiting = len(self._response)
        return chunk

    def reset_input_buffer(self):
        self._response = bytearray()
        self.in_waiting = 0

    def reset_output_buffer(self):
        return None

    def close(self):
        self.is_open = False


@pytest.fixture
def serial_stub(monkeypatch):
    created = []

    def factory(*args, **kwargs):
        inst = DummySerial(*args, **kwargs)
        created.append(inst)
        return inst

    monkeypatch.setattr("agent.py_service.pkg.makcu.controller.serial.Serial", factory)
    return created


def test_makcu_controller_initializes_and_formats_mouse_commands(serial_stub, monkeypatch):
    monkeypatch.setattr("agent.py_service.pkg.makcu.controller.WIN32_AVAILABLE", True)
    monkeypatch.setattr(
        "agent.py_service.pkg.makcu.controller.win32api",
        type("FakeWin32", (), {"GetCursorPos": staticmethod(lambda: (100, 200))})(),
    )

    controller = MakcuController(port="COM9", baudrate=9600, timeout=0.1)
    controller.move_absolute(130, 250)
    controller.click_current()
    controller.click_right(5, -3)
    controller.scroll("down", 2)

    writes = serial_stub[0].writes
    assert writes[0] == "km.init()\r\n"
    assert "km.move(30, 50)\r\n" in writes
    assert f"km.click({BUTTON_LEFT})\r\n" in writes
    assert "km.move(5, -3)\r\n" in writes
    assert f"km.click({BUTTON_RIGHT})\r\n" in writes
    assert writes.count("km.wheel(-1)\r\n") == 2


def test_makcu_keyboard_commands_use_string_key_names(serial_stub):
    controller = MakcuController(port="COM9", baudrate=9600, timeout=0.1)
    controller.press("alt+u")
    controller.key_down("shift")
    controller.key_up("shift")

    writes = serial_stub[0].writes
    assert "km.press('alt+u')\r\n" in writes
    assert "km.down('shift')\r\n" in writes
    assert "km.up('shift')\r\n" in writes


def test_initialize_uses_makcu_driver_when_requested(monkeypatch, tmp_path):
    config = load_interface_config()
    config["controller"] = [
        {
            "name": "Makcu-Test",
            "type": "Serial",
            "driver": "makcu",
            "serial": {"port": "COM9", "baudrate": 115200, "timeout": 1.0},
        }
    ]

    monkeypatch.setattr(service_main, "load_interface_config", lambda *args, **kwargs: config)
    monkeypatch.setattr(service_main, "register_all_modules", lambda: None)
    monkeypatch.setattr(service_main.Registry, "list_recognitions", staticmethod(lambda: {}))
    monkeypatch.setattr(service_main.Registry, "list_actions", staticmethod(lambda: {}))

    class FakeVisionEngine:
        def __init__(self, frame_cache):
            self.frame_cache = frame_cache

    class FakeMakcuController:
        def __init__(self, port, baudrate, timeout):
            self.port = port
            self.baudrate = baudrate
            self.timeout = timeout

    monkeypatch.setattr(service_main, "VisionEngine", FakeVisionEngine)
    monkeypatch.setattr(service_main, "MakcuController", FakeMakcuController)

    components = service_main.initialize(controller_name="Makcu-Test")
    assert isinstance(components.hardware_controller, FakeMakcuController)
    assert components.hardware_controller.port == "COM9"


def test_interface_has_makcu_controller_entry():
    config = load_interface_config()
    drivers = {
        controller.get("name"): controller.get("driver", "ferrum")
        for controller in config["controller"]
    }
    assert "MAKCU-Default" in drivers
    assert drivers["MAKCU-Default"] == "makcu"
