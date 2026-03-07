# Phase 03: Intelligent Wait System - Research

**Researched:** 2026-03-07
**Domain:** Python game UI automation wait orchestration (image-state driven)
**Confidence:** HIGH

## User Constraints (from CONTEXT.md)

### Locked Decisions
### 等待条件模型
- 智能等待优先采用统一的 `image` 条件语义。
- 等待目标状态明确支持两类：`appear` 与 `disappear`。
- 判定稳定性采用“连续 2 次命中/满足”才通过，避免单帧抖动误判。
- 轮询策略采用“默认固定间隔 + 步骤可配置覆盖”。
- 等待超时按步骤失败处理，交由现有 `step.retry` 机制执行重试。

### Timeout 与重试策略
- 默认超时采用“按动作/场景分级默认”，而不是单一全局固定值。
- 重试归属沿用 `step.retry`，不引入并行的新重试体系。
- 重试间隔采用“固定短间隔 + 可覆盖”策略。
- 达到最大重试后，流程按失败终止（保持 stop-on-failure 基线）。

### YAML 配置形状
- 新增专用智能等待动作（如 `wait_image`），与现有 `wait(duration_ms)` 分离建模。
- 等待方向使用显式字段表达（如 `state: appear|disappear`）。
- 超时/轮询采用“全局默认 + 步骤可覆盖”的优先级模型。
- 对既有 `wait(duration_ms)` 采用渐进迁移：新旧并存，逐步替换。

### Claude's Discretion
- 分级默认超时的具体档位与命名（如 short/medium/long 或按场景命名）。
- 智能等待动作的精确字段命名与 schema 细节（在不违背已锁定语义前提下）。
- 轮询与重试默认值的具体数值。

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WAIT-01 | System waits for images to appear before proceeding | `wait_image` + `state: appear` polling loop + timeout |
| WAIT-02 | System waits for images to disappear before proceeding | `wait_image` + `state: disappear` inverse condition loop |
| WAIT-03 | System supports configurable timeouts for all wait operations | global defaults + per-step timeout override |
| WAIT-04 | System implements automatic retry logic on timeout | raise `ExecutionError` on timeout and reuse existing `step.retry` |
| SPEED-03 | System eliminates all hardcoded `time.sleep()` calls | migrate workflow waits to image-driven conditions; isolate remaining launcher sleeps for follow-up |

## Summary

For this phase, the established architecture is a deterministic polling wait primitive integrated into the existing workflow runtime, not a separate scheduler framework. Keep the current compiler/executor model, add one dedicated action (`wait_image`), and make timeout failure flow through existing retry semantics.

Use OpenCV template matching exactly as the condition engine does today, but convert waits from fixed delays to state-based loops with monotonic deadline control. This aligns with Python timing guidance (`time.monotonic`) and avoids wall-clock drift issues.

**Primary recommendation:** Implement `wait_image` as a first-class schema action, execute via runtime polling (`poll_interval_ms`) until stable appear/disappear or timeout, then delegate retries to existing `step.retry` behavior.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `time` stdlib | 3.11+ | Timeout deadline and polling clock | `monotonic()` is explicitly non-adjustable by system clock changes |
| OpenCV (`cv2`) | 4.x | Template-match condition evaluation | Already used in project; canonical API for matchTemplate/minMaxLoc |
| NumPy | 1.x/2.x | Frame and template array operations | Required by OpenCV pipeline already in codebase |
| Pydantic | v2 | Strict workflow action schema (`wait_image`) | Matches current discriminated-union schema architecture |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Tenacity | stable | Complex retry policies (if retry logic must expand beyond `step.retry`) | Use only if project later needs backoff/jitter/circuit rules outside executor |
| python-mss | latest | Portable ROI screen capture fallback | Use if DXCam capture path is unstable on target machines |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom retry orchestration in wait loop | Tenacity decorators/context manager | Faster to ship now with `step.retry`; Tenacity only when retry policy complexity grows |
| PIL-only capture fallback | MSS | MSS is typically cleaner for frequent grabs; extra dependency cost |

**Installation:**
```bash
pip install tenacity mss
```

## Architecture Patterns

### Recommended Project Structure
```
core/
├── workflow_schema.py      # add WaitImageAction + defaults model
├── workflow_runtime.py     # polling wait dispatcher + condition helpers
├── workflow_executor.py    # unchanged retry owner (step.retry)
└── vision_engine.py        # unchanged template matching core
```

### Pattern 1: Deadline-Bounded Polling Wait
**What:** Loop until condition target state is reached or monotonic deadline expires.
**When to use:** All UI-state waits (appear/disappear) replacing fixed waits.
**Example:**
```python
import time

def wait_until(check_fn, timeout_s: float, poll_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if check_fn():
            return True
        time.sleep(poll_s)
    return False
```

### Pattern 2: Stability Gate (2 Consecutive Hits)
**What:** Require condition to pass twice consecutively before success.
**When to use:** Mitigate one-frame false positives/negatives.
**Example:**
```python
def stable_wait(check_fn, needed_hits=2):
    hits = 0
    while True:
        hits = hits + 1 if check_fn() else 0
        if hits >= needed_hits:
            return True
```

### Pattern 3: Timeout-as-Failure, Retry-in-Executor
**What:** Runtime wait raises execution failure on timeout; executor applies `step.retry`.
**When to use:** Always, to preserve current stop-on-failure semantics.

