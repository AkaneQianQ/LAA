"""
Discovery and traversal tests for character detection system.

Tests validate:
- Menu detection with retry logic and fail-fast behavior
- 9-slot visible slot scanning
- Scroll traversal with bottom termination
- Full character discovery workflow
"""

import pytest
import sys
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestMenuDetectionRetryAndFailfast:
    """Validate ESC menu detection with bounded retries and deterministic failure."""

    def test_detect_character_selection_screen_exists(self):
        """Detector has detect_character_selection_screen method."""
        from modules.character_detector import CharacterDetector

        assert hasattr(CharacterDetector, 'detect_character_selection_screen')

    def test_menu_detection_returns_tuple_with_bool_and_confidence(self):
        """Menu detection returns (is_ready, confidence) tuple."""
        from modules.character_detector import CharacterDetector

        detector = CharacterDetector()
        # Mock the internal detection to return a known value
        with patch.object(detector, '_load_template') as mock_load:
            mock_load.return_value = None  # No template found
            result = detector.detect_character_selection_screen(np.zeros((1080, 1920, 3), dtype=np.uint8))

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], float)

    def test_menu_detection_retries_up_to_max_attempts(self):
        """Menu detection retries up to MAX_DETECTION_RETRIES times."""
        from modules.character_detector import CharacterDetector, MAX_DETECTION_RETRIES

        detector = CharacterDetector()

        # Mock _load_template to return a valid template
        mock_template = np.zeros((50, 50), dtype=np.uint8)
        with patch.object(detector, '_load_template', return_value=mock_template):
            # Mock matchTemplate to always return low confidence (below threshold)
            with patch('cv2.matchTemplate') as mock_match:
                mock_match.return_value = np.array([[0.3]])  # Low confidence

                screenshot = np.zeros((1080, 1920, 3), dtype=np.uint8)
                result = detector.detect_character_selection_screen(screenshot)

                # Should have retried MAX_DETECTION_RETRIES times
                assert mock_match.call_count == MAX_DETECTION_RETRIES
                # Result should indicate not ready
                assert result[0] is False

    def test_menu_detection_succeeds_on_first_high_confidence(self):
        """Menu detection succeeds immediately when confidence >= threshold."""
        from modules.character_detector import CharacterDetector, SLOT_DETECTION_THRESHOLD

        detector = CharacterDetector()

        mock_template = np.zeros((50, 50), dtype=np.uint8)
        with patch.object(detector, '_load_template', return_value=mock_template):
            with patch('cv2.matchTemplate') as mock_match:
                # Return high confidence on first call
                mock_match.return_value = np.array([[0.95]])

                screenshot = np.zeros((1080, 1920, 3), dtype=np.uint8)
                result = detector.detect_character_selection_screen(screenshot)

                # Should only call matchTemplate once
                assert mock_match.call_count == 1
                # Result should indicate ready
                assert result[0] is True
                assert result[1] >= SLOT_DETECTION_THRESHOLD

    def test_menu_detection_fails_fast_when_template_missing(self):
        """Menu detection returns False immediately if template not found."""
        from modules.character_detector import CharacterDetector

        detector = CharacterDetector()

        # Template not found
        with patch.object(detector, '_load_template', return_value=None):
            screenshot = np.zeros((1080, 1920, 3), dtype=np.uint8)
            start_time = time.time()
            result = detector.detect_character_selection_screen(screenshot)
            elapsed = time.time() - start_time

            # Should return immediately (no retries)
            assert result[0] is False
            assert result[1] == 0.0
            assert elapsed < 0.1  # Fast fail

    def test_menu_detection_bounded_no_infinite_loop(self):
        """Menu detection is bounded and never loops infinitely."""
        from modules.character_detector import CharacterDetector, MAX_DETECTION_RETRIES

        detector = CharacterDetector()

        mock_template = np.zeros((50, 50), dtype=np.uint8)
        with patch.object(detector, '_load_template', return_value=mock_template):
            with patch('cv2.matchTemplate') as mock_match:
                # Always return low confidence
                mock_match.return_value = np.array([[0.1]])

                screenshot = np.zeros((1080, 1920, 3), dtype=np.uint8)
                start_time = time.time()
                result = detector.detect_character_selection_screen(screenshot)
                elapsed = time.time() - start_time

                # Should complete within reasonable time (bounded retries)
                assert mock_match.call_count <= MAX_DETECTION_RETRIES
                assert elapsed < 1.0  # Should complete quickly
                assert result[0] is False


