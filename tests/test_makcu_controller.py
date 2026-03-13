#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAKCU controller tests based on Legacy API serial behavior.
"""

import logging
from pathlib import Path

import pytest

from agent.py_service import main as service_main
from agent.py_service.main import load_interface_config
from agent.py_service.pkg.makcu import controller as makcu_controller
from agent.py_service.pkg.makcu.controller import MakcuController


class DummySerial:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.is_open = True
        self.writes = []
        self.in_waiting = 0
        self._response = bytearray()

    def write(self, data):
        command = data.decode("utf-8")
        self.writes.append(command)
        stripped = command.strip()
        if stripped == "km.version()":
            response = b"km.version()\r\n3.9\r\n>>> "
        else:
            response = f"{stripped}\r\n>>> ".encode("utf-8")
        self._response = bytearray(response)
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


class NoPromptSerial(DummySerial):
    def write(self, data):
        command = data.decode("utf-8")
        self.writes.append(command)
        self._response = bytearray(b"km.version()\r\n3.9\r\n")
        self.in_waiting = len(self._response)


@pytest.fixture
def serial_stub(monkeypatch):
    created = []

    def factory(*args, **kwargs):
        inst = DummySerial(*args, **kwargs)
        created.append(inst)
        return inst

    monkeypatch.setattr(makcu_controller.serial, "Serial", factory)
    return created


def test_makcu_controller_uses_legacy_api_serial_commands(serial_stub):
    controller = MakcuController(port="COM9", baudrate=115200, timeout=0.1)
    controller._move(13, -7)
    controller.move_absolute(640, 480)
    controller.click_current()
    controller.click(300, 200)
    controller.click_right(100, 200)
    controller.press("enter")
    controller.press("alt+u")
    controller.key_down("shift")
    controller.key_up("shift")
    controller.scroll("down", 2)

    serial_port = serial_stub[0]
    assert serial_port.kwargs["port"] == "COM9"
    assert serial_port.kwargs["baudrate"] == 115200
    assert serial_port.writes[0] == "km.version()\r\n"
    assert "km.move(13,-7)\r\n" in serial_port.writes
    assert "km.moveto(640,480)\r\n" in serial_port.writes
    assert "km.click(1,1,50)\r\n" in serial_port.writes
    assert "km.silent(300,200)\r\n" in serial_port.writes
    assert "km.moveto(100,200)\r\n" in serial_port.writes
    assert "km.click(2,1,50)\r\n" in serial_port.writes
    assert 'km.press("enter",50,0)\r\n' in serial_port.writes
    assert 'km.down("alt")\r\n' in serial_port.writes
    assert 'km.down("u")\r\n' in serial_port.writes
    assert 'km.up("u")\r\n' in serial_port.writes
    assert 'km.up("alt")\r\n' in serial_port.writes
    assert 'km.down("shift")\r\n' in serial_port.writes
    assert 'km.up("shift")\r\n' in serial_port.writes
    assert serial_port.writes.count("km.wheel(-1)\r\n") == 2


def test_makcu_handshake_uses_version_probe(serial_stub):
    controller = MakcuController(port="COM9", baudrate=115200, timeout=0.1)
    assert controller.handshake() is True
    assert serial_stub[0].writes.count("km.version()\r\n") >= 2


def test_makcu_controller_timeout_includes_raw_response(monkeypatch):
    monkeypatch.setattr(
        makcu_controller.serial,
        "Serial",
        lambda *args, **kwargs: NoPromptSerial(*args, **kwargs),
    )

    with pytest.raises(Exception) as exc_info:
        MakcuController(port="COM9", baudrate=115200, timeout=0.01)

    assert "raw=" in str(exc_info.value)
    assert "km.version()" in str(exc_info.value)


def test_makcu_controller_close_closes_serial(serial_stub):
    controller = MakcuController(port="COM9", baudrate=115200, timeout=0.1)
    serial_port = serial_stub[0]

    controller.close()

    assert serial_port.is_open is False


def test_makcu_controller_logs_hardware_ack(serial_stub, caplog):
    caplog.set_level(logging.INFO)

    controller = MakcuController(port="COM9", baudrate=115200, timeout=0.1)
    controller.press("enter")

    messages = [record.getMessage() for record in caplog.records]
    assert any('MAKCU send' in message and 'km.press("enter",50,0)' in message for message in messages)
    assert any('MAKCU ack' in message and 'km.press("enter",50,0)' in message for message in messages)


def test_makcu_controller_normalizes_ferrum_style_key_aliases(serial_stub):
    controller = MakcuController(port="COM9", baudrate=115200, timeout=0.1)
    controller.key_down("lctrl+return")
    controller.key_up("lctrl+return")

    serial_port = serial_stub[0]
    assert 'km.down("ctrl")\r\n' in serial_port.writes
    assert 'km.down("enter")\r\n' in serial_port.writes
    assert 'km.up("enter")\r\n' in serial_port.writes
    assert 'km.up("ctrl")\r\n' in serial_port.writes


def test_initialize_uses_makcu_driver_when_requested(monkeypatch):
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


def test_create_hardware_controller_uses_hybrid_makcu_when_python_keyboard_requested(monkeypatch):
    captured = {}

    class FakeHybridMakcuController:
        def __init__(self, port, baudrate, timeout):
            captured["args"] = (port, baudrate, timeout)

    monkeypatch.setattr(service_main, "HybridMakcuController", FakeHybridMakcuController)

    controller = service_main.create_hardware_controller(
        {
            "name": "Makcu-Test",
            "driver": "makcu",
            "serial": {"port": "COM7", "baudrate": 57600, "timeout": 2.0},
            "input": {"keyboard_via_python": True},
        }
    )

    assert isinstance(controller, FakeHybridMakcuController)
    assert captured["args"] == ("COM7", 57600, 2.0)


def test_interface_has_makcu_controller_entry_with_115200_baud():
    config = load_interface_config()
    makcu_entries = [controller for controller in config["controller"] if controller.get("name") == "MAKCU-Default"]
    assert len(makcu_entries) == 1
    assert makcu_entries[0].get("driver") == "makcu"
    assert makcu_entries[0]["serial"]["baudrate"] == 115200


def test_launcher_spec_does_not_package_makcu_dll():
    spec_text = Path("FerrumBotLauncher.spec").read_text(encoding="utf-8")
    assert "makcu-cpp.dll" not in spec_text


def test_service_version_is_1_0_13():
    assert service_main.VERSION == "1.0.15"
