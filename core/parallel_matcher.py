"""
Parallel Template Matcher Module

Provides parallel ROI-based template matching using ThreadPoolExecutor.
OpenCV releases the GIL during matchTemplate, so threads provide actual speedup.

This module implements SPEED-01 requirement for parallel processing.
"""

from typing import Tuple, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
import numpy as np
import time
import logging

logger = logging.getLogger(__name__)


def match_single_roi(
    screenshot: np.ndarray,
    template: np.ndarray,
    roi: Tuple[int, int, int, int],
    slot_index: int,
    threshold: float = 0.8
) -> Tuple[int, bool, float]:
    """
    Match template within a single ROI.

    Args:
        screenshot: Full screen capture as BGR numpy array
        template: Template image as grayscale numpy array
        roi: Region of interest (x1, y1, x2, y2)
        slot_index: Index to identify this ROI in results
        threshold: Minimum confidence threshold for match

    Returns:
        Tuple of (slot_index, found, confidence)
    """
    x1, y1, x2, y2 = roi

    # Validate ROI
    if x1 >= x2 or y1 >= y2:
        return slot_index, False, 0.0

    # Extract ROI region
    try:
        roi_region = screenshot[y1:y2, x1:x2]
    except IndexError:
        return slot_index, False, 0.0

    if roi_region.size == 0:
        return slot_index, False, 0.0

    # Convert to grayscale if needed
    if len(roi_region.shape) == 3:
        roi_gray = cv2.cvtColor(roi_region, cv2.COLOR_BGR2GRAY)
    else:
        roi_gray = roi_region

    try:
        result = cv2.matchTemplate(roi_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        found = max_val >= threshold
        return slot_index, found, max_val
    except cv2.error:
        return slot_index, False, 0.0


class ParallelMatcher:
    """
    Parallel template matcher using ThreadPoolExecutor.

    Scans multiple ROIs concurrently for improved performance.
    OpenCV releases the GIL during matchTemplate, so threads provide actual speedup.

    Attributes:
        max_workers: Number of worker threads (default: 4)
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize the parallel matcher.

        Args:
            max_workers: Maximum number of worker threads
        """
        self.max_workers = max_workers

    def scan_rois(
        self,
        screenshot: np.ndarray,
        template: np.ndarray,
        rois: List[Tuple[int, int, int, int]],
        threshold: float = 0.8
    ) -> Dict[int, Tuple[bool, float]]:
        """
        Scan multiple ROIs in parallel.

        Args:
            screenshot: Full screen capture as BGR numpy array
            template: Template image as grayscale numpy array
            rois: List of ROI tuples (x1, y1, x2, y2)
            threshold: Minimum confidence threshold for match

        Returns:
            Dictionary mapping slot_index to (found, confidence) tuple
        """
        results: Dict[int, Tuple[bool, float]] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(
                    match_single_roi,
                    screenshot,
                    template,
                    roi,
                    slot_index,
                    threshold
                ): slot_index
                for slot_index, roi in enumerate(rois)
            }

            # Collect results as they complete
            for future in as_completed(futures):
                slot_index = futures[future]
                try:
                    _, found, confidence = future.result()
                    results[slot_index] = (found, confidence)
                except Exception as e:
                    logger.error(f"Error processing slot {slot_index}: {e}")
                    results[slot_index] = (False, 0.0)

        return results

    def scan_slots(
        self,
        screenshot: np.ndarray,
        template: np.ndarray,
        rois: List[Tuple[int, int, int, int]],
        threshold: float = 0.8
    ) -> Dict[int, Tuple[bool, float]]:
        """
        Alias for scan_rois for slot-specific semantics.

        Args:
            screenshot: Full screen capture as BGR numpy array
            template: Template image as grayscale numpy array
            rois: List of slot ROI tuples
            threshold: Minimum confidence threshold

        Returns:
            Dictionary mapping slot_index to (found, confidence)
        """
        return self.scan_rois(screenshot, template, rois, threshold)


def benchmark_parallel_vs_sequential(
    screenshot: np.ndarray,
    template: np.ndarray,
    rois: List[Tuple[int, int, int, int]],
    threshold: float = 0.8,
    iterations: int = 3
) -> Dict[str, float]:
    """
    Benchmark parallel vs sequential ROI matching.

    Args:
        screenshot: Full screen capture
        template: Template image
        rois: List of ROIs to scan
        threshold: Detection threshold
        iterations: Number of iterations to average

    Returns:
        Dictionary with timing comparison:
        - sequential_ms: Average sequential time in milliseconds
        - parallel_ms: Average parallel time in milliseconds
        - speedup: Speedup factor (sequential / parallel)
        - parallel_faster: True if parallel was faster
    """
    # Sequential benchmark
    seq_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        for i, roi in enumerate(rois):
            match_single_roi(screenshot, template, roi, i, threshold)
        seq_times.append(time.perf_counter() - start)
    sequential_ms = (sum(seq_times) / len(seq_times)) * 1000

    # Parallel benchmark
    matcher = ParallelMatcher(max_workers=4)
    par_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        matcher.scan_rois(screenshot, template, rois, threshold)
        par_times.append(time.perf_counter() - start)
    parallel_ms = (sum(par_times) / len(par_times)) * 1000

    speedup = sequential_ms / parallel_ms if parallel_ms > 0 else 1.0

    return {
        'sequential_ms': sequential_ms,
        'parallel_ms': parallel_ms,
        'speedup': speedup,
        'parallel_faster': parallel_ms < sequential_ms
    }
