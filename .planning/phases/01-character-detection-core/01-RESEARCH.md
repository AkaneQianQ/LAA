# Phase 1: Character Detection Core - Research

**Researched:** 2026-03-07
**Domain:** OpenCV template matching based character discovery and local account indexing
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
## Implementation Decisions

### Character Slot Detection Method
- **Template-based detection**: Use `CharacterISorNo` image from assets folder
- **Masking**: FF00FF (magenta) color in template marks ignored regions
- **Detection logic**: Compare slot border features using template matching
- **ROI for each slot**:
  - 1-1: (904, 557, 1152, 624), size 248x67
  - 1-2: (1164, 557, 1412, 624), size 248x67
  - 1-3: (1425, 557, 1673, 624), size 248x67
  - 2-1: (904, 674, 1152, 741), size 248x67
  - 2-2: (1164, 674, 1412, 741), size 248x67
  - 2-3: (1425, 674, 1673, 741), size 248x67
  - 3-1: (904, 791, 1152, 858), size 248x67
  - 3-2: (1164, 791, 1412, 858), size 248x67
  - 3-3: (1425, 791, 1673, 858), size 248x67
- **Grid pattern**: 3x3 layout with ~260px column spacing, ~117px row spacing

### First-Run Discovery Flow
- **Quick index mode**: Screenshot only the first character as account identifier
- **Process**:
  1. Open ESC menu and detect character selection screen
  2. Detect which of 9 visible slots have characters
  3. Screenshot the first discovered character for account indexing
  4. Save account identifier to database
  5. Continue with automation workflow
- **Rationale**: Fast first-run experience; character details discovered on-demand during workflow

### Character Screenshot Indexing
- **Storage**: SQLite database for metadata + file system for screenshots
- **Structure**: `data/accounts/{account_hash}/characters/{slot_index}.png`
- **Screenshot content**: Character selection page screenshot for scroll detection + individual character screenshots for database
- **Account identifier**: Hash of first character's screenshot + creation timestamp
- **Progress tracking**: Screenshots also serve as "completed today" markers to avoid repetition
- **Claude's discretion**: Exact SQLite schema design (tables, indexes, relationships)

### Scroll Termination Detection
- **Method**: Template matching for scrollbar bottom indicator
- **Template image**: `Buttom.bmp` in assets folder
- **Detection ROI**: (1683, 828, 1697, 860), size 14x32
- **Logic**: If `Buttom.bmp` is detected in ROI, scrollbar has reached bottom
- **Alternative**: Screenshot comparison between consecutive pages (fallback method)

### Detection Confidence Thresholds
- **Template matching**: cv2.TM_CCOEFF_NORMED threshold >= 0.8
- **Exact match for scrollbar**: 100% pixel match for `Buttom.bmp`
- **Retries**: 3 attempts with small position jitter if initial detection fails

### Claude's Discretion
- Screenshot preprocessing (resize, grayscale, compression)
- Hash algorithm choice for account identification
- Retry logic timing and backoff strategy
- Cache invalidation policy (when to re-discover characters)
- SQLite schema design (tables, indexes, relationships)

### Deferred Ideas (OUT OF SCOPE)
## Deferred Ideas

- **Resolution independence**: Adaptive ROI scaling for non-2560x1440 displays — v2 consideration
- **Character class detection**: Identify character class from avatar image — feature enhancement, not core requirement
- **Item level reading**: Extract item level from slot display — requires OCR or advanced CV, deferred per user requirement
- **Parallel character discovery**: Process multiple slots simultaneously — optimization for v2
- **Machine learning character recognition**: Train model to identify characters more robustly — overkill for current needs
- **YAML task orchestration**: Configuration-driven automation workflows — Phase 2 scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CHAR-01 | System detects ESC menu opening via template matching | Add dedicated ESC/menu template asset + ROI-based `find_element()` API with retry/backoff and thresholded confidence |
| CHAR-02 | System identifies 9 character slot ROIs using pure image matching | Implement fixed ROI scan over the 3x3 coordinates with masked template matching and slot occupancy decision rules |
| CHAR-03 | System discovers total character count through scroll traversal | Use row-by-row scroll loop until `Buttom.bmp` bottom indicator matches in scrollbar ROI, count discovered occupied slots |
| CHAR-04 | System captures first detected character screenshot as account database index | Persist first discovered character screenshot and derive stable account hash from image bytes |
| CHAR-05 | System caches character screenshots for future recognition | Store screenshot files under account directory and maintain SQLite metadata for lookup, timestamping, and refresh policy |
</phase_requirements>

## Summary

Phase 1 should be planned as a deterministic computer-vision pipeline around fixed ROIs and two template assets (`CharacterISorNo.bmp`, `Buttom.bmp`), with no OCR path and no manual character-count prompt. The highest planning priority is to lock interfaces and data contracts (detector API + SQLite schema + screenshot path rules) because later phases depend on stable identity and slot-discovery output.