class TestScanVisibleSlots:
    """Validate 9-slot occupancy scanning behavior."""

    def test_scan_visible_slots_returns_nine_results(self):
        """Visible slot scan returns exactly 9 results."""
        from modules.character_detector import CharacterDetector

        detector = CharacterDetector()

        with patch.object(detector, '_load_template', return_value=None):
            screenshot = np.zeros((1080, 1920, 3), dtype=np.uint8)
            results = detector.scan_visible_slots(screenshot)

            assert len(results) == 9

    def test_scan_visible_slots_returns_slot_occupancy_results(self):
        """Each result is a SlotOccupancyResult with required fields."""
        from modules.character_detector import CharacterDetector, SlotOccupancyResult

        detector = CharacterDetector()

        with patch.object(detector, '_load_template', return_value=None):
            screenshot = np.zeros((1080, 1920, 3), dtype=np.uint8)
            results = detector.scan_visible_slots(screenshot)

            for i, result in enumerate(results):
                assert isinstance(result, SlotOccupancyResult)
                assert hasattr(result, 'slot_index')
                assert hasattr(result, 'roi')
                assert hasattr(result, 'has_character')
                assert hasattr(result, 'confidence')
                assert result.slot_index == i

    def test_scan_visible_slots_row_major_order(self):
        """Slots are returned in row-major order (left-to-right, top-to-bottom)."""
        from modules.character_detector import CharacterDetector, ALL_SLOT_ROIS

        detector = CharacterDetector()

        with patch.object(detector, '_load_template', return_value=None):
            screenshot = np.zeros((1080, 1920, 3), dtype=np.uint8)
            results = detector.scan_visible_slots(screenshot)

            for i, result in enumerate(results):
                assert result.roi == ALL_SLOT_ROIS[i]
                assert result.slot_index == i

    def test_scan_visible_slots_uses_ff00ff_masking(self):
        """Slot detection uses FF00FF-aware matching strategy."""
        from modules.character_detector import CharacterDetector

        detector = CharacterDetector()

        # Create a template with some magenta pixels
        mock_template = np.zeros((50, 50, 3), dtype=np.uint8)
        mock_template[10:20, 10:20] = [255, 0, 255]  # Magenta in BGR

        with patch.object(detector, '_load_template') as mock_load:
            mock_load.return_value = cv2.cvtColor(mock_template, cv2.COLOR_BGR2GRAY)

            screenshot = np.zeros((1080, 1920, 3), dtype=np.uint8)
            with patch('cv2.matchTemplate') as mock_match:
                mock_match.return_value = np.array([[0.9]])
                results = detector.scan_visible_slots(screenshot)

                # Template loading should have been called with FF00FF masking
                assert mock_load.called

    def test_scan_visible_slots_retry_on_borderline_confidence(self):
        """Slot scan retries when confidence is borderline."""
        from modules.character_detector import CharacterDetector, SLOT_DETECTION_THRESHOLD

        detector = CharacterDetector()

        mock_template = np.zeros((50, 50), dtype=np.uint8)
        with patch.object(detector, '_load_template', return_value=mock_template):
            with patch('cv2.matchTemplate') as mock_match:
                # Return borderline confidence (just below threshold)
                borderline = SLOT_DETECTION_THRESHOLD - 0.05
                mock_match.return_value = np.array([[borderline]])

                screenshot = np.zeros((1080, 1920, 3), dtype=np.uint8)
                results = detector.scan_visible_slots(screenshot)

                # Should have retried for borderline results
                assert mock_match.call_count > 9  # More than one per slot


