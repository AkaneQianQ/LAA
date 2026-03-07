# Phase 5: Performance & Multi-Account - Research

**Researched:** 2026-03-07
**Domain:** Python Performance Optimization, Computer Vision, Multi-Account State Management
**Confidence:** HIGH

## Summary

Phase 5 focuses on two distinct optimization areas: **performance** (parallel processing, ROI constraints, frame caching) and **multi-account support** (automatic identification, per-account progress persistence, seamless switching). The codebase already has strong foundations with DXCam for capture, OpenCV for template matching, and SQLite for persistence.

**Key insight:** SPEED-03 (eliminate hardcoded sleeps) was already completed in Phase 3 with the intelligent wait system. The remaining SPEED requirements focus on computational efficiency, while MULTI requirements leverage the existing database schema with extensions for progress tracking.

**Primary recommendation:** Implement a FrameCache with TTL-based invalidation for screen captures, use ThreadPoolExecutor for parallel template matching across multiple ROIs, and extend the existing SQLite schema with per-account progress tables.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SPEED-01 | System processes images in parallel where possible | ThreadPoolExecutor for concurrent ROI matching; multiprocessing unnecessary due to GIL and OpenCV's thread safety |
| SPEED-02 | System constrains template matching to specified ROIs | Already partially implemented in `vision_engine.py`; need to enforce ROI usage in all detection paths |
| SPEED-03 | System eliminates all hardcoded time.sleep() calls | **ALREADY COMPLETE** - Phase 3 intelligent wait system replaced all sleeps with image-based waits |
| SPEED-04 | System implements frame caching to reduce capture overhead | DXCam frame buffer + custom TTL cache; target 50%+ reduction in capture calls |
| MULTI-01 | System automatically identifies accounts without manual character count entry | Use existing `character_detector.discover_account()` which computes SHA-256 hash from first character screenshot |
| MULTI-02 | System persists progress per account across sessions | Extend database schema with `account_progress` table; track daily donation completion per character |
| MULTI-03 | System supports switching between accounts without restart | AccountManager class with `switch_account()` method; hot-reload workflow executor with new account context |
| MULTI-04 | System maintains separate state databases per account | SQLite supports per-account databases via dynamic db_path; or use table namespacing with account_id prefix |

---

## Standard Stack

### Core Performance Libraries

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| concurrent.futures | stdlib | ThreadPoolExecutor for parallel ROI matching | Standard Python parallelism without external deps |
| functools.lru_cache | stdlib | Template image caching | Already used in VisionEngine, proven pattern |
| threading | stdlib | Lock for frame cache thread safety | DXCam callbacks may be async |
| time.monotonic | stdlib | TTL expiration for frame cache | Monotonic clock prevents skew issues |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dxcam | latest | Screen capture with built-in buffer | Already in use; leverage frame buffer for caching |
| numpy | latest | Array operations for image processing | Already in use; memory-efficient frame storage |
| sqlite3 | stdlib | Per-account database isolation | Already in use; ACID guarantees for progress |

### Performance Targets

| Metric | Target | Current (estimated) | Strategy |
|--------|--------|---------------------|----------|
| Template matching per ROI | <100ms | ~50-150ms | ROI constraint + parallel processing |
| Screen capture reduction | 50%+ | 0% (no caching) | Frame cache with 100-200ms TTL |
| End-to-end per character | <30s | ~45-60s | Combined optimizations |

---

## Architecture Patterns

### Pattern 1: Frame Cache with TTL

**What:** Cache screen captures with time-based invalidation to reduce DXCam overhead

**When to use:** Multiple template matches within short time window (<200ms)

**Example:**
```python
# Source: Pattern based on DXCam documentation and common CV practices
import time
import threading
from typing import Optional, Tuple
import numpy as np

class FrameCache:
    """Thread-safe frame cache with TTL expiration."""

    def __init__(self, ttl_ms: float = 100.0):
        self.ttl_ms = ttl_ms
        self._cache: Optional[np.ndarray] = None
        self._timestamp: float = 0.0
        self._lock = threading.Lock()

    def get(self) -> Optional[np.ndarray]:
        """Get cached frame if not expired."""
        with self._lock:
            if self._cache is None:
                return None
            elapsed_ms = (time.monotonic() - self._timestamp) * 1000
            if elapsed_ms > self.ttl_ms:
                self._cache = None
                return None
            return self._cache.copy()  # Return copy to prevent mutation

    def set(self, frame: np.ndarray) -> None:
        """Cache a new frame."""
        with self._lock:
            self._cache = frame.copy()
            self._timestamp = time.monotonic()

    def invalidate(self) -> None:
        """Force cache invalidation."""
        with self._lock:
            self._cache = None
```

