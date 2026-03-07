"""
Configuration loader and schema validation tests.

Tests validate:
- Strict workflow schema contracts (step_id required, action types validated)
- YAML-only loading with safe parsing
- Compile-time semantic validation (dangling references, graph integrity)
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestWorkflowSchema:
    """Validate strict workflow schema contracts."""

    def test_schema_module_importable(self):
        """Workflow schema module can be imported."""
        from core import workflow_schema
        assert hasattr(workflow_schema, 'WorkflowConfig')
        assert hasattr(workflow_schema, 'WorkflowStep')
        assert hasattr(workflow_schema, 'ActionConfig')

    def test_missing_step_id_fails_validation(self):
        """Steps without step_id are rejected during validation."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    # Missing step_id
                    'action': {'type': 'wait', 'duration_ms': 1000},
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig.model_validate(invalid_config)

        assert 'step_id' in str(exc_info.value)

    def test_unsupported_action_type_fails_validation(self):
        """Unknown action types are rejected during validation."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'invalid_action', 'foo': 'bar'},
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig.model_validate(invalid_config)

        # Should fail on action type validation
        error_str = str(exc_info.value)
        assert 'type' in error_str or 'action' in error_str

    def test_wait_action_accepts_only_integer_milliseconds(self):
        """Wait action requires integer duration_ms field."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        # Valid wait action
        valid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 1000},
                    'next': None
                }
            ]
        }
        workflow = WorkflowConfig.model_validate(valid_config)
        assert workflow.steps[0].action.duration_ms == 1000

        # Invalid: string duration
        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 'one thousand'},
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError):
            WorkflowConfig.model_validate(invalid_config)

    def test_click_action_requires_coordinates(self):
        """Click action requires x, y coordinates."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        # Valid click action
        valid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'click', 'x': 100, 'y': 200},
                    'next': None
                }
            ]
        }
        workflow = WorkflowConfig.model_validate(valid_config)
        assert workflow.steps[0].action.x == 100
        assert workflow.steps[0].action.y == 200

        # Invalid: missing y coordinate
        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'click', 'x': 100},
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError):
            WorkflowConfig.model_validate(invalid_config)

    def test_click_action_supports_optional_roi(self):
        """Click action accepts optional ROI-relative coordinates."""
        from core.workflow_schema import WorkflowConfig

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {
                        'type': 'click',
                        'x': 100,
                        'y': 200,
                        'roi': [10, 20, 110, 120]
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        assert workflow.steps[0].action.roi == (10, 20, 110, 120)

    def test_press_action_requires_key_name(self):
        """Press action requires readable key_name field."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        # Valid press action
        valid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'press', 'key_name': 'enter'},
                    'next': None
                }
            ]
        }
        workflow = WorkflowConfig.model_validate(valid_config)
        assert workflow.steps[0].action.key_name == 'enter'

        # Invalid: missing key_name
        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'press'},
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError):
            WorkflowConfig.model_validate(invalid_config)

    def test_scroll_action_requires_direction_and_ticks(self):
        """Scroll action requires direction and ticks fields."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        # Valid scroll action
        valid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'scroll', 'direction': 'down', 'ticks': 3},
                    'next': None
                }
            ]
        }
        workflow = WorkflowConfig.model_validate(valid_config)
        assert workflow.steps[0].action.direction == 'down'
        assert workflow.steps[0].action.ticks == 3

        # Invalid: missing direction
        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'scroll', 'ticks': 3},
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError):
            WorkflowConfig.model_validate(invalid_config)

    def test_step_with_conditional_branching(self):
        """Steps support on_true/on_false conditional branching."""
        from core.workflow_schema import WorkflowConfig

        config = {
            'name': 'test_workflow',
            'start_step_id': 'check_condition',
            'steps': [
                {
                    'step_id': 'check_condition',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'on_true': 'success_step',
                    'on_false': 'failure_step'
                },
                {
                    'step_id': 'success_step',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                },
                {
                    'step_id': 'failure_step',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        check_step = workflow.steps[0]
        assert check_step.on_true == 'success_step'
        assert check_step.on_false == 'failure_step'

    def test_unique_step_ids_required(self):
        """Duplicate step_ids are rejected."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': 'step1'
                },
                {
                    'step_id': 'step1',  # Duplicate
                    'action': {'type': 'wait', 'duration_ms': 200},
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig.model_validate(invalid_config)

        assert 'duplicate' in str(exc_info.value).lower() or 'unique' in str(exc_info.value).lower()


class TestConfigLoader:
    """Validate YAML-only config loading behavior."""

    def test_loader_module_importable(self):
        """Config loader module can be imported."""
        from core import config_loader
        assert hasattr(config_loader, 'load_workflow_config')

    def test_non_yaml_extension_rejected(self, tmp_path):
        """Files without .yaml or .yml extension are rejected."""
        from core.config_loader import load_workflow_config

        # Create a file with wrong extension
        json_file = tmp_path / "workflow.json"
        json_file.write_text('{"name": "test"}')

        with pytest.raises(ValueError) as exc_info:
            load_workflow_config(str(json_file))

        assert 'yaml' in str(exc_info.value).lower() or 'extension' in str(exc_info.value).lower()

    def test_malformed_yaml_rejected(self, tmp_path):
        """Malformed YAML syntax is rejected."""
        from core.config_loader import load_workflow_config

        yaml_file = tmp_path / "workflow.yaml"
        yaml_file.write_text("""
name: test_workflow
steps: [
  invalid: yaml: syntax: here
""")

        with pytest.raises(Exception):  # yaml.YAMLError or similar
            load_workflow_config(str(yaml_file))

    def test_missing_file_raises_error(self, tmp_path):
        """Loading non-existent file raises appropriate error."""
        from core.config_loader import load_workflow_config

        non_existent = tmp_path / "does_not_exist.yaml"

        with pytest.raises(FileNotFoundError):
            load_workflow_config(str(non_existent))


class TestWorkflowCompiler:
    """Validate compile-time semantic validation."""

    def test_compiler_module_importable(self):
        """Workflow compiler module can be imported."""
        from core import workflow_compiler
        assert hasattr(workflow_compiler, 'compile_workflow')

    def test_dangling_next_reference_fails_compile(self):
        """References to non-existent step IDs fail compilation."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': 'non_existent_step'
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)

        with pytest.raises(ValueError) as exc_info:
            compile_workflow(workflow)

        assert 'non_existent_step' in str(exc_info.value)

    def test_dangling_on_true_reference_fails_compile(self):
        """Dangling on_true branch references fail compilation."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow

        config = {
            'name': 'test_workflow',
            'start_step_id': 'check_step',
            'steps': [
                {
                    'step_id': 'check_step',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'on_true': 'missing_step',
                    'on_false': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)

        with pytest.raises(ValueError) as exc_info:
            compile_workflow(workflow)

        assert 'missing_step' in str(exc_info.value)

    def test_dangling_on_false_reference_fails_compile(self):
        """Dangling on_false branch references fail compilation."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow

        config = {
            'name': 'test_workflow',
            'start_step_id': 'check_step',
            'steps': [
                {
                    'step_id': 'check_step',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'on_true': None,
                    'on_false': 'missing_step'
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)

        with pytest.raises(ValueError) as exc_info:
            compile_workflow(workflow)

        assert 'missing_step' in str(exc_info.value)

    def test_missing_start_step_fails_compile(self):
        """start_step_id must reference an existing step."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow

        config = {
            'name': 'test_workflow',
            'start_step_id': 'non_existent_start',
            'steps': [
                {
                    'step_id': 'actual_step',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)

        with pytest.raises(ValueError) as exc_info:
            compile_workflow(workflow)

        assert 'start_step_id' in str(exc_info.value) or 'non_existent_start' in str(exc_info.value)

    def test_valid_workflow_compiles_successfully(self):
        """Valid workflow with correct references compiles without error."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'click', 'x': 100, 'y': 200},
                    'next': 'step2'
                },
                {
                    'step_id': 'step2',
                    'action': {'type': 'wait', 'duration_ms': 1000},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        assert compiled is not None
        assert compiled.name == 'test_workflow'
        assert compiled.start_step_id == 'step1'

    def test_conditional_workflow_compiles(self):
        """Valid conditional workflow compiles successfully."""
        from core.workflow_schema import WorkflowConfig
        from core.workflow_compiler import compile_workflow

        config = {
            'name': 'conditional_workflow',
            'start_step_id': 'check',
            'steps': [
                {
                    'step_id': 'check',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'on_true': 'handle_true',
                    'on_false': 'handle_false'
                },
                {
                    'step_id': 'handle_true',
                    'action': {'type': 'press', 'key_name': 'enter'},
                    'next': 'end'
                },
                {
                    'step_id': 'handle_false',
                    'action': {'type': 'scroll', 'direction': 'down', 'ticks': 1},
                    'next': 'end'
                },
                {
                    'step_id': 'end',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        compiled = compile_workflow(workflow)

        assert compiled is not None
        assert 'check' in compiled.step_index
        assert 'handle_true' in compiled.step_index
        assert 'handle_false' in compiled.step_index


class TestEndToEnd:
    """End-to-end integration tests for config loading pipeline."""

    def test_load_valid_yaml_file(self, tmp_path):
        """Complete pipeline: load YAML -> validate schema -> compile."""
        from core.config_loader import load_workflow_config

        yaml_file = tmp_path / "workflow.yaml"
        yaml_file.write_text("""
name: donation_workflow
start_step_id: open_menu
steps:
  - step_id: open_menu
    action:
      type: press
      key_name: alt+u
    next: click_donate
  - step_id: click_donate
    action:
      type: click
      x: 1200
      y: 700
    next: null
""")

        compiled = load_workflow_config(str(yaml_file))
        assert compiled.name == 'donation_workflow'
        assert compiled.start_step_id == 'open_menu'

    def test_invalid_config_blocks_execution(self, tmp_path):
        """Invalid workflow config raises before any automation starts."""
        from core.config_loader import load_workflow_config

        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("""
name: bad_workflow
start_step_id: missing_step
steps:
  - step_id: existing_step
    action:
      type: wait
      duration_ms: 100
    next: null
""")

        with pytest.raises(ValueError):
            load_workflow_config(str(yaml_file))


class TestWaitImageSchema:
    """Validate intelligent wait image schema contracts (WAIT-01, WAIT-02, WAIT-03)."""

    def test_wait_image_accepts_appear_state(self):
        """wait_image accepts state=appear with required image condition fields."""
        from core.workflow_schema import WorkflowConfig

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
                        'roi': [100, 200, 300, 400]
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        assert workflow.steps[0].action.state == 'appear'
        assert workflow.steps[0].action.image == 'btn_login.png'
        assert workflow.steps[0].action.roi == (100, 200, 300, 400)

    def test_wait_image_accepts_disappear_state(self):
        """wait_image accepts state=disappear for waiting until image disappears."""
        from core.workflow_schema import WorkflowConfig

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {
                        'type': 'wait_image',
                        'state': 'disappear',
                        'image': 'loading_spinner.png',
                        'roi': [500, 600, 700, 800]
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        assert workflow.steps[0].action.state == 'disappear'
        assert workflow.steps[0].action.image == 'loading_spinner.png'

    def test_wait_image_rejects_invalid_state(self):
        """wait_image rejects invalid state values."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {
                        'type': 'wait_image',
                        'state': 'invalid_state',
                        'image': 'btn_login.png',
                        'roi': [100, 200, 300, 400]
                    },
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig.model_validate(invalid_config)

        assert 'state' in str(exc_info.value)

    def test_wait_image_requires_image_field(self):
        """wait_image requires image field for template matching."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {
                        'type': 'wait_image',
                        'state': 'appear'
                        # Missing image field
                    },
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig.model_validate(invalid_config)

        assert 'image' in str(exc_info.value)

    def test_wait_image_requires_roi_field(self):
        """wait_image requires roi field for search region."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {
                        'type': 'wait_image',
                        'state': 'appear',
                        'image': 'btn_login.png'
                        # Missing roi field
                    },
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig.model_validate(invalid_config)

        assert 'roi' in str(exc_info.value)

    def test_legacy_wait_action_remains_valid(self):
        """Existing wait(duration_ms) action remains valid for backward compatibility."""
        from core.workflow_schema import WorkflowConfig

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 1000},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        assert workflow.steps[0].action.type == 'wait'
        assert workflow.steps[0].action.duration_ms == 1000


class TestWaitDefaultsAndOverrides:
    """Validate workflow-level wait defaults and per-step override semantics."""

    def test_workflow_level_wait_defaults(self):
        """Workflow config supports global wait defaults for timeout/poll/retry."""
        from core.workflow_schema import WorkflowConfig

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'wait_defaults': {
                'timeout_ms': 5000,
                'poll_interval_ms': 100,
                'retry_interval_ms': 500
            },
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 1000},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        assert workflow.wait_defaults.timeout_ms == 5000
        assert workflow.wait_defaults.poll_interval_ms == 100
        assert workflow.wait_defaults.retry_interval_ms == 500

    def test_wait_defaults_use_standard_values_when_not_specified(self):
        """Wait defaults use sensible standard values when not specified."""
        from core.workflow_schema import WorkflowConfig

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 1000},
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        # Should have default values
        assert workflow.wait_defaults.timeout_ms == 10000  # 10s default
        assert workflow.wait_defaults.poll_interval_ms == 50  # 50ms default
        assert workflow.wait_defaults.retry_interval_ms == 1000  # 1s default

    def test_step_level_retry_interval_override(self):
        """Step-level retry_interval_ms overrides workflow default."""
        from core.workflow_schema import WorkflowConfig

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'wait_defaults': {
                'timeout_ms': 5000,
                'retry_interval_ms': 1000
            },
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {'type': 'wait', 'duration_ms': 100},
                    'retry': 3,
                    'retry_interval_ms': 200,  # Override default
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        assert workflow.steps[0].retry_interval_ms == 200
        # Workflow default still accessible
        assert workflow.wait_defaults.retry_interval_ms == 1000

    def test_wait_image_with_timeout_override(self):
        """wait_image action can override timeout at action level."""
        from core.workflow_schema import WorkflowConfig

        config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'wait_defaults': {
                'timeout_ms': 10000
            },
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {
                        'type': 'wait_image',
                        'state': 'appear',
                        'image': 'btn_login.png',
                        'roi': [100, 200, 300, 400],
                        'timeout_ms': 3000  # Override default
                    },
                    'next': None
                }
            ]
        }

        workflow = WorkflowConfig.model_validate(config)
        assert workflow.steps[0].action.timeout_ms == 3000
        assert workflow.wait_defaults.timeout_ms == 10000


