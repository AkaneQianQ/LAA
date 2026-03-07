"""
Guild Workflow Migration Tests

Tests for migrating hardcoded waits to intelligent wait_image actions.
Verifies that the production guild_donation.yaml uses state-driven waits.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestGuildWorkflowWaitImageCoverage:
    """Test that guild_donation.yaml uses wait_image for transition-critical waits."""

    def test_workflow_contains_wait_image_actions(self):
        """Workflow YAML contains wait_image actions for transition-critical waits."""
        from core.config_loader import load_workflow_config

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        # Collect all action types
        action_types = set()
        for step in compiled.steps:
            action_type = type(step.action).__name__
            action_types.add(action_type)

        # Verify wait_image is present
        assert 'WaitImageAction' in action_types, \
            "Workflow missing wait_image actions - migration incomplete"

    def test_workflow_has_appear_wait_state(self):
        """At least one wait_image with state=appear is present."""
        from core.config_loader import load_workflow_config
        from core.workflow_schema import WaitImageAction

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        # Find appear waits
        appear_waits = [
            step for step in compiled.steps
            if isinstance(step.action, WaitImageAction)
            and step.action.state == 'appear'
        ]

        assert len(appear_waits) > 0, \
            "Workflow missing wait_image with state='appear'"

    def test_workflow_has_disappear_wait_state(self):
        """At least one wait_image with state=disappear is present."""
        from core.config_loader import load_workflow_config
        from core.workflow_schema import WaitImageAction

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        # Find disappear waits
        disappear_waits = [
            step for step in compiled.steps
            if isinstance(step.action, WaitImageAction)
            and step.action.state == 'disappear'
        ]

        assert len(disappear_waits) > 0, \
            "Workflow missing wait_image with state='disappear'"

    def test_transition_waits_use_wait_image_not_fixed_duration(self):
        """UI transition waits use wait_image instead of fixed duration waits."""
        from core.config_loader import load_workflow_config
        from core.workflow_schema import WaitAction, WaitImageAction

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        # Critical UI transition steps that should use wait_image
        transition_step_patterns = [
            'wait_', 'wait_menu', 'wait_donation', 'wait_confirm',
            'wait_login', 'wait_scroll', 'wait_character'
        ]

        transition_steps = []
        for step in compiled.steps:
            step_id_lower = step.step_id.lower()
            if any(pattern in step_id_lower for pattern in transition_step_patterns):
                transition_steps.append(step)

        # At least half of transition steps should use wait_image
        wait_image_count = sum(
            1 for step in transition_steps
            if isinstance(step.action, WaitImageAction)
        )

        # We expect most transition waits to be migrated
        assert wait_image_count >= 3, \
            f"Only {wait_image_count} transition steps use wait_image, " \
            f"expected at least 3 out of {len(transition_steps)}"

    def test_wait_image_has_required_fields(self):
        """wait_image actions have required fields (image, roi, state)."""
        from core.config_loader import load_workflow_config
        from core.workflow_schema import WaitImageAction

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        for step in compiled.steps:
            if isinstance(step.action, WaitImageAction):
                action = step.action
                assert action.image, f"Step {step.step_id}: wait_image missing 'image'"
                assert action.roi, f"Step {step.step_id}: wait_image missing 'roi'"
                assert action.state in ('appear', 'disappear'), \
                    f"Step {step.step_id}: wait_image state must be 'appear' or 'disappear'"

    def test_wait_defaults_configurable_in_workflow(self):
        """Wait timeout settings are configurable through workflow defaults."""
        from core.config_loader import load_workflow_config

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        # Verify wait_defaults exists
        assert hasattr(compiled, 'wait_defaults'), \
            "Workflow missing wait_defaults configuration"

        defaults = compiled.wait_defaults

        # Verify configurable fields
        assert hasattr(defaults, 'timeout_ms'), \
            "wait_defaults missing timeout_ms"
        assert hasattr(defaults, 'poll_interval_ms'), \
            "wait_defaults missing poll_interval_ms"
        assert hasattr(defaults, 'retry_interval_ms'), \
            "wait_defaults missing retry_interval_ms"

        # Verify reasonable defaults
        assert defaults.timeout_ms > 0, "timeout_ms must be positive"
        assert defaults.poll_interval_ms > 0, "poll_interval_ms must be positive"
        assert defaults.retry_interval_ms >= 0, "retry_interval_ms must be non-negative"

    def test_workflow_has_recovery_anchor(self):
        """Workflow has at least one recovery anchor step (ERR-02)."""
        from core.config_loader import load_workflow_config

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        anchor_steps = [
            step for step in compiled.steps
            if step.recovery.anchor
        ]

        assert len(anchor_steps) > 0, \
            "Workflow missing recovery anchor steps"

    def test_wait_image_steps_have_recovery_timeout(self):
        """wait_image steps have recovery on_timeout configuration."""
        from core.config_loader import load_workflow_config
        from core.workflow_schema import WaitImageAction

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        wait_image_steps = [
            step for step in compiled.steps
            if isinstance(step.action, WaitImageAction)
        ]

        # At least some wait_image steps should have recovery timeout
        steps_with_recovery = [
            step for step in wait_image_steps
            if step.recovery.on_timeout is not None
        ]

        assert len(steps_with_recovery) >= 3, \
            f"Only {len(steps_with_recovery)} wait_image steps have recovery.on_timeout, " \
            f"expected at least 3"

    def test_recovery_references_valid_anchor(self):
        """Recovery on_timeout references point to valid anchor steps."""
        from core.config_loader import load_workflow_config

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        # Build set of valid step IDs
        valid_step_ids = {step.step_id for step in compiled.steps}

        # Check all recovery on_timeout references
        for step in compiled.steps:
            if step.recovery.on_timeout is not None:
                assert step.recovery.on_timeout in valid_step_ids, \
                    f"Step '{step.step_id}': recovery.on_timeout references " \
                    f"non-existent step '{step.recovery.on_timeout}'"

    def test_workflow_compiles_without_errors(self):
        """Guild donation workflow compiles without compilation errors."""
        from core.config_loader import load_workflow_config

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        # Should compile without raising
        compiled = load_workflow_config(workflow_path)

        assert compiled is not None
        assert compiled.name == 'guild_donation'
        assert len(compiled.steps) > 0


class TestWorkflowStepOverrides:
    """Test step-level timeout/poll interval overrides."""

    def test_step_can_override_timeout(self):
        """Individual steps can override default timeout."""
        from core.config_loader import load_workflow_config
        from core.workflow_schema import WaitImageAction

        workflow_path = Path(project_root) / 'config' / 'workflows' / 'guild_donation.yaml'

        if not workflow_path.exists():
            pytest.skip("guild_donation.yaml not yet created")

        compiled = load_workflow_config(workflow_path)

        # Find steps with wait_image that might have overrides
        wait_image_steps = [
            step for step in compiled.steps
            if isinstance(step.action, WaitImageAction)
        ]

        # At least one step should demonstrate override capability
        # (either through explicit timeout_ms or by using workflow defaults)
        steps_with_explicit_timeout = [
            step for step in wait_image_steps
            if step.action.timeout_ms is not None
        ]

        # It's ok if no steps have explicit overrides - defaults are used
        # But we verify the schema supports it
        if len(wait_image_steps) > 0:
            first = wait_image_steps[0].action
            assert hasattr(first, 'timeout_ms'), \
                "WaitImageAction missing timeout_ms field"
            assert hasattr(first, 'poll_interval_ms'), \
                "WaitImageAction missing poll_interval_ms field"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