### Pattern 2: Parallel ROI Matching

**What:** Use ThreadPoolExecutor to match multiple templates/ROIs concurrently

**When to use:** Scanning all 9 character slots simultaneously

**Example:**
```python
# Source: Python concurrent.futures documentation + OpenCV thread safety
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict
import cv2
import numpy as np

def match_single_roi(
    screenshot: np.ndarray,
    template: np.ndarray,
    roi: Tuple[int, int, int, int],
    slot_index: int
) -> Tuple[int, bool, float]:
    """Match template in single ROI. Returns (slot_index, found, confidence)."""
    x1, y1, x2, y2 = roi
    roi_region = screenshot[y1:y2, x1:x2]

    if roi_region.size == 0:
        return slot_index, False, 0.0

    roi_gray = cv2.cvtColor(roi_region, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(roi_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)

    return slot_index, max_val >= 0.8, max_val

def scan_slots_parallel(
    screenshot: np.ndarray,
    template: np.ndarray,
    rois: List[Tuple[int, int, int, int]],
    max_workers: int = 4
) -> Dict[int, Tuple[bool, float]]:
    """Scan all slots in parallel using thread pool."""
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(match_single_roi, screenshot, template, roi, i): i
            for i, roi in enumerate(rois)
        }

        for future in as_completed(futures):
            slot_index, found, confidence = future.result()
            results[slot_index] = (found, confidence)

    return results
```

### Pattern 3: Per-Account Database Isolation

**What:** Dynamic database path resolution for separate account state

**When to use:** MULTI-04 requirement for separate state databases

**Example:**
```python
# Source: Based on existing database.py patterns
import os
import sqlite3
from typing import Optional

class AccountDatabaseManager:
    """Manages per-account database connections."""

    def __init__(self, base_data_dir: str = "data"):
        self.base_data_dir = base_data_dir
        self._connections: Dict[str, sqlite3.Connection] = {}

    def get_db_path(self, account_hash: str) -> str:
        """Get database path for specific account."""
        account_dir = os.path.join(self.base_data_dir, "accounts", account_hash)
        os.makedirs(account_dir, exist_ok=True)
        return os.path.join(account_dir, "progress.db")

    def get_connection(self, account_hash: str) -> sqlite3.Connection:
        """Get or create connection for account."""
        if account_hash not in self._connections:
            db_path = self.get_db_path(account_hash)
            conn = sqlite3.connect(db_path, timeout=5.0)
            conn.row_factory = sqlite3.Row
            self._init_schema(conn)
            self._connections[account_hash] = conn
        return self._connections[account_hash]

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize progress tracking schema."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS character_progress (
                slot_index INTEGER PRIMARY KEY,
                character_name TEXT,
                last_donation_date TEXT,
                donation_count INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
```

### Pattern 4: Account Context Manager

**What:** Manage account switching without restart

**When to use:** MULTI-03 seamless account switching

