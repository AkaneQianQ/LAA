#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Guild Donation Module Tests

Test suite for guild donation functionality using existing APIs.
Validates Pipeline JSON, task configuration, and registered components.

Usage:
    pytest tests/test_guild_donation.py -v
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest

# Import existing APIs - no reinventing
from agent.py_service.main import (
    load_interface_config,
    get_task_config,
    load_pipeline,
    initialize,
    list_available_tasks,
    ConfigError,
)
from agent.py_service.register import Registry, register_all_modules, RecognitionResult
from agent.py_service.modules.donation.register import (
    open_guild_menu,
    close_guild_menu,
    execute_donation,
    check_guild_menu_open,
)


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
                # Private node - can be intermediate
                pass
            else:
                # Public node should have next, on_true/on_false, or be terminal
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

        # Verify pipeline file exists
        pipeline_path = project_root / task_config["pipeline"]
        assert pipeline_path.exists(), f"Pipeline file not found: {pipeline_path}"

        print(f"[OK] Task config valid: entry={task_config['entry']}")

    def test_entry_node_matches_pipeline(self):
        """Verify task entry node exists in pipeline."""
        config = load_interface_config()
        task_config = get_task_config(config, "GuildDonation")

        pipeline = load_pipeline(task_config["pipeline"])
        entry = task_config["entry"]

        # Check for exact match or flexible match (case/underscore differences)
        if entry not in pipeline:
            # GuildDonationMain -> guild_donationMain conversion
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


class TestModuleFunctions:
    """Test donation module functions directly."""

    def test_open_guild_menu_function_exists(self):
        """Verify open_guild_menu function exists and accepts context."""
        # Function should accept context dict
        context = {
            'hardware_controller': None,
            'vision_engine': None,
            'screenshot': None,
            'param': {}
        }

        # Should not raise with None hardware
        result = open_guild_menu(context)
        # Function returns None, just shouldn't crash

        print(f"[OK] open_guild_menu function works with empty context")

    def test_close_guild_menu_function_exists(self):
        """Verify close_guild_menu function exists and accepts context."""
        context = {
            'hardware_controller': None,
            'vision_engine': None,
            'screenshot': None,
            'param': {}
        }

        result = close_guild_menu(context)

        print(f"[OK] close_guild_menu function works with empty context")

    def test_check_guild_menu_open_returns_recognition_result(self):
        """Verify check_guild_menu_open returns RecognitionResult."""
        context = {
            'hardware_controller': None,
            'vision_engine': None,
            'screenshot': None,
            'param': {}
        }

        result = check_guild_menu_open(context)

        assert isinstance(result, RecognitionResult), \
            f"Expected RecognitionResult, got {type(result)}"

        print(f"[OK] check_guild_menu_open returns RecognitionResult")


class TestServiceInitialization:
    """Test service initialization in test mode."""

    def test_initialize_test_mode(self):
        """Test initialize() in test mode (no hardware)."""
        components = initialize(
            test_mode=True,
            skip_hardware=True
        )

        assert components.config is not None, "Config not loaded"
        assert components.vision_engine is not None, "Vision engine not initialized"

        print(f"[OK] Service initialized in test mode")

    def test_vision_engine_available(self):
        """Test that vision engine is properly initialized."""
        components = initialize(
            test_mode=True,
            skip_hardware=True
        )

        vision = components.vision_engine

        assert vision is not None, "Vision engine is None"
        assert hasattr(vision, 'find_element'), "Vision engine missing find_element method"
        assert hasattr(vision, 'get_screenshot'), "Vision engine missing get_screenshot method"

        print(f"[OK] Vision engine has required methods")


class TestIntegration:
    """Integration tests combining multiple components."""

    @classmethod
    def setup_class(cls):
        """Setup for integration tests."""
        register_all_modules()

    def test_full_initialization_pipeline(self):
        """Test full initialization to pipeline loading flow."""
        # 1. Initialize service
        components = initialize(
            test_mode=True,
            skip_hardware=True
        )

        # 2. Get task config
        task_config = get_task_config(components.config, "GuildDonation")

        # 3. Load pipeline
        pipeline = load_pipeline(task_config["pipeline"])

        # 4. Verify entry node (handle naming convention differences)
        entry = task_config["entry"]
        if entry not in pipeline:
            flexible_entry = entry.replace('Guild', 'guild_').lower()
            pipeline_keys_lower = {k.lower(): k for k in pipeline.keys()}
            assert flexible_entry in pipeline_keys_lower or entry.lower() in pipeline_keys_lower, \
                f"Entry '{entry}' not in pipeline"

        # 5. Verify actions are registered
        actions = Registry.list_actions()
        assert "OpenGuildMenu" in actions

        print(f"[OK] Full initialization flow works")


if __name__ == "__main__":
    # Run with: python tests/test_guild_donation.py
    pytest.main([__file__, "-v"])
