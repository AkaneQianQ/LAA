"""
Transparent overlay window for acceptance testing.

Provides a non-intrusive overlay that displays test progress,
phase information, and waits for user F1 input to continue.
"""

import tkinter as tk
from tkinter import ttk
import threading
import queue


class OverlayWindow:
    """
    A transparent overlay window for acceptance testing.

    Displays phase info, status, progress bar, recent logs, and waits for F1 key.
    Positioned at (20, 20) on a 2K display with 300x220 size.
    """

    # Status type to color mapping
    STATUS_COLORS = {
        'info': '#3498db',      # Blue
        'success': '#2ecc71',   # Green
        'warning': '#f39c12',   # Orange
        'error': '#e74c3c',     # Red
        'waiting': '#9b59b6',   # Purple
    }

    # Status type to icon mapping
    STATUS_ICONS = {
        'info': 'ℹ️',
        'success': '✅',
        'warning': '⚠️',
        'error': '❌',
        'waiting': '⏳',
    }

    def __init__(self):
        """Initialize the overlay window."""
        self.root = None
        self._f1_pressed = threading.Event()
        self._log_queue = queue.Queue()
        self._logs = []
        self._max_logs = 3

        # UI elements (initialized in _create_ui)
        self._phase_label = None
        self._phase_progress = None
        self._status_label = None
        self._f1_hint_label = None
        self._total_progress_var = None
        self._total_progress_label = None
        self._log_labels = []

        # Current state
        self._current_phase_num = 1
        self._total_phases = 5
        self._phase_name = ""

        self._create_window()

    def _create_window(self):
        """Create the main overlay window."""
        self.root = tk.Tk()
        self.root.title("LostarkBot 验收测试")

        # Window configuration
        self.root.geometry("300x220+20+20")  # Size 300x220, position (20, 20)
        self.root.overrideredirect(True)     # Remove window decorations
        self.root.attributes('-topmost', True)  # Keep on top
        self.root.attributes('-alpha', 0.75)    # 75% opacity

        # Make background transparent (Windows)
        try:
            self.root.attributes('-transparentcolor', 'black')
        except tk.TclError:
            pass  # Not supported on all platforms

        # Bind events
        self.root.bind('<F1>', self._on_f1_pressed)
        self.root.bind('<Button-1>', self._start_drag)
        self.root.bind('<B1-Motion>', self._on_drag)
        self.root.bind('<Escape>', lambda e: self.close())

        self._create_ui()
        self._start_update_loop()

    def _create_ui(self):
        """Create the UI components."""
        # Main frame with dark background
        main_frame = tk.Frame(self.root, bg='black', padx=10, pady=8)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title bar with drag hint
        title_frame = tk.Frame(main_frame, bg='black')
        title_frame.pack(fill=tk.X, pady=(0, 5))

        title_label = tk.Label(
            title_frame,
            text="LostarkBot 验收测试",
            font=('Microsoft YaHei', 11, 'bold'),
            fg='white',
            bg='black'
        )
        title_label.pack(side=tk.LEFT)

        drag_label = tk.Label(
            title_frame,
            text="[拖拽移动]",
            font=('Microsoft YaHei', 8),
            fg='#888888',
            bg='black'
        )
        drag_label.pack(side=tk.RIGHT)

        # Separator
        separator = tk.Frame(main_frame, height=1, bg='#444444')
        separator.pack(fill=tk.X, pady=2)

        # Phase info section
        phase_frame = tk.Frame(main_frame, bg='black')
        phase_frame.pack(fill=tk.X, pady=3)

        self._phase_label = tk.Label(
            phase_frame,
            text=f"Phase {self._current_phase_num}/{self._total_phases}  {self._phase_name}",
            font=('Microsoft YaHei', 10),
            fg='white',
            bg='black'
        )
        self._phase_label.pack(anchor=tk.W)

        # Phase progress bar
        self._phase_progress_var = tk.DoubleVar(value=0)
        self._phase_progress = ttk.Progressbar(
            phase_frame,
            variable=self._phase_progress_var,
            maximum=100,
            length=280,
            mode='determinate'
        )
        self._phase_progress.pack(fill=tk.X, pady=2)

        # Style the progress bar
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "Horizontal.TProgressbar",
            background='#3498db',
            troughcolor='#333333',
            borderwidth=0,
            lightcolor='#3498db',
            darkcolor='#2980b9'
        )

        # Status section
        self._status_label = tk.Label(
            main_frame,
            text="状态: ⏳ 等待用户确认",
            font=('Microsoft YaHei', 9),
            fg=self.STATUS_COLORS['waiting'],
            bg='black'
        )
        self._status_label.pack(anchor=tk.W, pady=3)

        # F1 hint
        self._f1_hint_label = tk.Label(
            main_frame,
            text="[按 F1 继续]",
            font=('Microsoft YaHei', 9, 'bold'),
            fg='#f39c12',
            bg='black'
        )
        self._f1_hint_label.pack(anchor=tk.W)

        # Separator
        separator2 = tk.Frame(main_frame, height=1, bg='#444444')
        separator2.pack(fill=tk.X, pady=5)

        # Total progress section
        total_progress_frame = tk.Frame(main_frame, bg='black')
        total_progress_frame.pack(fill=tk.X)

        self._total_progress_var = tk.DoubleVar(value=0)
        self._total_progress_label = tk.Label(
            total_progress_frame,
            text="总进度 ▓▓▓▓░░░░░░ 40%",
            font=('Microsoft YaHei', 9),
            fg='white',
            bg='black'
        )
        self._total_progress_label.pack(anchor=tk.W)

        # Log section (last 3 lines)
        log_frame = tk.Frame(main_frame, bg='black')
        log_frame.pack(fill=tk.X, pady=(5, 0))

        self._log_labels = []
        for i in range(self._max_logs):
            label = tk.Label(
                log_frame,
                text="",
                font=('Microsoft YaHei', 8),
                fg='#aaaaaa',
                bg='black',
                anchor=tk.W
            )
            label.pack(anchor=tk.W)
            self._log_labels.append(label)

        # Initialize with empty logs
        self._update_log_display()

    def _start_update_loop(self):
        """Start the periodic update loop for processing log queue."""
        self._process_queue()

    def _process_queue(self):
        """Process pending log messages from queue."""
        try:
            while True:
                message = self._log_queue.get_nowait()
                self._logs.append(message)
                # Keep only last 3 logs
                if len(self._logs) > self._max_logs:
                    self._logs.pop(0)
                self._update_log_display()
        except queue.Empty:
            pass

        # Schedule next check
        if self.root and self.root.winfo_exists():
            self.root.after(100, self._process_queue)

    def _update_log_display(self):
        """Update the log labels with current logs."""
        for i, label in enumerate(self._log_labels):
            if i < len(self._logs):
                label.config(text=f"• {self._logs[i]}")
            else:
                label.config(text="")

    def _on_f1_pressed(self, event=None):
        """Handle F1 key press."""
        self._f1_pressed.set()
        return 'break'

    def _start_drag(self, event):
        """Start window drag."""
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag(self, event):
        """Handle window drag."""
        x = self.root.winfo_x() + event.x - self._drag_start_x
        y = self.root.winfo_y() + event.y - self._drag_start_y
        self.root.geometry(f"+{x}+{y}")

    def update_phase(self, phase_num: int, total_phases: int, phase_name: str):
        """
        Update the current phase information.

        Args:
            phase_num: Current phase number (1-based)
            total_phases: Total number of phases
            phase_name: Name of the current phase
        """
        self._current_phase_num = phase_num
        self._total_phases = total_phases
        self._phase_name = phase_name

        if self._phase_label and self.root and self.root.winfo_exists():
            self._phase_label.config(
                text=f"Phase {phase_num}/{total_phases}  {phase_name}"
            )

        # Update phase progress
        if self._phase_progress_var and total_phases > 0:
            progress = ((phase_num - 1) / total_phases) * 100
            self._phase_progress_var.set(progress)

        # Update total progress display
        self._update_total_progress()

    def update_status(self, status: str, status_type: str = 'info'):
        """
        Update the status message.

        Args:
            status: Status message to display
            status_type: Type of status ('info', 'success', 'warning', 'error', 'waiting')
        """
        color = self.STATUS_COLORS.get(status_type, self.STATUS_COLORS['info'])
        icon = self.STATUS_ICONS.get(status_type, 'ℹ️')

        if self._status_label and self.root and self.root.winfo_exists():
            self._status_label.config(
                text=f"状态: {icon} {status}",
                fg=color
            )

    def _update_total_progress(self):
        """Update the total progress display."""
        if self._total_phases > 0:
            percentage = int((self._current_phase_num / self._total_phases) * 100)
            filled = int((percentage / 100) * 10)
            empty = 10 - filled
            bar = '█' * filled + '░' * empty

            if self._total_progress_label and self.root and self.root.winfo_exists():
                self._total_progress_label.config(
                    text=f"总进度 {bar} {percentage}%"
                )

            if self._total_progress_var:
                self._total_progress_var.set(percentage)

    def add_log(self, message: str):
        """
        Add a log message (keeps only last 3 lines).

        Args:
            message: Log message to add
        """
        self._log_queue.put(message)

    def wait_for_f1(self) -> bool:
        """
        Block until F1 is pressed.

        Returns:
            True if F1 was pressed, False if window was closed
        """
        self._f1_pressed.clear()

        # Update status to waiting
        self.update_status("等待用户确认", 'waiting')

        # Show F1 hint
        if self._f1_hint_label and self.root and self.root.winfo_exists():
            self._f1_hint_label.config(fg='#f39c12')

        # Wait for F1 or window close
        while self.root and self.root.winfo_exists():
            self.root.update()
            if self._f1_pressed.is_set():
                return True
            import time
            time.sleep(0.01)

        return False

    def close(self):
        """Close the overlay window."""
        if self.root and self.root.winfo_exists():
            self.root.destroy()
            self.root = None

    def is_open(self) -> bool:
        """Check if the overlay window is still open."""
        return self.root is not None and self.root.winfo_exists()

    def update(self):
        """Process pending UI updates."""
        if self.root and self.root.winfo_exists():
            self.root.update()


# Convenience function for quick testing
def create_overlay() -> OverlayWindow:
    """Create and return a new overlay window."""
    return OverlayWindow()


if __name__ == "__main__":
    # Quick test
    overlay = create_overlay()
    overlay.update_phase(2, 5, "角色检测")
    overlay.add_log("ESC菜单检测成功")
    overlay.add_log("发现6个角色")
    overlay.update_status("准备就绪", "success")

    # Keep window open for testing
    overlay.root.mainloop()
