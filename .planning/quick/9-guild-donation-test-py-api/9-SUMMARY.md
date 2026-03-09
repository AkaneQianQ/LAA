# Quick Task 9: Guild Donation Test Suite - Summary

**Completed:** 2026-03-09
**Task:** 为 guild_donation 生成 test.py，使用现有 API 走完整流程

---

## What Was Done

Created a comprehensive pytest-based test suite for the guild donation module at `tests/test_guild_donation.py`.

### Test Coverage

The test suite includes **16 test cases** organized into 5 test classes:

#### 1. TestPipelineConfiguration (3 tests)
- `test_pipeline_json_valid()` - Validates guild_donation.json is well-formed JSON
- `test_pipeline_nodes_have_required_fields()` - Ensures all nodes have required fields (desc, next/on_true/on_false)
- `test_load_pipeline_api()` - Tests the `load_pipeline()` API function

#### 2. TestTaskConfiguration (3 tests)
- `test_guild_donation_task_exists()` - Verifies GuildDonation task is in interface.json
- `test_task_config_structure()` - Checks task has entry and pipeline fields
- `test_entry_node_matches_pipeline()` - Validates entry node exists in pipeline (handles naming conventions)

#### 3. TestRegisteredComponents (4 tests)
- `test_donation_actions_registered()` - Confirms ExecuteDonation, OpenGuildMenu, CloseGuildMenu are registered
- `test_donation_recognitions_registered()` - Confirms GuildMenuOpen recognition is registered
- `test_get_action_function()` - Tests Registry.get_action() returns callable
- `test_get_recognition_function()` - Tests Registry.get_recognition() returns callable

#### 4. TestModuleFunctions (3 tests)
- `test_open_guild_menu_function_exists()` - Tests open_guild_menu accepts context
- `test_close_guild_menu_function_exists()` - Tests close_guild_menu accepts context
- `test_check_guild_menu_open_returns_recognition_result()` - Validates return type

#### 5. TestServiceInitialization (2 tests)
- `test_initialize_test_mode()` - Tests service initialization in test mode (no hardware)
- `test_vision_engine_available()` - Validates VisionEngine has required methods

#### 6. TestIntegration (1 test)
- `test_full_initialization_pipeline()` - End-to-end test of init -> config -> pipeline flow

### API Usage

The test suite uses existing APIs **without reinventing**:

| Test Category | APIs Used |
|---------------|-----------|
| Pipeline | `main.load_pipeline()`, `main.load_interface_config()` |
| Task Config | `main.get_task_config()`, `main.list_available_tasks()` |
| Registry | `register_all_modules()`, `Registry.list_actions()`, `Registry.get_action()` |
| Service | `main.initialize(test_mode=True, skip_hardware=True)` |
| Modules | `donation.register.open_guild_menu`, `check_guild_menu_open`, etc. |

### Design Decisions

1. **Test Mode Initialization**: Uses `test_mode=True` and `skip_hardware=True` to test without KMBox hardware
2. **Naming Convention Handling**: Tests handle the `GuildDonationMain` -> `guild_donationMain` naming difference
3. **Branching Logic Support**: Recognizes both `next` and `on_true/on_false` as valid node transitions
4. **Existing API Only**: No new abstractions - directly imports from existing modules

---

## Files Changed

```
tests/
└── test_guild_donation.py      # NEW - 186 lines, 16 test cases
```

## Test Results

```
============================= 16 passed in 0.13s ==============================
```

All tests pass successfully.

## Usage

```bash
# Run all tests
pytest tests/test_guild_donation.py -v

# Run specific test class
pytest tests/test_guild_donation.py::TestPipelineConfiguration -v

# Run with coverage
pytest tests/test_guild_donation.py --cov=agent.py_service.modules.donation
```

---

## References

- Pipeline: `assets/resource/pipeline/guild_donation.json`
- Module: `agent/py_service/modules/donation/register.py`
- Main API: `agent/py_service/main.py`
- CLAUDE.md: Testing section with MaaFramework patterns
