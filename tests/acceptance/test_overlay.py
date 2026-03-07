"""
Tests for the overlay window component.

These tests verify the basic functionality of the OverlayWindow class
used in acceptance testing.
"""

import pytest
import tkinter as tk
import time
import threading

from tests.acceptance.overlay import OverlayWindow, create_overlay


class TestOverlayWindowCreation:
    """Tests for overlay window creation and basic properties."""

    @pytest.fixture(autouse=True)
    def cleanup_tk(self):
        """Ensure Tkinter is cleaned up between tests."""
        yield
        # Clean up any remaining Tk instances
        try:
            for widget in tk._default_root.winfo_children():
                widget.destroy()
        except (AttributeError, tk.TclError):
            pass

    def test_overlay_window_creation(self):
        """Test that overlay window can be created successfully."""
        overlay = OverlayWindow()

        # Verify window exists
        assert overlay.root is not None
        assert overlay.is_open()

        # Clean up
        overlay.close()
        assert not overlay.is_open()

    def test_overlay_position_and_size(self):
        """Test that overlay window has correct position and size."""
        overlay = OverlayWindow()
        overlay.update()  # Force geometry update

        # Get actual geometry
        geometry = overlay.root.geometry()
        # Parse geometry string (format: "300x220+20+20")
        size_pos = geometry.split('+')
        size = size_pos[0].split('x')
        width = int(size[0])
        height = int(size[1])
        x = int(size_pos[1])
        y = int(size_pos[2])

        # Verify size (300x220)
        assert width == 300
        assert height == 220

        # Verify position (20, 20) - allow small tolerance for window manager
        assert abs(x - 20) <= 10
        assert abs(y - 20) <= 10

        # Clean up
        overlay.close()

    def test_overlay_window_properties(self):
        """Test that overlay window has correct properties."""
        overlay = OverlayWindow()

        # Check window is topmost
        assert overlay.root.attributes('-topmost') == 1

        # Check opacity (alpha)
        assert overlay.root.attributes('-alpha') == 0.75

        # Check no window decorations (overrideredirect)
        # Note: This returns 1 on Windows when overrideredirect is True
        # But the attribute might not be directly queryable

        # Clean up
        overlay.close()

    def test_create_overlay_convenience_function(self):
        """Test the create_overlay convenience function."""
        overlay = create_overlay()

        assert overlay is not None
        assert isinstance(overlay, OverlayWindow)
        assert overlay.is_open()

        # Clean up
        overlay.close()


class TestOverlayWindowMethods:
    """Tests for overlay window methods."""

    def test_update_phase(self):
        """Test updating phase information."""
        overlay = OverlayWindow()

        # Update phase
        overlay.update_phase(3, 5, "测试阶段")

        # Verify internal state
        assert overlay._current_phase_num == 3
        assert overlay._total_phases == 5
        assert overlay._phase_name == "测试阶段"

        # Clean up
        overlay.close()

    def test_update_status(self):
        """Test updating status with different types."""
        overlay = OverlayWindow()

        # Test different status types
        status_types = ['info', 'success', 'warning', 'error', 'waiting']

        for status_type in status_types:
            overlay.update_status(f"Test {status_type}", status_type)
            # Process UI updates
            overlay.update()

        # Clean up
        overlay.close()

    def test_add_log(self):
        """Test adding log messages."""
        overlay = OverlayWindow()

        # Add some logs
        overlay.add_log("First log message")
        overlay.add_log("Second log message")
        overlay.add_log("Third log message")

        # Wait for queue processing
        time.sleep(0.2)
        overlay.update()

        # Verify logs are stored (max 3)
        assert len(overlay._logs) == 3
        assert overlay._logs[0] == "First log message"
        assert overlay._logs[1] == "Second log message"
        assert overlay._logs[2] == "Third log message"

        # Clean up
        overlay.close()

    def test_add_log_max_limit(self):
        """Test that only last 3 logs are kept."""
        overlay = OverlayWindow()

        # Add 5 logs (more than max)
        for i in range(5):
            overlay.add_log(f"Log message {i + 1}")

        # Wait for queue processing
        time.sleep(0.2)
        overlay.update()

        # Verify only last 3 are kept
        assert len(overlay._logs) == 3
        assert overlay._logs[0] == "Log message 3"
        assert overlay._logs[1] == "Log message 4"
        assert overlay._logs[2] == "Log message 5"

        # Clean up
        overlay.close()


class TestOverlayWindowStatusTypes:
    """Tests for different status types and their visual properties."""

    def test_status_colors_defined(self):
        """Test that all status types have defined colors."""
        overlay = OverlayWindow()

        expected_types = ['info', 'success', 'warning', 'error', 'waiting']
        for status_type in expected_types:
            assert status_type in overlay.STATUS_COLORS
            assert status_type in overlay.STATUS_ICONS

        overlay.close()

    def test_status_color_values(self):
        """Test that status colors are valid hex colors."""
        overlay = OverlayWindow()

        for status_type, color in overlay.STATUS_COLORS.items():
            # Verify it's a hex color starting with #
            assert color.startswith('#')
            # Verify it's a valid 6-digit hex color
            assert len(color) == 7
            # Verify all characters after # are valid hex
            int(color[1:], 16)  # This will raise ValueError if invalid

        overlay.close()


class TestOverlayWindowEdgeCases:
    """Tests for edge cases and error handling."""

    def test_close_already_closed_window(self):
        """Test closing an already closed window doesn't raise error."""
        overlay = OverlayWindow()
        overlay.close()

        # Should not raise an error
        overlay.close()
        overlay.close()

    def test_update_after_close(self):
        """Test that updates after close don't raise errors."""
        overlay = OverlayWindow()
        overlay.close()

        # These should not raise errors even though window is closed
        overlay.update_phase(1, 5, "Test")
        overlay.update_status("Test", "info")
        overlay.add_log("Test log")

    def test_is_open_after_close(self):
        """Test is_open returns False after close."""
        overlay = OverlayWindow()
        assert overlay.is_open()

        overlay.close()
        assert not overlay.is_open()


class TestOverlayWindowWaitForF1:
    """Tests for the wait_for_f1 functionality."""

    def test_wait_for_f1_returns_false_when_closed(self):
        """Test that wait_for_f1 returns False if window is closed."""
        overlay = OverlayWindow()

        # Close the window
        overlay.close()

        # wait_for_f1 should return False since window is closed
        result = overlay.wait_for_f1()
        assert result is False

    def test_f1_event_handling(self):
        """Test that F1 key press is properly detected."""
        overlay = OverlayWindow()

        # Initially event should not be set
        assert not overlay._f1_pressed.is_set()

        # Simulate F1 press
        overlay._on_f1_pressed()

        # Event should now be set
        assert overlay._f1_pressed.is_set()

        overlay.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
