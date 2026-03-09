"""
Vision Engine Module

Provides low-level computer vision primitives for screen capture,
template matching, and image processing.

This module serves as the foundation for higher-level detection
logic in modules/character_detector.py.
"""

from typing import Tuple, Optional, List, Dict, Any
import cv2
import numpy as np

from core.frame_cache import FrameCache


def match_template_roi(
    screenshot: np.ndarray,
    template: np.ndarray,
    roi: Tuple[int, int, int, int],
    method: int = cv2.TM_CCOEFF_NORMED
) -> Tuple[float, Tuple[int, int]]:
    """
    Perform template matching within a specific ROI.

    Args:
        screenshot: Full screen capture as BGR numpy array
        template: Template image as grayscale numpy array
        roi: Region of interest (x1, y1, x2, y2)
        method: OpenCV template matching method (default: TM_CCOEFF_NORMED)

    Returns:
        Tuple of (confidence, (match_x, match_y))
    """
    x1, y1, x2, y2 = roi
    roi_region = screenshot[y1:y2, x1:x2]

    if roi_region.size == 0:
        return 0.0, (0, 0)

    # Convert ROI to grayscale if needed
    if len(roi_region.shape) == 3:
        roi_gray = cv2.cvtColor(roi_region, cv2.COLOR_BGR2GRAY)
    else:
        roi_gray = roi_region

    try:
        result = cv2.matchTemplate(roi_gray, template, method)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        return max_val, (x1 + max_loc[0], y1 + max_loc[1])
    except cv2.error:
        return 0.0, (0, 0)


def _validate_roi(roi: Tuple[int, int, int, int]) -> None:
    """
    Validate ROI tuple.

    Args:
        roi: Region of interest (x1, y1, x2, y2)

    Raises:
        ValueError: If ROI is invalid
    """
    if roi is None:
        raise ValueError("ROI is required for template matching (SPEED-02 compliance)")

    if len(roi) != 4:
        raise ValueError(f"ROI must be a 4-tuple (x1, y1, x2, y2), got {len(roi)} elements")

    x1, y1, x2, y2 = roi

    if x1 >= x2:
        raise ValueError(f"Invalid ROI: x1 ({x1}) must be less than x2 ({x2})")

    if y1 >= y2:
        raise ValueError(f"Invalid ROI: y1 ({y1}) must be less than y2 ({y2})")


def find_element(
    screenshot: np.ndarray,
    template: np.ndarray,
    roi: Tuple[int, int, int, int],
    threshold: float = 0.8,
    method: int = cv2.TM_CCOEFF_NORMED
) -> Tuple[bool, float, Tuple[int, int]]:
    """
    Find an element in the screenshot using template matching.

    SPEED-02: ROI constraint enforcement - full-screen matching is prohibited.

    Args:
        screenshot: Full screen capture as BGR numpy array
        template: Template image as grayscale numpy array
        roi: Required region of interest (x1, y1, x2, y2)
        threshold: Minimum confidence threshold for match
        method: OpenCV template matching method

    Returns:
        Tuple of (found, confidence, (x, y))

    Raises:
        ValueError: If ROI is None or invalid
    """
    _validate_roi(roi)
    confidence, location = match_template_roi(screenshot, template, roi, method)
    found = confidence >= threshold
    return found, confidence, location


def apply_ff00ff_mask(image: np.ndarray) -> np.ndarray:
    """
    Apply FF00FF (magenta) masking to an image.

    Magenta regions (used as transparent markers in templates) are
    set to black (0) so they don't affect template matching.

    Args:
        image: Input image as BGR numpy array

    Returns:
        Grayscale image with masked regions set to 0
    """
    # Convert to HSV for better color matching
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Define magenta range in HSV
    # Magenta is around hue 150-170 in OpenCV HSV (0-179 scale)
    lower_magenta = np.array([140, 50, 50])
    upper_magenta = np.array([180, 255, 255])

    # Create mask for magenta pixels
    mask = cv2.inRange(hsv, lower_magenta, upper_magenta)

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Set masked regions to 0
    gray[mask > 0] = 0

    return gray


def load_template_with_mask(path: str) -> Optional[np.ndarray]:
    """
    Load a template image and apply FF00FF masking.

    Args:
        path: Path to template image file

    Returns:
        Masked grayscale template, or None if loading failed
    """
    import os

    if not os.path.exists(path):
        return None

    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        return None

    return apply_ff00ff_mask(image)


class VisionEngine:
    """
    High-level vision engine for screen analysis.

    Provides template matching, ROI-based detection, and image
    processing primitives used by automation workflows.

    Supports optional frame caching to reduce screen capture overhead.
    """

    def __init__(self, frame_cache: Optional[FrameCache] = None):
        """
        Initialize the vision engine.

        Args:
            frame_cache: Optional FrameCache for screenshot caching.
                        If provided, get_screenshot() will use caching.
        """
        self._template_cache: dict = {}
        self._frame_cache: Optional[FrameCache] = frame_cache
        self._dxcam = None  # Lazy-loaded DXCam instance

    def find_element(
        self,
        screenshot: np.ndarray,
        template_path: str,
        roi: Tuple[int, int, int, int],
        threshold: float = 0.8
    ) -> Tuple[bool, float, Tuple[int, int]]:
        """
        Find an element by template path.

        SPEED-02: ROI is required - full-screen matching is prohibited.

        Args:
            screenshot: Full screen capture
            template_path: Path to template image
            roi: Required region of interest (x1, y1, x2, y2)
            threshold: Minimum confidence threshold

        Returns:
            Tuple of (found, confidence, (x, y))

        Raises:
            ValueError: If ROI is None or invalid
        """
        _validate_roi(roi)

        # Check cache
        if template_path not in self._template_cache:
            template = load_template_with_mask(template_path)
            if template is None:
                return False, 0.0, (0, 0)
            self._template_cache[template_path] = template

        template = self._template_cache[template_path]
        confidence, location = match_template_roi(screenshot, template, roi)
        found = confidence >= threshold
        return found, confidence, location

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._template_cache.clear()

    def _capture_screen(self) -> np.ndarray:
        """
        Capture screen using DXCam.

        Returns:
            BGR numpy array of the screen capture
        """
        if self._dxcam is None:
            import dxcam
            self._dxcam = dxcam.create()

        frame = self._dxcam.grab()
        if frame is None:
            # Return empty frame if capture fails
            return np.zeros((1440, 2560, 3), dtype=np.uint8)

        # DXCam returns RGB, convert to BGR for OpenCV compatibility
        if len(frame.shape) == 3:
            return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame

    def get_screenshot(self, force_fresh: bool = False) -> np.ndarray:
        """
        Get a screenshot, using cache if available.

        Args:
            force_fresh: If True, bypass cache and capture fresh frame

        Returns:
            BGR numpy array of the screen capture
        """
        # Check cache first (if not forcing fresh and cache exists)
        if not force_fresh and self._frame_cache is not None:
            cached = self._frame_cache.get()
            if cached is not None:
                return cached

        # Capture fresh frame
        frame = self._capture_screen()

        # Store in cache if available
        if self._frame_cache is not None:
            self._frame_cache.set(frame)

        return frame

    def invalidate_cache(self) -> None:
        """
        Invalidate the frame cache.

        Forces the next get_screenshot() call to capture a fresh frame.
        No-op if no frame cache is configured.
        """
        if self._frame_cache is not None:
            self._frame_cache.invalidate()

    @property
    def cache_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get cache statistics if frame cache is configured.

        Returns:
            Dictionary with cache statistics, or None if no cache
        """
        if self._frame_cache is not None:
            return self._frame_cache.cache_stats
        return None
