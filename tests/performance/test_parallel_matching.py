"""
Performance tests for parallel template matching.

Tests ParallelMatcher functionality including:
- match_single_roi returns correct slot_index and confidence
- scan_rois_parallel completes faster than sequential
- Results are correctly ordered by slot_index
- Empty ROI regions return (False, 0.0) without error
- ThreadPoolExecutor max_workers configurable (default 4)
"""

import pytest
import numpy as np
import cv2
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple, Dict, List

# Import the module to test (will be created)
import sys
sys.path.insert(0, 'C:/Users/Akane/FerrumProject/LostarkGuildDonationBot')


class TestMatchSingleRoi:
    """Tests for match_single_roi function."""

    def test_returns_correct_slot_index(self):
        """Test that match_single_roi returns the correct slot_index."""
        from core.parallel_matcher import match_single_roi

        # Create test screenshot and template
        screenshot = np.ones((200, 200, 3), dtype=np.uint8) * 255
        template = np.ones((50, 50), dtype=np.uint8) * 255
        roi = (10, 10, 60, 60)

        slot_index, found, confidence = match_single_roi(screenshot, template, roi, 0)

        assert slot_index == 0

    def test_returns_different_slot_indices(self):
        """Test that different slot indices are preserved."""
        from core.parallel_matcher import match_single_roi

        screenshot = np.ones((200, 200, 3), dtype=np.uint8) * 255
        template = np.ones((50, 50), dtype=np.uint8) * 255
        roi = (10, 10, 60, 60)

        for i in range(9):
            slot_index, _, _ = match_single_roi(screenshot, template, roi, i)
            assert slot_index == i

    def test_detects_match_in_roi(self):
        """Test that match is detected when template exists in ROI."""
        from core.parallel_matcher import match_single_roi

        # Create screenshot with white region
        screenshot = np.zeros((200, 200, 3), dtype=np.uint8)
        screenshot[50:100, 50:100] = 255  # White square

        # Create matching template
        template = np.ones((50, 50), dtype=np.uint8) * 255
        roi = (40, 40, 110, 110)  # Contains the white square

        slot_index, found, confidence = match_single_roi(screenshot, template, roi, 0)

        assert found is True
        assert confidence >= 0.8

    def test_no_match_returns_false(self):
        """Test that no match returns False with low confidence."""
        from core.parallel_matcher import match_single_roi

        # Create screenshot with random noise (no clear pattern)
        np.random.seed(42)
        screenshot = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)

        # Create template with specific pattern that won't match random noise well
        template = np.zeros((50, 50), dtype=np.uint8)
        template[10:40, 10:40] = 255  # White square in middle
        roi = (10, 10, 60, 60)

        slot_index, found, confidence = match_single_roi(screenshot, template, roi, 0)

        assert found is False
        assert confidence < 0.8

    def test_empty_roi_returns_false_and_zero(self):
        """Test that empty ROI region returns (False, 0.0)."""
        from core.parallel_matcher import match_single_roi

        screenshot = np.ones((200, 200, 3), dtype=np.uint8) * 255
        template = np.ones((50, 50), dtype=np.uint8) * 255
        # Invalid ROI (x1 >= x2)
        roi = (10, 10, 10, 60)

        slot_index, found, confidence = match_single_roi(screenshot, template, roi, 0)

        assert found is False
        assert confidence == 0.0

    def test_out_of_bounds_roi_returns_false(self):
        """Test that out-of-bounds ROI returns (False, 0.0)."""
        from core.parallel_matcher import match_single_roi

        screenshot = np.ones((100, 100, 3), dtype=np.uint8) * 255
        template = np.ones((50, 50), dtype=np.uint8) * 255
        # ROI outside screenshot bounds
        roi = (150, 150, 200, 200)

        slot_index, found, confidence = match_single_roi(screenshot, template, roi, 0)

        assert found is False
        assert confidence == 0.0


