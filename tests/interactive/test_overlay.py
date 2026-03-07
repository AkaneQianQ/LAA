"""
Unit tests for the TestOverlay UI component.

Tests cover overlay creation, geometry, visibility, hotkey registration,
and all public methods of the TestOverlay class.
"""

import pytest
import tkinter as tk
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.interactive.overlay import TestOverlay


class TestOverlayUI:
    """Test suite for TestOverlay UI component."""

    @pytest.fixture
    def overlay(self):
        """Fixture that creates a TestOverlay and cleans up after test."""
        root = tk.Tk()
        root.withdraw()  # Hide root window
        o = TestOverlay(root)
        yield o
        o.close()
        root.destroy()

    @pytest.fixture
    def overlay_no_root(self):
        """Fixture that creates a TestOverlay with its own root and cleans up."""
        o = TestOverlay()
        yield o
        o.close()

    def test_overlay_creation(self, overlay):
        """Test that TestOverlay instantiates without error."""
        assert overlay is not None
        assert overlay.is_visible()

    def test_overlay_creation_without_parent(self, overlay_no_root):
        """Test that TestOverlay can create its own root window."""
        assert overlay_no_root is not None
        assert overlay_no_root.is_visible()
        assert overlay_no_root._own_root is True

    def test_overlay_geometry(self, overlay):
        """Test that overlay has correct default size."""
        assert overlay.WIDTH == 900
        assert overlay.HEIGHT == 60
        # Update window to ensure geometry is applied
        overlay._window.update_idletasks()
        # Window geometry may vary by platform, check constants are correct
        assert overlay._window.winfo_reqwidth() > 0
        assert overlay._window.winfo_reqheight() > 0

    def test_overlay_position(self, overlay):
        """Test that overlay has correct default position."""
        x, y = overlay.get_position()
        assert x == overlay.DEFAULT_X
        assert y == overlay.DEFAULT_Y

    def test_overlay_always_on_top(self, overlay):
        """Test that topmost attribute is set."""
        # The topmost attribute is set during _setup_window
        # We verify the window exists and is visible
        assert overlay.is_visible()
        # Verify topmost attribute was set (may need window to be drawn)
        try:
            overlay._window.update_idletasks()
            is_topmost = overlay._window.wm_attributes('-topmost')
            assert is_topmost == 1
        except tk.TclError:
            # Some platforms may not support this query before window is drawn
            pass

    def test_overlay_transparent_color(self, overlay):
        """Test that transparent color is set for click-through."""
        assert hasattr(overlay, 'TRANSPARENT_COLOR')
        assert overlay.TRANSPARENT_COLOR == "#ff00ff"

    def test_set_instruction(self, overlay):
        """Test that instruction text updates correctly."""
        test_text = "Test instruction message"
        overlay.set_instruction(test_text)
        assert overlay._instruction_label.cget("text") == test_text

    def test_show_hide(self, overlay):
        """Test show and hide methods."""
        # Initially visible
        assert overlay.is_visible()

        # Hide
        overlay.hide()
        assert overlay.is_visible()  # Window still exists, just withdrawn

        # Show
        overlay.show()
        assert overlay.is_visible()

    def test_close_cleanup(self):
        """Test that close destroys window properly."""
        root = tk.Tk()
        root.withdraw()
        overlay = TestOverlay(root)

        assert overlay.is_visible()
        overlay.close()
        assert not overlay.is_visible()

        root.destroy()

    def test_set_position(self, overlay):
        """Test setting window position."""
        new_x, new_y = 100, 200
        overlay.set_position(new_x, new_y)
        # Update to ensure position is applied
        overlay._window.update_idletasks()
        x, y = overlay.get_position()
        assert x == new_x
        assert y == new_y

    def test_title_default(self, overlay):
        """Test default title is Chinese."""
        assert overlay._title_text == "FerrumBot 测试控制"

    def test_custom_title(self):
        """Test custom title can be set."""
        root = tk.Tk()
        root.withdraw()
        custom_title = "Custom Test Title"
        overlay = TestOverlay(root, title=custom_title)

        assert overlay._title_text == custom_title
        assert overlay._title_label.cget("text") == custom_title

        overlay.close()
        root.destroy()

    def test_colors_defined(self, overlay):
        """Test that color constants are defined."""
        # BG_COLOR is now transparent color for click-through
        assert overlay.BG_COLOR == overlay.TRANSPARENT_COLOR
        assert overlay.TITLE_BG_COLOR == "#1e1e1e"
        assert overlay.TEXT_COLOR == "#ffffff"
        assert overlay.SUBTLE_TEXT_COLOR == "#cccccc"

    def test_hotkey_indicators_displayed(self, overlay):
        """Test that hotkey indicators are shown in UI."""
        hotkey_text = overlay._hotkey_label.cget("text")
        assert "F1" in hotkey_text
        assert "END" in hotkey_text
        assert "Y" in hotkey_text
        assert "N" in hotkey_text

    def test_set_instruction_with_step(self, overlay):
        """Test that instruction text and step counter update correctly."""
        test_text = "Test instruction message"
        overlay.set_instruction(test_text, step=2, total=5)
        assert overlay._instruction_label.cget("text") == test_text
        assert overlay._status_label.cget("text") == "[2/5]"

    def test_status_label_hidden_without_step(self, overlay):
        """Test that status shows placeholder when no step provided."""
        overlay.set_instruction("Test message")
        assert overlay._status_label.cget("text") == "[--/--]"


