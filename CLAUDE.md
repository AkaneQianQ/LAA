# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **FerrumBot**, a game automation framework for Lost Ark (Korea server) that automates guild donation workflows across multiple characters. It uses pure computer vision (OpenCV template matching) and hardware-based input simulation (KMBox serial device) for XIGNCODE3 anti-cheat compliance.

**Key Design Principles:**
- Zero-configuration multi-account operation via screenshot-based account indexing
- Config-driven automation workflows (YAML-based)
- ACE-compliant hardware-only input (no software injection)
- Intelligent image-based waits replacing hardcoded delays
- ROI-constrained template matching for 2560x1440 resolution only

## Development Commands

**Run the application:**
```bash
python gui_launcher.py
```

**Run in test mode (headless):**
```bash
python gui_launcher.py --test
```

**Run interactive test flow:**
```bash
python test_flow_launcher.py
```

**List available test scenarios:**
```bash
python test_flow_launcher.py --list
```

**Run specific test scenario:**
```bash
python test_flow_launcher.py --scenario guild_donation
```

**Run tests with pytest:**
```bash
python -m pytest tests/ -v
```

**Run a single test file:**
```bash
python -m pytest tests/interactive/test_runner.py -v
```

**Build executable (if spec file exists):**
```bash
pyinstaller FerrumBot_v1.spec
```

## Architecture

### Core Architecture Pattern

The codebase uses a **layered architecture with workflow-driven automation**:

1. **Hardware Abstraction Layer** (`core/hardware_input_gateway.py`)
   - `HardwareInputGateway`: Single egress point for all input actions
   - ACE-compliant policy enforcement (hardware-only, no software paths)
   - Bounded timing jitter (±20% truncated normal distribution)
   - Audit logging for policy violations
   - Delegates to hardware controller for actual KMBox serial communication

2. **Vision Layer** (`core/vision_engine.py`)
   - `VisionEngine`: High-level screen analysis with template matching
   - ROI-constrained detection (full-screen matching prohibited per SPEED-02)
   - FF00FF (magenta) masking support for flexible templates
   - Optional frame caching via `FrameCache` for performance
   - DXCam integration for high-performance screen capture

3. **Workflow System** (config-driven, compiled at runtime)
   - `WorkflowBootstrap` (`core/workflow_bootstrap.py`): Entry point for creating executors
   - `WorkflowCompiler` (`core/workflow_compiler.py`): Semantic validation of YAML workflows
   - `WorkflowExecutor` (`core/workflow_executor.py`): Deterministic step execution with recovery
   - `ActionDispatcher` (`core/workflow_runtime.py`): Maps workflow actions to hardware
   - `ConditionEvaluator` (`core/workflow_runtime.py`): Evaluates conditional branches

4. **Character Detection** (`modules/character_detector.py`)
   - `CharacterDetector`: Computer vision-based character selection screen analysis
   - 9-slot ROI grid (3x3) with locked coordinates for 2560x1440
   - Screenshot-based account indexing (no OCR required)
   - SQLite database for account/character persistence (`core/database.py`)
   - Parallel slot scanning via `ParallelMatcher` (`core/parallel_matcher.py`)

5. **Error Recovery** (`core/error_recovery.py`)
   - `RecoveryOrchestrator`: Three-tier recovery (L1 retry, L2 rollback, L3 skip)
   - Error classification: `DISCONNECT`, `TIMEOUT`, `UI_STUCK`, `HARDWARE_ERROR`
   - Recovery anchors in workflow YAML define rollback points

### Key Data Files

- `config/workflows/guild_donation.yaml`: Main automation workflow definition
- `data/accounts.db`: SQLite database with account/character metadata
- `data/accounts/{hash}/characters/`: Cached character screenshots

### ROI Constants (Locked for 2560x1440)

Character slot ROIs (defined in `modules/character_detector.py`):
```python
SLOT_1_1_ROI = (904, 557, 1152, 624)  # Top-left
SLOT_1_2_ROI = (1164, 557, 1412, 624) # Top-middle
SLOT_1_3_ROI = (1425, 557, 1673, 624) # Top-right
# ... 9 slots total in 3x3 grid
```