class TestWaitImageValidationEdgeCases:
    """Edge case validation for wait_image constraints."""

    def test_wait_image_roi_must_be_four_integers(self):
        """ROI must be a tuple/list of exactly 4 integers."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {
                        'type': 'wait_image',
                        'state': 'appear',
                        'image': 'btn.png',
                        'roi': [100, 200]  # Only 2 values
                    },
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError):
            WorkflowConfig.model_validate(invalid_config)

    def test_wait_image_timeout_must_be_positive(self):
        """wait_image timeout_ms must be positive."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {
                        'type': 'wait_image',
                        'state': 'appear',
                        'image': 'btn.png',
                        'roi': [100, 200, 300, 400],
                        'timeout_ms': -1
                    },
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError):
            WorkflowConfig.model_validate(invalid_config)

    def test_wait_image_poll_interval_must_be_positive(self):
        """wait_image poll_interval_ms must be positive."""
        from core.workflow_schema import WorkflowConfig
        from pydantic import ValidationError

        invalid_config = {
            'name': 'test_workflow',
            'start_step_id': 'step1',
            'steps': [
                {
                    'step_id': 'step1',
                    'action': {
                        'type': 'wait_image',
                        'state': 'appear',
                        'image': 'btn.png',
                        'roi': [100, 200, 300, 400],
                        'poll_interval_ms': 0
                    },
                    'next': None
                }
            ]
        }

        with pytest.raises(ValidationError):
            WorkflowConfig.model_validate(invalid_config)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
