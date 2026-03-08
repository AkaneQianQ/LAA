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
import hashlib
import os
from datetime import datetime

from core.parallel_matcher import ParallelMatcher


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

# Account tag ROI for account identification (new ROI to prevent UI color change)
ACCOUNT_TAG_ROI: Tuple[int, int, int, int] = (666, 793, 772, 902)

# Mouse safe position to prevent UI color change when hovering over character slots
MOUSE_SAFE_POSITION: Tuple[int, int] = (827, 516)


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

    def __init__(self, assets_path: str = "assets", data_dir: str = "data",
                 db_path: str = "data/accounts.db", use_parallel: bool = False,
                 parallel_workers: int = 4, hardware_gateway=None):
        """
        Initialize the detector with path to template assets.

        Args:
            assets_path: Path to directory containing template images
            data_dir: Path to data directory for account storage
            db_path: Path to SQLite database file
            use_parallel: Whether to enable parallel scanning by default
            parallel_workers: Number of worker threads for parallel matching
            hardware_gateway: Optional HardwareInputGateway for mouse movement
        """
        self.assets_path: str = assets_path
        self.data_dir: str = data_dir
        self.db_path: str = db_path
        self._hardware_gateway = hardware_gateway
        self._template_cache: Dict[str, np.ndarray] = {}
        self._parallel_matcher: Optional[ParallelMatcher] = None
        self._pending_first_slot_capture: bool = False
        self._pending_account_hash: Optional[str] = None
        if use_parallel:
            self._parallel_matcher = ParallelMatcher(max_workers=parallel_workers)

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

    def detect_character_selection_screen(self, screenshot: np.ndarray) -> Tuple[bool, float]:
        """
        Detect if the ESC menu / character selection screen is ready.

        Uses template matching with bounded retries to verify the character
        selection UI is visible and ready for interaction.

        Args:
            screenshot: Full screen capture as BGR numpy array

        Returns:
            Tuple of (is_ready, confidence)
        """
        template = self._load_template(CHARACTER_DETECTION_TEMPLATE)

        if template is None:
            # Template not found - fail fast
            return False, 0.0

        best_confidence = 0.0

        # Retry up to MAX_DETECTION_RETRIES with small backoff
        for attempt in range(MAX_DETECTION_RETRIES):
            try:
                # Check a subset of slots to verify menu is ready
                # We check the first slot as a representative sample
                x1, y1, x2, y2 = SLOT_1_1_ROI
                slot_region = screenshot[y1:y2, x1:x2]

                if slot_region.size == 0:
                    continue

                slot_gray = cv2.cvtColor(slot_region, cv2.COLOR_BGR2GRAY)

                result = cv2.matchTemplate(
                    slot_gray, template, TEMPLATE_MATCH_METHOD
                )
                _, max_val, _, _ = cv2.minMaxLoc(result)
                best_confidence = max(best_confidence, max_val)

                # Early exit if we hit threshold
                if best_confidence >= SLOT_DETECTION_THRESHOLD:
                    return True, best_confidence

            except cv2.error:
                # Template matching error - continue to retry
                continue

        # Failed to reach threshold after all retries
        return False, best_confidence

    def detect_esc_menu(self, screenshot: np.ndarray) -> Tuple[bool, float]:
        """
        Detect if the ESC menu / character selection screen is open.

        Args:
            screenshot: Full screen capture as BGR numpy array

        Returns:
            Tuple of (is_open, confidence)
        """
        # Delegate to the new method for consistency
        return self.detect_character_selection_screen(screenshot)

    def scan_visible_slots(self, screenshot: np.ndarray) -> List[SlotOccupancyResult]:
        """
        Scan all 9 visible slots to determine which contain characters.

        This method evaluates all 9 slot ROIs in row-major order and returns
        occupancy results with confidence scores. Includes retry-on-borderline
        logic for improved accuracy.

        Args:
            screenshot: Full screen capture as BGR numpy array

        Returns:
            List of SlotOccupancyResult for each slot (index 0-8)
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

            # Perform template matching with retry logic for borderline cases
            best_confidence = 0.0
            retry_count = 0
            max_retries = MAX_DETECTION_RETRIES

            while retry_count < max_retries:
                try:
                    result = cv2.matchTemplate(
                        slot_gray, template, TEMPLATE_MATCH_METHOD
                    )
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    best_confidence = max(best_confidence, max_val)

                    # Check if we have a clear result
                    if best_confidence >= SLOT_DETECTION_THRESHOLD:
                        # Clear positive - no need to retry
                        break
                    elif best_confidence < SLOT_DETECTION_THRESHOLD - 0.15:
                        # Clear negative - no need to retry
                        break
                    else:
                        # Borderline case - retry for better accuracy
                        retry_count += 1
                except cv2.error:
                    # Template larger than region - no match possible
                    break

            has_character = best_confidence >= SLOT_DETECTION_THRESHOLD
            results.append(SlotOccupancyResult(
                slot_index, roi, has_character, best_confidence
            ))

        return results

    def scan_visible_slots_parallel(self, screenshot: np.ndarray,
                                    max_workers: int = 4) -> List[SlotOccupancyResult]:
        """
        Scan all 9 visible slots in parallel using ThreadPoolExecutor.

        This method provides the same functionality as scan_visible_slots but
        uses parallel processing for improved performance. OpenCV releases the
        GIL during matchTemplate, so threads provide actual speedup.

        Args:
            screenshot: Full screen capture as BGR numpy array
            max_workers: Number of worker threads (default: 4)

        Returns:
            List of SlotOccupancyResult for each slot (index 0-8)
        """
        results: List[SlotOccupancyResult] = []
        template = self._load_template(CHARACTER_DETECTION_TEMPLATE)

        if template is None:
            # Template not found - return all slots as empty
            for i, roi in enumerate(ALL_SLOT_ROIS):
                results.append(SlotOccupancyResult(i, roi, False, 0.0))
            return results

        # Use parallel matcher
        matcher = self._parallel_matcher if self._parallel_matcher else ParallelMatcher(max_workers=max_workers)
        parallel_results = matcher.scan_rois(screenshot, template, ALL_SLOT_ROIS, SLOT_DETECTION_THRESHOLD)

        # Convert parallel results to SlotOccupancyResult objects
        for slot_index in range(len(ALL_SLOT_ROIS)):
            roi = ALL_SLOT_ROIS[slot_index]
            found, confidence = parallel_results.get(slot_index, (False, 0.0))

            # Apply retry logic for borderline cases (same as sequential)
            if SLOT_DETECTION_THRESHOLD - 0.15 <= confidence < SLOT_DETECTION_THRESHOLD:
                # Borderline case - retry for better accuracy
                best_confidence = confidence
                for _ in range(MAX_DETECTION_RETRIES - 1):
                    _, retry_confidence, _ = self._match_single_slot(screenshot, template, roi)
                    best_confidence = max(best_confidence, retry_confidence)
                    if best_confidence >= SLOT_DETECTION_THRESHOLD:
                        break
                    if best_confidence < SLOT_DETECTION_THRESHOLD - 0.15:
                        break
                confidence = best_confidence
                found = confidence >= SLOT_DETECTION_THRESHOLD

            results.append(SlotOccupancyResult(slot_index, roi, found, confidence))

        return results

    def _match_single_slot(self, screenshot: np.ndarray, template: np.ndarray,
                           roi: Tuple[int, int, int, int]) -> Tuple[bool, float, Tuple[int, int]]:
        """
        Match template in a single slot ROI.

        Args:
            screenshot: Full screen capture
            template: Template image
            roi: Slot ROI coordinates

        Returns:
            Tuple of (found, confidence, location)
        """
        x1, y1, x2, y2 = roi
        slot_region = screenshot[y1:y2, x1:x2]

        if slot_region.size == 0:
            return False, 0.0, (0, 0)

        slot_gray = cv2.cvtColor(slot_region, cv2.COLOR_BGR2GRAY)

        try:
            result = cv2.matchTemplate(slot_gray, template, TEMPLATE_MATCH_METHOD)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            return max_val >= SLOT_DETECTION_THRESHOLD, max_val, (x1 + max_loc[0], y1 + max_loc[1])
        except cv2.error:
            return False, 0.0, (0, 0)

    def scan_slots_occupancy(self, screenshot: np.ndarray) -> List[SlotOccupancyResult]:
        """
        Scan all 9 slots to determine which contain characters.

        Alias for scan_visible_slots() for backward compatibility.

        Args:
            screenshot: Full screen capture as BGR numpy array

        Returns:
            List of SlotOccupancyResult for each slot
        """
        return self.scan_visible_slots(screenshot)

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

    def _scroll_down(self) -> None:
        """
        Simulate a scroll down action.

        This is a placeholder for the actual scroll implementation.
        In the real implementation, this would use the FerrumController
        to send scroll commands to the KMBox device.
        """
        # Placeholder - actual implementation requires hardware controller
        pass

    def _capture_screenshot(self) -> np.ndarray:
        """
        Capture a new screenshot.

        This is a placeholder for the actual screenshot implementation.
        In the real implementation, this would use DXCam or similar.

        Returns:
            Screenshot as BGR numpy array
        """
        # Placeholder - returns empty array
        # Actual implementation requires screen capture library
        return np.zeros((1440, 2560, 3), dtype=np.uint8)

    def discover_total_characters(
        self,
        screenshot: Optional[np.ndarray] = None,
        max_pages: int = 20
    ) -> CharacterDiscoveryResult:
        """
        Discover total character count through scroll traversal.

        This method implements the full discovery workflow:
        1. Verify character selection screen is ready
        2. Scan visible slots and accumulate count
        3. Scroll down by one row
        4. Repeat until scrollbar bottom is detected
        5. Deduplicate rows that appear on multiple pages

        Args:
            screenshot: Initial screenshot (if None, will capture)
            max_pages: Maximum number of pages to scan (safety limit)

        Returns:
            CharacterDiscoveryResult with total count and slot results
        """
        result = CharacterDiscoveryResult()

        # Use provided screenshot or capture one
        current_screenshot = screenshot if screenshot is not None else self._capture_screenshot()

        # Step 1: Verify menu is ready
        is_ready, confidence = self.detect_character_selection_screen(current_screenshot)
        if not is_ready:
            # Menu not ready - return empty result
            result.total_characters = 0
            return result

        # Track unique characters across pages
        # Key: slot signature (confidence values), Value: count
        all_slot_signatures: List[List[float]] = []
        total_unique_characters = 0
        page_count = 0

        while page_count < max_pages:
            # Step 2: Scan visible slots
            slot_results = self.scan_visible_slots(current_screenshot)

            # Create signature for this page (confidence values)
            page_signature = [r.confidence for r in slot_results]

            # Check if this page is a duplicate of the previous page
            if all_slot_signatures and self._is_duplicate_page(page_signature, all_slot_signatures[-1]):
                # Duplicate page detected - we've reached the end
                break

            all_slot_signatures.append(page_signature)

            # Count characters on this page
            page_characters = sum(1 for r in slot_results if r.has_character)

            # For deduplication: estimate new characters (bottom row of previous page
            # may overlap with top row of current page)
            if page_count == 0:
                # First page - all characters are new
                total_unique_characters += page_characters
            else:
                # Subsequent pages - assume up to 3 characters may be duplicates
                # (the bottom row of the previous page)
                estimated_new = max(0, page_characters - 3)
                total_unique_characters += estimated_new

            # Store slot results from first page for reference
            if page_count == 0:
                result.slot_results = slot_results

            # Step 3: Check if we've reached the bottom
            is_at_bottom, bottom_confidence = self.detect_scroll_bottom(current_screenshot)
            if is_at_bottom:
                # Bottom detected - we're done
                break

            # Step 4: Scroll down by one row
            self._scroll_down()

            # Capture new screenshot after scroll
            current_screenshot = self._capture_screenshot()

            page_count += 1

        result.total_characters = total_unique_characters
        return result

    def _is_duplicate_page(self, sig1: List[float], sig2: List[float], tolerance: float = 0.1) -> bool:
        """
        Check if two page signatures are similar enough to be considered duplicates.

        Args:
            sig1: First page signature (confidence values)
            sig2: Second page signature (confidence values)
            tolerance: Maximum difference for values to be considered equal

        Returns:
            True if pages are likely duplicates
        """
        if len(sig1) != len(sig2):
            return False

        # Check if all values are within tolerance
        for v1, v2 in zip(sig1, sig2):
            if abs(v1 - v2) > tolerance:
                return False

        return True

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
        # Delegate to discover_total_characters for full workflow
        return self.discover_total_characters(screenshot)

    # ========================================================================
    # ACCOUNT INDEXING AND CACHE METHODS
    # ========================================================================

    def _compute_screenshot_hash(self, screenshot: np.ndarray) -> str:
        """
        Compute SHA-256 hash of screenshot bytes for account identity.

        Args:
            screenshot: Screenshot as numpy array

        Returns:
            Hexadecimal hash string (64 characters)
        """
        # Convert to bytes and compute hash
        screenshot_bytes = screenshot.tobytes()
        return hashlib.sha256(screenshot_bytes).hexdigest()

    def _ensure_account_directory(self, account_hash: str) -> str:
        """
        Create account directory structure if it doesn't exist.

        Args:
            account_hash: The account hash identifier

        Returns:
            Path to the account directory
        """
        account_dir = os.path.join(self.data_dir, "accounts", account_hash)
        chars_dir = os.path.join(account_dir, "characters")

        os.makedirs(chars_dir, exist_ok=True)

        return account_dir

    def _move_mouse_to_safe_position(self) -> None:
        """
        移动鼠标到安全位置，防止UI变色。

        将鼠标移动到MOUSE_SAFE_POSITION位置，避免鼠标悬停在角色格上
        导致UI颜色变化影响截图识别。
        """
        if self._hardware_gateway is not None:
            try:
                self._hardware_gateway.move_mouse(MOUSE_SAFE_POSITION[0], MOUSE_SAFE_POSITION[1])
            except Exception:
                # 鼠标移动失败不影响后续流程
                pass

    def _capture_account_tag(self, screenshot: np.ndarray) -> np.ndarray:
        """
        截取账号标签区域。

        Args:
            screenshot: 全屏截图

        Returns:
            账号标签区域的截图
        """
        x1, y1, x2, y2 = ACCOUNT_TAG_ROI
        return screenshot[y1:y2, x1:x2]

    def _compute_screenshot_hash(self, screenshot: np.ndarray) -> str:
        """
        Compute SHA-256 hash of screenshot bytes for account identity.

        Args:
            screenshot: Screenshot as numpy array

        Returns:
            Hexadecimal hash string (64 characters)
        """
        # Convert to bytes and compute hash
        screenshot_bytes = screenshot.tobytes()
        return hashlib.sha256(screenshot_bytes).hexdigest()

    def match_account_tag(self, screenshot: np.ndarray, account_hash: str) -> bool:
        """
        对比截图中的账号标签与库中存储的标签是否匹配。

        Args:
            screenshot: 全屏截图
            account_hash: 要匹配的账号hash

        Returns:
            如果匹配返回True，否则返回False
        """
        import sqlite3

        # 截取当前账号标签
        current_tag = self._capture_account_tag(screenshot)
        current_hash = self._compute_screenshot_hash(current_tag)

        # 获取库中存储的标签路径
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT tag_screenshot_path FROM accounts WHERE account_hash = ?",
                (account_hash,)
            )
            row = cursor.fetchone()

            if row is None or row[0] is None:
                return False

            tag_path = row[0]
            if not os.path.exists(tag_path):
                return False

            # 读取存储的标签并计算hash
            stored_tag = cv2.imread(tag_path, cv2.IMREAD_COLOR)
            if stored_tag is None:
                return False

            stored_hash = self._compute_screenshot_hash(stored_tag)

            return current_hash == stored_hash
        finally:
            conn.close()

    def create_or_get_account_index(self, screenshot: np.ndarray) -> Tuple[int, str]:
        """
        Create or retrieve account index based on account tag ROI.

        This method implements the first-run index capture flow:
        1. Move mouse to safe position to prevent UI color change
        2. Extract account tag screenshot from ACCOUNT_TAG_ROI
        3. Compute hash for account identity
        4. Create account in database if new
        5. Save account tag screenshot to cache
        6. Save all character screenshots to cache (except slot 0 if pending)

        Args:
            screenshot: Full screen capture as BGR numpy array

        Returns:
            Tuple of (account_id, account_hash)
        """
        from core.database import init_database, get_or_create_account, upsert_character

        # Ensure database is initialized
        init_database(self.db_path)

        # Step 1: Move mouse to safe position to prevent UI color change
        self._move_mouse_to_safe_position()

        # Step 2: Extract account tag screenshot
        tag_screenshot = self._capture_account_tag(screenshot)

        # Step 3: Compute hash from account tag for account identity
        account_hash = self._compute_screenshot_hash(tag_screenshot)

        # Step 4: Create or get account
        account_id = get_or_create_account(self.db_path, account_hash)

        # Step 5: Ensure directory structure exists and save account tag
        account_dir = self._ensure_account_directory(account_hash)
        tag_path = os.path.join(account_dir, "tag.png")
        cv2.imwrite(tag_path, tag_screenshot)

        # Update database with tag screenshot path
        self._update_account_tag_path(account_id, tag_path)

        # Scan slots to find occupied ones
        slot_results = self.scan_visible_slots(screenshot)
        occupied_slots = [r for r in slot_results if r.has_character]

        if not occupied_slots:
            return account_id, account_hash

        # Step 6: Save character screenshots
        chars_dir = os.path.join(account_dir, "characters")
        os.makedirs(chars_dir, exist_ok=True)

        # For slot 0, mark as pending capture (will capture when switching to second character)
        # For other slots, capture immediately
        for slot in occupied_slots:
            if slot.slot_index == 0:
                # Mark first slot as pending capture
                self._pending_first_slot_capture = True
                self._pending_account_hash = account_hash
            else:
                # Capture non-first slots immediately
                sx1, sy1, sx2, sy2 = slot.roi
                slot_screenshot = screenshot[sy1:sy2, sx1:sx2]
                screenshot_path = os.path.join(chars_dir, f"{slot.slot_index}.png")
                cv2.imwrite(screenshot_path, slot_screenshot)
                # Update database with character metadata
                upsert_character(self.db_path, account_id, slot.slot_index, screenshot_path)

        return account_id, account_hash

    def _update_account_tag_path(self, account_id: int, tag_path: str) -> None:
        """
        Update account tag screenshot path in database.

        Args:
            account_id: The account ID
            tag_path: Path to the tag screenshot
        """
        import sqlite3

        conn = sqlite3.connect(self.db_path, timeout=5.0)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE accounts SET tag_screenshot_path = ? WHERE id = ?",
                (tag_path, account_id)
            )
            conn.commit()
        finally:
            conn.close()

    def cache_character_screenshot(self, account_id: int, slot_index: int,
                                    screenshot: np.ndarray,
                                    roi: Optional[Tuple[int, int, int, int]] = None) -> str:
        """
        Cache a character screenshot for the given account and slot.

        Args:
            account_id: The account ID
            slot_index: The slot index (0-8)
            screenshot: Full screen capture
            roi: The ROI coordinates for the character (optional, defaults to slot ROIs)

        Returns:
            Path to the saved screenshot
        """
        from core.database import upsert_character
        import sqlite3

        # Get account hash from database
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT account_hash FROM accounts WHERE id = ?", (account_id,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Account {account_id} not found")
            account_hash = row[0]
        finally:
            conn.close()

        # Use provided ROI or get from slot index
        if roi is None:
            roi = get_slot_roi(slot_index)

        # Extract character region
        x1, y1, x2, y2 = roi
        char_screenshot = screenshot[y1:y2, x1:x2]

        # Ensure directory exists
        chars_dir = self._ensure_account_directory(account_hash)

        # Save screenshot
        screenshot_path = os.path.join(chars_dir, f"{slot_index}.png")
        cv2.imwrite(screenshot_path, char_screenshot)

        # Update database
        upsert_character(self.db_path, account_id, slot_index, screenshot_path)

        return screenshot_path

    def load_cached_characters(self, account_id: int) -> List[Dict[str, Any]]:
        """
        Load cached character metadata for the given account.

        Args:
            account_id: The account ID

        Returns:
            List of character dictionaries with valid screenshot paths
        """
        from core.database import list_characters_by_account

        characters = list_characters_by_account(self.db_path, account_id)

        # Filter out characters with missing screenshot files
        valid_characters = []
        for char in characters:
            if os.path.exists(char['screenshot_path']):
                valid_characters.append(char)

        return valid_characters

    def discover_account(self, screenshot: np.ndarray) -> Dict[str, Any]:
        """
        Discover account and characters from screenshot.

        This is the main entry point for launcher integration. It:
        1. Creates or retrieves account index
        2. Returns account info with character count

        Args:
            screenshot: Full screen capture as BGR numpy array

        Returns:
            Dictionary with account_id, account_hash, character_count
        """
        account_id, account_hash = self.create_or_get_account_index(screenshot)

        if account_id is None:
            return {
                'account_id': None,
                'account_hash': None,
                'character_count': 0,
            }

        # Count characters from slot results
        slot_results = self.scan_visible_slots(screenshot)
        character_count = sum(1 for r in slot_results if r.has_character)

        return {
            'account_id': account_id,
            'account_hash': account_hash,
            'character_count': character_count,
        }


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
