"""
Tests for ScreenshotArchiver module.

Validates screenshot capture, archiving, and filename generation.
"""

import os
import cv2
import pytest
import numpy as np
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from tests.acceptance.screenshot_archiver import ScreenshotArchiver


class TestScreenshotArchiverInit:
    """Tests for ScreenshotArchiver initialization."""

    def test_creates_output_directory(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        output_dir = tmp_path / "new_screenshots"
        assert not output_dir.exists()

        archiver = ScreenshotArchiver(output_dir=str(output_dir))

        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_uses_existing_directory(self, tmp_path):
        """Test that existing directory is used without error."""
        output_dir = tmp_path / "existing_screenshots"
        output_dir.mkdir()

        archiver = ScreenshotArchiver(output_dir=str(output_dir))

        assert archiver.output_dir == output_dir

    def test_default_output_dir(self):
        """Test default output directory is 'test_artifacts/screenshots'."""
        with patch.object(Path, 'mkdir'):
            archiver = ScreenshotArchiver()
            assert archiver.output_dir == Path("test_artifacts/screenshots")

    def test_counter_starts_at_zero(self, tmp_path):
        """Test that counter starts at zero."""
        archiver = ScreenshotArchiver(output_dir=str(tmp_path))
        assert archiver._counter == 0


class TestFilenameGeneration:
    """Tests for filename generation."""

    def test_filename_format(self, tmp_path):
        """Test filename follows format: {counter:02d}_{description}_{HHMMSS}.png"""
        archiver = ScreenshotArchiver(output_dir=str(tmp_path))

        with patch('tests.acceptance.screenshot_archiver.datetime') as mock_dt:
            mock_now = Mock()
            mock_now.strftime.return_value = "143022"
            mock_dt.now.return_value = mock_now

            filename = archiver._generate_filename("env_check")

        assert filename == "01_env_check_143022.png"

    def test_counter_increments(self, tmp_path):
        """Test counter auto-increments with each filename."""
        archiver = ScreenshotArchiver(output_dir=str(tmp_path))

        with patch('tests.acceptance.screenshot_archiver.datetime') as mock_dt:
            mock_now = Mock()
            mock_now.strftime.return_value = "143022"
            mock_dt.now.return_value = mock_now

            filename1 = archiver._generate_filename("first")
            filename2 = archiver._generate_filename("second")
            filename3 = archiver._generate_filename("third")

        assert filename1.startswith("01_")
        assert filename2.startswith("02_")
        assert filename3.startswith("03_")

    def test_description_sanitization(self, tmp_path):
        """Test description is sanitized (spaces to underscores)."""
        archiver = ScreenshotArchiver(output_dir=str(tmp_path))

        with patch('tests.acceptance.screenshot_archiver.datetime') as mock_dt:
            mock_now = Mock()
            mock_now.strftime.return_value = "143022"
            mock_dt.now.return_value = mock_now

            filename = archiver._generate_filename("env check test")

        assert "env_check_test" in filename

    def test_special_chars_removed(self, tmp_path):
        """Test special characters are replaced with underscores."""
        archiver = ScreenshotArchiver(output_dir=str(tmp_path))

        with patch('tests.acceptance.screenshot_archiver.datetime') as mock_dt:
            mock_now = Mock()
            mock_now.strftime.return_value = "143022"
            mock_dt.now.return_value = mock_now

            filename = archiver._generate_filename("test@file#name!")

        assert "test_file_name_" in filename


class TestSaveFrame:
    """Tests for save_frame method."""

    def test_save_valid_frame(self, tmp_path):
        """Test saving a valid frame creates PNG file."""
        archiver = ScreenshotArchiver(output_dir=str(tmp_path))

        # Create a test frame (BGR format, 100x100 red square)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[:, :] = [0, 0, 255]  # Red in BGR

        with patch('tests.acceptance.screenshot_archiver.datetime') as mock_dt:
            mock_now = Mock()
            mock_now.strftime.return_value = "143022"
            mock_dt.now.return_value = mock_now

            filepath = archiver.save_frame(frame, "test_screenshot")

        assert os.path.exists(filepath)
        assert filepath.endswith(".png")
        assert "01_test_screenshot_143022.png" in filepath

    def test_returns_full_path(self, tmp_path):
        """Test save_frame returns full path to saved file."""
        archiver = ScreenshotArchiver(output_dir=str(tmp_path))
        frame = np.zeros((10, 10, 3), dtype=np.uint8)

        with patch('tests.acceptance.screenshot_archiver.datetime') as mock_dt:
            mock_now = Mock()
            mock_now.strftime.return_value = "143022"
            mock_dt.now.return_value = mock_now

            filepath = archiver.save_frame(frame, "test")

        assert str(tmp_path) in filepath
        assert os.path.isabs(filepath) or str(tmp_path) in filepath

    def test_raises_on_none_frame(self, tmp_path):
        """Test save_frame raises ValueError for None frame."""
        archiver = ScreenshotArchiver(output_dir=str(tmp_path))

        with pytest.raises(ValueError, match="Frame cannot be None"):
            archiver.save_frame(None, "test")

    def test_raises_on_empty_frame(self, tmp_path):
        """Test save_frame raises ValueError for empty frame."""
        archiver = ScreenshotArchiver(output_dir=str(tmp_path))

        with pytest.raises(ValueError, match="Frame cannot be empty"):
            archiver.save_frame(np.array([]), "test")

    def test_png_compression_used(self, tmp_path):
        """Test that PNG format is used for saving."""
        archiver = ScreenshotArchiver(output_dir=str(tmp_path))
        frame = np.zeros((10, 10, 3), dtype=np.uint8)

        with patch('cv2.imwrite') as mock_imwrite:
            mock_imwrite.return_value = True
            archiver.save_frame(frame, "test")

            mock_imwrite.assert_called_once()
            args = mock_imwrite.call_args[0]
            assert args[0].endswith(".png")


class TestCaptureAndSave:
    """Tests for capture_and_save method."""

    def test_uses_provided_frame(self, tmp_path):
        """Test that provided frame is used directly without capture."""
        archiver = ScreenshotArchiver(output_dir=str(tmp_path))
        frame = np.zeros((10, 10, 3), dtype=np.uint8)

        with patch.object(archiver, '_get_vision_engine') as mock_get_engine:
            with patch('tests.acceptance.screenshot_archiver.datetime') as mock_dt:
                mock_now = Mock()
                mock_now.strftime.return_value = "143022"
                mock_dt.now.return_value = mock_now

                filepath = archiver.capture_and_save("test", frame=frame)

        # Vision engine should not be called when frame is provided
        mock_get_engine.assert_not_called()
        assert os.path.exists(filepath)

    def test_captures_when_no_frame_provided(self, tmp_path):
        """Test that screen is captured when no frame provided."""
        mock_vision = Mock()
        mock_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        mock_vision.get_screenshot.return_value = mock_frame

        archiver = ScreenshotArchiver(
            output_dir=str(tmp_path),
            vision_engine=mock_vision
        )

        with patch('tests.acceptance.screenshot_archiver.datetime') as mock_dt:
            mock_now = Mock()
            mock_now.strftime.return_value = "143022"
            mock_dt.now.return_value = mock_now

            filepath = archiver.capture_and_save("test")

        mock_vision.get_screenshot.assert_called_once()
        assert os.path.exists(filepath)

    def test_creates_vision_engine_if_needed(self, tmp_path):
        """Test that VisionEngine is created if not provided."""
        archiver = ScreenshotArchiver(output_dir=str(tmp_path))

        with patch('tests.acceptance.screenshot_archiver.VisionEngine') as MockVision:
            mock_instance = Mock()
            mock_instance.get_screenshot.return_value = np.zeros((10, 10, 3), dtype=np.uint8)
            MockVision.return_value = mock_instance

            with patch('tests.acceptance.screenshot_archiver.datetime') as mock_dt:
                mock_now = Mock()
                mock_now.strftime.return_value = "143022"
                mock_dt.now.return_value = mock_now

                archiver.capture_and_save("test")

            MockVision.assert_called_once()


class TestArchiveInfo:
    """Tests for get_archive_info method."""

    def test_returns_archive_info(self, tmp_path):
        """Test get_archive_info returns correct structure."""
        archiver = ScreenshotArchiver(output_dir=str(tmp_path))

        # Save a couple of frames
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        archiver.save_frame(frame, "test1")
        archiver.save_frame(frame, "test2")

        info = archiver.get_archive_info()

        assert "output_dir" in info
        assert "screenshot_count" in info
        assert "existing_files" in info
        assert info["screenshot_count"] == 2
        assert len(info["existing_files"]) == 2

    def test_lists_only_png_files(self, tmp_path):
        """Test that only PNG files are listed in existing_files."""
        archiver = ScreenshotArchiver(output_dir=str(tmp_path))

        # Create a non-PNG file
        (tmp_path / "readme.txt").write_text("test")

        # Create a PNG file via archiver
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        archiver.save_frame(frame, "test")

        info = archiver.get_archive_info()

        assert all(f.endswith(".png") for f in info["existing_files"])
        assert "readme.txt" not in info["existing_files"]


class TestResetCounter:
    """Tests for reset_counter method."""

    def test_resets_counter_to_zero(self, tmp_path):
        """Test reset_counter sets counter back to zero."""
        archiver = ScreenshotArchiver(output_dir=str(tmp_path))

        # Generate some filenames to increment counter
        with patch('tests.acceptance.screenshot_archiver.datetime') as mock_dt:
            mock_now = Mock()
            mock_now.strftime.return_value = "143022"
            mock_dt.now.return_value = mock_now

            archiver._generate_filename("test1")
            archiver._generate_filename("test2")
            assert archiver._counter == 2

            archiver.reset_counter()
            assert archiver._counter == 0

            # Next filename should start at 01 again
            filename = archiver._generate_filename("test3")
            assert filename.startswith("01_")


class TestIntegration:
    """Integration tests for ScreenshotArchiver."""

    def test_full_workflow(self, tmp_path):
        """Test complete workflow from capture to archive info."""
        mock_vision = Mock()
        mock_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_frame[:, :] = [255, 0, 0]  # Blue in BGR
        mock_vision.get_screenshot.return_value = mock_frame

        archiver = ScreenshotArchiver(
            output_dir=str(tmp_path),
            vision_engine=mock_vision
        )

        # Capture and save multiple screenshots
        with patch('tests.acceptance.screenshot_archiver.datetime') as mock_dt:
            mock_now = Mock()
            mock_now.strftime.return_value = "143022"
            mock_dt.now.return_value = mock_now

            path1 = archiver.capture_and_save("env_check")
            path2 = archiver.capture_and_save("character_select")
            path3 = archiver.capture_and_save("donation_complete")

        # Verify files exist
        assert os.path.exists(path1)
        assert os.path.exists(path2)
        assert os.path.exists(path3)

        # Verify naming
        assert "01_env_check_143022.png" in path1
        assert "02_character_select_143022.png" in path2
        assert "03_donation_complete_143022.png" in path3

        # Verify archive info
        info = archiver.get_archive_info()
        assert info["screenshot_count"] == 3
        assert len(info["existing_files"]) == 3

        # Verify PNG files can be loaded
        for filepath in [path1, path2, path3]:
            loaded = cv2.imread(filepath)
            assert loaded is not None
            assert loaded.shape == (100, 100, 3)
