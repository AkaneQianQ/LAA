# Roadmap: LostarkGuildDonationBot

**Created:** 2026-03-07
**Depth:** Quick (5 phases)
**Mode:** YOLO (auto-approve)

## Phase Overview

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Character Detection Core | Implement automatic character discovery without OCR | CHAR-01 to CHAR-05 | 5 | 4/4 | Complete    | 2026-03-07 | Build YAML/JSON task orchestration engine | CFG-01 to CFG-04 | 4 |
| 3 | Intelligent Wait System | Replace hardcoded sleeps with image-based waits | WAIT-01 to WAIT-04 | 4 |
| 4 | Error Recovery & ACE | Implement auto-recovery and ACE-compliant patterns | ERR-01 to ERR-04, ACE-01 to ACE-04 | 8 |
| 5 | Performance & Multi-Account | Optimize speed and enable seamless multi-account | SPEED-01 to SPEED-04, MULTI-01 to MULTI-04 | 8 |
| 6 | 3/3 | Complete   | 2026-03-07 | 6 |

**Total:** 6 phases | 35 requirements mapped | 100% coverage

---

## Phase 1: Character Detection Core

**Goal:** Implement automatic character discovery using pure image template matching, eliminating OCR dependency and manual character count input.

**Status:** Complete (3/3 plans)

**Plans:**
| Plan | Name | Status | Requirements |
|------|------|--------|--------------|
| 01 | Contracts and Persistence Foundation | Complete    | 2026-03-07 |
| 02 | Vision Engine Integration | Complete    | 2026-03-07 |
| 03 | Account Indexing and Screenshot Cache | Complete    | 2026-03-07 |

**Requirements:**
- CHAR-01: System detects ESC menu opening via template matching
- CHAR-02: System identifies 9 character slot ROIs using pure image matching
- CHAR-03: System discovers total character count through scroll traversal
- CHAR-04: System captures first detected character screenshot as account database index
- CHAR-05: System caches character screenshots for future recognition

**Success Criteria:**
1. Bot can open ESC menu and detect character selection screen
2. All 9 character slots are correctly identified as occupied or empty
3. Bot scrolls through all characters and counts total without manual input
4. First character screenshot is saved and used as account identifier
5. Subsequent runs recognize account from cached screenshot

**Order:** 1 (foundation for all other features)

---

## Phase 2: Configuration System

**Goal:** Build YAML/JSON-based task orchestration system that allows users to define automation workflows without code changes.

**Status:** Complete (3/3 plans)

**Plans:**
| Plan | Name | Status | Requirements |
|------|------|--------|--------------|
| 01 | YAML Configuration Foundation | Complete | CFG-01, CFG-03 |
| 02 | Workflow Executor | Complete | CFG-02, CFG-04 |
| 03 | Workflow Bootstrap | Complete | CFG-01 to CFG-04 |

**Requirements:**
- CFG-01: System loads task definitions from YAML configuration files
- CFG-02: System executes multi-step workflows defined in configuration
- CFG-03: Configuration supports click, wait, press, and scroll actions
- CFG-04: Configuration supports conditional logic based on image detection

**Success Criteria:**
1. YAML files can define complete automation workflows
2. All action types (click, wait, press, scroll) work from config
3. Conditions allow branching based on screen state
4. Example guild donation workflow implemented in YAML

**Order:** 2 (builds on character detection)

---

## Phase 3: Intelligent Wait System

**Goal:** Replace all 39 hardcoded `time.sleep()` calls with intelligent image-based wait conditions that adapt to actual UI state.

**Status:** Complete (3/3 plans)

Plans:
- [x] 03-01-PLAN.md — Add intelligent wait schema contracts and validation coverage
- [x] 03-02-PLAN.md — Implement wait_image runtime semantics and executor retry interval handling
- [x] 03-03-PLAN.md — Migrate guild workflow waits and update integration tests for end-to-end intelligent wait behavior

