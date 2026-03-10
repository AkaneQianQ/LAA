# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 强制约束

**开发新功能前，必须阅读 `API_REFERENCE.md`**

在添加任何新功能、新API或新模块之前，**必须**先阅读 `API_REFERENCE.md` 文件，确认：
1. 所需功能是否已存在（避免重复造轮子）
2. 使用现有的API而非重新实现
3. 遵循现有的命名规范和接口设计

如果计划实现的API与现有功能类似，应复用或扩展现有实现，而非创建新的重复代码。

---

## Project Overview

This is **FerrumBot**, a game automation framework for Lost Ark (Korea server) that automates guild donation workflows across multiple characters. Built on **MaaFramework-inspired architecture** with Pipeline JSON configuration, custom recognizers, and hardware-based input simulation (KMBox serial device) for XIGNCODE3 anti-cheat compliance.

**Architecture Pattern:** MaaFramework-style Pipeline JSON + Python Agent Service
**Configuration:** Declarative JSON Pipelines with registered custom recognizers/actions
**Resolution:** 2560x1440 only (locked)
**Input Method:** KMBox hardware serial device (COM2, 115200 baud)

---

## Quick Start

### Run the application
```bash
python gui_launcher.py
```

### Run service directly
```bash
python -m agent.py_service.main --task GuildDonation
```

### List available tasks
```bash
python -m agent.py_service.main --list-tasks
```

### Convert YAML to Pipeline JSON
```bash
python tools/convert_yaml_to_pipeline.py assets/tasks/guild_donation.yaml
```

### Run tests
```bash
python -m pytest tests/ -v
```

---

## MaaFramework Architecture

### Directory Structure (Maa Style)

```
agent/py_service/              # Python Agent Service (like Maa's go-service)
├── register.py                # Component registry (REQUIRED for new modules)
├── main.py                    # Service entry point
├── pkg/                       # Shared packages
│   ├── ferrum/                # Hardware abstraction
│   ├── vision/                # Computer vision engine
│   ├── workflow/              # Workflow execution
│   ├── recovery/              # Error recovery
│   └── common/                # Common utilities
└── modules/                   # Feature modules (MUST have register.py)
    ├── character/             # Character detection
    ├── donation/              # Guild donation
    └── login/                 # Auto login

assets/                        # Static resources (Maa style)
├── interface.json             # Main configuration (REQUIRED)
├── resource/
│   ├── pipeline/*.json        # Pipeline JSON workflows
│   └── image/                 # Template images
└── tasks/*.yaml               # Source YAML (convert to JSON)

tools/                         # Development tools
└── convert_yaml_to_pipeline.py
```

### Core Components

#### 1. Pipeline JSON System
Workflows are defined as **MaaFramework-style Pipeline JSON**:

```json
{
    "NodeName": {
        "desc": "Human-readable description",
        "recognition": {
            "type": "TemplateMatch",
            "param": {
                "template": "image/button.png",
                "roi": [x, y, w, h],
                "threshold": 0.8
            }
        },
        "action": "Click",
        "next": ["NextNode"],
        "on_error": ["ErrorNode"]
    }
}
```

**Recognition Types:**
- `TemplateMatch` - OpenCV template matching (primary)
- `OCR` - Text recognition
- `Custom` - Registered custom recognizer

**Action Types:**
- `Click` - Mouse click
- `KeyPress` - Keyboard input
- `Custom` - Registered custom action
- `DoNothing` - No operation

#### 2. Component Registry System

**CRITICAL:** All custom recognizers and actions MUST be registered:

```python
# agent/py_service/modules/{module}/register.py
from ...register import recognition, action, RecognitionResult

@recognition("RecognitionName")
def my_recognizer(context: dict) -> RecognitionResult:
    """
    Args:
        context: {
            'screenshot': np.ndarray,
            'vision_engine': VisionEngine,
            'hardware_controller': FerrumController,
            'param': dict  # Custom params from Pipeline JSON
        }
    Returns:
        RecognitionResult(matched=True|False, box=None|tuple, payload=dict)
    """
    pass

@action("ActionName")
def my_action(context: dict):
    """Execute custom action"""
    pass

def register():
    """Module entry - called by register_all_modules()"""
    print("[Module] {name} registered")
```

#### 3. Interface Configuration

**assets/interface.json** (MaaFramework style):

```json
{
    "interface_version": 1,
    "name": "FerrumBot",
    "controller": [
        {
            "name": "KMBox-Default",
            "type": "Serial",
            "serial": {"port": "COM2", "baudrate": 115200}
        }
    ],
    "resource": [
        {"name": "LostArk-KR-2560x1440", "resolution": "2560x1440"}
    ],
    "task": [
        {
            "name": "GuildDonation",
            "entry": "DonationMain",
            "pipeline": "assets/resource/pipeline/guild_donation.json"
        }
    ]
}
```

---

## Development Guidelines (Maa Style)

**重要提示**: 开发新功能前，务必先阅读 `API_REFERENCE.md` 了解现有API。

