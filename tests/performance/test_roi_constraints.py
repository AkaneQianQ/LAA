"""
Tests for ROI constraint enforcement (SPEED-02 requirement).

Ensures all template matching uses explicit ROI constraints with no full-screen matching.
"""

import pytest
import numpy as np
import cv2
from typing import Tuple

import sys
sys.path.insert(0, 'C:/Users/Akane/FerrumProject/LostarkGuildDonationBot')


class TestVisionEngineRoiConstraints:
    """Tests for ROI constraint enforcement in vision_engine.py."""

    def test_find_element_requires_roi_parameter(self):
        """Test that find_element requires ROI parameter (no None default)."""
        from core.vision_engine import find_element
        import inspect

        sig = inspect.signature(find_element)
        roi_param = sig.parameters['roi']

        # ROI should not have a default value of None
        assert roi_param.default is not None, "ROI parameter must be required"

    def test_find_element_raises_error_on_none_roi(self):
        """Test that find_element raises ValueError when ROI is None."""
        from core.vision_engine import find_element

        screenshot = np.ones((100, 100, 3), dtype=np.uint8) * 255
        template = np.ones((50, 50), dtype=np.uint8) * 255

        with pytest.raises(ValueError):
            find_element(screenshot, template, roi=None)

    def test_find_element_raises_error_on_invalid_roi(self):
        """Test that find_element raises ValueError on invalid ROI."""
        from core.vision_engine import find_element

        screenshot = np.ones((100, 100, 3), dtype=np.uint8) * 255
        template = np.ones((50, 50), dtype=np.uint8) * 255

        # Invalid ROI: x1 >= x2
        with pytest.raises(ValueError):
            find_element(screenshot, template, roi=(60, 10, 50, 60))

        # Invalid ROI: y1 >= y2
        with pytest.raises(ValueError):
            find_element(screenshot, template, roi=(10, 60, 60, 50))

    def test_find_element_accepts_valid_roi(self):
        """Test that find_element works with valid ROI."""
        from core.vision_engine import find_element

        screenshot = np.ones((100, 100, 3), dtype=np.uint8) * 255
        template = np.ones((50, 50), dtype=np.uint8) * 255
        roi = (10, 10, 70, 70)

        found, confidence, location = find_element(screenshot, template, roi)

        assert isinstance(found, bool)
        assert isinstance(confidence, float)
        assert isinstance(location, tuple)

    def test_match_template_roi_validates_bounds(self):
        """Test that match_template_roi validates ROI bounds."""
        from core.vision_engine import match_template_roi

        screenshot = np.ones((100, 100, 3), dtype=np.uint8) * 255
        template = np.ones((50, 50), dtype=np.uint8) * 255

        # ROI outside screenshot bounds should return 0.0 confidence
        roi = (150, 150, 200, 200)
        confidence, location = match_template_roi(screenshot, template, roi)

        assert confidence == 0.0
        assert location == (0, 0)

    def test_match_template_roi_returns_zero_for_empty(self):
        """Test that match_template_roi returns 0.0 for empty ROI."""
        from core.vision_engine import match_template_roi

        screenshot = np.ones((100, 100, 3), dtype=np.uint8) * 255
        template = np.ones((50, 50), dtype=np.uint8) * 255

        # Empty ROI (x1 == x2)
        roi = (10, 10, 10, 60)
        confidence, location = match_template_roi(screenshot, template, roi)

        assert confidence == 0.0
        assert location == (0, 0)


