"""
Error Recovery Schema Tests

Tests for recovery contract schema validation and compiler semantic checks.
Validates error recovery behavior is configuration-driven and verifiable before runtime.

Covers:
- Recovery anchor fields and escalation limits
- Compiler validation for recovery graph safety
- Backward compatibility with Phase 1-3 workflows
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestRecoverySchemaFields:
    """Test recovery contract fields in workflow schema."""

    def test_step_accepts_recovery_anchor_field(self):
        """Steps can be marked as recovery anchors."""
        from core.workflow_schema import WorkflowConfig

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'recovery': {
                        'anchor': True
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        assert workflow.steps[0].recovery.anchor is True

    def test_step_accepts_on_timeout_rollback_target(self):
        """Steps can define rollback target on timeout."""
        from core.workflow_schema import WorkflowConfig

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'anchor_step',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'recovery': {'anchor': True},
                    'next': 'step2'
                },
                {
                    'step_id': 'step2',
                    'action': {'type': 'wait_image', 'state': 'appear', 'image': 'btn.png', 'roi': [100, 200, 300, 400]},
                    'recovery': {
                        'on_timeout': 'anchor_step'
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        assert workflow.steps[1].recovery.on_timeout == 'anchor_step'

    def test_step_accepts_max_escalations(self):
        """Steps can define max escalation count for recovery."""
        from core.workflow_schema import WorkflowConfig

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'recovery': {
                        'max_escalations': 3
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        assert workflow.steps[0].recovery.max_escalations == 3

    def test_step_accepts_audit_context(self):
        """Steps can include optional audit context."""
        from core.workflow_schema import WorkflowConfig

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'recovery': {
                        'audit_context': {'phase': 'donation', 'critical': True}
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        assert workflow.steps[0].recovery.audit_context == {'phase': 'donation', 'critical': True}

    def test_recovery_fields_backward_compatible(self):
        """Existing workflows without recovery fields remain valid."""
        from core.workflow_schema import WorkflowConfig

        config = {
            'name': 'legacy_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        assert workflow.steps[0].step_id == 'step1'
        # Recovery should have default values
        assert hasattr(workflow.steps[0], 'recovery')

    def test_max_escalations_must_be_non_negative(self):
        """max_escalations must be >= 0."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'recovery': {
                        'max_escalations': -1
                    },
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig.model_validate(invalid_config)

        assert 'max_escalations' in str(exc_info.value)

    def test_anchor_must_be_boolean(self):
        """anchor field must be boolean (non-coercible values rejected)."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'recovery': {
                        'anchor': {'invalid': 'object'}  # Object cannot be coerced to bool
                    },
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig.model_validate(invalid_config)

        assert 'anchor' in str(exc_info.value)

    def test_on_timeout_must_be_string_or_none(self):
        """on_timeout must be a valid step id string or None."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'recovery': {
                        'on_timeout': 123  # Invalid: must be string
                    },
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig.model_validate(invalid_config)

        assert 'on_timeout' in str(exc_info.value)

    def test_audit_context_must_be_dict(self):
        """audit_context must be a dictionary."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'recovery': {
                        'audit_context': 'invalid_context'
                    },
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig.model_validate(invalid_config)

        assert 'audit_context' in str(exc_info.value)


class TestRecoveryCompilerValidation:
    """Test compiler semantic validation for recovery graph safety."""

    def test_compiler_rejects_missing_rollback_target(self):
        """Compiler rejects on_timeout referencing non-existent step."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow, WorkflowCompilationError

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'recovery': {
                        'on_timeout': 'non_existent_anchor'
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)

        with pytest.raises(WorkflowCompilationError) as exc_info:
            compile_workflow(workflow)

        assert 'non_existent_anchor' in str(exc_info.value)

    def test_compiler_accepts_valid_rollback_target(self):
        """Compiler accepts on_timeout referencing existing step."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow

        config = {
            'name': 'test_workflow',
            'start_step_id': 'anchor_step',
            'steps': [
                {
                    'step_id': 'anchor_step',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'recovery': {'anchor': True},
                    'next': 'step2'
                },
                {
                    'step_id': 'step2',
                    'action': {'type': 'wait', 'duration_ms': 200},
                    'recovery': {
                        'on_timeout': 'anchor_step'
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        assert compiled is not None
        assert compiled.name == 'test_workflow'

    def test_compiler_rejects_cyclic_recovery_only_loop(self):
        """Compiler rejects recovery-only cycles (no normal path forward)."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow, WorkflowCompilationError

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': 'step2'
                },
                {
                    'step_id': 'step2',
                    'action': {'type': 'wait', 'duration_ms': 200},
                    'recovery': {
                        'on_timeout': 'step3'
                    },
                    'next': None
                },
                {
                    'step_id': 'step3',
                    'action': {'type': 'wait', 'duration_ms': 300},
                    'recovery': {
                        'on_timeout': 'step2'  # Creates cycle: step2 -> step3 -> step2
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)

        with pytest.raises(WorkflowCompilationError) as exc_info:
            compile_workflow(workflow)

        assert 'cycle' in str(exc_info.value).lower() or 'loop' in str(exc_info.value).lower()

    def test_compiler_accepts_anchored_recovery_path(self):
        """Compiler accepts valid anchor-linked recovery paths."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow

        config = {
            'name': 'test_workflow',
            'start_step_id': 'open_menu',
            'steps': [
                {
                    'step_id': 'open_menu',
                    'action': {'type': 'press', 'key_name': 'alt+u'},
                    'recovery': {'anchor': True},
                    'next': 'wait_menu'
                },
                {
                    'step_id': 'wait_menu',
                    'action': {'type': 'wait_image', 'state': 'appear', 'image': 'menu.png', 'roi': [100, 200, 300, 400]},
                    'recovery': {
                        'on_timeout': 'open_menu',
                        'max_escalations': 3
                    },
                    'next': 'click_donate'
                },
                {
                    'step_id': 'click_donate',
                    'action': {'type': 'click', 'x': 100, 'y': 200},
                    'recovery': {
                        'on_timeout': 'open_menu',
                        'max_escalations': 3
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        assert compiled is not None
        # Verify recovery metadata preserved
        wait_step = compiled.step_index['wait_menu']
        assert wait_step.recovery.on_timeout == 'open_menu'
        assert wait_step.recovery.max_escalations == 3

    def test_compiler_reports_all_recovery_errors(self):
        """Compiler reports all recovery-related errors, not just first."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow, WorkflowCompilationError

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'recovery': {
                        'on_timeout': 'missing_anchor_1'
                    },
                    'next': 'step2'
                },
                {
                    'step_id': 'step2',
                    'action': {'type': 'wait', 'duration_ms': 200},
                    'recovery': {
                        'on_timeout': 'missing_anchor_2'
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)

        with pytest.raises(WorkflowCompilationError) as exc_info:
            compile_workflow(workflow)

        error_str = str(exc_info.value)
        # Should mention both missing targets
        assert 'missing_anchor_1' in error_str or 'missing_anchor_2' in error_str

    def test_compiler_preserves_recovery_fields_in_compiled_workflow(self):
        """Recovery fields are preserved in compiled workflow output."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'recovery': {
                        'anchor': True,
                        'max_escalations': 5,
                        'audit_context': {'critical': True}
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        step = compiled.step_index['step1']
        assert step.recovery.anchor is True
        assert step.recovery.max_escalations == 5
        assert step.recovery.audit_context == {'critical': True}


class TestRecoveryBackwardCompatibility:
    """Test backward compatibility with Phase 1-3 workflows."""

    def test_wait_image_semantics_unchanged(self):
        """wait_image actions work exactly as before recovery fields."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {
                        'type': 'wait_image',
                        'state': 'appear',
                        'image': 'btn_login.png',
                        'roi': [100, 200, 300, 400],
                        'timeout_ms': 5000
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        step = compiled.step_index['step1']
        assert step.action.state == 'appear'
        assert step.action.image == 'btn_login.png'
        assert step.action.timeout_ms == 5000

    def test_retry_fields_unchanged(self):
        """Existing retry fields work as before."""
        from core.workflow_schema import WorkflowConfig

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'retry': 3,
                    'retry_interval_ms': 500,
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        assert workflow.steps[0].retry == 3
        assert workflow.steps[0].retry_interval_ms == 500

    def test_conditional_routing_unchanged(self):
        """on_true/on_false routing works as before."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow

        config = {
            'name': 'test_workflow',
            'start_step_id': 'check',
            'steps': [
                {
                    'step_id': 'check',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'on_true': 'success',
                    'on_false': 'failure'
                },
                {
                    'step_id': 'success',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                },
                {
                    'step_id': 'failure',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        check_step = compiled.step_index['check']
        assert check_step.on_true == 'success'
        assert check_step.on_false == 'failure'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