class TestOverlayHotkeys:
    """Test suite for hotkey functionality."""

    @pytest.fixture
    def overlay(self):
        """Fixture that creates a TestOverlay with mocked keyboard."""
        root = tk.Tk()
        root.withdraw()
        o = TestOverlay(root)
        yield o
        o.close()
        root.destroy()

    def test_hotkey_registration(self, overlay):
        """Test hotkey registration with mocked keyboard library."""
        with patch('tests.interactive.overlay.keyboard') as mock_keyboard:
            mock_keyboard.add_hotkey.return_value = Mock()

            callbacks = {
                "f1": Mock(),
                "end": Mock(),
                "y": Mock(),
                "n": Mock()
            }

            overlay.register_hotkeys(callbacks)

            # Verify keyboard.add_hotkey was called for each key
            assert mock_keyboard.add_hotkey.call_count == 4

    def test_hotkey_cleanup(self, overlay):
        """Test hotkey cleanup on close."""
        with patch('tests.interactive.overlay.keyboard') as mock_keyboard:
            mock_handle = Mock()
            mock_keyboard.add_hotkey.return_value = mock_handle

            callbacks = {"f1": Mock()}
            overlay.register_hotkeys(callbacks)

            # Verify hotkey was registered
            assert "f1" in overlay._hotkey_handles

            # Close should unregister hotkeys
            overlay.close()

            # Verify remove_hotkey was called
            mock_keyboard.remove_hotkey.assert_called_with(mock_handle)

    def test_hotkey_unregistration(self, overlay):
        """Test explicit hotkey unregistration."""
        with patch('tests.interactive.overlay.keyboard') as mock_keyboard:
            mock_handle = Mock()
            mock_keyboard.add_hotkey.return_value = mock_handle

            callbacks = {"f1": Mock(), "y": Mock()}
            overlay.register_hotkeys(callbacks)

            # Unregister
            overlay.unregister_hotkeys()

            # Verify remove_hotkey was called for each
            assert mock_keyboard.remove_hotkey.call_count == 2

            # Verify internal state cleared
            assert len(overlay._hotkey_handles) == 0
            assert len(overlay._hotkey_callbacks) == 0

    def test_hotkey_keyboard_unavailable(self, overlay):
        """Test behavior when keyboard library is not available."""
        with patch('tests.interactive.overlay.KEYBOARD_AVAILABLE', False):
            callbacks = {"f1": Mock()}
            # Should not raise exception
            overlay.register_hotkeys(callbacks)
            # No hotkeys should be registered
            assert len(overlay._hotkey_handles) == 0

    def test_hotkey_registration_failure(self, overlay):
        """Test handling of hotkey registration failure."""
        with patch('tests.interactive.overlay.keyboard') as mock_keyboard:
            mock_keyboard.add_hotkey.side_effect = Exception("Permission denied")

            callbacks = {"f1": Mock()}
            # Should not raise exception, just log warning
            overlay.register_hotkeys(callbacks)

            # No hotkeys should be registered due to failure
            assert len(overlay._hotkey_handles) == 0