### Anti-Patterns to Avoid
- **Hidden retries in runtime + retries in executor:** causes retry multiplication and unpredictable delays.
- **Using `time.time()` for timeout control:** wall-clock changes can break timeout logic.
- **Mixing old `wait` semantics silently:** keep `wait` and `wait_image` explicit during migration.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Generic policy engine for retries | New backoff framework inside runtime | Existing `step.retry` (and Tenacity only if needed later) | Current executor already owns retry lifecycle |
| Pixel-by-pixel custom matcher | Homegrown matcher | OpenCV `matchTemplate` + `minMaxLoc` | Mature, optimized, already integrated |
| Wall-clock timeout math | Ad hoc `time.time()` arithmetic | `time.monotonic()` deadlines | Monotonic clock avoids system time adjustments |
| New scheduler subsystem | Threaded/event scheduler for waits | Single-thread polling in dispatcher | Simpler, deterministic, matches current executor model |

**Key insight:** The phase should change wait semantics, not execution topology.

## Common Pitfalls

### Pitfall 1: Polling Too Fast
**What goes wrong:** CPU spikes, unstable frame cadence.
**Why it happens:** Very small poll interval (e.g., 1-5ms) with frequent capture/matching.
**How to avoid:** Use fixed default interval (e.g., 80-150ms) with per-step override.
**Warning signs:** High CPU during waits, increased false negatives.

### Pitfall 2: Polling Too Slow
**What goes wrong:** Automation feels laggy; timeout misses near-threshold states.
**Why it happens:** Large poll interval (e.g., >500ms) on short transitions.
**How to avoid:** Use tiered timeout defaults and moderate polling intervals.
**Warning signs:** Repeated timeout failures on normally stable UI.

### Pitfall 3: Double Retry Paths
**What goes wrong:** Total attempts exceed configured `step.retry`; long tail latencies.
**Why it happens:** Runtime loop retries internally after timeout and executor retries again.
**How to avoid:** On timeout, fail once and let executor own retries.
**Warning signs:** Logs show more attempts than configured.

### Pitfall 4: Threshold/State Inversion Bugs
**What goes wrong:** `disappear` waits never complete or complete immediately.
**Why it happens:** Incorrect inversion of match predicate or threshold semantics.
**How to avoid:** Unit tests for `appear` and `disappear` with deterministic mock confidence sequences.
**Warning signs:** Waits succeed on first frame despite visible target.

### Pitfall 5: Migrating YAML Without Compatibility Guard
**What goes wrong:** Existing workflows break before full migration.
**Why it happens:** Replacing `wait` behavior in place instead of introducing `wait_image`.
**How to avoid:** Keep old `wait(duration_ms)` action valid; migrate gradually.
**Warning signs:** Validation failures in legacy YAML.

## Code Examples

Verified patterns from official sources:

### Monotonic Timeout Control
```python
import time

start = time.monotonic()
# ... polling work ...
if time.monotonic() - start > timeout_s:
    raise TimeoutError
```
Source: https://docs.python.org/3/library/time.html

### Template Matching Decision
```python
result = cv.matchTemplate(image, templ, cv.TM_CCOEFF_NORMED)
_, max_val, _, max_loc = cv.minMaxLoc(result)
found = max_val >= threshold
```
Source: https://docs.opencv.org/4.x/de/da9/tutorial_template_matching.html

### Tenacity Retry Block (Optional Future)
```python
from tenacity import Retrying, stop_after_attempt, wait_fixed

for attempt in Retrying(stop=stop_after_attempt(3), wait=wait_fixed(0.2)):
    with attempt:
        do_action()
```
Source: https://tenacity.readthedocs.io/en/stable/index.html

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed `sleep` delays in UI automation | State-driven waits with explicit timeout and stability checks | Established best practice across modern automation frameworks (ongoing) | Faster on responsive UI, safer on slow UI, fewer brittle timing failures |
| Ad hoc timeout clocks (`time.time`) | `time.monotonic` deadline loops | Python 3 era best practice (documented in stdlib) | Clock-change-safe timeout behavior |

**Deprecated/outdated:**
- Pure fixed-delay sequencing for dynamic game UI transitions.

## Open Questions

1. **How many hardcoded waits remain outside workflow actions?**
- What we know: current scan found `time.sleep()` in `gui_launcher.py`.
- What's unclear: whether other branches/scripts still contain the reported 39 calls.
- Recommendation: run full-repo `rg "time\.sleep\("` as a planning gate and attach exact inventory.

2. **Default timeout tiers exact values**
- What we know: tiered defaults are locked, exact numbers are discretionary.
- What's unclear: best values per action class in your real latency envelope.
- Recommendation: start with conservative defaults and tune from telemetry in Phase 03 tests.

## Sources

### Primary (HIGH confidence)
- Python `time` docs (monotonic/sleep semantics): https://docs.python.org/3/library/time.html
- Python `sched` docs (default scheduler uses monotonic + sleep): https://docs.python.org/3/library/sched.html
- OpenCV template matching tutorial (`matchTemplate`, `minMaxLoc`, method behavior): https://docs.opencv.org/4.x/de/da9/tutorial_template_matching.html
- OpenCV imgproc object API (`TemplateMatchModes`, mask behavior): https://docs.opencv.org/4.x/df/dfb/group__imgproc__object.html

### Secondary (MEDIUM confidence)
- Tenacity official docs (retry policies and stop/wait composition): https://tenacity.readthedocs.io/en/stable/index.html
- python-mss API docs (`grab` capture interface): https://python-mss.readthedocs.io/api.html

### Tertiary (LOW confidence)
- DXcam repository README claims on high-FPS capture: https://github.com/ra1nty/DXcam

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - anchored in existing project code plus official Python/OpenCV docs.
- Architecture: HIGH - directly constrained by locked decisions and current executor/runtime design.
- Pitfalls: MEDIUM-HIGH - grounded in implementation patterns and verified API behavior.

**Research date:** 2026-03-07
**Valid until:** 2026-04-06
