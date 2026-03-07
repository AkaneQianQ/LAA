# Roadmap: LostarkGuildDonationBot

**Created:** 2026-03-07
**Depth:** Quick (5 phases)
**Mode:** YOLO (auto-approve)

## Phase Overview

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Character Detection Core | Implement automatic character discovery without OCR | CHAR-01 to CHAR-05 | 5 |
| 2 | Configuration System | Build YAML/JSON task orchestration engine | CFG-01 to CFG-04 | 4 |
| 3 | Intelligent Wait System | Replace hardcoded sleeps with image-based waits | WAIT-01 to WAIT-04 | 4 |
| 4 | Error Recovery & ACE | Implement auto-recovery and ACE-compliant patterns | ERR-01 to ERR-04, ACE-01 to ACE-04 | 8 |
| 5 | Performance & Multi-Account | Optimize speed and enable seamless multi-account | SPEED-01 to SPEED-04, MULTI-01 to MULTI-04 | 8 |

**Total:** 5 phases | 29 requirements mapped | 100% coverage ✓

---

## Phase 1: Character Detection Core

**Goal:** Implement automatic character discovery using pure image template matching, eliminating OCR dependency and manual character count input.

**Status:** ✓ Complete (3/3 plans)

**Plans:**
| Plan | Name | Status | Requirements |
|------|------|--------|--------------|
| 01 | Contracts and Persistence Foundation | Complete    | 2026-03-07 |
| 02 | Vision Engine Integration | ✓ Complete | CHAR-01, CHAR-02, CHAR-03 |
| 03 | Account Indexing and Screenshot Cache | ✓ Complete | CHAR-04, CHAR-05 |

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

**Status:** ✓ Complete (3/3 plans)

**Plans:**
| Plan | Name | Status | Requirements |
|------|------|--------|--------------|
| 01 | YAML Configuration Foundation | ✓ Complete | CFG-01, CFG-03 |
| 02 | Workflow Executor | ✓ Complete | CFG-02, CFG-04 |
| 03 | Workflow Bootstrap | ✓ Complete | CFG-01 to CFG-04 |

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

## Implementation Notes

### Dependencies Between Phases
- Phase 1 → Phase 2: Character detection required for workflow testing
- Phase 2 → Phase 3: Config system needed to define wait conditions
- Phase 3 → Phase 4: Intelligent waits required for error recovery
- Phase 4 → Phase 5: XIGNCODE3 compliance required before multi-account testing

### Risk Areas
- **Phase 1**: Character slot detection accuracy depends on template images
- **Phase 3**: Replacing all sleeps may expose race conditions
- **Phase 4**: XIGNCODE3 compliance cannot be fully tested without actual game

### Rollback Strategy
- Each phase maintains backward compatibility with existing code
- Old `main.py` preserved until Phase 5 complete
- Feature flags allow gradual migration

---

*Roadmap created: 2026-03-07*