**Example:**
```python
# Source: Pattern for hot-swapping execution context
from typing import Optional, Callable
from dataclasses import dataclass

@dataclass
class AccountContext:
    """Runtime context for a specific account."""
    account_hash: str
    account_id: int
    character_count: int
    db_path: str
    progress_tracker: 'ProgressTracker'

class AccountManager:
    """Manages account switching and context lifecycle."""

    def __init__(self, detector: 'CharacterDetector', db_manager: AccountDatabaseManager):
        self.detector = detector
        self.db_manager = db_manager
        self._current_context: Optional[AccountContext] = None
        self._on_switch_callbacks: List[Callable[[AccountContext], None]] = []

    def switch_account(self, screenshot: np.ndarray) -> AccountContext:
        """Switch to account detected in screenshot."""
        # Detect account from screenshot
        account_info = self.detector.discover_account(screenshot)
        account_hash = account_info['account_hash']

        # Create new context
        new_context = AccountContext(
            account_hash=account_hash,
            account_id=account_info['account_id'],
            character_count=account_info['character_count'],
            db_path=self.db_manager.get_db_path(account_hash),
            progress_tracker=ProgressTracker(self.db_manager, account_hash)
        )

        self._current_context = new_context

        # Notify subscribers
        for callback in self._on_switch_callbacks:
            callback(new_context)

        return new_context

    @property
    def current_context(self) -> Optional[AccountContext]:
        return self._current_context
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parallel processing | Custom thread pool | `concurrent.futures.ThreadPoolExecutor` | Battle-tested, context manager support, graceful shutdown |
| Frame caching | Custom buffer management | DXCam's built-in buffer + TTL wrapper | DXCam already optimizes capture; add TTL for freshness |
| Database migrations | Custom schema versioning | SQLite `PRAGMA user_version` + simple upgrade scripts | Complex migration frameworks overkill for single-table additions |
| Progress serialization | Custom binary format | SQLite JSON columns | Queryable, atomic, no parsing code needed |
| Account identification | OCR text recognition | SHA-256 hash of character screenshot | Already implemented in Phase 1; zero-config, privacy-preserving |

---

## Common Pitfalls

### Pitfall 1: GIL Contention with CPU-Bound CV

**What goes wrong:** ThreadPoolExecutor provides no speedup for CPU-bound OpenCV operations due to Python's Global Interpreter Lock (GIL).

**Why it happens:** OpenCV's `matchTemplate` releases the GIL, but heavy numpy operations may not. Parallel execution can be slower than sequential due to overhead.

**How to avoid:**
- Benchmark parallel vs sequential for actual workload
- Use `max_workers=2-4` based on CPU cores, not 9 (one per slot)
- Consider process pool only if GIL truly limits (measure first)

**Warning signs:** Slower execution with parallel enabled, high CPU usage without throughput gain

### Pitfall 2: Frame Cache Stale Data

**What goes wrong:** Cached frame used after significant game state change leads to detection on wrong UI state.

**Why it happens:** TTL too long, or explicit invalidation missed after user input.

**How to avoid:**
- Keep TTL short (100-200ms) for fast-paced detection
- Explicit `invalidate()` after every action (click, press, scroll)
- Double-check with fresh capture on critical decisions (login, donation confirm)

**Warning signs:** Detections "lagging" behind actual UI state, intermittent failures

### Pitfall 3: Database Connection Leaks

**What goes wrong:** Per-account connections accumulate without cleanup, hitting OS file descriptor limits.

**Why it happens:** AccountManager keeps connections open indefinitely for "fast switching".

**How to avoid:**
- Implement connection pooling with max size
- Use context managers for transactions, not long-lived connections
- Close idle connections after timeout (e.g., 5 minutes)

**Warning signs:** "Too many open files" errors, increasing memory usage over long sessions

### Pitfall 4: Race Conditions in Account Switching

**What goes wrong:** Workflow executor uses old account context mid-execution after switch.

**Why it happens:** Account switch happens on different thread than workflow execution.

**How to avoid:**
- Account context is immutable after creation
- Workflow executor receives context at start, not looked up dynamically
- Explicit stop/restart of workflow on account switch (safer than hot-swap)

**Warning signs:** Progress tracked to wrong account, donations applied to wrong character

---

## Code Examples

### Frame-Integrated Vision Engine

```python
# Source: Extension of existing vision_engine.py patterns
from typing import Optional, Tuple, List
import numpy as np
import cv2
import time
import threading

class CachedVisionEngine:
    """Vision engine with frame caching for reduced capture overhead."""

    def __init__(self, ttl_ms: float = 100.0):
        self._template_cache: dict = {}
        self._frame_cache: Optional[np.ndarray] = None
        self._frame_timestamp: float = 0.0
        self._ttl_ms = ttl_ms
        self._lock = threading.Lock()
        self._capture_count = 0
        self._cache_hit_count = 0

    def get_screenshot(self, force_fresh: bool = False) -> np.ndarray:
        """Get screenshot with caching."""
        if not force_fresh:
            cached = self._get_cached_frame()
            if cached is not None:
                self._cache_hit_count += 1
                return cached

        # Capture fresh frame
        import dxcam
        camera = dxcam.create()
        screenshot = camera.grab()

        if screenshot is not None:
            frame = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
            self._set_cached_frame(frame)
            self._capture_count += 1
            return frame

        raise RuntimeError("Failed to capture screenshot")

    def _get_cached_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._frame_cache is None:
                return None
            elapsed_ms = (time.monotonic() - self._frame_timestamp) * 1000
            if elapsed_ms > self._ttl_ms:
                self._frame_cache = None
                return None
            return self._frame_cache.copy()

    def _set_cached_frame(self, frame: np.ndarray) -> None:
        with self._lock:
            self._frame_cache = frame.copy()
            self._frame_timestamp = time.monotonic()

    def invalidate_cache(self) -> None:
        """Force cache invalidation after actions."""
        with self._lock:
            self._frame_cache = None

    @property
    def cache_stats(self) -> dict:
        total = self._capture_count + self._cache_hit_count
        hit_rate = self._cache_hit_count / total if total > 0 else 0.0
        return {
            'captures': self._capture_count,
            'cache_hits': self._cache_hit_count,
            'hit_rate': hit_rate,
            'reduction_pct': (1 - self._capture_count / total) * 100 if total > 0 else 0
        }
