# Architecture

**Analysis Date:** 2026-03-07

## Pattern Overview

**Overall:** Layered Architecture with Hardware Abstraction

**Key Characteristics:**
- Hardware-software bridge pattern for KMBox serial device control
- Computer vision-based automation with template matching
- Event-driven task execution with threading
- State persistence via JSON files for tracking progress
- Hardcoded ROI coordinates for 2560x1440 resolution

## Layers

**Hardware Interface Layer:**
- Purpose: Abstracts KMBox serial device communication for mouse/keyboard control
- Location: `core/ferrum_controller.py`
- Contains: Serial connection management, mouse movement, key presses, HID commands
- Depends on: `pyserial`, `win32api`
- Used by: All automation modules (`main.py`, `trigger_action.py`, `modules/auto_login.py`, `modules/guild_donation.py`)

**Vision Engine Layer:**
- Purpose: Computer vision and screen analysis for UI element detection
- Location: `core/vision_engine.py`
- Contains: Screen capture, template matching, OCR text extraction, pixel color checking
- Depends on: `dxcam`, `opencv-python`, `rapidocr_onnxruntime`
- Used by: All automation modules for UI state detection

**Automation Logic Layer:**
- Purpose: High-level automation workflows and game-specific logic
- Location: `modules/auto_login.py`, `modules/guild_donation.py`
- Contains: Character switching, guild donation workflows, scroll calculations
- Depends on: Hardware Interface Layer, Vision Engine Layer
- Used by: Main execution scripts

**Execution Layer:**
- Purpose: Entry points and task orchestration
- Location: `main.py`, `trigger_action.py`
- Contains: Main automation loop, trigger detection loop, error handling
- Depends on: All lower layers
- Used by: GUI Launcher

**Presentation Layer:**
- Purpose: User interface and task control
- Location: `gui_launcher.py`
- Contains: Tkinter GUI, global hotkey registration, thread management
- Depends on: Execution Layer scripts
- Used by: End user

## Data Flow

**Main Automation Flow:**

1. User starts task via GUI (F10 hotkey or button)
2. `gui_launcher.py` creates thread running `main.run_main_task(port, stop_event)`
3. `main.py` initializes `FerrumController` and `VisionEngine`
4. Account identification via OCR on character selection screen
5. Load character count from `account_config.json` (prompt if missing)
6. Load processed slots from `slot_progress_archive.json`
7. WHILE not stopped:
   - Execute guild donation workflow (`run_guild_donation()`)
   - Save progress to archive
   - Switch to next character (`switch_to_next_character()`)
   - Calculate scroll position based on 3x3 grid math
   - Login to next character
8. Clean up and close serial connection

**Trigger Detection Flow:**

1. User starts trigger via GUI (F11 hotkey or button)
2. `gui_launcher.py` creates thread running `trigger_action.run_trigger_task()`
3. Continuous 20ms polling loop:
   - Check for target image A in ROI → Execute key sequence (Up, Up, Down)
   - Check for target images B in full screen → Execute offset clicks + Enter
4. Stop on END key or GUI stop button

**State Management:**
- Character progress: `slot_progress_archive.json` (date-keyed)
- Account metadata: `account_config.json` (character counts)
- Runtime state: `threading.Event` objects for cancellation

## Key Abstractions

**FerrumController:**
- Purpose: Hardware abstraction for KMBox serial device
- Examples: `core/ferrum_controller.py`
- Pattern: Device controller with command queue
- Key Methods: `move_to()`, `click()`, `press_key()`, `send_command()`

**VisionEngine:**
- Purpose: Screen analysis and computer vision operations
- Examples: `core/vision_engine.py`
- Pattern: Service class with lazy-loaded OCR
- Key Methods: `get_screen()`, `find_element()`, `get_text()`, `check_pixel_color()`

**Configuration Dictionaries:**
- Purpose: Centralize hardcoded coordinates and parameters
- Examples: `CONFIG` in `modules/auto_login.py`, `ROI_CONFIG` in `modules/guild_donation.py`, `CONFIG` in `trigger_action.py`
- Pattern: Module-level constants for ROI coordinates, file paths, timing values

## Entry Points

**GUI Launcher:**
- Location: `gui_launcher.py`
- Triggers: Direct execution `python gui_launcher.py`
- Responsibilities: Initialize Tkinter UI, register global hotkeys, manage worker threads

**Main Task:**
- Location: `main.py` → `run_main_task(port, stop_event)`
- Triggers: F10 hotkey or GUI button
- Responsibilities: Orchestrate full automation workflow across multiple characters

**Trigger Task:**
- Location: `trigger_action.py` → `run_trigger_task(port, stop_event, config)`
- Triggers: F11 hotkey or GUI button
- Responsibilities: Real-time image detection and immediate response

## Error Handling

**Strategy:** Try-catch blocks with cleanup in finally blocks

**Patterns:**
- Serial connection cleanup in `finally` blocks
- Thread-safe stopping via `threading.Event`
- Keyboard interrupt checking via `win32api.GetAsyncKeyState(0x23)` (END key)
- Retry logic in `reset_and_restart()` for guild donation flow
- Traceback printing for crash diagnostics

## Cross-Cutting Concerns

**Logging:** Print statements with Chinese prefixes (e.g., "[公会]", "[任务]", "[错误]")

**Validation:** Hardcoded ROI coordinates validated at runtime via template matching confidence thresholds (default 0.8)

**Authentication:** None (local hardware device only)

---

*Architecture analysis: 2026-03-07*