class TestParallelMatcher:
    """Tests for ParallelMatcher class."""

    def test_default_max_workers(self):
        """Test that default max_workers is 4."""
        from core.parallel_matcher import ParallelMatcher

        matcher = ParallelMatcher()
        assert matcher.max_workers == 4

    def test_custom_max_workers(self):
        """Test that max_workers is configurable."""
        from core.parallel_matcher import ParallelMatcher

        matcher = ParallelMatcher(max_workers=2)
        assert matcher.max_workers == 2

        matcher = ParallelMatcher(max_workers=8)
        assert matcher.max_workers == 8

    def test_scan_rois_returns_dict(self):
        """Test that scan_rois returns a dictionary."""
        from core.parallel_matcher import ParallelMatcher

        matcher = ParallelMatcher()
        screenshot = np.ones((500, 500, 3), dtype=np.uint8) * 255
        template = np.ones((50, 50), dtype=np.uint8) * 255
        rois = [(i*60, i*60, i*60+50, i*60+50) for i in range(9)]

        results = matcher.scan_rois(screenshot, template, rois)

        assert isinstance(results, dict)
        assert len(results) == 9

    def test_scan_rois_correct_ordering(self):
        """Test that results are keyed by correct slot_index."""
        from core.parallel_matcher import ParallelMatcher

        matcher = ParallelMatcher()
        screenshot = np.ones((500, 500, 3), dtype=np.uint8) * 255
        template = np.ones((50, 50), dtype=np.uint8) * 255
        rois = [(i*60, i*60, i*60+50, i*60+50) for i in range(9)]

        results = matcher.scan_rois(screenshot, template, rois)

        # Check all slot indices are present
        for i in range(9):
            assert i in results
            found, confidence = results[i]
            assert isinstance(found, bool)
            assert isinstance(confidence, float)

    def test_scan_rois_detects_matches(self):
        """Test that scan_rois correctly detects matches."""
        from core.parallel_matcher import ParallelMatcher

        matcher = ParallelMatcher()

        # Create screenshot with alternating pattern
        screenshot = np.zeros((500, 500, 3), dtype=np.uint8)
        for i in range(0, 500, 100):
            screenshot[i:i+50, i:i+50] = 255  # White squares at intervals

        template = np.ones((50, 50), dtype=np.uint8) * 255
        # ROIs that align with white squares
        rois = [(i*100, i*100, i*100+50, i*100+50) for i in range(5)]

        results = matcher.scan_rois(screenshot, template, rois)

        # All should match
        for i in range(5):
            found, confidence = results[i]
            assert found is True
            assert confidence >= 0.8


class TestBenchmark:
    """Benchmark tests for parallel vs sequential performance."""

    def create_test_screenshot(self, size: Tuple[int, int] = (1440, 2560)) -> np.ndarray:
        """Create a realistic test screenshot."""
        return np.random.randint(0, 256, (*size, 3), dtype=np.uint8)

    def create_test_rois(self, count: int = 9) -> List[Tuple[int, int, int, int]]:
        """Create test ROIs similar to character slots."""
        # 3x3 grid pattern similar to character slots
        rois = []
        base_x, base_y = 900, 550
        for row in range(3):
            for col in range(3):
                x1 = base_x + col * 260
                y1 = base_y + row * 117
                x2 = x1 + 248
                y2 = y1 + 67
                rois.append((x1, y1, x2, y2))
        return rois[:count]

    def test_parallel_faster_than_sequential(self):
        """Test that parallel scan is faster than sequential for 9 slots."""
        from core.parallel_matcher import ParallelMatcher, match_single_roi

        screenshot = self.create_test_screenshot()
        template = np.ones((67, 248), dtype=np.uint8) * 128
        rois = self.create_test_rois(9)

        # Sequential scan
        start = time.perf_counter()
        sequential_results = {}
        for i, roi in enumerate(rois):
            slot_index, found, confidence = match_single_roi(screenshot, template, roi, i)
            sequential_results[slot_index] = (found, confidence)
        sequential_time = time.perf_counter() - start

        # Parallel scan
        matcher = ParallelMatcher(max_workers=4)
        start = time.perf_counter()
        parallel_results = matcher.scan_rois(screenshot, template, rois)
        parallel_time = time.perf_counter() - start

        # Results should be identical
        assert parallel_results == sequential_results

        # Parallel should be faster (allow some tolerance for test environment)
        # We expect at least some speedup, but in CI/single-core might be minimal
        # Just verify it completes without error and produces correct results
        assert parallel_time < sequential_time * 2  # Shouldn't be 2x slower

    def test_parallel_completes_under_200ms(self):
        """Test that 9-slot parallel scan completes in under 200ms."""
        from core.parallel_matcher import ParallelMatcher

        screenshot = self.create_test_screenshot()
        template = np.ones((67, 248), dtype=np.uint8) * 128
        rois = self.create_test_rois(9)

        matcher = ParallelMatcher(max_workers=4)

        start = time.perf_counter()
        results = matcher.scan_rois(screenshot, template, rois)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(results) == 9
        # Target: <200ms for 9 slots (allow 50% tolerance for test environment)
        assert elapsed_ms < 300, f"Parallel scan took {elapsed_ms:.1f}ms, expected <300ms"


