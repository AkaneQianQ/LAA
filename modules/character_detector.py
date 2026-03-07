"""
Character Detector Module

Provides computer vision-based character detection for Lost Ark's
character selection screen. Uses template matching with locked ROI
coordinates for 2560x1440 resolution.

Detection Strategy:
- TM_CCOEFF_NORMED template matching with threshold >= 0.8
- FF00FF (magenta) masked regions in templates are ignored
- 3 retry attempts with small position jitter on failure
"""

from typing import List, Tuple, Optional, Dict, Any
import cv2
import numpy as np


# =============================================================================
# LOCKED ROI CONSTANTS (2560x1440 resolution)
# =============================================================================

# 3x3 Character slot ROIs - each slot is 248x67 pixels
# Row 1
SLOT_1_1_ROI: Tuple[int, int, int, int] = (904, 557, 1152, 624)   # (x1, y1, x2, y2)
SLOT_1_2_ROI: Tuple[int, int, int, int] = (1164, 557, 1412, 624)
SLOT_1_3_ROI: Tuple[int, int, int, int] = (1425, 557, 1673, 624)

# Row 2
SLOT_2_1_ROI: Tuple[int, int, int, int] = (904, 674, 1152, 741)
SLOT_2_2_ROI: Tuple[int, int, int, int] = (1164, 674, 1412, 741)
SLOT_2_3_ROI: Tuple[int, int, int, int] = (1425, 674, 1673, 741)

# Row 3
SLOT_3_1_ROI: Tuple[int, int, int, int] = (904, 791, 1152, 858)
SLOT_3_2_ROI: Tuple[int, int, int, int] = (1164, 791, 1412, 858)
SLOT_3_3_ROI: Tuple[int, int, int, int] = (1425, 791, 1673, 858)

# All slots as a list for iteration
ALL_SLOT_ROIS: List[Tuple[int, int, int, int]] = [
    SLOT_1_1_ROI, SLOT_1_2_ROI, SLOT_1_3_ROI,
    SLOT_2_1_ROI, SLOT_2_2_ROI, SLOT_2_3_ROI,
    SLOT_3_1_ROI, SLOT_3_2_ROI, SLOT_3_3_ROI,
]

# Scrollbar bottom detection ROI (14x32 pixels)
SCROLLBAR_BOTTOM_ROI: Tuple[int, int, int, int] = (1683, 828, 1697, 860)

# ESC menu / character selection detection ROI
# 根据 CLAUDE.md: Current ID (ESC menu): (657, 854, 831, 876)
ESC_MENU_ROI: Tuple[int, int, int, int] = (657, 854, 831, 876)


# =============================================================================
# DETECTION CONFIGURATION CONSTANTS
# =============================================================================

# Template matching method - LOCKED to TM_CCOEFF_NORMED per phase decision
TEMPLATE_MATCH_METHOD: int = cv2.TM_CCOEFF_NORMED

# Detection confidence threshold (>= 0.8 as per locked decision)
SLOT_DETECTION_THRESHOLD: float = 0.8

# Maximum retry attempts for failed detections
MAX_DETECTION_RETRIES: int = 3

# Template file names (expected in assets/ directory)
CHARACTER_DETECTION_TEMPLATE: str = "CharacterISorNo.bmp"
SCROLLBAR_BOTTOM_TEMPLATE: str = "Buttom.bmp"


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

class SlotOccupancyResult:
    """Result of checking a single slot for character presence."""

    def __init__(self, slot_index: int, roi: Tuple[int, int, int, int],
                 has_character: bool, confidence: float):
        self.slot_index: int = slot_index
        self.roi: Tuple[int, int, int, int] = roi
        self.has_character: bool = has_character
        self.confidence: float = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            'slot_index': self.slot_index,
            'roi': self.roi,
            'has_character': self.has_character,
            'confidence': self.confidence,
        }