OpenCV constraints matter here: mask support in `cv::matchTemplate` is only available for `TM_SQDIFF` and `TM_CCORR_NORMED` in official OpenCV docs, so a strict FF00FF mask design conflicts with the currently stated `TM_CCOEFF_NORMED` method unless masking is handled manually (e.g., pre-masking images) or method is changed to `TM_CCORR_NORMED`. This is a key planning decision to resolve in Wave 0.

There is also a repo-state risk: this checkout currently contains planning docs and assets but not the referenced Python runtime modules (`core/`, `modules/`, `main.py`, etc.). Planning should include an explicit reconciliation step to confirm actual implementation targets and file paths before creating executable tasks.

**Primary recommendation:** Plan Phase 1 around a single `CharacterDetector` service with explicit I/O contracts, enforce OpenCV mask/method compatibility up front, and define SQLite schema + cache policy before implementation.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.13.x | Runtime + orchestration | Project baseline and standard library coverage for hashing/sqlite |
| OpenCV (`opencv-python`) | 4.x | Template matching, masking, ROI comparisons | Canonical CV toolkit for deterministic UI template matching |
| NumPy | 1.x/2.x compatible with OpenCV | Pixel matrix manipulation and mask transforms | Required companion for OpenCV image ops |
| sqlite3 (stdlib) | Python stdlib | Local metadata persistence | Zero-dependency embedded DB fits account cache use case |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `hashlib` (stdlib) | Python stdlib | SHA-256 account fingerprinting from screenshot bytes | Always for account ID derivation |
| `pathlib` (stdlib) | Python stdlib | Safe cross-path file handling | Always for screenshot/cache paths |
| `datetime` (stdlib) | Python stdlib | Cache timestamps, discovery audit | For refresh/invalidation and debug traceability |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `sqlite3` direct | TinyDB/JSON files | Simpler start, weaker query/index semantics and higher corruption risk at scale |
| `TM_CCORR_NORMED` + mask | `TM_CCOEFF_NORMED` without mask | More robust in some scenes but loses direct support for FF00FF ignore regions |

**Installation:**
```bash
pip install opencv-python numpy
```

## Architecture Patterns

### Recommended Project Structure
```
assets/
  CharacterISorNo.bmp
  Buttom.bmp
src/
  core/
    vision_engine.py
    database.py
  modules/
    character_detector.py
  data/
    accounts/
      {account_hash}/
        characters/
          {slot_index}.png
```

### Pattern 1: Deterministic ROI Scan
**What:** Iterate fixed 3x3 slot ROIs, evaluate occupancy with template score, produce ordered visible-slot map.
**When to use:** Every time character selection screen is entered.
**Example:**
```python
# Source: OpenCV template matching tutorial + project context ROIs
for slot_index, roi in SLOT_ROIS.items():
    roi_img = frame[y1:y2, x1:x2]
    score = match_slot(roi_img, slot_template, slot_mask)
    occupied[slot_index] = score >= SLOT_THRESHOLD
```

### Pattern 2: Scroll-Until-Terminal Traversal
**What:** Count discovered slots page-by-page and stop only when scrollbar-bottom template matches.
**When to use:** Total character count discovery.
**Example:**
```python
while True:
    scan_visible_slots()
    if is_scrollbar_bottom(frame, bottom_template):
        break
    scroll_one_row_down()
```

### Pattern 3: Content-Addressed Account Cache
**What:** Derive account key from screenshot hash and persist metadata + file path mappings.
**When to use:** First-run indexing and repeat-run recognition.
**Example:**
```python
import hashlib
account_hash = hashlib.sha256(first_character_png_bytes).hexdigest()
```

### Anti-Patterns to Avoid
- **Mixing OCR fallback into Phase 1:** Violates requirement scope and raises complexity.
- **Hardcoding DB writes across modules:** Introduces schema drift; centralize through repository functions.
- **Unbounded retry loops:** Can deadlock automation; use bounded retries and explicit failure states.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image similarity core | Custom pixel-scoring algorithm | OpenCV `matchTemplate` | Battle-tested implementation with normalized methods and mask support rules |
| Persistent metadata store | Ad-hoc JSON merge logic | `sqlite3` with indexed tables | Better consistency, querying, and concurrency behavior |
| Cryptographic ID | Homegrown hash function | `hashlib.sha256` | Standard secure and deterministic hash primitive |

**Key insight:** The risky complexity in this phase is not algorithms; it is deterministic state flow and asset/threshold correctness.

## Common Pitfalls

