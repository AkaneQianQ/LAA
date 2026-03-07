# Codebase Structure

**Analysis Date:** 2026-03-07

## Directory Layout

```
[project-root]/
├── assets/              # Template images for computer vision
├── core/                # Core hardware and vision abstractions
│   ├── ferrum_controller.py
│   └── vision_engine.py
├── modules/             # Automation workflow implementations
│   ├── auto_login.py
│   └── guild_donation.py
├── .planning/           # Planning documentation (this directory)
│   └── codebase/
├── build/               # PyInstaller build artifacts
├── dist/                # Executable output directory
├── gui_launcher.py      # Main GUI entry point
├── main.py              # Main automation task script
├── trigger_action.py    # Real-time trigger detection task
├── FerrumBot_v1.spec    # PyInstaller specification
├── account_config.json  # Account character count configuration
└── slot_progress_archive.json  # Daily progress tracking
```

## Directory Purposes

**assets/:**
- Purpose: Template images for OpenCV template matching
- Contains: PNG images for UI elements (buttons, markers, targets)
- Key files: `btn_*.png`, `guild_flag_mark.png`, `target_*.png`, `status_online_tag.png`
- Note: All assets must be listed in `FerrumBot_v1.spec` datas array

**core/:**
- Purpose: Hardware abstraction and computer vision engine
- Contains: Low-level controller classes with no game-specific logic
- Key files: `ferrum_controller.py`, `vision_engine.py`
- Pattern: Reusable hardware interface layer

**modules/:**
- Purpose: Game-specific automation workflows
- Contains: High-level automation logic for specific tasks
- Key files: `auto_login.py` (character switching), `guild_donation.py` (donation workflow)
- Pattern: Task-specific automation scripts with hardcoded coordinates

**.planning/codebase/:**
- Purpose: Architecture and planning documentation
- Contains: Markdown files documenting system design
- Generated: No
- Committed: Yes

**build/ & dist/:**
- Purpose: PyInstaller output directories
- Contains: Build artifacts and final executable
- Generated: Yes (by `pyinstaller FerrumBot_v1.spec`)
- Committed: No (should be in .gitignore)

## Key File Locations

**Entry Points:**
- `gui_launcher.py`: Primary user interface - run this for normal operation
- `main.py`: CLI entry point for main automation (called by GUI)
- `trigger_action.py`: CLI entry point for trigger detection (called by GUI)

**Configuration:**
- `FerrumBot_v1.spec`: PyInstaller build configuration - edit when adding new assets
- `account_config.json`: Maps account names to character counts (e.g., `{"AccountName": 21}`)
- `slot_progress_archive.json`: Tracks processed slots per account by date

**Core Logic:**
- `core/ferrum_controller.py`: Serial communication with KMBox hardware
- `core/vision_engine.py`: Screen capture, template matching, OCR
- `modules/auto_login.py`: Character grid navigation and login logic
- `modules/guild_donation.py`: Guild donation UI workflow

**Data Files:**
- `assets/*.png`: Template images for CV matching
- `slot_progress_archive.json`: Daily progress persistence
- `account_config.json`: Account metadata

## Naming Conventions

**Files:**
- Modules: `snake_case.py` (e.g., `auto_login.py`, `guild_donation.py`)
- Assets: `descriptive_element_type.png` (e.g., `btn_login_yellow.png`, `guild_flag_mark.png`)
- Config: `descriptive_name.json` (e.g., `account_config.json`)

**Directories:**
- Lowercase, descriptive (e.g., `core/`, `modules/`, `assets/`)

**Classes:**
- PascalCase, descriptive (e.g., `FerrumController`, `VisionEngine`, `FerrumApp`)

**Functions:**
- snake_case, action-oriented (e.g., `run_main_task()`, `switch_to_next_character()`)

**Constants:**
- UPPER_CASE in CONFIG dictionaries (e.g., `ROI_MENU_TITLE`, `LOAD_CHAR_WAIT`)

**Variables:**
- snake_case, descriptive (e.g., `bot`, `vision`, `current_abs`, `total_count`)

## Where to Add New Code

**New Automation Task:**
- Primary code: Create `modules/new_task.py` with `run_new_task(bot, vision)` function
- Integration: Import and call from `main.py` or create new execution script
- Assets: Add template images to `assets/` and update `FerrumBot_v1.spec`

**New Vision Capability:**
- Implementation: Add method to `core/vision_engine.py`
- Pattern: Follow existing methods like `find_element()` or `get_text()`
- Return: Coordinates tuple, boolean, or extracted data

**New Hardware Command:**
- Implementation: Add method to `core/ferrum_controller.py`
- Pattern: Use `send_command()` with KMBox protocol string
- Commands: `km.move(dx, dy)`, `km.click(0)`, `km.press(hid_code)`

**New ROI Configuration:**
- Location: Add to CONFIG dict in relevant module
- Format: `"DESCRIPTIVE_NAME": (x1, y1, x2, y2)`
- Resolution: All coordinates are for 2560x1440

**GUI Modifications:**
- Location: `gui_launcher.py` in `FerrumApp` class
- Pattern: Add button method, create thread with `stop_event`, register hotkey

## Special Directories

**assets/:**
- Purpose: Template images for computer vision
- Generated: No
- Committed: Yes
- Critical: Must update `FerrumBot_v1.spec` datas array when adding files

**core/__pycache__/, modules/__pycache__/:**
- Purpose: Python bytecode cache
- Generated: Yes
- Committed: No

**dist/:**
- Purpose: Final executable output
- Generated: Yes (by PyInstaller)
- Committed: No
- Output: `dist/FerrumBot_v1.exe`

---

*Structure analysis: 2026-03-07*