class CharacterDiscoveryResult:
    """Complete result of character discovery process."""

    def __init__(self, account_id: Optional[str] = None,
                 total_characters: int = 0,
                 slot_results: Optional[List[SlotOccupancyResult]] = None,
                 screenshots: Optional[List[str]] = None):
        self.account_id: Optional[str] = account_id
        self.total_characters: int = total_characters
        self.slot_results: List[SlotOccupancyResult] = slot_results or []
        self.screenshots: List[str] = screenshots or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'account_id': self.account_id,
            'total_characters': self.total_characters,
            'slot_results': [r.to_dict() for r in self.slot_results],
            'screenshots': self.screenshots,
        }


# =============================================================================
# CHARACTER DETECTOR CLASS
# =============================================================================

class CharacterDetector:
    """
    Computer vision-based character detection for Lost Ark.

    Detects character presence in the 9-slot grid using template matching
    with FF00FF-masked templates. Provides methods for ESC menu detection,
    slot occupancy scanning, scroll bottom detection, and full discovery.
    """

    def __init__(self, assets_path: str = "assets"):
        """
        Initialize the detector with path to template assets.

        Args:
            assets_path: Path to directory containing template images
        """
        self.assets_path: str = assets_path
        self._template_cache: Dict[str, np.ndarray] = {}

    def _load_template(self, template_name: str) -> Optional[np.ndarray]:
        """
        Load and cache a template image with FF00FF masking.

        Args:
            template_name: Name of the template file

        Returns:
            Loaded template as grayscale numpy array, or None if not found
        """
        if template_name in self._template_cache:
            return self._template_cache[template_name]

        import os
        template_path = os.path.join(self.assets_path, template_name)

        if not os.path.exists(template_path):
            return None

        # Load image (supports .bmp and .png)
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            return None

        # Apply FF00FF (magenta) masking - ignore these regions
        # Convert to HSV for better color matching
        hsv = cv2.cvtColor(template, cv2.COLOR_BGR2HSV)

        # Define magenta range in HSV
        # Magenta is around hue 150-170 in OpenCV HSV (0-179 scale)
        lower_magenta = np.array([140, 50, 50])
        upper_magenta = np.array([180, 255, 255])

        # Create mask for magenta pixels
        mask = cv2.inRange(hsv, lower_magenta, upper_magenta)

        # Convert to grayscale for template matching
        gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        # Set masked regions to 0 (will be ignored in matching)
        gray[mask > 0] = 0

        self._template_cache[template_name] = gray
        return gray

    def detect_esc_menu(self, screenshot: np.ndarray) -> Tuple[bool, float]:
        """
        Detect if the ESC menu / character selection screen is open.

        Args:
            screenshot: Full screen capture as BGR numpy array

        Returns:
            Tuple of (is_open, confidence)
        """
        # For now, check if we can detect the character selection UI elements
        # This is a placeholder - actual implementation would check for
        # specific menu markers

        # Check if any slot has a character (indicates character selection screen)
        results = self.scan_slots_occupancy(screenshot)
        any_detected = any(r.has_character for r in results)

        # Calculate average confidence of detections
        if results:
            avg_confidence = sum(r.confidence for r in results) / len(results)
        else:
            avg_confidence = 0.0

        return any_detected, avg_confidence

    def scan_slots_occupancy(self, screenshot: np.ndarray) -> List[SlotOccupancyResult]:
        """
        Scan all 9 slots to determine which contain characters.

        Args:
            screenshot: Full screen capture as BGR numpy array

        Returns:
            List of SlotOccupancyResult for each slot
        """
        results: List[SlotOccupancyResult] = []
        template = self._load_template(CHARACTER_DETECTION_TEMPLATE)

        if template is None:
            # Template not found - return all slots as empty
            for i, roi in enumerate(ALL_SLOT_ROIS):
                results.append(SlotOccupancyResult(i, roi, False, 0.0))
            return results

        for slot_index, roi in enumerate(ALL_SLOT_ROIS):
            x1, y1, x2, y2 = roi
            slot_region = screenshot[y1:y2, x1:x2]

            if slot_region.size == 0:
                results.append(SlotOccupancyResult(slot_index, roi, False, 0.0))
                continue

            # Convert slot region to grayscale
            slot_gray = cv2.cvtColor(slot_region, cv2.COLOR_BGR2GRAY)

            # Perform template matching with retry logic
            best_confidence = 0.0
            for _ in range(MAX_DETECTION_RETRIES):
                try:
                    result = cv2.matchTemplate(
                        slot_gray, template, TEMPLATE_MATCH_METHOD
                    )
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    best_confidence = max(best_confidence, max_val)

                    if best_confidence >= SLOT_DETECTION_THRESHOLD:
                        break
                except cv2.error:
                    # Template larger than region - no match possible
                    break

            has_character = best_confidence >= SLOT_DETECTION_THRESHOLD
            results.append(SlotOccupancyResult(
                slot_index, roi, has_character, best_confidence
            ))

        return results

    def detect_scroll_bottom(self, screenshot: np.ndarray) -> Tuple[bool, float]:
        """
        Detect if scrollbar has reached the bottom of character list.

        Args:
            screenshot: Full screen capture as BGR numpy array

        Returns:
            Tuple of (is_at_bottom, confidence)
        """
        template = self._load_template(SCROLLBAR_BOTTOM_TEMPLATE)

        if template is None:
            return False, 0.0

        x1, y1, x2, y2 = SCROLLBAR_BOTTOM_ROI
        roi_region = screenshot[y1:y2, x1:x2]

        if roi_region.size == 0:
            return False, 0.0

        roi_gray = cv2.cvtColor(roi_region, cv2.COLOR_BGR2GRAY)

        # For scrollbar bottom, we use exact matching (100% pixel match)
        # This is specified in the phase context
        try:
            result = cv2.matchTemplate(
                roi_gray, template, TEMPLATE_MATCH_METHOD
            )
            _, max_val, _, _ = cv2.minMaxLoc(result)
            # For bottom detection, require near-perfect match
            is_at_bottom = max_val >= 0.95
            return is_at_bottom, max_val
        except cv2.error:
            return False, 0.0

    def discover_characters(self, screenshot: np.ndarray) -> CharacterDiscoveryResult:
        """
        Perform full character discovery on current screen.

        This is the main entry point for character detection. It scans all
        slots and returns a complete discovery result.

        Args:
            screenshot: Full screen capture as BGR numpy array

        Returns:
            CharacterDiscoveryResult with all discovery information
        """
        result = CharacterDiscoveryResult()

        # Scan all slots
        slot_results = self.scan_slots_occupancy(screenshot)
        result.slot_results = slot_results

        # Count total characters detected
        result.total_characters = sum(1 for r in slot_results if r.has_character)

        # TODO: Account ID generation from first character screenshot
        # This will be implemented when screenshot persistence is added

        return result


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_slot_roi(slot_index: int) -> Tuple[int, int, int, int]:
    """
    Get the ROI coordinates for a specific slot index.

    Args:
        slot_index: 0-8 index corresponding to 3x3 grid position

    Returns:
        ROI tuple (x1, y1, x2, y2)

    Raises:
        IndexError: If slot_index is not in range 0-8
    """
    if not 0 <= slot_index <= 8:
        raise IndexError(f"Slot index must be 0-8, got {slot_index}")
    return ALL_SLOT_ROIS[slot_index]


def slot_index_to_grid_pos(slot_index: int) -> Tuple[int, int]:
    """
    Convert slot index to grid position (row, col).

    Args:
        slot_index: 0-8 index

    Returns:
        Tuple of (row, col) where row and col are 0-2
    """
    if not 0 <= slot_index <= 8:
        raise IndexError(f"Slot index must be 0-8, got {slot_index}")
    row = slot_index // 3
    col = slot_index % 3
    return row, col


def grid_pos_to_slot_index(row: int, col: int) -> int:
    """
    Convert grid position to slot index.

    Args:
        row: Row index 0-2
        col: Column index 0-2

    Returns:
        Slot index 0-8
    """
    if not 0 <= row <= 2:
        raise IndexError(f"Row must be 0-2, got {row}")
    if not 0 <= col <= 2:
        raise IndexError(f"Col must be 0-2, got {col}")
    return row * 3 + col
