---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 6
current_plan: 02
status: executing
last_updated: "2026-03-07T18:25:35.552Z"
progress:
  total_phases: 8
  completed_phases: 6
  total_plans: 23
  completed_plans: 20
---

# Project State: LostarkGuildDonationBot

**Initialized:** 2026-03-07
**Current Phase:** 6
**Current Plan:** 02
**Status:** executing

---

## Progress

```
Phase 1: Character Detection Core      ✓ Complete (3/3 plans)
  Plan 01: Contracts and Persistence   ✓ Complete
  Plan 02: Vision Engine Integration   ✓ Complete
  Plan 03: Account Indexing and Cache  ✓ Complete
Phase 2: Configuration System          ✓ Complete (3/3 plans)
  Plan 01: YAML Configuration Foundation ✓ Complete
  Plan 02: Workflow Executor             ✓ Complete
  Plan 03: Workflow Bootstrap            ✓ Complete
Phase 3: Intelligent Wait System       ✓ Complete (3/3 plans)
  Plan 01: Schema Contracts            ✓ Complete
  Plan 02: Wait Image Runtime          ✓ Complete
  Plan 03: Guild Workflow Migration    ✓ Complete
Phase 4: Error Recovery & ACE          ✓ Complete (3/3 plans)
  Plan 01: Recovery Contracts Schema   ✓ Complete
  Plan 02: Runtime Recovery & Logging  ✓ Complete
  Plan 03: ACE Compliance Guard        ✓ Complete
Phase 5: Performance & Multi-Account   ✓ Complete (4/4 plans)
  Plan 01: Frame Cache with TTL         ✓ Complete
  Plan 02: Parallel ROI Matching        ✓ Complete
  Plan 03: Account Manager & Progress   ✓ Complete
  Plan 04: Account Switching            ✓ Complete
Phase 6: Interactive Test Flow         ○ In Progress (2/3 plans)
  Plan 01: Test Overlay UI              ✓ Complete
  Plan 02: Test Flow Engine             ✓ Complete
  Plan 03: Scenario Definitions         ○ Not started
```

**Overall:** 5/6 phases complete (83%)
**Phase 6:** 2/3 plans complete (67%)

---

## Project Reference

See: [.planning/PROJECT.md](PROJECT.md) (updated 2026-03-07)

**Core value:** Zero-config multi-account automation with XIGNCODE3-friendly pure Python interactions
**Current focus:** Phase 6 - Interactive Test Flow System

---

## Active Context

**Last Action:** Completed Plan 06-02: Test Flow Engine and JSON Logging
**Next Action:** Plan 06-03: Scenario Definitions and Integration

**Blockers:** None

**Notes:**
- Plan 06-02 completed with TestLogger (JSON persistence) and TestFlow (state machine)
- 15 unit tests passing for interactive test system
- TestLogger: atomic file writes, thread-safe, ISO timestamp format
- TestFlow: F1-driven progression, Y/N/SKIP feedback, state machine
- Integration points: TestOverlay UI, TestLogger persistence

---

## Decisions Made