```

### Progress Tracker Implementation

```python
# Source: Extension of existing database.py patterns
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any

class ProgressTracker:
    """Per-account progress persistence."""

    def __init__(self, db_manager: 'AccountDatabaseManager', account_hash: str):
        self.db_manager = db_manager
        self.account_hash = account_hash

    def mark_character_done(self, slot_index: int, character_name: str = None) -> None:
        """Mark character donation as complete for today."""
        conn = self.db_manager.get_connection(self.account_hash)
        today = datetime.now().strftime('%Y-%m-%d')

        conn.execute("""
            INSERT INTO character_progress
                (slot_index, character_name, last_donation_date, donation_count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(slot_index) DO UPDATE SET
                character_name = COALESCE(EXCLUDED.character_name, character_progress.character_name),
                last_donation_date = EXCLUDED.last_donation_date,
                donation_count = character_progress.donation_count + 1,
                updated_at = CURRENT_TIMESTAMP
        """, (slot_index, character_name, today))
        conn.commit()

    def is_character_done_today(self, slot_index: int) -> bool:
        """Check if character has completed donation today."""
        conn = self.db_manager.get_connection(self.account_hash)
        today = datetime.now().strftime('%Y-%m-%d')

        cursor = conn.execute(
            "SELECT last_donation_date FROM character_progress WHERE slot_index = ?",
            (slot_index,)
        )
        row = cursor.fetchone()

        if row is None:
            return False

        return row['last_donation_date'] == today

    def get_account_summary(self) -> Dict[str, Any]:
        """Get progress summary for account."""
        conn = self.db_manager.get_connection(self.account_hash)
        today = datetime.now().strftime('%Y-%m-%d')

        cursor = conn.execute("""
            SELECT
                COUNT(*) as total_characters,
                SUM(CASE WHEN last_donation_date = ? THEN 1 ELSE 0 END) as completed_today
            FROM character_progress
        """, (today,))
        row = cursor.fetchone()

        return {
            'account_hash': self.account_hash,
            'total_characters': row['total_characters'] or 0,
            'completed_today': row['completed_today'] or 0,
            'remaining_today': (row['total_characters'] or 0) - (row['completed_today'] or 0)
        }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded time.sleep() | Image-based wait conditions | Phase 3 (2026-03-07) | Adaptive waits, faster execution |
| Single global database | Per-account database isolation | Phase 5 (planned) | Better isolation, easier backup |
| Full-screen template matching | ROI-constrained matching | Phase 1 (2026-03-07) | Faster matching, less false positives |
| Manual character count entry | Automatic account discovery | Phase 1 (2026-03-07) | Zero-config setup |
| Synchronous sequential detection | Parallel ROI scanning | Phase 5 (planned) | ~2-3x speedup for slot scanning |

**Deprecated/outdated:**
- `time.sleep()` calls: Replaced by `wait_image` actions with configurable timeouts
- Full-screen `matchTemplate`: Use ROI-constrained matching for SPEED-02 compliance
- Global `account_config.json`: Replaced by SQLite database with automatic discovery

---

## Open Questions

1. **Optimal TTL for frame cache**
   - What we know: 100-200ms is typical for game automation
   - What's unclear: Ferrum's UI animation speeds may require tuning
   - Recommendation: Start with 150ms, make configurable, benchmark actual hit rates

2. **Parallel matching thread count**
   - What we know: 9 slots to scan, 4-8 typical CPU cores
   - What's unclear: Whether OpenCV releases GIL effectively for this workload
   - Recommendation: Benchmark with 1, 2, 4 threads; use fastest configuration

3. **Account switch workflow integration**
   - What we know: Workflow executor has explicit step progression
   - What's unclear: Whether to interrupt running workflow or wait for completion
   - Recommendation: Require workflow completion/stop before account switch for safety

