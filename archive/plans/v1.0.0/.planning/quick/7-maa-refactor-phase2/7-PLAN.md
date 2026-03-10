# Quick Task 7: MaaEnd Structure Refactoring Phase 2

**Task:** Complete MaaEnd structure refactoring for LostarkGuildDonationBot
**Date:** 2026-03-09
**Status:** In Progress

## Overview

Complete the MaaEnd (MaaFramework) style structure migration that was started in Phase 1.

## must_haves

- truths:
  - interface.json must be valid JSON with proper MaaEnd structure
  - YAML to JSON converter must handle all three workflow files
  - Module registration files must use the @recognition/@action decorators
  - Import paths must be fixed to use new pkg/ locations
  - Old files must be deleted without breaking imports
  - Original YAML files must be preserved

- artifacts:
  - assets/interface.json
  - tools/convert_yaml_to_pipeline.py
  - agent/py-service/modules/character/register.py
  - agent/py-service/modules/donation/register.py
  - agent/py-service/modules/login/register.py
  - assets/resource/pipeline/*.json (converted from YAML)

- key_links:
  - REFACTOR_STATUS.md for current state
  - REFACTOR_EXAMPLES.md for implementation patterns
  - MaaEnd reference project structure

## Tasks

### Task 1: Create interface.json

**Files:** assets/interface.json
**Action:** Create MaaEnd-style interface configuration

- interface_version: 1
- name: "FerrumBot"
- controller: KMBox Serial (COM2, 115200)
- resource: 2560x1440 resolution
- task: guild_donation, character_switch, account_indexing

**Verify:**
```bash
python -c "import json; json.load(open('assets/interface.json'))"
```

### Task 2: Create YAML to JSON Pipeline Converter

**Files:** tools/convert_yaml_to_pipeline.py
**Action:** Create conversion tool based on REFACTOR_EXAMPLES.md

Must support:
- press -> KeyPress
- click -> Click
- click_detected -> TemplateMatch + Click
- wait_image -> TemplateMatch with timeout
- wait -> fixed delay
- capture_roi -> Custom recognition

**Verify:**
```bash
python tools/convert_yaml_to_pipeline.py assets/tasks/account_indexing.yaml
```

### Task 3: Create Module Registration Files

**Files:**
- agent/py-service/modules/character/register.py
- agent/py-service/modules/donation/register.py
- agent/py-service/modules/login/register.py

**Action:** Create registration files using decorators from register.py

**Verify:**
```bash
python -c "from agent.py_service.register import register_all_modules; register_all_modules()"
```

### Task 4: Fix Import Paths

**Files:** agent/py-service/modules/character/detector.py
**Action:** Replace old import with new relative import

Change:
```python
from core.parallel_matcher import ParallelMatcher
```
To:
```python
from ...pkg.vision.parallel_matcher import ParallelMatcher
```

**Verify:**
```bash
python -c "from agent.py_service.modules.character.detector import CharacterDetector"
```

### Task 5: Clean Up Old Files

**Files to delete:**
- core/account_manager.py
- core/account_switcher.py
- core/compliance_guard.py
- core/config_loader.py
- core/error_logger.py
- core/frame_cache.py
- core/hardware_input_gateway.py
- core/progress_tracker.py

**Action:** Delete files that have been migrated to pkg/ directory

**Verify:**
```bash
python -c "from core import FerrumController, VisionEngine"
```

### Task 6: Convert YAML Workflows to JSON

**Action:** Run converter on all three YAML files

Input:
- assets/tasks/guild_donation.yaml
- assets/tasks/character_switch.yaml
- assets/tasks/account_indexing.yaml

Output:
- assets/resource/pipeline/guild_donation.json
- assets/resource/pipeline/character_switch.json
- assets/resource/pipeline/account_indexing.json

**Verify:** All JSON files are valid and match YAML structure

## done

- [ ] Task 1: interface.json created and valid
- [ ] Task 2: Converter tool created and working
- [ ] Task 3: Module registration files created
- [ ] Task 4: Import paths fixed
- [ ] Task 5: Old files cleaned up
- [ ] Task 6: YAML files converted to JSON