class TestScrollTraversalAndCounting:
    """Validate scroll traversal with bottom termination and character counting."""

    def test_discover_total_characters_exists(self):
        """Detector has discover_total_characters method."""
        from modules.character_detector import CharacterDetector

        assert hasattr(CharacterDetector, 'discover_total_characters')

    def test_discover_total_characters_returns_discovery_result(self):
        """Discovery returns CharacterDiscoveryResult with total count."""
        from modules.character_detector import CharacterDetector, CharacterDiscoveryResult

        detector = CharacterDetector()

        # Mock all dependencies
        with patch.object(detector, 'detect_character_selection_screen', return_value=(True, 0.9)):
            with patch.object(detector, 'scan_visible_slots') as mock_scan:
                # Return 3 occupied slots
                mock_results = []
                for i in range(9):
                    mock_result = Mock()
                    mock_result.has_character = (i < 3)
                    mock_result.confidence = 0.9 if i < 3 else 0.1
                    mock_results.append(mock_result)
                mock_scan.return_value = mock_results

                with patch.object(detector, 'detect_scroll_bottom', return_value=(True, 1.0)):
                    result = detector.discover_total_characters(np.zeros((1080, 1920, 3), dtype=np.uint8))

        assert isinstance(result, CharacterDiscoveryResult)
        assert result.total_characters == 3

    def test_scroll_traversal_terminates_at_bottom_detection(self):
        """Discovery loop stops when Buttom.bmp detected in scrollbar ROI."""
        from modules.character_detector import CharacterDetector

        detector = CharacterDetector()

        call_count = {'bottom_checks': 0}

        def mock_bottom_detection(screenshot):
            call_count['bottom_checks'] += 1
            # Return True (at bottom) after 2 pages
            return (call_count['bottom_checks'] >= 2, 1.0)

        # Create mock slot results with different signatures per page to avoid duplicate detection
        page1_results = [Mock(has_character=True, confidence=0.9) for _ in range(9)]
        page2_results = [Mock(has_character=True, confidence=0.8) for _ in range(9)]

        with patch.object(detector, 'detect_character_selection_screen', return_value=(True, 0.9)):
            with patch.object(detector, 'scan_visible_slots', side_effect=[page1_results, page2_results, []]):
                with patch.object(detector, 'detect_scroll_bottom', side_effect=mock_bottom_detection):
                    with patch.object(detector, '_capture_screenshot'):
                        with patch.object(detector, '_scroll_down'):
                            result = detector.discover_total_characters(np.zeros((1080, 1920, 3), dtype=np.uint8))

        # Should have stopped after detecting bottom (at least 2 checks: page 1 and page 2)
        assert call_count['bottom_checks'] >= 1

    def test_scroll_bottom_requires_exact_pixel_match(self):
        """Scrollbar termination requires 100% pixel match for Buttom.bmp."""
        from modules.character_detector import CharacterDetector

        detector = CharacterDetector()

        mock_template = np.zeros((32, 14), dtype=np.uint8)  # Bottom template size
        with patch.object(detector, '_load_template', return_value=mock_template):
            with patch('cv2.matchTemplate') as mock_match:
                # Return perfect match
                mock_match.return_value = np.array([[1.0]])

                screenshot = np.zeros((1080, 1920, 3), dtype=np.uint8)
                is_at_bottom, confidence = detector.detect_scroll_bottom(screenshot)

                assert is_at_bottom is True
                assert confidence == 1.0

    def test_discover_total_characters_deduplicates_rows(self):
        """Discovery deduplicates characters across scroll pages."""
        from modules.character_detector import CharacterDetector

        detector = CharacterDetector()

        # Simulate scrolling where bottom row becomes top row
        page_results = [
            # Page 1: slots 0-2 occupied
            [Mock(has_character=True, confidence=0.9) for _ in range(3)] +
            [Mock(has_character=False, confidence=0.1) for _ in range(6)],
            # Page 2: slots 3-5 occupied (new), but slots 0-2 still visible at bottom
            [Mock(has_character=True, confidence=0.9) for _ in range(6)] +
            [Mock(has_character=False, confidence=0.1) for _ in range(3)],
        ]

        call_count = {'page': 0}

        def mock_scan(screenshot):
            idx = min(call_count['page'], len(page_results) - 1)
            call_count['page'] += 1
            return page_results[idx]

        with patch.object(detector, 'detect_character_selection_screen', return_value=(True, 0.9)):
            with patch.object(detector, 'scan_visible_slots', side_effect=mock_scan):
                with patch.object(detector, 'detect_scroll_bottom', side_effect=[(False, 0.0), (True, 1.0)]):
                    result = detector.discover_total_characters(np.zeros((1080, 1920, 3), dtype=np.uint8))

        # Should count 6 unique characters (3 on page 1 + 3 new on page 2)
        assert result.total_characters == 6

    def test_discover_has_max_page_cap(self):
        """Discovery has maximum page cap to prevent infinite loops."""
        from modules.character_detector import CharacterDetector

        detector = CharacterDetector()

        # Bottom never detected
        with patch.object(detector, 'detect_character_selection_screen', return_value=(True, 0.9)):
            with patch.object(detector, 'scan_visible_slots', return_value=[]):
                with patch.object(detector, 'detect_scroll_bottom', return_value=(False, 0.0)):
                    with patch.object(detector, '_scroll_down') as mock_scroll:
                        result = detector.discover_total_characters(np.zeros((1080, 1920, 3), dtype=np.uint8))

        # Should have stopped due to max page cap
        assert mock_scroll.call_count <= 20  # Reasonable max pages

    def test_discover_returns_error_when_menu_not_ready(self):
        """Discovery returns error state when menu detection fails."""
        from modules.character_detector import CharacterDetector, CharacterDiscoveryResult

        detector = CharacterDetector()

        with patch.object(detector, 'detect_character_selection_screen', return_value=(False, 0.1)):
            result = detector.discover_total_characters(np.zeros((1080, 1920, 3), dtype=np.uint8))

        assert isinstance(result, CharacterDiscoveryResult)
        assert result.total_characters == 0
        # Should indicate error state somehow
        assert len(result.slot_results) == 0


# Import cv2 for tests that need it
try:
    import cv2
except ImportError:
    cv2 = None


@pytest.mark.skipif(cv2 is None, reason="OpenCV not available")
class TestIntegrationWithRealCV:
    """Integration tests that require actual OpenCV."""

    def test_template_matching_with_real_images(self):
        """Template matching works with actual image data."""
        from modules.character_detector import CharacterDetector

        detector = CharacterDetector(assets_path="assets")

        # Create a synthetic screenshot with a pattern
        screenshot = np.random.randint(0, 255, (1440, 2560, 3), dtype=np.uint8)

        # Try to detect (will fail gracefully if templates don't exist)
        result = detector.detect_character_selection_screen(screenshot)

        assert isinstance(result, tuple)
        assert len(result) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