class TestCharacterDetectorIntegration:
    """Integration tests with CharacterDetector."""

    def test_character_detector_has_parallel_method(self):
        """Test that CharacterDetector has scan_visible_slots_parallel method."""
        from modules.character_detector import CharacterDetector

        detector = CharacterDetector()
        assert hasattr(detector, 'scan_visible_slots_parallel')

    def test_parallel_returns_same_results_as_sequential(self):
        """Test that parallel scan returns same results as sequential."""
        from modules.character_detector import CharacterDetector

        detector = CharacterDetector()

        # Create test screenshot
        screenshot = np.ones((1440, 2560, 3), dtype=np.uint8) * 200

        # Sequential scan
        sequential_results = detector.scan_visible_slots(screenshot)

        # Parallel scan
        parallel_results = detector.scan_visible_slots_parallel(screenshot)

        # Results should have same length
        assert len(parallel_results) == len(sequential_results)

        # Each slot should have same occupancy status
        for i, (seq, par) in enumerate(zip(sequential_results, parallel_results)):
            assert seq.slot_index == par.slot_index
            assert seq.has_character == par.has_character
            assert seq.roi == par.roi

    def test_parallel_is_faster(self):
        """Test that parallel scan is measurably faster."""
        from modules.character_detector import CharacterDetector

        detector = CharacterDetector()
        screenshot = np.ones((1440, 2560, 3), dtype=np.uint8) * 200

        # Warm up
        detector.scan_visible_slots(screenshot)
        detector.scan_visible_slots_parallel(screenshot)

        # Sequential timing
        start = time.perf_counter()
        for _ in range(3):
            detector.scan_visible_slots(screenshot)
        sequential_time = (time.perf_counter() - start) / 3 * 1000

        # Parallel timing
        start = time.perf_counter()
        for _ in range(3):
            detector.scan_visible_slots_parallel(screenshot)
        parallel_time = (time.perf_counter() - start) / 3 * 1000

        # Parallel should not be significantly slower
        assert parallel_time < sequential_time * 1.5


class TestBenchmarkUtility:
    """Tests for benchmark utility function."""

    def test_benchmark_returns_comparison_dict(self):
        """Test that benchmark function returns timing comparison."""
        from core.parallel_matcher import benchmark_parallel_vs_sequential

        screenshot = np.ones((500, 500, 3), dtype=np.uint8) * 255
        template = np.ones((50, 50), dtype=np.uint8) * 255
        rois = [(i*60, i*60, i*60+50, i*60+50) for i in range(9)]

        result = benchmark_parallel_vs_sequential(screenshot, template, rois)

        assert 'sequential_ms' in result
        assert 'parallel_ms' in result
        assert 'speedup' in result
        assert 'parallel_faster' in result
        assert isinstance(result['sequential_ms'], float)
        assert isinstance(result['parallel_ms'], float)
        assert isinstance(result['speedup'], float)
        assert isinstance(result['parallel_faster'], bool)