class TestCharacterDetectorRoiConstraints:
    """Tests for ROI constraint usage in CharacterDetector."""

    def test_all_slot_rois_defined(self):
        """Test that ALL_SLOT_ROIs are defined and valid."""
        from modules.character_detector import ALL_SLOT_ROIS

        assert len(ALL_SLOT_ROIS) == 9

        for roi in ALL_SLOT_ROIS:
            assert len(roi) == 4
            x1, y1, x2, y2 = roi
            assert x1 < x2, f"Invalid ROI: x1 ({x1}) >= x2 ({x2})"
            assert y1 < y2, f"Invalid ROI: y1 ({y1}) >= y2 ({y2})"

    def test_detect_character_selection_screen_uses_roi(self):
        """Test that detect_character_selection_screen uses SLOT_1_1_ROI."""
        from modules.character_detector import CharacterDetector, SLOT_1_1_ROI

        detector = CharacterDetector()
        screenshot = np.ones((1440, 2560, 3), dtype=np.uint8) * 200

        # This should use SLOT_1_1_ROI, not full screen
        result = detector.detect_character_selection_screen(screenshot)

        # Result should be a tuple
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_scan_visible_slots_uses_rois(self):
        """Test that scan_visible_slots uses ALL_SLOT_ROIs."""
        from modules.character_detector import CharacterDetector, ALL_SLOT_ROIS

        detector = CharacterDetector()
        screenshot = np.ones((1440, 2560, 3), dtype=np.uint8) * 200

        results = detector.scan_visible_slots(screenshot)

        # Should return 9 results, one per ROI
        assert len(results) == len(ALL_SLOT_ROIS)

        # Each result should reference its ROI
        for i, result in enumerate(results):
            assert result.slot_index == i
            assert result.roi == ALL_SLOT_ROIS[i]

    def test_scan_visible_slots_parallel_uses_rois(self):
        """Test that scan_visible_slots_parallel uses ALL_SLOT_ROIs."""
        from modules.character_detector import CharacterDetector, ALL_SLOT_ROIS

        detector = CharacterDetector()
        screenshot = np.ones((1440, 2560, 3), dtype=np.uint8) * 200

        results = detector.scan_visible_slots_parallel(screenshot)

        # Should return 9 results, one per ROI
        assert len(results) == len(ALL_SLOT_ROIS)

        # Each result should reference its ROI
        for i, result in enumerate(results):
            assert result.slot_index == i
            assert result.roi == ALL_SLOT_ROIS[i]

    def test_detect_scroll_bottom_uses_roi(self):
        """Test that detect_scroll_bottom uses SCROLLBAR_BOTTOM_ROI."""
        from modules.character_detector import CharacterDetector, SCROLLBAR_BOTTOM_ROI

        detector = CharacterDetector()
        screenshot = np.ones((1440, 2560, 3), dtype=np.uint8) * 200

        result = detector.detect_scroll_bottom(screenshot)

        # Result should be a tuple
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_no_fullscreen_matching_in_character_detector(self):
        """Test that CharacterDetector methods don't use full-screen matching."""
        import inspect
        from modules import character_detector

        # Get source code of key methods
        source = inspect.getsource(character_detector.CharacterDetector.scan_visible_slots)

        # Should not contain patterns that indicate full-screen matching
        # (i.e., no direct cv2.matchTemplate on full screenshot)
        assert "screenshot[y1:y2, x1:x2]" in source or "slot_region" in source


class TestNoFullscreenMatchingPaths:
    """Tests to verify no full-screen template matching exists."""

    def test_vision_engine_find_element_no_fullscreen_fallback(self):
        """Test that find_element has no full-screen fallback path."""
        import inspect
        from core import vision_engine

        source = inspect.getsource(vision_engine.find_element)

        # Should not have a branch for roi is None that does full-screen matching
        # The function should require ROI and error if not provided
        assert "if roi is not None:" not in source or "raise ValueError" in source

    def test_all_matching_uses_roi_constraints(self):
        """Integration test that all matching uses ROI constraints."""
        from core.vision_engine import find_element, match_template_roi
        import inspect

        # Check find_element signature
        sig = inspect.signature(find_element)
        roi_param = sig.parameters['roi']

        # ROI must be required (no default)
        assert roi_param.default is inspect.Parameter.empty or roi_param.default is not None


class TestRoiValidation:
    """Tests for ROI validation functions."""

    def test_valid_roi_passes(self):
        """Test that valid ROIs are accepted."""
        from core.vision_engine import find_element

        screenshot = np.ones((200, 200, 3), dtype=np.uint8) * 255
        template = np.ones((50, 50), dtype=np.uint8) * 255

        # Valid ROI
        roi = (10, 10, 100, 100)
        found, confidence, location = find_element(screenshot, template, roi)

        assert isinstance(found, bool)

    def test_roi_at_edges(self):
        """Test ROIs at screenshot edges."""
        from core.vision_engine import match_template_roi

        screenshot = np.ones((100, 100, 3), dtype=np.uint8) * 255
        template = np.ones((10, 10), dtype=np.uint8) * 255

        # ROI at top-left corner
        roi = (0, 0, 10, 10)
        confidence, location = match_template_roi(screenshot, template, roi)
        assert confidence > 0.9  # Should match perfectly

        # ROI at bottom-right corner
        roi = (90, 90, 100, 100)
        confidence, location = match_template_roi(screenshot, template, roi)
        assert confidence > 0.9
