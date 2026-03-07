# Requirements: FerrumBot Refactor

**Defined:** 2026-03-07
**Core Value:** Zero-config multi-account automation with ACE-friendly pure Python interactions

## v1 Requirements

### Character Detection (CHAR)

Requirements for automatic character discovery and indexing without manual configuration.

- [ ] **CHAR-01**: System detects ESC menu opening via template matching
- [ ] **CHAR-02**: System identifies 9 character slot ROIs using pure image matching
- [ ] **CHAR-03**: System discovers total character count through scroll traversal
- [ ] **CHAR-04**: System captures first detected character screenshot as account database index
- [ ] **CHAR-05**: System caches character screenshots for future recognition

### Configuration System (CFG)

Requirements for YAML/JSON-based task orchestration.

- [ ] **CFG-01**: System loads task definitions from YAML configuration files
- [ ] **CFG-02**: System executes multi-step workflows defined in configuration
- [ ] **CFG-03**: Configuration supports click, wait, press, and scroll actions
- [ ] **CFG-04**: Configuration supports conditional logic based on image detection

### Wait Conditions (WAIT)

Requirements replacing hardcoded sleeps with intelligent image-based waits.

- [x] **WAIT-01**: System waits for images to appear before proceeding
- [x] **WAIT-02**: System waits for images to disappear before proceeding
- [x] **WAIT-03**: System supports configurable timeouts for all wait operations
- [x] **WAIT-04**: System implements automatic retry logic on timeout

### Error Recovery (ERR)

Requirements for handling exceptions and recovering from failures.

- [x] **ERR-01**: System detects and recovers from network lag conditions
- [x] **ERR-02**: System handles UI loading timeouts gracefully
- [x] **ERR-03**: System recovers from game client disconnection scenarios
- [x] **ERR-04**: System logs all errors with context for debugging

### ACE Compliance (ACE)

Requirements ensuring compatibility with Tencent ACE anti-cheat.

- [ ] **ACE-01**: System uses only hardware-based input simulation (no software injection)
- [x] **ACE-02**: System implements human-like timing with randomized delays
- [ ] **ACE-03**: System avoids any direct game memory access
- [ ] **ACE-04**: System avoids DLL injection or process manipulation

### Performance Optimization (SPEED)

Requirements for improving execution speed.

- [x] **SPEED-01**: System processes images in parallel where possible
- [x] **SPEED-02**: System constrains template matching to specified ROIs
- [ ] **SPEED-03**: System eliminates all hardcoded time.sleep() calls
- [x] **SPEED-04**: System implements frame caching to reduce capture overhead

### Multi-Account Support (MULTI)

Requirements for seamless multi-account operation.

- [ ] **MULTI-01**: System automatically identifies accounts without manual character count entry
- [ ] **MULTI-02**: System persists progress per account across sessions
- [ ] **MULTI-03**: System supports switching between accounts without restart
- [ ] **MULTI-04**: System maintains separate state databases per account

## v2 Requirements

Deferred features for future consideration.

### Multi-Game Support

- **MG-01**: Abstract core for use with other games
- **MG-02**: Game-specific plugin architecture
- **MG-03**: Resolution independence (adaptive ROI scaling)

### Advanced Features

- **ADV-01**: Real-time trigger detection (redesigned)
- **ADV-02**: Machine learning for element detection
- **ADV-03**: Remote monitoring via web interface

## Out of Scope

| Feature | Reason |
|---------|--------|
| OCR text recognition | Explicitly removed per user requirement; replaced by image matching |
| Game memory reading | Avoided for ACE compliance |
| Non-2560x1440 resolutions | Single resolution support for v1 |
| Multi-monitor support | Complexity exceeds v1 scope |
| Cloud/remote execution | Hardware dependency makes this impractical |
| Mobile/touch input | Desktop automation only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CHAR-01 | Phase 1 | Pending |
| CHAR-02 | Phase 1 | Pending |
| CHAR-03 | Phase 1 | Pending |
| CHAR-04 | Phase 1 | Pending |
| CHAR-05 | Phase 1 | Pending |
| CFG-01 | Phase 2 | Pending |
| CFG-02 | Phase 2 | Pending |
| CFG-03 | Phase 2 | Pending |
| CFG-04 | Phase 2 | Pending |
| WAIT-01 | Phase 3 | Complete |
| WAIT-02 | Phase 3 | Complete |
| WAIT-03 | Phase 3 | Complete |
| WAIT-04 | Phase 3 | Complete |
| ERR-01 | Phase 4 | Complete |
| ERR-02 | Phase 4 | Complete |
| ERR-03 | Phase 4 | Complete |
| ERR-04 | Phase 4 | Complete |
| ACE-01 | Phase 5 | Pending |
| ACE-02 | Phase 5 | Complete |
| ACE-03 | Phase 5 | Pending |
| ACE-04 | Phase 5 | Pending |
| SPEED-01 | Phase 6 | Complete |
| SPEED-02 | Phase 6 | Complete |
| SPEED-03 | Phase 6 | Pending |
| SPEED-04 | Phase 6 | Complete |
| MULTI-01 | Phase 7 | Pending |
| MULTI-02 | Phase 7 | Pending |
| MULTI-03 | Phase 7 | Pending |
| MULTI-04 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-07*
*Last updated: 2026-03-07 after initial definition*