---

## Validation Architecture

> Note: `workflow.nyquist_validation` is not explicitly set to false in `.planning/config.json`, so this section is included.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | None (uses pytest defaults) |
| Quick run command | `pytest tests/performance/ -x -v` |
| Full suite command | `pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPEED-01 | Parallel ROI matching completes faster than sequential | performance | `pytest tests/performance/test_parallel_matching.py -x` | ❌ Wave 0 |
| SPEED-02 | All template matching uses ROI constraints | unit | `pytest tests/performance/test_roi_constraints.py -x` | ❌ Wave 0 |
| SPEED-03 | No hardcoded time.sleep() calls in codebase | static analysis | `grep -r "time.sleep" core/ modules/ --include="*.py"` | ❌ Wave 0 |
| SPEED-04 | Frame cache reduces captures by 50%+ | performance | `pytest tests/performance/test_frame_cache.py -x` | ❌ Wave 0 |
| MULTI-01 | Account identification returns consistent hash | integration | `pytest tests/multi_account/test_account_identification.py -x` | ❌ Wave 0 |
| MULTI-02 | Progress persists across database reconnections | integration | `pytest tests/multi_account/test_progress_persistence.py -x` | ❌ Wave 0 |
| MULTI-03 | Account switch updates active context | unit | `pytest tests/multi_account/test_account_switching.py -x` | ❌ Wave 0 |
| MULTI-04 | Per-account databases are isolated | integration | `pytest tests/multi_account/test_database_isolation.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/performance/test_<feature>.py -x -v`
- **Per wave merge:** `pytest tests/performance/ tests/multi_account/ -v --tb=short`
- **Phase gate:** Full suite green + performance benchmarks meet targets before `/gsd:verify-work`

### Performance Benchmark Targets

| Benchmark | Target | Tolerance |
|-----------|--------|-----------|
| Sequential slot scan (9 ROIs) | <500ms total | +20% |
| Parallel slot scan (9 ROIs, 4 workers) | <200ms total | +20% |
| Frame cache hit rate | >50% | -10% |
| Screenshot capture count (typical workflow) | <50% of uncached | +/-5% |
| End-to-end per character | <30s | +10% |

### Wave 0 Gaps

- [ ] `tests/performance/test_parallel_matching.py` — covers SPEED-01
- [ ] `tests/performance/test_roi_constraints.py` — covers SPEED-02
- [ ] `tests/performance/test_frame_cache.py` — covers SPEED-04
- [ ] `tests/multi_account/test_account_identification.py` — covers MULTI-01
- [ ] `tests/multi_account/test_progress_persistence.py` — covers MULTI-02
- [ ] `tests/multi_account/test_account_switching.py` — covers MULTI-03
- [ ] `tests/multi_account/test_database_isolation.py` — covers MULTI-04
- [ ] `tests/conftest.py` — shared fixtures for performance benchmarks

---

## Sources

### Primary (HIGH confidence)
- Existing codebase (`core/vision_engine.py`, `core/database.py`, `modules/character_detector.py`) - Current implementation patterns
- Python 3.13 `concurrent.futures` documentation - ThreadPoolExecutor API
- OpenCV 4.x documentation - `cv2.matchTemplate` thread safety
- DXCam GitHub repository README - Frame buffer behavior
- SQLite documentation - Per-database isolation guarantees

### Secondary (MEDIUM confidence)
- Python GIL behavior with NumPy/OpenCV - Community benchmarks
- Frame caching patterns in game automation - General CV best practices
- SQLite connection pooling patterns - SQLAlchemy implementation (for reference)

### Tertiary (LOW confidence)
- Optimal TTL values for game UI - Requires empirical testing with Ferrum
- Thread count optimization - Workload-specific, requires benchmarking

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Based on existing codebase and stdlib
- Architecture: HIGH - Patterns proven in Phases 1-4
- Pitfalls: MEDIUM - Some edge cases require empirical validation
- Performance targets: MEDIUM - Estimates based on similar CV workloads

**Research date:** 2026-03-07
**Valid until:** 2026-04-07 (30 days for stable stack)

**Dependencies:**
- Phase 1 (Character Detection): Provides account identification foundation
- Phase 2 (Configuration): Provides workflow schema for integration
- Phase 3 (Intelligent Wait): Already completed SPEED-03
- Phase 4 (Error Recovery): Provides logging infrastructure for performance metrics