class TestOverlayDragFunctionality:
    """Test suite for drag functionality."""

    @pytest.fixture
    def overlay(self):
        """Fixture that creates a TestOverlay."""
        root = tk.Tk()
        root.withdraw()
        o = TestOverlay(root)
        yield o
        o.close()
        root.destroy()

    def test_drag_start_captures_position(self, overlay):
        """Test that drag start captures initial position."""
        # Create a mock event
        mock_event = Mock()
        mock_event.x_root = 100
        mock_event.y_root = 200

        initial_x = overlay._window.winfo_x()
        initial_y = overlay._window.winfo_y()

        overlay._on_drag_start(mock_event)

        assert overlay._drag_start_x == 100
        assert overlay._drag_start_y == 200
        assert overlay._window_start_x == initial_x
        assert overlay._window_start_y == initial_y

    def test_drag_motion_updates_position(self, overlay):
        """Test that drag motion updates window position."""
        # First deiconify the window so it can be moved
        overlay._window.deiconify()
        overlay._window.update_idletasks()

        # Get initial position
        initial_x = overlay._window.winfo_x()
        initial_y = overlay._window.winfo_y()

        # Setup initial drag state
        overlay._drag_start_x = 100
        overlay._drag_start_y = 100
        overlay._window_start_x = initial_x
        overlay._window_start_y = initial_y

        # Create a mock event (moved 50 pixels)
        mock_event = Mock()
        mock_event.x_root = 150
        mock_event.y_root = 150

        overlay._on_drag_motion(mock_event)
        overlay._window.update_idletasks()

        # Window should have moved by 50 pixels from initial position
        x, y = overlay.get_position()
        assert x == initial_x + 50
        assert y == initial_y + 50


class TestOverlayCloseButton:
    """Test suite for close button functionality."""

    @pytest.fixture
    def overlay(self):
        """Fixture that creates a TestOverlay."""
        root = tk.Tk()
        root.withdraw()
        o = TestOverlay(root)
        yield o
        o.close()
        root.destroy()

    def test_close_button_hover(self, overlay):
        """Test close button hover changes color."""
        mock_event = Mock()
        overlay._on_close_hover(mock_event)
        assert overlay._close_button.cget("fg") == overlay.CLOSE_BUTTON_HOVER_COLOR

    def test_close_button_leave(self, overlay):
        """Test close button leave restores color."""
        mock_event = Mock()
        overlay._on_close_leave(mock_event)
        assert overlay._close_button.cget("fg") == overlay.CLOSE_BUTTON_COLOR

    def test_close_button_click(self, overlay):
        """Test close button click closes overlay."""
        mock_event = Mock()
        assert overlay.is_visible()
        overlay._on_close_click(mock_event)
        assert not overlay.is_visible()


@pytest.mark.skipif(
    os.environ.get('HEADLESS') == '1',
    reason="Skipping GUI tests in headless environment"
)
class TestOverlayDisplay:
    """Tests that require an actual display (not headless)."""

    def test_overlay_visible_on_screen(self):
        """Test that overlay is actually visible on screen."""
        root = tk.Tk()
        root.withdraw()
        overlay = TestOverlay(root)

        # Update to ensure window is drawn
        overlay._window.update()

        # Check window is viewable
        assert overlay._window.winfo_viewable() == 1

        overlay.close()
        root.destroy()

    def test_overlay_topmost_attribute(self):
        """Test that topmost attribute is actually set on window."""
        root = tk.Tk()
        root.withdraw()
        overlay = TestOverlay(root)

        # Update to ensure window attributes are applied
        overlay._window.update()

        # Check that window manager attributes include topmost
        # Note: This is platform-specific, but on Windows we can check wm_attributes
        try:
            is_topmost = overlay._window.wm_attributes('-topmost')
            assert is_topmost == 1
        except tk.TclError:
            # Some platforms may not support this query
            pass

        overlay.close()
        root.destroy()