### Workflow Action Types

Workflow steps in YAML support these action types:
- `click`: Click at (x, y) coordinates
- `press`: Press key or key combination (e.g., `alt+u`, `esc`)
- `scroll`: Scroll up/down with tick count
- `wait`: Fixed duration wait (duration_ms)
- `wait_image`: Intelligent wait for image appear/disappear with timeout

### Global Hotkeys

The GUI launcher (`gui_launcher.py`) registers these hotkeys via `keyboard` library:
- **F10**: Start main automation (guild donation workflow)
- **F11**: Discover/index account from character selection screen
- **END**: Stop current task (via `threading.Event`)

### Test Framework

Interactive testing is provided via `test_flow_launcher.py`:
- **F1**: Continue to next step
- **Y**: Mark step as passed
- **N**: Mark step as failed
- **1-9**: Select test scenario
- Semi-transparent overlay displays instructions

### Hardware Interface (KMBox)

The KMBox device communicates over serial (default COM2, 115200 baud):
- Commands: `km.move(dx, dy)`, `km.click(0)`, `km.press(hid_code)`
- HID codes: 24=U, 38=Up arrow, 40=Down arrow, 41=ESC, 226=Left Alt
- Input validation: Relative movement clamped to ±120 per command

### Key Dependencies

- `opencv-python`: Template matching (`cv2.matchTemplate` with `TM_CCOEFF_NORMED`)
- `dxcam`: Screen capture (returns RGB, converted to BGR for OpenCV)
- `pyyaml`: Workflow configuration parsing
- `keyboard`: Global hotkey registration
- `pyserial`: KMBox hardware communication

## Code Conventions

**Language:** Comments and user-facing messages use Chinese (Simplified)

**Naming:**
- Classes: PascalCase (`CharacterDetector`, `WorkflowExecutor`)
- Functions/variables: snake_case (`find_element`, `slot_results`)
- Constants: UPPER_CASE in module-level dictionaries

**Error Handling:**
- Silent failures for non-critical operations: `try: ... except: pass`
- `threading.Event` for cancellation signaling across threads
- Custom exceptions: `ConfigLoadError`, `ComplianceError`, `InputPolicyViolation`

**Logging:** Print statements with Chinese prefix tags:
- `[Vision]`: Vision engine messages
- `[任务]`: Task/automation messages
- `[错误]`: Error messages

### Windows Console Unicode Handling

**Default Header for Python Scripts:**

All Python scripts must include the following header to fix Windows console Unicode issues:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io

# Fix Windows console encoding for Chinese output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

**Console Output Guidelines:**
- Avoid Unicode emoji characters (✅, ❌, ✓, →) in print statements
- Use ASCII alternatives: `[OK]`, `[ERROR]`, `[DONE]`, `-->`
- For status indicators, use bracketed text: `[SUCCESS]`, `[FAILED]`, `[WARNING]`
- Example:
  ```python
  # Bad
  print(f"✓ 工作流名称: {name}")
  print(f"❌ 加载失败: {e}")

  # Good
  print(f"[OK] 工作流名称: {name}")
  print(f"[ERROR] 加载失败: {e}")
  ```

**Alternative: Set Console Code Page (for batch scripts):**
```batch
chcp 65001 >nul  # Set UTF-8 code page
```

## Workflow Development Guidelines

**Image Detection Click Randomization:**
All icon detection click operations MUST use the `get_random_click_position()` function from `core/workflow_runtime.py` for anti-detection and edge-avoidance. This function calculates a safe click area within the detected ROI (shrunk by configurable percentage) and returns a randomized click position.

Example usage:
```python
from core.workflow_runtime import get_random_click_position

# Generate random click within safe area (10% shrink)
click_x, click_y = get_random_click_position(detection_roi, shrink_percent=0.10)
```

For workflow YAML files, use the `click_detected` action type which internally uses this function:
```yaml
action:
  type: click_detected
  image: assets/button.bmp
  roi: [100, 200, 300, 400]
  threshold: 0.8
  shrink_percent: 0.10  # 10% shrink for safe click area
```

**Do NOT** use fixed coordinates or simple random offsets for icon clicks - always use the safe-area randomization function.
