# Coding Conventions

**Analysis Date:** 2026-03-07

## Naming Patterns

**Files:**
- Module files use snake_case: `ferrum_controller.py`, `vision_engine.py`, `auto_login.py`
- No strict separation between "core" and "modules" - core contains low-level hardware interface, modules contain automation logic

**Classes:**
- PascalCase for class names: `FerrumController`, `VisionEngine`
- Single class per file (mostly), matching filename

**Functions:**
- snake_case for all functions: `move_to()`, `find_element()`, `run_guild_donation()`
- Verbose, descriptive names that explain the action
- Private methods use single underscore prefix: `_cleanup_debug_files()`

**Variables:**
- snake_case: `stop_event`, `port_var`, `processed_slots`
- Chinese comments and string literals used throughout for UI/user-facing messages
- Constants use UPPER_CASE in config dictionaries: `CONFIG["ROI_MENU_TITLE"]`

**Parameters:**
- Descriptive parameter names: `target_x`, `target_y`, `hid_code`
- Default values for optional parameters: `baudrate=115200`, `speed=0.6`

## Code Style

**Formatting:**
- No automated formatter detected (no Black, autopep8, or yapf configuration)
- Mixed indentation consistency - mostly 4 spaces
- Line length varies, some long lines exceed 120 characters
- Compact style with multiple statements on same line using semicolons in some places:
  ```python
  bot.move_to(*CONFIG["SLOTS"][i]); bot.click(); time.sleep(1.2)
  ```

**Linting:**
- No ESLint, flake8, or pylint configuration detected
- No pre-commit hooks

**Import Organization:**
1. Standard library imports first
2. Third-party imports second
3. Local application imports last

Example from `gui_launcher.py`:
```python
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import keyboard  # 需要 pip install keyboard
import main as main_script
import trigger_action as trigger_script
```

## Error Handling

**Patterns:**
- Try-except blocks used sparingly
- Silent failure pattern for non-critical operations:
  ```python
  try: os.remove(f)
  except: pass
  ```
- Exception printing with traceback for main threads:
  ```python
  except Exception as e:
      print(f"[崩溃] {e}"); traceback.print_exc()
  ```
- Hardware connection failures caught and logged but not raised

**No Custom Exceptions:**
- Uses built-in Python exceptions only
- No exception hierarchy defined

## Logging

**Framework:** Direct `print()` statements only

**Patterns:**
- Prefix tags for categorization: `[Vision]`, `[Ferrum]`, `[公会]`, `[任务]`
- Chinese language tags for user-facing messages
- Status updates printed to console throughout execution

**Examples:**
```python
print(f"[Ferrum] 已连接: {self.port}")
print("[Vision] 工业级视觉引擎已就绪")
print("[公会] 开始执行捐赠流程...")
```

**No Structured Logging:**
- No logging module configuration
- No log levels (DEBUG, INFO, ERROR)
- No log file rotation

## Comments

**Language:** Primarily Chinese (Simplified)

**When to Comment:**
- Function docstrings for public API: `"""获取资源绝对路径，适配 PyInstaller"""`
- Inline comments for complex logic
- Section headers in config dictionaries

**Comment Patterns:**
```python
# 关键：使用 get_resource_path 加载模板
# 修正：此处使用参数 config 而非全局 CONFIG
# 提速：从 1.5 -> 1.2
```

**JSDoc/TSDoc:** Not applicable (Python project)

## Function Design

**Size:**
- Functions vary widely in length (5-50 lines typical)
- Some longer functions in automation workflows (e.g., `switch_to_next_character()` at ~60 lines)
- No strict limit, but functions generally fit on screen

**Parameters:**
- Prefer explicit parameters over `**kwargs`
- Dependency injection pattern: `run_main_task(port, stop_event)`
- Configuration dictionaries passed or imported

**Return Values:**
- Explicit return types: coordinates as tuples, booleans for success
- None used for "not found" or failure cases
- Multiple return statements allowed

**Examples:**
```python
def find_element(self, template_path, roi=None, threshold=0.8):
    # ... returns (x, y) tuple or None

def get_account_char_count(account_key):
    # ... returns int or None
```

## Module Design

**Exports:**
- No `__all__` declarations
- Implicit exports via definition order
- Import patterns: `from core.ferrum_controller import FerrumController`

**Barrel Files:**
- No barrel files (index.py, __init__.py exports)
- Direct imports to specific modules

**Configuration:**
- Module-level CONFIG dictionaries with constants
- Hardcoded paths and coordinates (2560x1440 resolution specific)
- JSON files for persistent data: `account_config.json`, `slot_progress_archive.json`

**Examples:**
```python
CONFIG = {
    "SLOTS": [
        (1030, 586), (1290, 586), (1550, 586), # Row 1
        # ...
    ],
    "ROI_MENU_TITLE": (1100, 350, 1800, 550),
    # ...
}
```

## Threading and Concurrency

**Pattern:** Threading with Events
- `threading.Event()` used for cancellation signaling
- Daemon threads for background tasks
- No locks or semaphores (single-threaded logic within threads)

**Example:**
```python
self.stop_event = threading.Event()
self.running_thread = threading.Thread(
    target=main_script.run_main_task,
    args=(port, self.stop_event),
    daemon=True
)
```

## Hardware Interface Conventions

**Serial Communication:**
- Text commands over serial with `\r\n` termination
- Immediate sleep after commands: `time.sleep(0.005)`
- Clamp values to safe ranges: `max(min(int(diff_x * speed), 120), -120)`

**HID Key Codes:**
- Hardcoded decimal values (not enums or constants)
- 24 = U key, 38 = Up arrow, 40 = Down arrow, 41 = ESC, 226 = Left Alt

---

*Convention analysis: 2026-03-07*