### Pitfall 1: Mask + Method Incompatibility
**What goes wrong:** Using FF00FF mask with `TM_CCOEFF_NORMED` does not follow documented mask support.
**Why it happens:** OpenCV only documents mask support for `TM_SQDIFF` and `TM_CCORR_NORMED`.
**How to avoid:** Choose `TM_CCORR_NORMED` for masked matching, or explicitly pre-mask template/ROI before unmasked matching.
**Warning signs:** Runtime assertion/errors or unstable scores across identical frames.

### Pitfall 2: Duplicate Counting Across Scroll Pages
**What goes wrong:** Characters visible on adjacent pages are counted multiple times.
**Why it happens:** Scroll moves by rows and pages overlap if indexing logic is naive.
**How to avoid:** Track global slot indices by page offset (`page*3 + local_row`) and deduplicate.
**Warning signs:** Total count exceeding realistic account max.

### Pitfall 3: Fragile Exact Match for `Buttom.bmp`
**What goes wrong:** 100% pixel-equality fails due to capture/compression/render variance.
**Why it happens:** Small anti-aliasing or frame capture differences.
**How to avoid:** Use template threshold near-exact (e.g., >=0.99) plus 2-3 confirmation frames.
**Warning signs:** Endless scroll loop at bottom.

### Pitfall 4: SQLite Locked Errors During Multi-threaded Use
**What goes wrong:** Discovery thread collides with another writer.
**Why it happens:** SQLite allows one writer at a time.
**How to avoid:** Single writer path, short transactions, sensible `timeout`, and optional WAL mode.
**Warning signs:** Intermittent `OperationalError: database is locked`.

## Code Examples

Verified patterns from official sources:

### OpenCV Mask-Compatible Template Matching
```python
result = cv2.matchTemplate(image, template, cv2.TM_CCORR_NORMED, mask=mask)
_, max_val, _, max_loc = cv2.minMaxLoc(result)
matched = max_val >= threshold
```
Source: https://docs.opencv.org/4.x/de/da9/tutorial_template_matching.html

### SQLite Connection With Explicit Timeout
```python
import sqlite3
conn = sqlite3.connect(db_path, timeout=5.0)
```
Source: https://docs.python.org/3/library/sqlite3.html

### Stable SHA-256 Fingerprint
```python
import hashlib
account_hash = hashlib.sha256(image_bytes).hexdigest()
```
Source: https://docs.python.org/3/library/hashlib.html

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OCR-based account identification | Pure template matching + screenshot hash indexing | Project decision on 2026-03-07 | Removes OCR dependency, simplifies runtime dependencies |
| Manual character-count input | Scroll traversal auto-discovery | Phase 1 scope definition (2026-03-07) | Enables zero-config onboarding |
| JSON-only state persistence | SQLite metadata + filesystem screenshots | Phase 1 design decision (2026-03-07) | Improves queryability and cache lifecycle control |

**Deprecated/outdated:**
- OCR-based account naming for v1 character discovery (explicitly out of scope).

## Open Questions

1. **Where is the runtime code in this checkout?**
- What we know: Planning docs reference `core/` and `modules/` files.
- What's unclear: These files are not present in current working tree.
- Recommendation: Confirm branch/worktree or restore source files before planning executable tasks.

2. **Which template-matching method is final for masked slot detection?**
- What we know: Context mandates FF00FF masking and threshold 0.8 with `TM_CCOEFF_NORMED`.
- What's unclear: OpenCV mask support documentation conflicts with that method.
- Recommendation: Decide Wave 0 policy: switch to `TM_CCORR_NORMED` or define pre-mask preprocessing with validation dataset.

3. **How strict should scrollbar-bottom detection be?**
- What we know: Context asks for 100% exact match.
- What's unclear: Whether screen capture path guarantees bit-perfect repeatability.
- Recommendation: Define acceptance test with real captures; if unstable, adopt >=0.99 template score + consecutive confirmation frames.

## Sources

### Primary (HIGH confidence)
- OpenCV Template Matching tutorial (4.x): https://docs.opencv.org/4.x/de/da9/tutorial_template_matching.html (match methods, mask constraints)
- Python `sqlite3` docs (3.14): https://docs.python.org/3/library/sqlite3.html (connection options, timeout, thread behavior)
- Python `hashlib` docs (3.14): https://docs.python.org/3/library/hashlib.html (SHA-256 usage)
- SQLite WAL official docs: https://www.sqlite.org/wal.html (concurrency model and one-writer constraint)

### Secondary (MEDIUM confidence)
- `.planning/codebase/*.md` documents generated on 2026-03-07 (architecture/stack assumptions; currently inconsistent with checkout contents)

### Tertiary (LOW confidence)
- None required for current recommendations.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - standard Python/OpenCV/sqlite stack with official docs
- Architecture: MEDIUM - strong domain fit, but repository contents currently mismatch documented structure
- Pitfalls: HIGH - derived from official API constraints plus deterministic automation failure modes

**Research date:** 2026-03-07
**Valid until:** 2026-04-06 (30 days)
