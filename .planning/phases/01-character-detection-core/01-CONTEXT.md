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
- **Dual detection approach**: Detect both character presence AND empty slot markers
- **Primary**: Character avatar presence detection in slot center region
- **Secondary**: Empty slot background/UI detection for validation
- **Result**: Slot marked as occupied only if character avatar detected AND empty marker NOT detected

### First-Run Discovery Flow
- **Complete discovery mode on first encounter**: Full character enumeration and caching
- **Process**:
  1. Detect all 9 visible slots for character presence
  2. Screenshot each discovered character (for account indexing)
  3. Scroll down to next page
  4. Repeat until no new characters detected
  5. Save all character data to database
- **Rationale**: First run establishes complete account profile; subsequent runs use cached data for instant recognition

### Character Screenshot Indexing
- **Storage**: SQLite database for metadata + file system for screenshots
- **Structure**: `data/accounts/{account_hash}/characters/{slot_index}.png`
- **Screenshot content**: Character avatar only (not full slot) for precise matching
- **Account identifier**: Hash of first character's screenshot + creation timestamp
- **Database schema**: Characters table with account_id, slot_index, screenshot_path, discovered_at

### Scroll Termination Detection
- **Approach**: Screenshot comparison between consecutive pages
- **Logic**: If current page screenshot matches previous page screenshot → reached end
- **Optimization**: Compare only the 3 bottom slots (positions 7-9) since top slots may show overlap
- **Fallback**: Maximum 10 scroll attempts as safety limit (supports up to 30 characters)

### ROI Coordinates
- **Source**: User will provide precise ROI coordinates for 9 slots at 2560x1440 resolution
- **Format**: List of (x1, y1, x2, y2) tuples for each slot position
- **Avatar ROI**: Sub-region within each slot for character screenshot capture
- **Graceful degradation**: If user doesn't provide coordinates, implement will fail with clear error message

### Detection Confidence Thresholds
- **Character presence**: cv2.TM_CCOEFF_NORMED threshold >= 0.8
- **Empty slot detection**: Same threshold, separate template
- **Screenshot matching**: threshold >= 0.9 for account identification
- **Retries**: 3 attempts with small position jitter if initial detection fails

### Claude's Discretion
- Exact SQLite schema design (tables, indexes, relationships)
- Screenshot preprocessing (resize, grayscale, compression)
- Hash algorithm choice for account identification
- Retry logic timing and backoff strategy
- Cache invalidation policy (when to re-discover characters)

</decisions>

<specifics>
## Specific Ideas

**Lost Ark Character Selection UI:**
- 3x3 grid layout (9 visible slots at a time)
- Scroll moves down by 3 slots (one full row)
- Character slots show: avatar (circular), character name, class icon, item level
- Empty slots show: "+" icon or darker background

**Desired Behavior:**
- ESC opens character selection menu
- Bot should identify account within 5 seconds of first encounter
- Subsequent runs should identify account instantly from cached data
- Character discovery should complete within 30 seconds for accounts with 20+ characters

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

</deferred>

---

*Phase: 01-character-detection-core*
*Context gathered: 2026-03-07*