### 1. Creating New Pipeline Nodes

**File Location:** `assets/resource/pipeline/{Feature}*.json`

**Node Naming Convention:**
- **Public nodes** (entry points): PascalCase, no prefix - `DonationMain`, `CharacterSwitch`
- **Private nodes**: Underscore prefix + PascalCase - `_OpenMenu`, `_ClickButton`
- **Error handlers**: Suffix `Err` or `Error` - `_NetworkError`, `_TimeoutHandler`

**Required Fields:**
```json
{
    "NodeName": {
        "desc": "Description in Chinese or English",
        "recognition": {...},  // Optional but recommended
        "action": {...},       // Optional
        "next": ["NextNode"],  // Required unless terminal
        "on_error": ["ErrorNode"]  // Required if recognition has timeout
    }
}
```

**Pipeline Best Practices:**
1. **Never use hardcoded delays** - Use `wait_image` or `post_wait_freezes`
2. **Always specify ROI** - Full-screen matching is prohibited
3. **Always handle errors** - Provide `on_error` for every recognition node
4. **Use focus messages** - Add user feedback via `focus` field

### 2. Creating New Modules

**Step 1:** Create directory structure
```bash
mkdir -p agent/py_service/modules/{module_name}
touch agent/py_service/modules/{module_name}/__init__.py
touch agent/py_service/modules/{module_name}/register.py
```

**Step 2:** Implement register.py (REQUIRED)
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""{Module} registration"""

from ...register import recognition, action, RecognitionResult
from ...pkg.vision.engine import VisionEngine
from ...pkg.ferrum.controller import FerrumController


@recognition("{Module}Detection")
def detect_something(context: dict) -> RecognitionResult:
    """Detect something on screen"""
    screenshot = context.get('screenshot')
    vision: VisionEngine = context.get('vision_engine')

    if screenshot is None:
        return RecognitionResult(matched=False)

    # Implementation here
    detection_result = vision.find_element(...)

    return RecognitionResult(
        matched=detection_result is not None,
        box=detection_result,
        payload={'data': detection_result}
    )


@action("Execute{Module}")
def execute_action(context: dict):
    """Execute module action"""
    hardware: FerrumController = context.get('hardware_controller')

    if hardware:
        # Implementation here
        pass


def register():
    """Module registration entry"""
    print("[Module] {module_name} registered")
```

**Step 3:** Add Pipeline JSON
```bash
# Create pipeline file
touch assets/resource/pipeline/{Module}.json
```

**Step 4:** Update interface.json
```json
{
    "task": [
        {
            "name": "{Module}Task",
            "entry": "{Module}Main",
            "pipeline": "assets/resource/pipeline/{Module}.json"
        }
    ]
}
```

### 3. Converting YAML to Pipeline JSON

**Old YAML format (legacy):**
```yaml
steps:
  - name: "打开菜单"
    action:
      type: press
      key: esc
```

**New Pipeline JSON format:**
```json
{
    "OpenMenu": {
        "desc": "打开菜单",
        "action": {
            "type": "KeyPress",
            "param": {"key": "esc"}
        },
        "next": ["NextNode"]
    }
}
```

**Use conversion tool:**
```bash
python tools/convert_yaml_to_pipeline.py assets/tasks/{workflow}.yaml
# Output: assets/resource/pipeline/{workflow}.json
```

### 4. Image Resources

**Location:** `assets/resource/image/`

**Naming Convention:**
- `{feature}_{element}_{type}.png` - e.g., `guild_button_confirm.png`
- Use descriptive names in English
- Templates must be 720p-compatible (Maa scales automatically)
- Use FF00FF (magenta) for transparent/masked areas

**Template Requirements:**
- Format: PNG with alpha channel (optional)
- Resolution: Capture at 2560x1440, reference at 720p
- Mask color: FF00FF for ignored regions

---

## Code Conventions

### File Header (REQUIRED)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module description

Detailed description of what this module does.
"""

import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Imports here
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `CharacterDetector`, `PipelineExecutor` |
| Functions | snake_case | `detect_slots()`, `execute_action()` |
| Variables | snake_case | `slot_results`, `click_position` |
| Constants | UPPER_CASE | `SLOT_1_1_ROI`, `DETECTION_THRESHOLD` |
| Pipeline Nodes | PascalCase | `DonationMain`, `_ClickButton` |
| Custom Recognizers | PascalCase | `CharacterSlotDetection` |
| Custom Actions | PascalCase | `ExecuteDonation` |

### Logging Format

**Use ASCII brackets, NO Unicode emoji:**
```python
# Good
print(f"[OK] Task completed: {task_name}")
print(f"[ERROR] Detection failed: {reason}")
print(f"[WARNING] Retrying... ({attempt}/3)")

# Bad - DON'T USE
print(f"✓ Task completed: {task_name}")
print(f"❌ Detection failed: {reason}")
```

