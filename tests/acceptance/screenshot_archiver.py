"""
Screenshot Archiver Module

Manages screenshot capture and archiving for acceptance testing.
Provides auto-incrementing filenames with timestamps for organized
screenshot storage.
"""

import os
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.vision_engine import VisionEngine


class ScreenshotArchiver:
    """
    Manages screenshot capture and archiving.

    Features:
    - Auto-creates output directory if not exists
    - Auto-incrementing counter for filenames (01_, 02_, etc.)
    - Timestamp in filename (HHMMSS format)
    - Support for pre-captured frames (for efficiency)
    - PNG format with compression
    - Returns filename for logging
    """

    def __init__(
        self,
        output_dir: str = "test_artifacts/screenshots",
        vision_engine: Optional[VisionEngine] = None
    ):
        """
        Initialize the screenshot archiver.

        Args:
            output_dir: Directory to save screenshots (created if not exists)
            vision_engine: Optional VisionEngine instance for screen capture.
                          If not provided, a new one will be created.
        """
        self.output_dir = Path(output_dir)
        self._counter = 0
        self._vision_engine = vision_engine

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_next_counter(self) -> int:
        """Get the next counter value and increment."""
        self._counter += 1
        return self._counter

    def _generate_filename(self, description: str) -> str:
        """
        Generate a filename with counter, description, and timestamp.

        Format: {counter:02d}_{description}_{HHMMSS}.png
        Example: 01_env_check_143022.png

        Args:
            description: Description of the screenshot

        Returns:
            Generated filename string
        """
        counter = self._get_next_counter()
        timestamp = datetime.now().strftime("%H%M%S")
        # Sanitize description: replace spaces with underscores, remove special chars
        safe_description = "".join(
            c if c.isalnum() or c == "_" else "_"
            for c in description.replace(" ", "_")
        )
        return f"{counter:02d}_{safe_description}_{timestamp}.png"

    def _get_vision_engine(self) -> VisionEngine:
        """Get or create the VisionEngine instance."""
        if self._vision_engine is None:
            self._vision_engine = VisionEngine()
        return self._vision_engine

    def save_frame(
        self,
        frame: np.ndarray,
        description: str
    ) -> str:
        """
        Save an existing frame to the archive.

        Args:
            frame: Pre-captured frame as numpy array (BGR format)
            description: Description of the screenshot

        Returns:
            Full path to the saved file

        Raises:
            ValueError: If frame is None or empty
        """
        if frame is None:
            raise ValueError("Frame cannot be None")

        if frame.size == 0:
            raise ValueError("Frame cannot be empty")

        filename = self._generate_filename(description)
        filepath = self.output_dir / filename

        # Save with PNG compression (default compression level 3)
        # PNG is lossless and good for screenshots with text/UI elements
        success = cv2.imwrite(str(filepath), frame)

        if not success:
            raise RuntimeError(f"Failed to save screenshot to {filepath}")

        return str(filepath)

    def capture_and_save(
        self,
        description: str,
        frame: Optional[np.ndarray] = None
    ) -> str:
        """
        Capture screen and save to the archive.

        If a pre-captured frame is provided, it will be used directly
        for efficiency. Otherwise, a new screenshot will be captured.

        Args:
            description: Description of the screenshot
            frame: Optional pre-captured frame to use instead of capturing

        Returns:
            Full path to the saved file
        """
        if frame is not None:
            return self.save_frame(frame, description)

        # Capture fresh frame
        vision = self._get_vision_engine()
        captured_frame = vision.get_screenshot()

        return self.save_frame(captured_frame, description)

    def get_archive_info(self) -> dict:
        """
        Get information about the current archive state.

        Returns:
            Dictionary with archive information:
            - output_dir: Path to output directory
            - screenshot_count: Current counter value
            - existing_files: List of existing screenshot files
        """
        existing_files = [
            f.name for f in self.output_dir.iterdir()
            if f.is_file() and f.suffix.lower() == ".png"
        ]

        return {
            "output_dir": str(self.output_dir),
            "screenshot_count": self._counter,
            "existing_files": sorted(existing_files)
        }

    def reset_counter(self) -> None:
        """Reset the filename counter to zero."""
        self._counter = 0
