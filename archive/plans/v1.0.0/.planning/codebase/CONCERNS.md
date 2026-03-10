# Codebase Concerns

**Analysis Date:** 2026-03-07

## Tech Debt

### Hardcoded Coordinates and Magic Numbers
- **Issue:** All screen coordinates, ROI regions, and timing values are hardcoded for 2560x1440 resolution
- **Files:** `modules/auto_login.py`, `modules/guild_donation.py`, `trigger_action.py`
- **Impact:** Code will fail on any other screen resolution or if game UI changes
- **Fix approach:** Extract coordinates to configuration files with resolution detection and scaling

### Excessive Hardcoded Sleep Calls
- **Issue:** 39 `time.sleep()` calls throughout codebase with no wait conditions or synchronization
- **Files:** All modules
- **Impact:** Brittle automation that breaks under lag or varying load times; unnecessarily slow execution
- **Fix approach:** Replace with image-based waits (wait for element to appear/disappear) or implement dynamic polling

### Silent Exception Swallowing
- **Issue:** Multiple bare `except: pass` blocks hide errors
- **Files:**
  - `core/vision_engine.py:25-26` (debug file cleanup)
  - `modules/auto_login.py:31, 41, 69, 79` (JSON file operations)
- **Impact:** Errors go unnoticed, making debugging difficult; data corruption possible
- **Fix approach:** Add proper logging to exception handlers even if continuing execution

### Mixed Language Comments and Strings
- **Issue:** Code uses English identifiers but Chinese comments and some user-facing strings
- **Files:** Throughout codebase
- **Impact:** Inconsistent maintainability for international developers
- **Fix approach:** Standardize on English for all comments and user messages

## Known Bugs

### JSON Archive Data Corruption
- **Symptoms:** Slot indices appear out of order in archive (e.g., 2026-02-21 shows [..., 14, 13, 15])
- **Files:** `slot_progress_archive.json` lines 99-100
- **Trigger:** Race condition or manual editing of archive file
- **Workaround:** Manual deletion of corrupted date entries

### Hardcoded Asset Paths in Trigger Config
- **Symptoms:** Will fail in PyInstaller bundle if assets not properly bundled
- **Files:** `trigger_action.py:10, 15`
- **Trigger:** Running as executable vs running in development
- **Fix:** Use `get_resource_path()` utility like other modules do

### No Validation of Character Count Input
- **Symptoms:** User can enter invalid character counts via GUI dialog
- **Files:** `main.py:29`
- **Trigger:** Entering wrong character count breaks scroll calculations
- **Impact:** Auto-login logic fails, may scroll incorrectly or miss characters

## Security Considerations

### No Input Validation on JSON Files
- **Risk:** Malformed JSON in account_config.json or slot_progress_archive.json can crash the bot
- **Files:** `modules/auto_login.py` (all JSON loading functions)
- **Current mitigation:** Bare except blocks catch errors but hide them
- **Recommendations:** Add JSON schema validation and backup file creation

### Hardcoded File Paths
- **Risk:** Path traversal possible if account keys contain special characters
- **Files:** `modules/auto_login.py:58` (account key used directly in regex)
- **Current mitigation:** Regex sanitizes account key for OCR
- **Recommendations:** Validate account keys before using as filenames or in paths

### No Rate Limiting on Hardware Commands
- **Risk:** Could potentially overwhelm KMBox device with rapid commands
- **Files:** `core/ferrum_controller.py`
- **Current mitigation:** Small sleeps between commands
- **Recommendations:** Add command queue with minimum interval enforcement

## Performance Bottlenecks

### Inefficient Screen Capture
- **Problem:** DXCam initialized once but no frame buffering; multiple captures per operation
- **Files:** `core/vision_engine.py`
- **Cause:** Each `get_screen()` call captures fresh frame; rapid successive calls are expensive
- **Improvement path:** Implement frame caching with configurable TTL (e.g., 50ms)

### Blocking Sleep in Main Loops
- **Problem:** 20ms-22 second blocking sleeps prevent responsive shutdown
- **Files:**
  - `modules/auto_login.py:148-149` (22 second character load wait)
  - `trigger_action.py:59` (20ms polling loop)
- **Cause:** Sleep cannot be interrupted except via `os._exit(0)`
- **Improvement path:** Use `stop_event.wait(timeout)` instead of `time.sleep()` for cancellable delays

### OCR Engine Lazy Loading Without Cleanup
- **Problem:** RapidOCR initialized on first use but never released; memory overhead
- **Files:** `core/vision_engine.py:62`
- **Cause:** OCR object created once and held for entire session
- **Improvement path:** Implement context manager pattern for OCR resource management