**Standard Log Prefixes:**
- `[Vision]` - Vision engine messages
- `[Hardware]` - KMBox/controller messages
- `[Pipeline]` - Pipeline execution messages
- `[Module]` - Module registration/loading
- `[Task]` - Task automation messages
- `[Error]` - Error messages

### Import Style

**Within agent/py_service:**
```python
# Use relative imports
from ...register import recognition, action
from ...pkg.vision.engine import VisionEngine
from ...pkg.ferrum.controller import FerrumController
```

**From outside (legacy compatibility):**
```python
# Use compatible layer
from core import FerrumController, VisionEngine
from agent.py_service.modules.character.detector import CharacterDetector
```

---

## ROI Constraints (CRITICAL)

**Resolution:** 2560x1440 only
**Full-screen matching:** PROHIBITED
**Required:** ROI must be specified for all template matching

### Character Slot ROIs (Locked)

```python
# Row 1
SLOT_1_1_ROI = (904, 557, 1152, 624)
SLOT_1_2_ROI = (1164, 557, 1412, 624)
SLOT_1_3_ROI = (1425, 557, 1673, 624)
# Row 2
SLOT_2_1_ROI = (904, 674, 1152, 741)
SLOT_2_2_ROI = (1164, 674, 1412, 741)
SLOT_2_3_ROI = (1425, 674, 1673, 741)
# Row 3
SLOT_3_1_ROI = (904, 791, 1152, 858)
SLOT_3_2_ROI = (1164, 791, 1412, 858)
SLOT_3_3_ROI = (1425, 791, 1673, 858)
```

---

## Error Handling

### Pipeline Error Handling

**Always provide error handlers:**
```json
{
    "DetectButton": {
        "desc": "检测按钮",
        "recognition": {
            "type": "TemplateMatch",
            "param": {...}
        },
        "timeout": 5000,
        "on_error": ["_HandleTimeout"],
        "next": ["ClickButton"]
    },
    "_HandleTimeout": {
        "desc": "处理超时",
        "focus": {
            "Node.Action.Failed": "[Error] 检测超时"
        },
        "next": ["_RecoveryPoint"]
    }
}
```

### Python Error Handling

```python
# Silent failures for non-critical
 try:
     result = some_optional_operation()
 except Exception:
     result = None  # Silent fallback

# Cancellation check
def long_running_task(stop_event: threading.Event):
    while not stop_event.is_set():
        # Do work
        if stop_event.wait(0.1):  # Check every 100ms
            break
```

---

## Testing

### Pipeline Testing

**Location:** `tests/{feature}/test_*.json`

**Format:**
```json
{
    "configs": {
        "name": "Test Suite Name",
        "resource": "LostArk-KR-2560x1440",
        "controller": "KMBox-Default"
    },
    "cases": [
        {
            "name": "Test case description",
            "image": "tests/screenshots/test_scene.png",
            "hits": ["ExpectedNode1", "ExpectedNode2"]
        }
    ]
}
```

### Unit Testing

```python
# tests/test_character_detection.py
def test_slot_detection():
    from agent.py_service.modules.character.detector import CharacterDetector
    from agent.py_service.pkg.vision.engine import VisionEngine

    vision = VisionEngine()
    detector = CharacterDetector(vision)

    # Test with sample screenshot
    screenshot = cv2.imread("tests/samples/character_select.png")
    slots = detector.detect_character_slots(screenshot)

    assert len(slots) > 0
    assert all(0 <= slot <= 8 for slot in slots)
```

---

## Migration Notes

### From Old Structure

| Old | New |
|-----|-----|
| `core/*.py` | `agent/py_service/pkg/*/*.py` |
| `modules/*.py` | `agent/py_service/modules/*/` |
| `config/workflows/*.yaml` | `assets/resource/pipeline/*.json` |
| Hardcoded workflows | Pipeline JSON + registered actions |
| Direct class instantiation | Registry pattern |

### Compatibility Layer

Old imports still work via `core/__init__.py`:
```python
# This still works (backward compatible)
from core import FerrumController, VisionEngine
```

But prefer new structure:
```python
# Preferred new way
from agent.py_service.pkg.ferrum.controller import FerrumController
from agent.py_service.pkg.vision.engine import VisionEngine
```

---

## Key Dependencies

- `opencv-python`: Template matching (`TM_CCOEFF_NORMED`)
- `dxcam`: Screen capture (RGB → BGR)
- `pyyaml`: YAML parsing (for conversion tool)
- `pyserial`: KMBox serial communication
- `keyboard`: Global hotkey registration
- `numpy`: Image array operations

---

## References

- **API Reference (必读):** `API_REFERENCE.md` - 所有可用API汇总
- **MaaFramework Docs:** https://maafw.com/
- **Project Planning:** `.planning/MAA_REFACTOR_GUIDE.md`
- **Code Examples:** `.planning/REFACTOR_EXAMPLES.md`
- **Quick Reference:** `.planning/QUICK_REFERENCE.md`

---

*Last Updated: 2026-03-09*
*Architecture: MaaFramework-style Pipeline JSON + Python Agent*