**Requirements:**
- WAIT-01: System waits for images to appear before proceeding
- WAIT-02: System waits for images to disappear before proceeding
- WAIT-03: System supports configurable timeouts for all wait operations
- WAIT-04: System implements automatic retry logic on timeout

**Success Criteria:**
1. No hardcoded sleep calls remain in main workflow
2. All waits use image appearance/disappearance detection
3. Timeouts are configurable per wait operation
4. Retry logic handles transient failures automatically

**Order:** 3 (integrates with config system)

---

## Phase 4: Error Recovery & XIGNCODE3 Compliance

**Goal:** Implement robust error recovery for network/UI issues and ensure all interactions comply with Tencent ACE anti-cheat detection.

**Status:** Complete (4/4 plans)

**Plans:**
| Plan | Name | Status | Requirements |
|------|------|--------|--------------|
| 01 | Recovery Contracts Schema | Complete | ERR-02, ERR-04 |
| 02 | Error Taxonomy & RecoveryOrchestrator | Complete | ERR-01, ERR-02, ERR-03 |
| 03 | Structured Logging & Evidence | Complete | ERR-04 |
| 04 | ACE Compliance Guard | Complete | ACE-01, ACE-02, ACE-03, ACE-04 |

**Requirements:**
- ERR-01: System detects and recovers from network lag conditions
- ERR-02: System handles UI loading timeouts gracefully
- ERR-03: System recovers from game client disconnection scenarios
- ERR-04: System logs all errors with context for debugging
- ACE-01: System uses only hardware-based input simulation
- ACE-02: System implements human-like timing with randomized delays
- ACE-03: System avoids any direct game memory access
- ACE-04: System avoids DLL injection or process manipulation

**Success Criteria:**
1. Bot recovers automatically from network lag without manual intervention
2. All input uses KMBox hardware device (no software simulation)
3. Timing includes human-like randomization (±20% variance)
4. No memory access or injection techniques used
5. Comprehensive error logging to file for troubleshooting

**Order:** 4 (safety layer for production use)

---

## Phase 5: Performance & Multi-Account

**Goal:** Optimize execution speed through parallel processing and ROI constraints, and implement seamless multi-account operation.

**Status:** Complete (4/4 plans)

**Plans:**
| Plan | Name | Status | Requirements | Files Modified |
|------|------|--------|--------------|----------------|
| 01 | Frame Caching System | Complete | SPEED-04 | core/frame_cache.py |
| 02 | Parallel ROI Matching | Complete | SPEED-01, SPEED-02 | core/parallel_matcher.py, modules/character_detector.py |
| 03 | Account Manager and Progress Persistence | Complete | MULTI-01, MULTI-02, MULTI-04 | core/account_manager.py, core/progress_tracker.py |
| 04 | Account Switching and Sleep Verification | Complete | MULTI-03, SPEED-03 | core/account_switcher.py, modules/workflow_bootstrap.py |

**Requirements:**
- SPEED-01: System processes images in parallel where possible
- SPEED-02: System constrains template matching to specified ROIs
- SPEED-03: System eliminates all hardcoded time.sleep() calls
- SPEED-04: System implements frame caching to reduce capture overhead
- MULTI-01: System automatically identifies accounts without manual character count entry
- MULTI-02: System persists progress per account across sessions
- MULTI-03: System supports switching between accounts without restart
- MULTI-04: System maintains separate state databases per account

**Success Criteria:**
1. Template matching completes in <100ms per ROI-constrained search
2. Account switching requires no manual character count input
3. Progress tracked separately per account in database
4. Frame caching reduces screen capture calls by 50%+
5. End-to-end guild donation workflow completes in under 30 seconds per character

**Order:** 5 (final polish and optimization)

---

## Phase 6: Interactive Test Flow System

**Goal:** Create an F1-driven interactive test interface system where users follow AI instructions to manually operate the game and provide feedback on observations. This is a "human-in-the-loop" testing system for verifying automation flow accuracy and stability.

**Status:** Planned (3 plans)

