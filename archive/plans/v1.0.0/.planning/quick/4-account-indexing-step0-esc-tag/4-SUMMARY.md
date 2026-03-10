---
phase: quick-4
plan: 4
subsystem: account_indexing
tags: [perceptual_hash, workflow, capture_roi, account_tag]
dependency_graph:
  requires: [database, vision_engine, workflow_system]
  provides: [perceptual_hash_matching, roi_capture]
  affects: [account_indexing_workflow]
tech_stack:
  added: [imagehash, Pillow]
  patterns: [pHash, hamming_distance, roi_extraction]
key_files:
  created:
    - core/perceptual_hash.py
  modified:
    - core/workflow_schema.py
    - core/workflow_runtime.py
    - config/workflows/account_indexing.yaml
    - modules/character_detector.py
decisions:
  - Use imagehash library for pHash (perceptual hash) implementation
  - Hamming distance threshold of 10 for account matching
  - ROI (666, 793, 772, 902) for account tag capture
  - CaptureROI action stores image in workflow context
metrics:
  duration: 15min
  completed_date: "2026-03-08"
  tasks: 3
  files: 5
---

# Phase Quick-4 Plan 4: Account Indexing Step0 - ESC Tag Summary

## Overview

Implemented Step0 of account indexing: ESC menu opening, account tag ROI capture, and perceptual hash-based account matching. This enables zero-configuration account recognition using visual similarity instead of strict SHA-256 hashing.

## Implementation Details

### Task 1: Perceptual Hash Module (core/perceptual_hash.py)

Created a new module for visual similarity comparison using pHash (perceptual hashing):

- `compute_phash(image_source)` - Computes 64-bit pHash from image path or numpy array
- `compare_phash(hash1, hash2)` - Returns hamming distance (0-64) between hashes
- `find_similar_account(db_path, screenshot, roi, threshold)` - Finds best matching account from database
- `compute_phash_from_roi(screenshot, roi)` - Helper for direct ROI capture

Key features:
- PIL Image conversion from OpenCV BGR format
- Error handling for missing files or invalid images
- Chinese comments per project convention

### Task 2: CaptureROI Action (workflow_schema.py, workflow_runtime.py)

Added new workflow action type for ROI screenshot capture:

**CaptureROIAction schema:**
- `roi` - Region of interest coordinates (x1, y1, x2, y2)
- `output_key` - Key to store captured image in workflow context
- `save_path` - Optional path to save screenshot to file

**ActionDispatcher._dispatch_capture_roi:**
- Captures screenshot using DXCam or PIL fallback
- Extracts ROI region with bounds validation
- Stores numpy array in workflow context under output_key
- Optionally saves to file if save_path specified

### Task 3: Account Indexing Workflow (account_indexing.yaml, character_detector.py)

**Updated workflow (Step0 implementation):**
1. `open_esc_menu` - Press ESC key to open menu
2. `wait_after_esc` - Wait 200ms for UI stabilization
3. `capture_account_tag` - Capture ROI (666, 793, 772, 902)
4. `match_or_create_account` - Match against existing accounts
5. `workflow_complete` - End workflow

**CharacterDetector integration:**
- Added `find_account_by_perceptual_hash(screenshot, threshold=10)` method
- Uses perceptual hash comparison instead of strict SHA-256
- Returns (account_id, account_hash) tuple or None
- Maintains backward compatibility with existing strict hash methods

## Verification Results

All verification checks passed:
- [OK] Perceptual hash module imports and functions correctly
- [OK] CaptureROI action registered in workflow schema
- [OK] Action dispatcher handles capture_roi action type
- [OK] Account indexing workflow loads with 5 steps
- [OK] CharacterDetector integrates perceptual hash lookup

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| 73afa88 | feat(quick-4): create perceptual hash module for visual similarity |
| 11b4e72 | feat(quick-4): add CaptureROI action to workflow system |
| 4ab7f48 | feat(quick-4): update account indexing workflow and perceptual hash integration |

## Requirements Traceability

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| IDX-01 | Complete | Perceptual hash module with find_similar_account() |
| IDX-02 | Complete | CaptureROI action for account tag extraction |

## Notes

- Perceptual hashing provides robustness against minor UI variations
- Hamming distance threshold of 10 allows for small visual differences while maintaining accuracy
- The new ROI (666, 793, 772, 902) prevents UI color change issues from mouse hover
- Workflow context stores captured images for downstream processing

## Self-Check: PASSED

All files verified present:
- [OK] core/perceptual_hash.py (created)
- [OK] core/workflow_schema.py (modified)
- [OK] core/workflow_runtime.py (modified)
- [OK] config/workflows/account_indexing.yaml (modified)
- [OK] modules/character_detector.py (modified)
- [OK] 4-SUMMARY.md (created)

All commits verified:
- [OK] 73afa88 feat(quick-4): create perceptual hash module for visual similarity
- [OK] 11b4e72 feat(quick-4): add CaptureROI action to workflow system
- [OK] 4ab7f48 feat(quick-4): update account indexing workflow and perceptual hash integration
