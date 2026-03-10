# LostarkGuildDonationBot

## What This Is

A game automation framework for Lost Ark (Korea server) that uses pure computer vision and hardware-based input simulation. The bot automates guild donation workflows across multiple characters with zero configuration required. It eliminates OCR dependency, optimizes execution speed through image-based waits instead of fixed sleeps, and supports seamless multi-account operation.

## Core Value

**Zero-config multi-account automation with ACE-friendly pure Python interactions.**

The bot must work out-of-the-box for any account without manual character count input, while maintaining detection-avoidance through non-intrusive automation patterns.

## Requirements

### Validated

(From existing codebase - to be validated after refactor)

- ✓ Hardware-based mouse/keyboard control via KMBox serial device
- ✓ Template matching for UI element detection (OpenCV)
- ✓ Global hotkey support for start/stop control
- ✓ Thread-safe task execution with cancellation

### Active

- [ ] **CHAR-01**: Character selection screen auto-detection via ESC menu
- [ ] **CHAR-02**: 9-slot ROI-based character presence detection (pure image matching)
- [ ] **CHAR-03**: Automatic character count discovery through scroll traversal
- [ ] **CHAR-04**: First detected character screenshot as account database index
- [ ] **CHAR-05**: Character screenshot caching for future recognition
- [ ] **CFG-01**: YAML/JSON configuration file for task definition
- [ ] **CFG-02**: Script orchestration engine for multi-step workflows
- [ ] **WAIT-01**: Image-based wait conditions (appear/disappear) replacing fixed sleeps
- [ ] **WAIT-02**: Configurable timeouts with automatic retry logic
- [ ] **ERR-01**: Automatic state recovery on network lag or UI timeouts
- [ ] **ERR-02**: Graceful handling of game client disconnections
- [ ] **ACE-01**: ACE-compliant input patterns (human-like delays, randomized movements)
- [ ] **ACE-02**: No direct game memory access or DLL injection
- [ ] **SPEED-01**: Parallel image processing where possible
- [ ] **SPEED-02**: Optimized template matching with ROI constraints
- [ ] **MULTI-01**: Seamless account switching without manual character count entry
- [ ] **MULTI-02**: Progress persistence across sessions per account

### Out of Scope

- Multi-game support (v2 consideration) — Lost Ark-only for v1
- OCR text recognition — Replaced by image template matching per user requirement
- Game memory reading — Explicitly avoided for ACE compliance
- Computer vision AI (YOLO/etc) — Overkill for current needs
- Real-time trigger detection — Will be removed or redesigned
- Non-2560x1440 resolution support — Single resolution for v1

## Context

**Current Pain Points:**
1. OCR recognition rate is low and easily interfered with
2. 39 hardcoded `time.sleep()` calls cause inefficiency
3. Character count must be manually input per account
4. Execution speed is slow due to excessive waiting
5. Character traversal based on count is stable but hard to maintain

**New Design Approach:**
- ESC menu opens character selection (9 visible slots)
- Template matching detects which slots have characters
- Scroll down moves to next row (default game behavior)
- First character screenshot becomes account identifier
- All characters discovered and cached on first run
- YAML tasks define workflows (click, wait, press sequences)

**XIGNCODE3 Compliance Strategy:**
- Pure Python interaction (no memory hooks)
- Hardware input device (KMBox) for mouse/keyboard
- Human-like timing with randomization
- No DLL injection or process manipulation
- Window-based interaction only (no direct process access)

## Constraints

- **Tech Stack**: Python 3.10+, OpenCV, PyYAML, PySerial, DXCam
- **Hardware**: KMBox or compatible serial input device required
- **Resolution**: 2560x1440 only (hard constraint for v1)
- **Game**: Lost Ark (Korea server) with XIGNCODE3 anti-cheat
- **Anti-Cheat**: Must not trigger XIGNCODE3 detection (no memory access)
- **Input Method**: Serial-based hardware simulation only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Remove OCR entirely | Low accuracy, high latency, unnecessary complexity | — Pending |
| Image-based character discovery | More robust than count-based, self-healing | — Pending |
| YAML task orchestration | User-friendly, version controllable, flexible | — Pending |
| ROI-constrained template matching | Faster processing, reduces false positives | — Pending |
| Screenshot-based account indexing | No OCR needed, visually verifiable | — Pending |

---
*Last updated: 2026-03-07 after initialization*
