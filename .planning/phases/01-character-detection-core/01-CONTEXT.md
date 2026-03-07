# Phase 1: Character Detection Core - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement automatic character discovery for Lost Ark using pure image template matching. The system must detect which of the 9 visible character slots contain characters, discover the total character count through scroll traversal, and establish an account identifier without OCR or manual input.

This phase delivers the foundation for all multi-account automation — zero-config character discovery that works out-of-the-box for any account.

</domain>

<decisions>
## Implementation Decisions

### Character Slot Detection Method
- **Template-based detection**: Use `CharacterISorNo` image from assets folder
- **Masking**: FF00FF (magenta) color in template marks ignored regions
- **Detection logic**: Compare slot border features using template matching
- **ROI for each slot**:
  - 1-1: (904, 557, 1152, 624), size 248x67
  - 1-2: (1164, 557, 1412, 624), size 248x67
  - 1-3: (1425, 557, 1673, 624), size 248x67
  - 2-1: (904, 674, 1152, 741), size 248x67
  - 2-2: (1164, 674, 1412, 741), size 248x67
  - 2-3: (1425, 674, 1673, 741), size 248x67
  - 3-1: (904, 791, 1152, 858), size 248x67
  - 3-2: (1164, 791, 1412, 858), size 248x67
  - 3-3: (1425, 791, 1673, 858), size 248x67
- **Grid pattern**: 3x3 layout with ~260px column spacing, ~117px row spacing

### First-Run Discovery Flow
- **Quick index mode**: Screenshot only the first character as account identifier
- **Process**:
  1. Open ESC menu and detect character selection screen
  2. Detect which of 9 visible slots have characters
  3. Screenshot the first discovered character for account indexing
  4. Save account identifier to database
  5. Continue with automation workflow
- **Rationale**: Fast first-run experience; character details discovered on-demand during workflow

### Character Screenshot Indexing
- **Storage**: SQLite database for metadata + file system for screenshots
- **Structure**: `data/accounts/{account_hash}/characters/{slot_index}.png`
- **Screenshot content**: Character selection page screenshot for scroll detection + individual character screenshots for database
- **Account identifier**: Hash of first character's screenshot + creation timestamp
- **Progress tracking**: Screenshots also serve as "completed today" markers to avoid repetition
- **Claude's discretion**: Exact SQLite schema design (tables, indexes, relationships)

### Scroll Termination Detection
- **Method**: Template matching for scrollbar bottom indicator
- **Template image**: `Buttom.bmp` in assets folder
- **Detection ROI**: (1683, 828, 1697, 860), size 14x32
- **Logic**: If `Buttom.bmp` is detected in ROI, scrollbar has reached bottom
- **Alternative**: Screenshot comparison between consecutive pages (fallback method)

### Detection Confidence Thresholds
- **Template matching**: cv2.TM_CCOEFF_NORMED threshold >= 0.8
- **Exact match for scrollbar**: 100% pixel match for `Buttom.bmp`
- **Retries**: 3 attempts with small position jitter if initial detection fails

### Claude's Discretion
- Screenshot preprocessing (resize, grayscale, compression)
- Hash algorithm choice for account identification
- Retry logic timing and backoff strategy
- Cache invalidation policy (when to re-discover characters)
- SQLite schema design (tables, indexes, relationships)

</decisions>

<specifics>
## Specific Ideas

**Lost Ark Character Selection UI:**
- 3x3 grid layout (9 visible slots at a time)
- Scroll moves down by 3 slots (one full row)
- Character slots show: avatar (circular), character name, class icon, item level
- Empty slots show: different border color/texture

**Detection Assets:**
- `CharacterISorNo`: Template for detecting if a slot has character (FF00FF masks ignored regions)
- `Buttom.bmp`: Scrollbar bottom indicator for end-of-list detection

**Desired Behavior:**
- ESC opens character selection menu
- Bot should identify account within 5 seconds of first encounter
- Screenshot full character selection page before selecting character
- Individual character screenshots saved for database and progress tracking
- Subsequent runs recognize account instantly from cached data

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- **VisionEngine** (`core/vision_engine.py`): Template matching with `find_element()`, ROI support, screenshot capture
- **FerrumController** (`core/ferrum_controller.py`): KMBox serial communication, mouse movement, key presses
- **Slot position math** (`modules/auto_login.py`): 3x3 grid calculation logic can be adapted

### Established Patterns
- **CONFIG dictionaries**: Module-level constants for ROI coordinates and timing values
- **Template matching**: cv2.matchTemplate with TM_CCOEFF_NORMED, threshold 0.8
- **Time.sleep()**: Currently used throughout; this phase will NOT replace them (Phase 3 handles that)
- **JSON file persistence**: Existing code uses JSON for account_config.json and slot_progress_archive.json

### Integration Points
- **Database layer**: New SQLite module to be created in `core/database.py`
- **Character detector**: New module `modules/character_detector.py` implementing discovery logic
- **GUI launcher**: Will call character detector on first run before main automation loop

### Code Patterns to Follow
- Snake_case naming for functions and variables
- UPPER_CASE for config dictionary keys
- Chinese comments for user-facing messages (maintain consistency)
- Descriptive function names that explain the action

</code_context>

<deferred>
## Deferred Ideas

- **Resolution independence**: Adaptive ROI scaling for non-2560x1440 displays — v2 consideration
- **Character class detection**: Identify character class from avatar image — feature enhancement, not core requirement
- **Item level reading**: Extract item level from slot display — requires OCR or advanced CV, deferred per user requirement
- **Parallel character discovery**: Process multiple slots simultaneously — optimization for v2
- **Machine learning character recognition**: Train model to identify characters more robustly — overkill for current needs
- **YAML task orchestration**: Configuration-driven automation workflows — Phase 2 scope

</deferred>

---

*Phase: 01-character-detection-core*
*Context gathered: 2026-03-07*