| Date | Decision | Context |
|------|----------|---------|
| 2026-03-07 | Pydantic v2 discriminated unions for action types | Type-safe workflow schema |
| 2026-03-07 | YAML-only loading with yaml.safe_load | Security and simplicity |
| 2026-03-07 | Separate schema validation from semantic compilation | Clean architecture |
| 2026-03-07 | Explicit step_id required for every step | Workflow determinism |
| 2026-03-07 | Conditional branching via on_true/on_false fields | Branching semantics |
| 2026-03-07 | ROI constants locked to 2560x1440 | Phase context specification |
| 2026-03-07 | TM_CCOEFF_NORMED matching enforced | Locked phase decision |
| 2026-03-07 | Slot threshold >=0.8 with 3 retries | Locked phase decision |
| 2026-03-07 | SQLite upsert pattern for characters | Repository design |
| 2026-03-07 | FF00FF masking via HSV color space | Template processing |
| 2026-03-07 | Menu detection uses bounded retries | Fail-fast behavior |
| 2026-03-07 | Borderline confidence triggers retry | Accuracy improvement |
| 2026-03-07 | Scroll bottom requires 100% pixel match | Locked context policy |
| 2026-03-07 | Max page cap (20) prevents infinite loops | Safety safeguard |
| 2026-03-07 | Account identity from first character SHA-256 | Zero-config recognition |
| 2026-03-07 | Cache directory structure data/accounts/{hash}/characters | Filesystem cache |
| 2026-03-07 | Launcher workflow: Discover (F11) before Automation (F10) | User experience |
| 2026-03-07 | Cursor-based step progression with explicit next links | Workflow determinism |
| 2026-03-07 | Per-step retry policy with configurable retry count | Error handling flexibility |
| 2026-03-07 | Loop guard at 1000 steps prevents runaway execution | Safety safeguard |
| 2026-03-07 | Bootstrap module provides single entrypoint create_workflow_executor() | Clean integration API |
| 2026-03-07 | Launcher uses config-driven workflow with fallback simulation | Graceful degradation |
| 2026-03-07 | WaitImageAction separate from WaitAction for clear semantics | Schema clarity |
| 2026-03-07 | Explicit state field with Literal[appear, disappear] | Type safety |
| 2026-03-07 | Three-tier override hierarchy (action/step/workflow) | Configuration flexibility |
| 2026-03-07 | Legacy wait(duration_ms) preserved for phased migration | Backward compatibility |
| 2026-03-07 | 2-hit stability for image state changes | Prevents flickering false positives |
| 2026-03-07 | Executor single retry authority | No parallel retry systems |
| 2026-03-07 | Monotonic clock for timeout deadlines | Prevents clock skew issues |
| 2026-03-07 | RecoveryConfig with anchor/on_timeout/max_escalations | ERR-02 recovery schema |
| 2026-03-07 | Compiler validates recovery graph safety | Fail-fast recovery validation |
| 2026-03-07 | Guild workflow uses open_guild_menu as recovery anchor | ERR-02 implementation |
| 2026-03-07 | ErrorKind enum with 5 classification types | ERR-01/02/03 error routing |
| 2026-03-07 | Three-tier escalation L1 retry -> L2 rollback -> L3 skip | ERR-01/02/03 recovery policy |
| 2026-03-07 | Circuit breaker pattern for same-kind failures | Infinite loop prevention |
| 2026-03-07 | JSONL logging with daily file partitioning | ERR-04 evidence pipeline |
| 2026-03-07 | RoleSkipError for graceful disconnect handling | ERR-03 no forced restart |
| 2026-03-07 | Session-seeded truncated normal jitter for timing compliance | ACE-02 timing policy |
| 2026-03-07 | Hardware-only input gateway with policy enforcement | ACE-01 input compliance |
| 2026-03-07 | Fail-fast compliance validation at startup | ACE-03/04 guard integration |
| 2026-03-07 | Default TTL of 150ms balances freshness vs performance | Frame cache design |
| 2026-03-07 | Dependency injection pattern for VisionEngine integration | Clean architecture |
| 2026-03-07 | OpenCV releases GIL during matchTemplate enabling thread speedup | SPEED-01 implementation |
| 2026-03-07 | max_workers=4 optimal for 9-slot scanning | ThreadPoolExecutor tuning |
| 2026-03-07 | ROI enforcement is breaking change requiring explicit ROI | SPEED-02 compliance |
| 2026-03-08 | Account switching requires workflow stop for safety | MULTI-03 implementation |
| 2026-03-08 | Deadlock prevention via _can_switch_unlocked helper | Thread safety pattern |
| 2026-03-08 | SPEED-03 allows timing_jitter, retry_interval, poll_interval sleeps | Legitimate use documentation |
| 2026-03-08 | Atomic file writes for test results | Thread-safe JSON persistence |
| 2026-03-08 | TestFlow state machine with explicit states | Clear test lifecycle management |
| 2026-03-08 | F1/Y/N/END hotkey mapping for test flow | Intuitive user interaction |

---
- [Phase 06]: Chinese text for all test scenario instructions and expected results
- [Phase 07]: Default port COM2 for Ferrum device consistency with existing docs
- [Phase 07]: Baudrate 115200 standard for Ferrum hardware
- [Phase 07]: 1 second timeout for responsive error detection
- [Phase 07]: Retry-once policy for transient serial failures
- [Phase 07]: Chinese prefix tags per project convention: [Ferrum] for info, [错误] for errors

## Phase History

| Phase | Started | Completed | Duration | Notes |
|-------|---------|-----------|----------|-------|
| 1 | 2026-03-07 | 2026-03-07 | 60 min | All 3 plans complete |
| 2 | 2026-03-07 | 2026-03-07 | 28 min | All 3 plans complete |
| 3 | 2026-03-07 | 2026-03-07 | 53 min | All 3 plans complete |
| 4 | 2026-03-07 | 2026-03-07 | 60 min | All 3 plans complete |
| 5 | 2026-03-07 | 2026-03-08 | 90 min | All 4 plans complete |

---

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01 | 01 | 15 min | 3 | 3 |
| 01 | 02 | 25 min | 3 | 3 |
| 01 | 03 | 20 min | 3 | 3 |
| 02 | 01 | 5 min | 2 | 4 |
| 02 | 02 | 20 min | 2 | 3 |
| 02 | 03 | 3 min | 2 | 4 |
| 03 | 01 | 8 min | 2 | 2 |
| 03 | 02 | 20 min | 2 | 5 |
| 03 | 03 | 25 min | 3 | 4 |
| 04 | 01 | 25 min | 3 | 4 |
| 04 | 02 | 20 min | 3 | 3 |
| 04 | 03 | 15 min | 3 | 4 |
| 05 | 01 | 15 min | 3 | 4 |
| 05 | 02 | 25 min | 3 | 4 |
| 05 | 03 | 20 min | 4 | 6 |
| 05 | 04 | 45 min | 4 | 7 |
| 06 | 01 | 10 min | 3 | 1 |
| 06 | 02 | 15 min | 3 | 2 |

---
| Phase 06 P03 | 25 | 4 tasks | 4 files |
| Phase 07 P01 | 15 min | 6 tasks | 1 files |

## Accumulated Context

### Roadmap Evolution

- Phase 5.1 inserted after Phase 5: 现在基于这个项目编写一个全功能测试脚本，调用superpowers:brainstorm (URGENT)
- Phase 6 added: 6 增加一个测试流程序，由你来指挥，我来协助操作并且观察操作进行测试。要求，你以半透明横向功能区显示，默认覆盖在左上角，设计关闭按钮和拖动区域，让我按F1下一步，你输出指令以及预期结果，我来进行观察，随时可以终端测试并且告诉你未按照预期进行的情况
- Phase 7 added: 基于skills：ferrum和现有的代码，开发一个交互逻辑子程序，满足项目内现有代码所有的交互逻辑调用

---

*State updated: 2026-03-08 after completing 06-02*
