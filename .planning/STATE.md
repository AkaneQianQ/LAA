---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 7
current_plan: Not started
status: completed
last_updated: "2026-03-08T05:35:00.000Z"
progress:
  total_phases: 9
  completed_phases: 7
  total_plans: 23
  completed_plans: 23
---

# Project State: LostarkGuildDonationBot

**Initialized:** 2026-03-07
**Current Phase:** 7
**Current Plan:** Not started
**Status:** Milestone complete

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
Phase 6: Interactive Test Flow         ✓ Complete (3/3 plans)
  Plan 01: Test Overlay UI              ✓ Complete
  Plan 02: Test Flow Engine             ✓ Complete
  Plan 03: Scenario Definitions         ✓ Complete
Phase 7: Skills Ferrum                 ○ In Progress (1/4 plans)
  Plan 01: FerrumController Core        ✓ Complete
  Plan 02: Mouse Actions                ✓ Complete
  Plan 03: Keyboard Actions             ✓ Complete
  Plan 04: Integration & Testing        ✓ Complete
```

**Overall:** 6/8 phases complete (75%)
**Phase 7:** 4/4 plans complete (100%)

---

## Project Reference

See: [.planning/PROJECT.md](PROJECT.md) (updated 2026-03-07)

**Core value:** Zero-config multi-account automation with XIGNCODE3-friendly pure Python interactions
**Current focus:** Phase 7 - Ferrum Hardware Integration (Complete)

---

## Active Context

**Last Action:** Completed Plan 07-04: Integration with HardwareInputGateway and Testing
**Next Action:** Phase 7 complete - all Ferrum integration plans finished

**Blockers:** None

**Notes:**
- Plan 07-04 completed with FerrumController integration and testing
- FerrumController implements all ActionDispatcher required methods (click, press, scroll, wait)
- HardwareInputGateway wraps FerrumController with ACE compliance and jitter
- 17 pytest integration tests created with mock/hardware support
- Manual test launcher for interactive hardware verification
- Integration documentation with complete code examples

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
| 2026-03-08 | FerrumController implements full ActionDispatcher interface | Hardware integration compatibility |
| 2026-03-08 | HardwareInputGateway wraps FerrumController for ACE compliance | Policy enforcement and jitter |
| 2026-03-08 | Relative coordinate movement for km.move API | Ferrum device protocol compliance |
| 2026-03-08 | Key combination support with modifier-first ordering | Correct combo key semantics |

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
| Phase 07 P02 | 15 min | 6 tasks | 2 files |
| Phase 07 P04 | 25 min | 6 tasks | 4 files |
| Phase quick P2 | 20 | 4 tasks | 5 files |

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | 添加Ferrum硬件连接预检测试，确保所有测试前硬件连接正常 | 2026-03-07 | fc0fd75 | [1-ferrum](./quick/1-ferrum/) |
| 2 | 修改账号TAG ROI和截图逻辑：新ROI(666,793,772,902)，防UI变色鼠标移动，延迟首角色截图 | 2026-03-08 | 4d067c8 | [2-tag-roi](./quick/2-tag-roi-roi-666-793-772-902-ui/) |
| 3 | 添加公会捐献完成后的缓存记录和ESC退出检测流程 | 2026-03-08 | 624aa0b | [3-esc](./quick/3-esc/) |
| 4 | account_indexing:step0 - ESC菜单+账号tag检测与视觉哈希对比 | 2026-03-08 | 1dca9f9 | [4-account-indexing-step0-esc-tag](./quick/4-account-indexing-step0-esc-tag/) |

## Accumulated Context

### Roadmap Evolution

- Phase 5.1 inserted after Phase 5: 现在基于这个项目编写一个全功能测试脚本，调用superpowers:brainstorm (URGENT)
- Phase 6 added: 6 增加一个测试流程序，由你来指挥，我来协助操作并且观察操作进行测试。要求，你以半透明横向功能区显示，默认覆盖在左上角，设计关闭按钮和拖动区域，让我按F1下一步，你输出指令以及预期结果，我来进行观察，随时可以终端测试并且告诉你未按照预期进行的情况
- Phase 6.1 inserted after Phase 6: 基于Phase 6的测试框架，添加Ferrum硬件连接预检测试作为所有测试的前置检查 (URGENT)
- Phase 7 added: 基于skills：ferrum和现有的代码，开发一个交互逻辑子程序，满足项目内现有代码所有的交互逻辑调用

---

*State updated: 2026-03-08 after completing quick task 4: account_indexing:step0 - ESC菜单+账号tag检测与视觉哈希对比*
