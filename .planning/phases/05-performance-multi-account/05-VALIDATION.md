---
phase: 5
slug: performance-multi-account
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `pytest tests/performance/ -x --tb=short` |
| **Full suite command** | `pytest tests/performance/ -v --tb=short` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/performance/ -x --tb=short -k <task>`
- **After every plan wave:** Run `pytest tests/performance/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 1 | SPEED-04 | unit | `pytest tests/performance/test_frame_cache.py -v` | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 1 | SPEED-04 | unit | `pytest tests/performance/test_frame_cache.py::test_ttl_expiration -v` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 1 | SPEED-01 | unit | `pytest tests/performance/test_parallel_matching.py -v` | ❌ W0 | ⬜ pending |
| 5-02-02 | 02 | 1 | SPEED-02 | unit | `pytest tests/performance/test_roi_constraints.py -v` | ❌ W0 | ⬜ pending |
| 5-03-01 | 03 | 2 | MULTI-01 | unit | `pytest tests/multi_account/test_account_manager.py -v` | ❌ W0 | ⬜ pending |
| 5-03-02 | 03 | 2 | MULTI-02 | unit | `pytest tests/multi_account/test_progress_persistence.py -v` | ❌ W0 | ⬜ pending |
| 5-03-03 | 03 | 2 | MULTI-04 | unit | `pytest tests/multi_account/test_database_isolation.py -v` | ❌ W0 | ⬜ pending |
| 5-04-01 | 04 | 2 | MULTI-03 | unit | `pytest tests/multi_account/test_account_switching.py -v` | ❌ W0 | ⬜ pending |
| 5-04-02 | 04 | 2 | SPEED-03 | verify | `grep -r "time.sleep" core/ modules/ --include="*.py" \| grep -v "# legacy" \| wc -l` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/performance/conftest.py` — shared fixtures for perf tests
- [ ] `tests/performance/test_frame_cache.py` — frame cache tests
- [ ] `tests/performance/test_parallel_matching.py` — parallel matching tests
- [ ] `tests/performance/test_roi_constraints.py` — ROI constraint tests
- [ ] `tests/multi_account/conftest.py` — shared fixtures for multi-account tests
- [ ] `tests/multi_account/test_account_manager.py` — account manager tests
- [ ] `tests/multi_account/test_progress_persistence.py` — progress persistence tests
- [ ] `tests/multi_account/test_database_isolation.py` — database isolation tests
- [ ] `tests/multi_account/test_account_switching.py` — account switching tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end timing | SPEED targets | Requires actual game client | Run full guild donation workflow, verify <30s per character |
| Frame cache hit rate | SPEED-04 | Requires screen capture hardware | Monitor cache metrics during runtime |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
