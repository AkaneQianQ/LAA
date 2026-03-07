"""
Test Overlay UI for Interactive Test Flow

Provides a semi-transparent horizontal overlay that displays test instructions
and receives user feedback via hotkeys.
"""

import tkinter as tk
import logging
from typing import Callable, Optional, Dict

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


class TestOverlay:
    """
    A semi-transparent overlay window for interactive test flow.

    Features:
    - 600x80 pixel size, positioned at top-left by default
    - 70% opacity with dark theme
    - Draggable via 20px title bar
    - Close button (X) on the right
    - Always-on-top behavior
    - Hotkey registration support (F1, END, Y, N)
    """

    # UI Constants
    WIDTH = 600
    HEIGHT = 80
    TITLE_BAR_HEIGHT = 20
    CONTENT_HEIGHT = 60
    DEFAULT_X = 0
    DEFAULT_Y = 0
    ALPHA = 0.7

    # Colors
    BG_COLOR = "#2b2b2b"
    TITLE_BG_COLOR = "#1e1e1e"
    TEXT_COLOR = "#ffffff"
    SUBTLE_TEXT_COLOR = "#888888"
    CLOSE_BUTTON_COLOR = "#ff5f56"
    CLOSE_BUTTON_HOVER_COLOR = "#ff3b30"

    def __init__(self, parent: Optional[tk.Tk] = None, title: str = "FerrumBot 测试控制"):
        """
        Initialize the test overlay.

        Args:
            parent: Optional parent Tk instance. If None, creates a new Tk root.
            title: The title to display in the title bar.
        """
        self.logger = logging.getLogger(__name__)
        self._title_text = title
        self._hotkey_handles: Dict[str, Callable] = {}
        self._hotkey_callbacks: Dict[str, Callable[[], None]] = {}

        # Create window
        if parent is None:
            self._root = tk.Tk()
            self._own_root = True
        else:
            self._root = parent
            self._own_root = False

        self._window = tk.Toplevel(self._root)
        self._window.title(title)

        # Configure window properties
        self._setup_window()
        self._create_widgets()
        self._setup_dragging()

    def _setup_window(self) -> None:
        """Configure window geometry and attributes."""
        # Set geometry: 600x80 at position (0, 0)
        geometry = f"{self.WIDTH}x{self.HEIGHT}+{self.DEFAULT_X}+{self.DEFAULT_Y}"
        self._window.geometry(geometry)

        # Remove window decorations (title bar, border)
        self._window.overrideredirect(True)

        # Always on top
        self._window.wm_attributes('-topmost', True)

        # Set opacity (alpha)
        self._window.wm_attributes('-alpha', self.ALPHA)

        # Prevent resizing
        self._window.resizable(False, False)

    def _create_widgets(self) -> None:
        """Create the UI widgets."""
        # Main container frame (dark background)
        self._main_frame = tk.Frame(
            self._window,
            bg=self.BG_COLOR,
            width=self.WIDTH,
            height=self.HEIGHT
        )
        self._main_frame.pack(fill=tk.BOTH, expand=True)
        self._main_frame.pack_propagate(False)

        # Title bar frame
        self._title_bar = tk.Frame(
            self._main_frame,
            bg=self.TITLE_BG_COLOR,
            height=self.TITLE_BAR_HEIGHT,
            width=self.WIDTH
        )
        self._title_bar.pack(side=tk.TOP, fill=tk.X)
        self._title_bar.pack_propagate(False)

        # Title label (left side of title bar)
        self._title_label = tk.Label(
            self._title_bar,
            text=self._title_text,
            bg=self.TITLE_BG_COLOR,
            fg=self.TEXT_COLOR,
            font=("Arial", 9),
            anchor=tk.W,
            padx=8
        )
        self._title_label.pack(side=tk.LEFT, fill=tk.Y)

        # Drag handle indicator (subtle dots)
        self._drag_handle = tk.Label(
            self._title_bar,
            text="\u2630",  # Trigram for heaven symbol (looks like drag handle)
            bg=self.TITLE_BG_COLOR,
            fg=self.SUBTLE_TEXT_COLOR,
            font=("Arial", 8),
            cursor="fleur"
        )
        self._drag_handle.pack(side=tk.LEFT, padx=(0, 5))

        # Close button (X) on the right
        self._close_button = tk.Label(
            self._title_bar,
            text="\u2715",  # Multiplication X
            bg=self.TITLE_BG_COLOR,
            fg=self.CLOSE_BUTTON_COLOR,
            font=("Arial", 10, "bold"),
            cursor="hand2",
            width=3
        )
        self._close_button.pack(side=tk.RIGHT, fill=tk.Y)
        self._close_button.bind("<Enter>", self._on_close_hover)
        self._close_button.bind("<Leave>", self._on_close_leave)
        self._close_button.bind("<Button-1>", self._on_close_click)

        # Content area frame
        self._content_frame = tk.Frame(
            self._main_frame,
            bg=self.BG_COLOR,
            height=self.CONTENT_HEIGHT,
            width=self.WIDTH
        )
        self._content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self._content_frame.pack_propagate(False)

        # Instruction text (main display)
        self._instruction_label = tk.Label(
            self._content_frame,
            text="等待测试开始...",
            bg=self.BG_COLOR,
            fg=self.TEXT_COLOR,
            font=("Arial", 11),
            wraplength=self.WIDTH - 20,
            justify=tk.CENTER
        )
        self._instruction_label.pack(expand=True, pady=(5, 0))

        # Hotkey indicators frame (bottom of content)
        self._hotkey_frame = tk.Frame(
            self._content_frame,
            bg=self.BG_COLOR,
            height=16
        )
        self._hotkey_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 2))

        # Hotkey indicator labels
        hotkey_text = "F1: \u4e0b\u4e00\u6b65  |  END: \u7ec8\u6b62  |  Y: \u901a\u8fc7  |  N: \u5931\u8d25"
        self._hotkey_label = tk.Label(
            self._hotkey_frame,
            text=hotkey_text,
            bg=self.BG_COLOR,
            fg=self.SUBTLE_TEXT_COLOR,
            font=("Arial", 8)
        )
        self._hotkey_label.pack()

    def _setup_dragging(self) -> None:
        """Setup drag functionality for the title bar."""
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._window_start_x = 0
        self._window_start_y = 0

        # Bind drag events to title bar and its children
        for widget in [self._title_bar, self._title_label, self._drag_handle]:
            widget.bind("<Button-1>", self._on_drag_start)
            widget.bind("<B1-Motion>", self._on_drag_motion)
            widget.bind("<ButtonRelease-1>", self._on_drag_end)

    def _on_drag_start(self, event: tk.Event) -> None:
        """Handle start of drag operation."""
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        self._window_start_x = self._window.winfo_x()
        self._window_start_y = self._window.winfo_y()

    def _on_drag_motion(self, event: tk.Event) -> None:
        """Handle drag motion."""
        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y
        new_x = self._window_start_x + dx
        new_y = self._window_start_y + dy
        self._window.geometry(f"+{new_x}+{new_y}")

    def _on_drag_end(self, event: tk.Event) -> None:
        """Handle end of drag operation."""
        pass  # No special handling needed

    def _on_close_hover(self, event: tk.Event) -> None:
        """Handle mouse entering close button."""
        self._close_button.config(fg=self.CLOSE_BUTTON_HOVER_COLOR)

    def _on_close_leave(self, event: tk.Event) -> None:
        """Handle mouse leaving close button."""
        self._close_button.config(fg=self.CLOSE_BUTTON_COLOR)

    def _on_close_click(self, event: tk.Event) -> None:
        """Handle close button click."""
        self.close()

    def show(self) -> None:
        """Display the overlay window."""
        self._window.deiconify()
        self._window.lift()

    def hide(self) -> None:
        """Hide the overlay window (withdraw)."""
        self._window.withdraw()

    def set_instruction(self, text: str) -> None:
        """
        Update the instruction text displayed in the overlay.

        Args:
            text: The instruction text to display.
        """
        self._instruction_label.config(text=text)
        self._window.update_idletasks()

    def close(self) -> None:
        """Destroy the window and cleanup resources."""
        self.unregister_hotkeys()
        if self._window and self._window.winfo_exists():
            self._window.destroy()
        if self._own_root and self._root and self._root.winfo_exists():
            self._root.destroy()

    def is_visible(self) -> bool:
        """
        Check if the overlay window exists and is visible.

        Returns:
            True if the window exists, False otherwise.
        """
        return self._window is not None and self._window.winfo_exists()

    def register_hotkeys(self, callbacks: Dict[str, Callable[[], None]]) -> None:
        """
        Register global hotkeys for the overlay.

        Args:
            callbacks: Dictionary mapping hotkey names to callback functions.
                      Supported keys: "f1", "end", "y", "n"

        Example:
            overlay.register_hotkeys({
                "f1": on_next_step,
                "end": on_stop,
                "y": on_pass,
                "n": on_fail
            })
        """
        if not KEYBOARD_AVAILABLE:
            self.logger.warning("keyboard library not available, hotkeys disabled")
            return

        self.unregister_hotkeys()  # Clear any existing hotkeys

        for key, callback in callbacks.items():
            try:
                handle = keyboard.add_hotkey(key, callback)
                self._hotkey_handles[key] = handle
                self._hotkey_callbacks[key] = callback
                self.logger.debug(f"Registered hotkey: {key}")
            except Exception as e:
                self.logger.warning(f"Failed to register hotkey '{key}': {e}")

    def unregister_hotkeys(self) -> None:
        """Unregister all global hotkeys."""
        if not KEYBOARD_AVAILABLE:
            return

        for key, handle in list(self._hotkey_handles.items()):
            try:
                keyboard.remove_hotkey(handle)
                self.logger.debug(f"Unregistered hotkey: {key}")
            except Exception as e:
                self.logger.warning(f"Failed to unregister hotkey '{key}': {e}")

        self._hotkey_handles.clear()
        self._hotkey_callbacks.clear()

    def get_position(self) -> tuple:
        """
        Get the current window position.

        Returns:
            Tuple of (x, y) coordinates.
        """
        return (self._window.winfo_x(), self._window.winfo_y())

    def set_position(self, x: int, y: int) -> None:
        """
        Set the window position.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        self._window.geometry(f"+{x}+{y}")
