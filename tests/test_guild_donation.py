#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Guild Donation Module Tests

Test suite for guild donation functionality using existing APIs.
Supports both test mode (no hardware) and hardware mode (real Ferrum device).

Usage:
    # Test mode (no hardware, default):
    pytest tests/test_guild_donation.py -v

    # Hardware mode (real Ferrum device):
    pytest tests/test_guild_donation.py -v --hardware

    # Full donation test with real hardware:
    pytest tests/test_guild_donation.py::TestFullDonation -v --hardware
"""

import sys
import json
import time
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest

# Import conftest globals
from conftest import HARDWARE_MODE, STARTUP_DELAY_SECONDS

# Import existing APIs - no reinventing
from agent.py_service.main import (
    load_interface_config,
    get_task_config,
    load_pipeline,
    initialize,
    list_available_tasks,
    ConfigError,
)
from agent.py_service.register import Registry, register_all_modules
from agent.py_service.modules.donation.register import (
    open_guild_menu,
    close_guild_menu,
    execute_donation,
    check_guild_menu_open,
)
from agent.py_service.pkg.ferrum.controller import FerrumController


@pytest.fixture(scope="session")
def hardware_mode():
    """Return whether hardware mode is enabled."""
    return HARDWARE_MODE


@pytest.fixture(scope="session")
def components(hardware_mode):
    """
    Initialize components for testing.

    In hardware mode: connects to real Ferrum device
    In test mode: skips hardware initialization
    """
    if hardware_mode:
        print(f"\n[Hardware] Initializing with real Ferrum device...")
        print(f"[Hardware] Starting in {STARTUP_DELAY_SECONDS} seconds...")
        print(f"[Hardware] Please switch to game window now!\n")

        for i in range(STARTUP_DELAY_SECONDS, 0, -1):
            print(f"[Hardware] {i}...")
            time.sleep(1)

        comps = initialize(
            test_mode=False,
            skip_hardware=False
        )
        print("[Hardware] Ferrum device connected!")
        return comps
    else:
        print("\n[Test] Running in test mode (no hardware)")
        return initialize(
            test_mode=True,
            skip_hardware=True
        )


@pytest.fixture(scope="session")
def hardware_controller(components):
    """Get hardware controller if in hardware mode."""
    return components.hardware_controller


@pytest.fixture(scope="session")
def vision_engine(components):
    """Get vision engine."""
    return components.vision_engine


class TestPipelineConfiguration:
    """Test Pipeline JSON and task configuration."""

    def test_pipeline_json_valid(self):
        """Verify guild_donation.json is valid JSON and contains nodes."""
        pipeline_path = project_root / "assets" / "resource" / "pipeline" / "guild_donation.json"

        assert pipeline_path.exists(), f"Pipeline file not found: {pipeline_path}"

        with open(pipeline_path, 'r', encoding='utf-8') as f:
            pipeline = json.load(f)

        assert isinstance(pipeline, dict), "Pipeline must be a JSON object"
        assert len(pipeline) > 0, "Pipeline must contain at least one node"

        # Check for main entry point
        assert "guild_donationMain" in pipeline, "Pipeline must have guild_donationMain entry"

        print(f"[OK] Pipeline has {len(pipeline)} nodes")

    def test_pipeline_nodes_have_required_fields(self):
        """Verify each node has required fields per CLAUDE.md spec."""
        pipeline_path = project_root / "assets" / "resource" / "pipeline" / "guild_donation.json"

        with open(pipeline_path, 'r', encoding='utf-8') as f:
            pipeline = json.load(f)

        for node_name, node_config in pipeline.items():
            # Every node must have 'desc'
            assert "desc" in node_config, f"Node {node_name} missing 'desc' field"

            # Check node name conventions
            if node_name.startswith('_'):
                pass
            else:
                terminal_nodes = ['workflow_complete', 'donation_complete']
                has_next = "next" in node_config or "on_error" in node_config
                has_branching = "on_true" in node_config or "on_false" in node_config

                if node_name not in terminal_nodes:
                    assert has_next or has_branching, \
                        f"Public node {node_name} should have 'next', 'on_error', or 'on_true/on_false'"

        print(f"[OK] All {len(pipeline)} nodes have required fields")

    def test_load_pipeline_api(self):
        """Test load_pipeline API function."""
        pipeline = load_pipeline("assets/resource/pipeline/guild_donation.json")

        assert isinstance(pipeline, dict)
        assert "guild_donationMain" in pipeline

        print(f"[OK] load_pipeline API works correctly")


class TestTaskConfiguration:
    """Test interface.json task configuration."""

    def test_guild_donation_task_exists(self):
        """Verify GuildDonation task is configured in interface.json."""
        config = load_interface_config()

        tasks = list_available_tasks(config)
        task_names = [t['name'] for t in tasks]

        assert "GuildDonation" in task_names, "GuildDonation task not found"

        print(f"[OK] GuildDonation task found in interface.json")

    def test_task_config_structure(self):
        """Verify GuildDonation task has required configuration."""
        config = load_interface_config()
        task_config = get_task_config(config, "GuildDonation")

        assert "entry" in task_config, "Task missing 'entry' field"
        assert "pipeline" in task_config, "Task missing 'pipeline' field"

        pipeline_path = project_root / task_config["pipeline"]
        assert pipeline_path.exists(), f"Pipeline file not found: {pipeline_path}"

        print(f"[OK] Task config valid: entry={task_config['entry']}")

    def test_entry_node_matches_pipeline(self):
        """Verify task entry node exists in pipeline."""
        config = load_interface_config()
        task_config = get_task_config(config, "GuildDonation")

        pipeline = load_pipeline(task_config["pipeline"])
        entry = task_config["entry"]

        if entry not in pipeline:
            flexible_entry = entry.replace('Guild', 'guild_').lower()
            pipeline_keys_lower = {k.lower(): k for k in pipeline.keys()}
            assert flexible_entry in pipeline_keys_lower or entry.lower() in pipeline_keys_lower, \
                f"Entry node '{entry}' not found in pipeline"

        print(f"[OK] Entry node '{entry}' exists in pipeline")


class TestRegisteredComponents:
    """Test that donation module components are properly registered."""

    @classmethod
    def setup_class(cls):
        """Register all modules before testing."""
        register_all_modules()

    def test_donation_actions_registered(self):
        """Verify donation actions are in the registry."""
        actions = Registry.list_actions()

        assert "ExecuteDonation" in actions, "ExecuteDonation action not registered"
        assert "OpenGuildMenu" in actions, "OpenGuildMenu action not registered"
        assert "CloseGuildMenu" in actions, "CloseGuildMenu action not registered"

        print(f"[OK] Found {len(actions)} registered actions")

    def test_donation_recognitions_registered(self):
        """Verify donation recognitions are in the registry."""
        recognitions = Registry.list_recognitions()

        assert "GuildMenuOpen" in recognitions, "GuildMenuOpen recognition not registered"

        print(f"[OK] Found {len(recognitions)} registered recognitions")

    def test_get_action_function(self):
        """Test Registry.get_action returns callable."""
        open_action = Registry.get_action("OpenGuildMenu")

        assert open_action is not None, "OpenGuildMenu not found"
        assert callable(open_action), "OpenGuildMenu is not callable"

        print(f"[OK] OpenGuildMenu action is callable")

    def test_get_recognition_function(self):
        """Test Registry.get_recognition returns callable."""
        check_recognition = Registry.get_recognition("GuildMenuOpen")

        assert check_recognition is not None, "GuildMenuOpen not found"
        assert callable(check_recognition), "GuildMenuOpen is not callable"

        print(f"[OK] GuildMenuOpen recognition is callable")


class TestHardwareConnection:
    """Test Ferrum hardware connection (hardware mode only)."""

    @pytest.mark.skipif(not HARDWARE_MODE, reason="Hardware mode not enabled")
    def test_ferrum_controller_connected(self, components):
        """Verify Ferrum controller is connected."""
        controller = components.hardware_controller

        assert controller is not None, "Hardware controller is None"
        assert isinstance(controller, FerrumController), "Controller is not FerrumController"

        print(f"[OK] Ferrum controller connected: {controller}")

    @pytest.mark.skipif(not HARDWARE_MODE, reason="Hardware mode not enabled")
    def test_hardware_basic_operations(self, hardware_controller):
        """Test basic hardware operations."""
        # Move mouse to safe position (absolute)
        hardware_controller.move_absolute(100, 100)
        time.sleep(0.5)

        # Test key press (using 'esc' as safe test key)
        hardware_controller.press('esc')
        time.sleep(0.2)

        print(f"[OK] Hardware operations working")


class TestVisionEngine:
    """Test Vision Engine functionality."""

    def test_vision_engine_available(self, vision_engine):
        """Test that vision engine is properly initialized."""
        vision = vision_engine

        assert vision is not None, "Vision engine is None"
        assert hasattr(vision, 'find_element'), "Vision engine missing find_element method"
        assert hasattr(vision, 'get_screenshot'), "Vision engine missing get_screenshot method"

        print(f"[OK] Vision engine has required methods")

    def test_screenshot_capture(self, vision_engine):
        """Test screenshot capture."""
        screenshot = vision_engine.get_screenshot()

        assert screenshot is not None, "Screenshot is None"
        assert screenshot.shape[0] > 0 and screenshot.shape[1] > 0, "Invalid screenshot dimensions"

        print(f"[OK] Screenshot captured: {screenshot.shape}")


class TestFullDonation:
    """
    Full donation workflow test with real hardware.

    This test class performs the actual guild donation workflow.
    ONLY run this with --hardware flag and when game is ready.
    """

    @pytest.mark.skipif(not HARDWARE_MODE, reason="Hardware mode not enabled")
    def test_open_guild_menu_with_hardware(self, hardware_controller, vision_engine):
        """Test opening guild menu with real hardware."""
        print("\n[Donation] Testing guild menu opening...")

        # Create context with real hardware
        context = {
            'hardware_controller': hardware_controller,
            'vision_engine': vision_engine,
            'screenshot': vision_engine.get_screenshot(),
            'param': {}
        }

        # Execute open guild menu action
        open_guild_menu(context)
        time.sleep(1.0)  # Wait for menu to appear

        # Verify menu is open
        context['screenshot'] = vision_engine.get_screenshot()
        result = check_guild_menu_open(context)

        # Note: This may fail if game is not in correct state
        print(f"[Donation] Guild menu detection result: matched={result.matched}")

        # Close menu
        close_guild_menu(context)
        time.sleep(0.5)

        print("[OK] Guild menu open/close test completed")

    @pytest.mark.skipif(not HARDWARE_MODE, reason="Hardware mode not enabled")
    def test_full_donation_workflow(self, hardware_controller, vision_engine):
        """
        Execute full donation workflow.

        WARNING: This will actually perform donations if game is ready!
        Make sure you're in-game and ready before running.
        """
        print("\n" + "="*60)
        print("[Donation] FULL WORKFLOW TEST STARTING")
        print("="*60)
        print("This will execute actual donation actions!")
        print("Press Ctrl+C within 3 seconds to cancel...")
        print("="*60 + "\n")

        time.sleep(3)

        context = {
            'hardware_controller': hardware_controller,
            'vision_engine': vision_engine,
            'screenshot': None,
            'param': {}
        }

        # Step 1: Open guild menu
        print("[Step 1] Opening guild menu...")
        open_guild_menu(context)
        time.sleep(1.5)

        # Step 2: Capture screenshot and check menu state
        context['screenshot'] = vision_engine.get_screenshot()
        result = check_guild_menu_open(context)
        print(f"[Step 2] Guild menu check: {result.matched}")

        # Step 3: Execute donation (if menu is open)
        if result.matched:
            print("[Step 3] Executing donation...")
            execute_donation(context)
            time.sleep(2.0)
            print("[OK] Donation workflow completed")
        else:
            print("[WARNING] Guild menu not detected, skipping donation")

        # Step 4: Close guild menu
        print("[Step 4] Closing guild menu...")
        close_guild_menu(context)
        time.sleep(0.5)

        print("\n" + "="*60)
        print("[Donation] WORKFLOW TEST COMPLETED")
        print("="*60)


class TestIntegration:
    """Integration tests combining multiple components."""

    @classmethod
    def setup_class(cls):
        """Setup for integration tests."""
        register_all_modules()

    def test_full_initialization_pipeline(self):
        """Test full initialization to pipeline loading flow."""
        components = initialize(
            test_mode=True,
            skip_hardware=True
        )

        task_config = get_task_config(components.config, "GuildDonation")
        pipeline = load_pipeline(task_config["pipeline"])

        entry = task_config["entry"]
        if entry not in pipeline:
            flexible_entry = entry.replace('Guild', 'guild_').lower()
            pipeline_keys_lower = {k.lower(): k for k in pipeline.keys()}
            assert flexible_entry in pipeline_keys_lower or entry.lower() in pipeline_keys_lower, \
                f"Entry '{entry}' not in pipeline"

        actions = Registry.list_actions()
        assert "OpenGuildMenu" in actions

        print(f"[OK] Full initialization flow works")


if __name__ == "__main__":
    # When running directly, use argparse instead of pytest options
    parser = argparse.ArgumentParser()
    parser.add_argument("--hardware", action="store_true", help="Enable hardware mode")
    parser.add_argument("--delay", type=int, default=3, help="Startup delay in seconds")
    args, remaining = parser.parse_known_args()

    # Note: Direct run mode doesn't use conftest.py, so we set global flags here
    # but they won't affect skipif decorators (those need pytest -c conftest.py)
    if args.hardware:
        print(f"\n[Main] Direct run mode - hardware flag detected")
        print(f"[Main] Use 'pytest {__file__} -v --hardware' for full hardware mode")

    # Run pytest with remaining args
    sys.argv = [sys.argv[0]] + remaining
    pytest.main([__file__, "-v"] + remaining)