**Plans:**
3/3 plans complete
|------|------|--------|--------------|----------------|
| 01 | Overlay UI System | Planned | TEST-01, TEST-02 | tests/interactive/overlay.py, tests/interactive/test_overlay.py |
| 02 | Test Flow Engine and JSON Logging | Planned | TEST-03, TEST-04 | tests/interactive/test_logger.py, tests/interactive/test_flow.py |
| 03 | Test Scenarios and Integration | Planned | TEST-05, TEST-06 | tests/interactive/scenarios.py, tests/interactive/test_runner.py, test_flow_launcher.py |

**Requirements:**
- TEST-01: System displays semi-transparent overlay (600x80 pixels, 70% opacity, dark theme)
- TEST-02: Overlay supports drag via title bar and close button
- TEST-03: System logs test results to JSON with timestamps and user feedback
- TEST-04: Test flow manages linear step progression with skip support
- TEST-05: System provides scenario selection dropdown with hardcoded Python scenarios
- TEST-06: Hotkeys work as specified (F1=next, END=terminate, Y/N=pass/fail)

**Success Criteria:**
1. Overlay appears at top-left (600x80 pixels), semi-transparent, draggable
2. User can select test scenario from dropdown
3. F1 advances steps, Y/N records feedback, END terminates
4. Test results saved to JSON files in logs/tests/
5. Two complete scenarios: guild_donation (8 steps) and character_detection (6 steps)
6. All instructions displayed in Chinese

**Wave Structure:**
- **Wave 1 (Parallel):** Plan 01 (Overlay UI), Plan 02 (Test Flow Engine)
- **Wave 2 (Sequential):** Plan 03 (Integration and Scenarios) - depends on Wave 1

**Order:** 6 (testing infrastructure for verification)

---

## Implementation Notes

### Dependencies Between Phases
- Phase 1 → Phase 2: Character detection required for workflow testing
- Phase 2 → Phase 3: Config system needed to define wait conditions
- Phase 3 → Phase 4: Intelligent waits required for error recovery
- Phase 4 → Phase 5: XIGNCODE3 compliance required before multi-account testing
- Phase 5 → Phase 6: Test flow verifies all previous phases work correctly

### Phase 06.1: 基于Phase 6的测试框架，添加Ferrum硬件连接预检测试作为所有测试的前置检查 (INSERTED)

**Goal:** [Urgent work - to be planned]
**Requirements**: TBD
**Depends on:** Phase 6
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 06.1 to break down)

### Phase 05.1: 现在基于这个项目编写一个全功能测试脚本，调用superpowers:brainstorm (INSERTED)

**Goal:** [Urgent work - to be planned]
**Requirements**: TBD
**Depends on:** Phase 5
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 05.1 to break down)

### Phase 5 Wave Structure

**Wave 1 (Parallel Execution):**
- Plan 05-01: Frame Caching System (SPEED-04)
- Plan 05-02: Parallel ROI Matching (SPEED-01, SPEED-02)

**Wave 2 (Sequential - depends on Wave 1):**
- Plan 05-03: Account Manager and Progress Persistence (MULTI-01, MULTI-02, MULTI-04)
- Plan 05-04: Account Switching and Sleep Verification (MULTI-03, SPEED-03)

### Risk Areas
- **Phase 1**: Character slot detection accuracy depends on template images
- **Phase 3**: Replacing all sleeps may expose race conditions
- **Phase 4**: XIGNCODE3 compliance cannot be fully tested without actual game
- **Phase 5**: Parallel processing may have GIL contention; requires benchmarking
- **Phase 6**: Overlay window management may conflict with game fullscreen mode

### Rollback Strategy
- Each phase maintains backward compatibility with existing code
- Old `main.py` preserved until Phase 5 complete
- Feature flags allow gradual migration

### Phase 7: 基于skills：ferrum和现有的代码，开发一个交互逻辑子程序，满足项目内现有代码所有的交互逻辑调用