## Fragile Areas

### Character Switching Logic
- **Files:** `modules/auto_login.py:97-157`
- **Why fragile:** Complex scroll math with multiple edge cases (max_scroll, tail page alignment)
- **Safe modification:** Add extensive logging and test with various character counts (1-50)
- **Test coverage:** No automated tests; manual testing only

### Guild Donation Workflow
- **Files:** `modules/guild_donation.py:40-87`
- **Why fragile:** Multiple sequential UI interactions with fixed sleeps; any UI change breaks flow
- **Safe modification:** Add verification steps between actions with retry logic
- **Test coverage:** None; relies entirely on visual template matching

### Hardware Communication
- **Files:** `core/ferrum_controller.py`
- **Why fragile:** Serial communication with no retry logic; assumes KMBox always responsive
- **Safe modification:** Add command acknowledgment checking and reconnection logic
- **Test coverage:** None; requires physical hardware to test

### Template Matching Dependencies
- **Files:** All modules using `vision.find_element()`
- **Why fragile:** Template images must exactly match game UI; any game update breaks automation
- **Safe modification:** Implement fuzzy matching with confidence thresholds and fallback strategies
- **Test coverage:** No validation that template images exist until runtime

## Scaling Limits

### Archive File Growth
- **Current capacity:** Unlimited daily entries in JSON file
- **Limit:** File will grow indefinitely; JSON parsing slows over time
- **Scaling path:** Implement log rotation or database (SQLite) for history

### Character Slot Maximum
- **Current capacity:** Hard limit of 50 characters (GUI dialog max)
- **Limit:** UI math assumes 3-column grid; breaks if game changes layout
- **Scaling path:** Make grid dimensions configurable

### Single-Threaded Execution
- **Current capacity:** One automation task at a time
- **Limit:** Cannot parallelize multiple accounts simultaneously
- **Scaling path:** Would require significant architectural changes for multi-instance support

## Dependencies at Risk

### RapidOCR ONNX Runtime
- **Risk:** Heavy dependency for simple text recognition (account ID)
- **Impact:** Large bundle size, potential compatibility issues
- **Migration plan:** Consider lighter OCR alternative or template matching for known account IDs

### DXCam Screen Capture
- **Risk:** Windows-specific, requires specific display setup
- **Impact:** Won't work on multi-monitor setups or if game not on primary display
- **Migration plan:** Add display selection configuration and fallback capture methods

### KMBox Hardware Dependency
- **Risk:** Proprietary hardware required; no software fallback
- **Impact:** Cannot run without physical device
- **Migration plan:** Add optional pyautogui fallback for development/testing (with detection risk warning)

### PyInstaller Single-Executable Build
- **Risk:** Antivirus false positives common with PyInstaller bundles
- **Impact:** Users may not be able to run executable
- **Migration plan:** Provide alternative distribution methods (Python source with requirements.txt)

## Missing Critical Features

### State Recovery and Resume
- **Problem:** If bot crashes mid-session, progress is lost for current character
- **Files:** `main.py` workflow
- **Blocks:** Reliable unattended operation

### Comprehensive Logging
- **Problem:** Print statements only; no structured logging or log files
- **Files:** Throughout
- **Blocks:** Debugging production issues

### Configuration Management
- **Problem:** Hardcoded values scattered across files; no centralized config
- **Files:** All modules
- **Blocks:** Easy customization and maintenance

### Input Validation
- **Problem:** No validation on user inputs, file contents, or hardware responses
- **Files:** Throughout
- **Blocks:** Robust error handling

## Test Coverage Gaps

### No Unit Tests
- **What's not tested:** Any function or module
- **Files:** All `.py` files
- **Risk:** Changes can break functionality without detection
- **Priority:** High

### No Integration Tests
- **What's not tested:** End-to-end workflows (login, donation, switching)
- **Files:** Workflow orchestration in `main.py`
- **Risk:** Module interactions fail in production
- **Priority:** High

### No Hardware Mocking
- **What's not tested:** KMBox communication without physical device
- **Files:** `core/ferrum_controller.py`
- **Risk:** Cannot develop or test without hardware connected
- **Priority:** Medium

### No Visual Regression Tests
- **What's not tested:** Template matching accuracy
- **Files:** All template images in `assets/`
- **Risk:** Game updates break template matching
- **Priority:** Medium

---

*Concerns audit: 2026-03-07*
