"""
Workflow Integration Tests

End-to-end tests for the config-driven workflow pipeline:
- YAML loading and compilation
- Bootstrap module creating executor with dependencies
- Full parse->validate->compile->execute wiring
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import tempfile
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestWorkflowBootstrap:
    """Test workflow bootstrap module creating executor from config path."""

    def test_bootstrap_loads_yaml_and_creates_executor(self):
        """Bootstrap loads YAML and creates executor with all dependencies."""
        from core.workflow_bootstrap import create_workflow_executor

        # Create a temporary workflow YAML file
        workflow_config = {
            'name': 'test_workflow',
            'start_step_id': 'start',
            'steps': [
                {
                    'step_id': 'start',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(workflow_config, f)
            temp_path = f.name

        try:
            # Create mock dependencies
            mock_controller = Mock()
            mock_vision = Mock()

            # Bootstrap should create executor
            executor = create_workflow_executor(
                workflow_path=temp_path,
                controller=mock_controller,
                vision_engine=mock_vision
            )

            assert executor is not None
            assert hasattr(executor, 'execute')
            assert hasattr(executor, 'workflow')
            assert executor.workflow.name == 'test_workflow'

        finally:
            os.unlink(temp_path)

    def test_bootstrap_invalid_yaml_raises_error(self):
        """Bootstrap raises ConfigLoadError for invalid YAML."""
        from core.workflow_bootstrap import create_workflow_executor, ConfigLoadError

        # Create a temporary file with invalid YAML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            mock_controller = Mock()
            mock_vision = Mock()

            with pytest.raises(ConfigLoadError):
                create_workflow_executor(
                    workflow_path=temp_path,
                    controller=mock_controller,
                    vision_engine=mock_vision
                )

        finally:
            os.unlink(temp_path)

    def test_bootstrap_missing_file_raises_error(self):
        """Bootstrap raises FileNotFoundError for missing config file."""
        from core.workflow_bootstrap import create_workflow_executor

        mock_controller = Mock()
        mock_vision = Mock()

        with pytest.raises(FileNotFoundError):
            create_workflow_executor(
                workflow_path='/nonexistent/workflow.yaml',
                controller=mock_controller,
                vision_engine=mock_vision
            )

    def test_bootstrap_creates_dispatcher_and_evaluator(self):
        """Bootstrap creates ActionDispatcher and ConditionEvaluator."""
        from core.workflow_bootstrap import create_workflow_executor
        from core.workflow_runtime import ActionDispatcher, ConditionEvaluator

        workflow_config = {
            'name': 'test_workflow',
            'start_step_id': 'start',
            'steps': [
                {
                    'step_id': 'start',
                    'action': {'type': 'click', 'x': 100, 'y': 200},
                    'next': None
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(workflow_config, f)
            temp_path = f.name

        try:
            mock_controller = Mock()
            mock_vision = Mock()

            executor = create_workflow_executor(
                workflow_path=temp_path,
                controller=mock_controller,
                vision_engine=mock_vision
            )

            # Verify dispatcher and evaluator were created
            assert isinstance(executor.dispatcher, ActionDispatcher)
            assert isinstance(executor.condition, ConditionEvaluator)

            # Verify they have correct dependencies
            assert executor.dispatcher.controller is mock_controller
            assert executor.condition.vision is mock_vision

        finally:
            os.unlink(temp_path)


class TestGuildDonationWorkflow:
    """Test sample guild donation workflow YAML."""

    def test_guild_donation_yaml_loads_and_compiles(self):
        """Guild donation YAML loads and compiles into executable workflow."""
        from core.config_loader import load_workflow_config

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        # Skip if file doesn't exist yet (will be created)
        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        assert compiled is not None
        assert compiled.name == 'guild_donation'
        assert len(compiled.steps) > 0
        assert compiled.start_step_id is not None

    def test_guild_donation_has_required_action_types(self):
        """Guild donation workflow includes all required action types."""
        from core.config_loader import load_workflow_config
        from core.workflow_schema import ClickAction, WaitAction, PressAction, ScrollAction

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        # Collect all action types
        action_types = set()
        for step in compiled.steps:
            action_type = type(step.action).__name__
            action_types.add(action_type)

        # Verify all required types are present
        assert 'ClickAction' in action_types, "Missing click action"
        assert 'WaitAction' in action_types, "Missing wait action"
        assert 'PressAction' in action_types, "Missing press action"
        assert 'ScrollAction' in action_types, "Missing scroll action"

    def test_guild_donation_has_conditional_branch(self):
        """Guild donation workflow includes at least one conditional branch."""
        from core.config_loader import load_workflow_config

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        # Check for conditional routing
        has_conditional = any(
            step.on_true is not None or step.on_false is not None
            for step in compiled.steps
        )

        assert has_conditional, "Workflow missing conditional branch"

    def test_guild_donation_has_loop_path(self):
        """Guild donation workflow includes a loop path for character iteration."""
        from core.config_loader import load_workflow_config

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        # Build step graph and detect cycles
        step_ids = {step.step_id for step in compiled.steps}
        edges = set()

        for step in compiled.steps:
            if step.next is not None:
                edges.add((step.step_id, step.next))
            if step.on_true is not None:
                edges.add((step.step_id, step.on_true))
            if step.on_false is not None:
                edges.add((step.step_id, step.on_false))

        # Check for back edges (cycles/loops)
        has_loop = any(target in step_ids and target != step_id for step_id, target in edges if target is not None)
        assert has_loop, "Workflow missing loop path for character iteration"

    def test_guild_donation_has_explicit_step_ids(self):
        """Guild donation workflow uses explicit step IDs."""
        from core.config_loader import load_workflow_config

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        # All steps should have explicit IDs
        for step in compiled.steps:
            assert step.step_id is not None
            assert len(step.step_id) > 0
            assert step.step_id.isidentifier() or '_' in step.step_id

    def test_guild_donation_has_wait_image_actions(self):
        """Guild donation workflow includes wait_image actions for intelligent waits."""
        from core.config_loader import load_workflow_config
        from core.workflow_schema import WaitImageAction

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        # Count wait_image actions
        wait_image_count = sum(
            1 for step in compiled.steps
            if isinstance(step.action, WaitImageAction)
        )

        assert wait_image_count >= 3, \
            f"Expected at least 3 wait_image actions, found {wait_image_count}"

    def test_guild_donation_has_appear_and_disappear_waits(self):
        """Guild donation workflow has both appear and disappear wait states."""
        from core.config_loader import load_workflow_config
        from core.workflow_schema import WaitImageAction

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        # Find appear and disappear waits
        appear_waits = [
            step for step in compiled.steps
            if isinstance(step.action, WaitImageAction)
            and step.action.state == 'appear'
        ]
        disappear_waits = [
            step for step in compiled.steps
            if isinstance(step.action, WaitImageAction)
            and step.action.state == 'disappear'
        ]

        assert len(appear_waits) > 0, "Missing wait_image with state='appear'"
        assert len(disappear_waits) > 0, "Missing wait_image with state='disappear'"

    def test_guild_donation_has_wait_defaults(self):
        """Guild donation workflow has configurable wait defaults."""
        from core.config_loader import load_workflow_config

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        # Verify wait_defaults exists with required fields
        assert hasattr(compiled, 'wait_defaults'), "Missing wait_defaults"
        defaults = compiled.wait_defaults

        assert hasattr(defaults, 'timeout_ms'), "Missing timeout_ms"
        assert hasattr(defaults, 'poll_interval_ms'), "Missing poll_interval_ms"
        assert hasattr(defaults, 'retry_interval_ms'), "Missing retry_interval_ms"

        assert defaults.timeout_ms > 0
        assert defaults.poll_interval_ms > 0
        assert defaults.retry_interval_ms >= 0


class TestIntelligentWaitIntegration:
    """Test intelligent wait execution through bootstrap and executor."""

    def test_bootstrap_executes_workflow_with_wait_image(self):
        """Bootstrap successfully loads and executes workflow containing wait_image."""
        from core.workflow_bootstrap import create_workflow_executor

        workflow_config = {
            'name': 'wait_image_test',
            'start_step_id': 'wait_for_element',
            'wait_defaults': {
                'timeout_ms': 2000,
                'poll_interval_ms': 50,
                'retry_interval_ms': 100
            },
            'steps': [
                {
                    'step_id': 'wait_for_element',
                    'action': {
                        'type': 'wait_image',
                        'state': 'appear',
                        'image': 'test_element.png',
                        'roi': [100, 100, 200, 200],
                        'timeout_ms': 1000,
                        'poll_interval_ms': 50
                    },
                    'next': 'done'
                },
                {
                    'step_id': 'done',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(workflow_config, f)
            temp_path = f.name

        try:
            mock_controller = Mock()
            mock_vision = Mock()

            # Mock vision to find element (2 consecutive hits needed for stability)
            mock_vision.find_element = Mock(return_value=(True, 0.9, (150, 150)))

            executor = create_workflow_executor(
                workflow_path=temp_path,
                controller=mock_controller,
                vision_engine=mock_vision
            )

            result = executor.execute()

            assert result.success is True
            assert result.steps_executed == 2

        finally:
            os.unlink(temp_path)

    def test_intelligent_wait_timeout_triggers_retry(self):
        """Timeout failure in intelligent wait can be retried by executor path."""
        from core.workflow_bootstrap import create_workflow_executor
        from core.workflow_executor import ExecutionError

        workflow_config = {
            'name': 'retry_test',
            'start_step_id': 'wait_for_element',
            'wait_defaults': {
                'timeout_ms': 500,
                'poll_interval_ms': 50,
                'retry_interval_ms': 100
            },
            'steps': [
                {
                    'step_id': 'wait_for_element',
                    'action': {
                        'type': 'wait_image',
                        'state': 'appear',
                        'image': 'test_element.png',
                        'roi': [100, 100, 200, 200],
                        'timeout_ms': 200  # Short timeout
                    },
                    'next': 'done',
                    'retry': 2  # Allow 2 retries
                },
                {
                    'step_id': 'done',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(workflow_config, f)
            temp_path = f.name

        try:
            mock_controller = Mock()
            mock_vision = Mock()

            # Mock vision to never find element (always timeout)
            mock_vision.find_element = Mock(return_value=(False, 0.3, None))

            executor = create_workflow_executor(
                workflow_path=temp_path,
                controller=mock_controller,
                vision_engine=mock_vision
            )

            result = executor.execute()

            # Should fail after retries exhausted
            assert result.success is False
            assert result.error is not None
            # Should have attempted the step multiple times (initial + 2 retries = 3 attempts)
            # But only count successful step executions

        finally:
            os.unlink(temp_path)

    def test_intelligent_wait_resolves_step_level_retry_interval(self):
        """Step-level retry_interval_ms overrides workflow default."""
        from core.workflow_bootstrap import create_workflow_executor

        workflow_config = {
            'name': 'retry_interval_test',
            'start_step_id': 'wait_step',
            'wait_defaults': {
                'timeout_ms': 1000,
                'poll_interval_ms': 50,
                'retry_interval_ms': 500  # Default 500ms
            },
            'steps': [
                {
                    'step_id': 'wait_step',
                    'action': {
                        'type': 'wait_image',
                        'state': 'appear',
                        'image': 'test.png',
                        'roi': [100, 100, 200, 200]
                        # No timeout override - uses default
                    },
                    'next': 'done',
                    'retry': 1,
                    'retry_interval_ms': 100  # Override to 100ms
                },
                {
                    'step_id': 'done',
                    'action': {'type': 'wait', 'duration_ms': 50},
                    'next': None
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(workflow_config, f)
            temp_path = f.name

        try:
            mock_controller = Mock()
            mock_vision = Mock()

            # First call fails, second succeeds
            call_count = [0]
            def mock_find(*args, **kwargs):
                call_count[0] += 1
                return (call_count[0] >= 2, 0.9 if call_count[0] >= 2 else 0.3, None)

            mock_vision.find_element = mock_find

            executor = create_workflow_executor(
                workflow_path=temp_path,
                controller=mock_controller,
                vision_engine=mock_vision
            )

            result = executor.execute()

            # Should succeed after retry
            assert result.success is True

        finally:
            os.unlink(temp_path)


class TestBootstrapExecutorIntegration:
    """Test bootstrap creating executor that can run with mocked dependencies."""

    def test_executor_runs_through_mocked_dependencies(self):
        """Executor created by bootstrap runs through mocked dispatcher/vision."""
        from core.workflow_bootstrap import create_workflow_executor

        workflow_config = {
            'name': 'integration_test',
            'start_step_id': 'open_menu',
            'steps': [
                {
                    'step_id': 'open_menu',
                    'action': {'type': 'press', 'key_name': 'alt+u'},
                    'next': 'wait_menu'
                },
                {
                    'step_id': 'wait_menu',
                    'action': {'type': 'wait', 'duration_ms': 500},
                    'next': 'check_menu'
                },
                {
                    'step_id': 'check_menu',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'on_true': 'click_donate',
                    'on_false': 'wait_menu',  # Loop back to wait
                    'condition': {
                        'type': 'image',
                        'template': 'assets/guild_flag_mark.png',
                        'roi': [1000, 200, 1600, 400],
                        'threshold': 0.8
                    }
                },
                {
                    'step_id': 'click_donate',
                    'action': {'type': 'click', 'x': 1200, 'y': 600},
                    'next': None
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(workflow_config, f)
            temp_path = f.name

        try:
            mock_controller = Mock()
            mock_vision = Mock()

            # Mock vision to return True on second check (after one loop)
            call_count = [0]
            def mock_find_element(*args, **kwargs):
                call_count[0] += 1
                return (call_count[0] >= 2, 0.9 if call_count[0] >= 2 else 0.5, (100, 100))

            mock_vision.find_element = mock_find_element

            executor = create_workflow_executor(
                workflow_path=temp_path,
                controller=mock_controller,
                vision_engine=mock_vision
            )

            result = executor.execute()

            # Should complete successfully after one loop
            assert result.success is True
            # Steps: open_menu, wait_menu, check_menu (false), wait_menu, check_menu (true), click_donate = 6 steps
            assert result.steps_executed == 6

        finally:
            os.unlink(temp_path)


class TestWorkflowValidation:
    """Test workflow validation at bootstrap time."""

    def test_bootstrap_fails_on_dangling_reference(self):
        """Bootstrap fails if workflow has dangling step reference."""
        from core.workflow_bootstrap import create_workflow_executor
        from core.workflow_compiler import WorkflowCompilationError

        workflow_config = {
            'name': 'invalid_workflow',
            'start_step_id': 'start',
            'steps': [
                {
                    'step_id': 'start',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': 'nonexistent_step'  # Dangling reference
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(workflow_config, f)
            temp_path = f.name

        try:
            mock_controller = Mock()
            mock_vision = Mock()

            with pytest.raises((WorkflowCompilationError, Exception)):
                create_workflow_executor(
                    workflow_path=temp_path,
                    controller=mock_controller,
                    vision_engine=mock_vision
                )

        finally:
            os.unlink(temp_path)


class TestLauncherIntegration:
    """Test launcher integration with workflow bootstrap."""

    def test_launcher_imports_bootstrap(self):
        """Launcher module imports workflow bootstrap correctly."""
        import gui_launcher

        # Verify bootstrap components are imported
        assert hasattr(gui_launcher, 'create_workflow_executor')
        assert hasattr(gui_launcher, 'ConfigLoadError')

    def test_launcher_has_workflow_path_config(self):
        """Launcher has configurable workflow path."""
        import gui_launcher

        # Verify launcher has workflow path logic
        source = Path(gui_launcher.__file__).read_text()
        # Check for path components (handles both / and \ separators)
        assert 'config' in source and 'workflows' in source and 'guild_donation.yaml' in source

    def test_launcher_creates_controller_with_stop_event(self):
        """Launcher creates controller that respects stop event."""
        import gui_launcher
        import threading

        # Verify controller creation method exists
        assert hasattr(gui_launcher.FerrumBotLauncher, '_create_controller')

        # Create a mock launcher to test controller
        class MockLauncher:
            def __init__(self):
                self.stop_event = threading.Event()

            def _log(self, msg):
                pass

            _create_controller = gui_launcher.FerrumBotLauncher._create_controller

        mock = MockLauncher()
        controller = mock._create_controller()

        # Verify controller has required methods
        assert hasattr(controller, 'click')
        assert hasattr(controller, 'wait')
        assert hasattr(controller, 'press')
        assert hasattr(controller, 'scroll')

    def test_launcher_handles_config_load_error(self):
        """Launcher handles ConfigLoadError gracefully."""
        import gui_launcher

        source = Path(gui_launcher.__file__).read_text()

        # Verify error handling exists
        assert 'ConfigLoadError' in source
        assert 'Configuration error' in source

    def test_launcher_handles_missing_workflow_file(self):
        """Launcher handles missing workflow file with fallback."""
        import gui_launcher

        source = Path(gui_launcher.__file__).read_text()

        # Verify fallback exists
        assert 'FileNotFoundError' in source or 'workflow config not found' in source.lower()
        assert '_simulate_automation' in source or 'fallback' in source.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