**Goal:** Integrate Ferrum hardware API for all keyboard/mouse interactions via FerrumController that implements the hardware controller interface expected by HardwareInputGateway.

**Requirements:**
- REQ-HW-01: Ferrum serial communication via pyserial
- REQ-HW-02: Command/response protocol handling with echo parsing
- REQ-HW-03: Hardware initialization (km.init())
- REQ-MOUSE-01: Mouse movement via km.move(x, y)
- REQ-MOUSE-02: Left button click via km.click(0)
- REQ-MOUSE-03: Scroll wheel via km.wheel(amount)
- REQ-KBD-01: Key name to HID code mapping
- REQ-KBD-02: Key press via km.down() + km.up()
- REQ-KBD-03: Key combination support (e.g., "alt+u")
- REQ-INT-01: FerrumController compatible with HardwareInputGateway
- REQ-INT-02: Works with ActionDispatcher
- REQ-INT-03: End-to-end testing capability

**Depends on:** Phase 6
**Plans:** 4/4 plans complete

| Plan | Name | Wave | Depends On |
|------|------|------|------------|
| 07.01 | FerrumController Core and Serial Communication | 1 | - |
| 07.02 | Mouse Actions - Move, Click, and Scroll | 1 | 07.01 |
| 07.03 | Keyboard Actions - HID Mapping and Key Press | 1 | 07.01 |
| 07.04 | Integration with HardwareInputGateway and Testing | 2 | 07.01, 07.02, 07.03 |

**Success Criteria:**
1. FerrumController connects to Ferrum device via serial port
2. All commands use correct Ferrum KM API syntax (km.move, km.click, km.press, etc.)
3. Key combinations like "alt+u" work correctly for guild menu
4. HardwareInputGateway wraps FerrumController and adds jitter/compliance
5. ActionDispatcher successfully dispatches actions through the full chain
6. Integration tests verify end-to-end functionality

### Phase 8: 创建基于MXU框架的前端，兼容assets/tasks工作脚本并支持自动识别功能

**Goal:** Create a frontend based on MXU (MaaFramework Next UI) framework that provides a graphical interface for the FerrumBot automation system. The frontend must be compatible with existing `assets/tasks/*.yaml` workflow scripts and support automatic recognition features for game window, hardware, and account identification.

**Requirements:**
- MXU-01: Frontend uses Tauri v2 + React 19 + TypeScript architecture
- MXU-02: Frontend loads and parses interface.json configuration
- MXU-03: Python service exposes WebSocket API for frontend communication
- MXU-04: Auto-recognition detects Lost Ark game window automatically
- MXU-05: Auto-recognition detects KMBox/Ferrum hardware on COM ports
- MXU-06: Frontend connects to Python service via WebSocket through Tauri IPC
- MXU-07: Task execution can be started/stopped from frontend UI
- MXU-08: Real-time logs stream to frontend log viewer component

**Depends on:** Phase 7
**Plans:** 3 plans planned

| Plan | Name | Wave | Depends On |
|------|------|------|------------|
| 08-01 | MXU Frontend Setup and Tauri Integration | 1 | - |
| 08-02 | Python Service WebSocket API and Auto-Recognition | 1 | - |
| 08-03 | Frontend-Backend Integration and Task Execution | 2 | 08-01, 08-02 |

**Wave Structure:**
- **Wave 1 (Parallel):** Plan 08-01 (Frontend Setup), Plan 08-02 (WebSocket API)
- **Wave 2 (Sequential):** Plan 08-03 (Integration) - depends on Wave 1

**Success Criteria:**
1. MXU frontend project builds successfully with Tauri v2 + React 19
2. Frontend displays task list from interface.json with Chinese labels
3. Python service WebSocket server accepts connections on port 8765
4. Auto-detection finds Lost Ark window, KMBox hardware, and identifies account
5. Frontend can start/stop tasks and view real-time execution logs
6. Dark theme and Chinese language are defaults

---

*Roadmap created: 2026-03-07*
*Updated: 2026-03-09 with Phase 8 plans*
