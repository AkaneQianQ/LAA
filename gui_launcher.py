"""
GUI Launcher for FerrumBot

Provides a Tkinter interface with global hotkeys for automation control.
Integrates account discovery/indexing before main automation starts.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import keyboard
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from modules.character_detector import CharacterDetector


class FerrumBotLauncher:
    """Main GUI launcher for FerrumBot with account discovery integration."""

    def __init__(self):
        """Initialize the launcher window and components."""
        self.root = tk.Tk()
        self.root.title("FerrumBot - Lost Ark Guild Donation Automation")
        self.root.geometry("600x500")
        self.root.resizable(True, True)

        # State
        self.stop_event = threading.Event()
        self.current_task = None
        self.detector = None
        self.account_info = None

        # Initialize UI
        self._create_widgets()
        self._setup_hotkeys()

        # Initialize detector
        self._init_detector()

    def _init_detector(self):
        """Initialize the character detector with default paths."""
        try:
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
            db_path = os.path.join(data_dir, "accounts.db")
            assets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

            self.detector = CharacterDetector(
                assets_path=assets_path,
                data_dir=data_dir,
                db_path=db_path
            )
            self._log("Character detector initialized")
        except Exception as e:
            self._log(f"Warning: Could not initialize detector: {e}")

    def _create_widgets(self):
        """Create the GUI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="FerrumBot Automation",
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 10), sticky=tk.W)

        # Account Info Frame
        account_frame = ttk.LabelFrame(main_frame, text="Account Status", padding="10")
        account_frame.grid(row=1, column=0, pady=(0, 10), sticky=(tk.W, tk.E))
        account_frame.columnconfigure(0, weight=1)

        self.account_label = ttk.Label(
            account_frame,
            text="No account discovered. Click 'Discover Account' to begin.",
            wraplength=550
        )
        self.account_label.grid(row=0, column=0, sticky=tk.W)

        # Button Frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=(0, 10), sticky=(tk.W, tk.E))

        self.discover_btn = ttk.Button(
            button_frame,
            text="Discover Account (F11)",
            command=self._start_discovery
        )
        self.discover_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.start_btn = ttk.Button(
            button_frame,
            text="Start Automation (F10)",
            command=self._start_automation,
            state=tk.DISABLED
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.stop_btn = ttk.Button(
            button_frame,
            text="Stop (END)",
            command=self._stop_task,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT)

        # Log Frame
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="10")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Hotkeys Frame
        hotkeys_frame = ttk.LabelFrame(main_frame, text="Hotkeys", padding="10")
        hotkeys_frame.grid(row=4, column=0, pady=(10, 0), sticky=(tk.W, tk.E))

        hotkeys_text = (
            "F10: Start main automation task\n"
            "F11: Discover/Index account\n"
            "END: Stop current task"
        )
        hotkeys_label = ttk.Label(hotkeys_frame, text=hotkeys_text, justify=tk.LEFT)
        hotkeys_label.pack(anchor=tk.W)

    def _setup_hotkeys(self):
        """Setup global hotkeys for automation control."""
        try:
            keyboard.add_hotkey('f10', self._start_automation)
            keyboard.add_hotkey('f11', self._start_discovery)
            keyboard.add_hotkey('end', self._stop_task)
            self._log("Global hotkeys registered (F10, F11, END)")
        except Exception as e:
            self._log(f"Warning: Could not register global hotkeys: {e}")
            self._log("Use buttons instead")

    def _log(self, message: str):
        """Add a message to the log display."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}\n"

        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, full_message)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _start_discovery(self):
        """Start account discovery in a separate thread."""
        if self.current_task and self.current_task.is_alive():
            self._log("Task already running. Press END to stop.")
            return

        self.stop_event.clear()
        self.current_task = threading.Thread(target=self._discovery_worker, daemon=True)
        self.current_task.start()

        self.discover_btn.configure(state=tk.DISABLED)
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)

    def _discovery_worker(self):
        """Worker thread for account discovery."""
        self._log("=" * 50)
        self._log("Starting account discovery...")
        self._log("Please open the character selection screen in Lost Ark")

        try:
            # Import here to avoid issues if not available
            import numpy as np
            import cv2

            # Wait for user to be ready (3 second countdown)
            for i in range(3, 0, -1):
                if self.stop_event.is_set():
                    self._log("Discovery cancelled")
                    return
                self._log(f"Starting in {i}...")
                import time
                time.sleep(1)

            # Capture screenshot
            self._log("Capturing screen...")

            # Try to use DXCam if available
            try:
                import dxcam
                camera = dxcam.create()
                screenshot = camera.grab()
                if screenshot is not None:
                    # DXCam returns RGB, convert to BGR for OpenCV
                    screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
            except Exception:
                screenshot = None

            if screenshot is None:
                # Fallback: try to use PIL
                try:
                    from PIL import ImageGrab
                    screenshot = np.array(ImageGrab.grab())
                    screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
                except Exception as e:
                    self._log(f"Could not capture screen: {e}")
                    self._log("Using mock screenshot for testing")
                    # Create a mock screenshot for testing
                    screenshot = np.zeros((1440, 2560, 3), dtype=np.uint8)

            # Perform discovery
            self._log("Analyzing character selection screen...")

            if self.detector is None:
                self._init_detector()

            result = self.detector.discover_account(screenshot)

            if result['account_id'] is None:
                self._log("No characters found on screen")
                self._log("Please ensure the character selection screen is visible")
            else:
                self.account_info = result
                account_hash_short = result['account_hash'][:16] + "..."

                self._log(f"Account discovered!")
                self._log(f"  Account ID: {result['account_id']}")
                self._log(f"  Account Hash: {account_hash_short}")
                self._log(f"  Characters found: {result['character_count']}")

                # Update UI
                self.root.after(0, self._update_account_ui, result)

        except Exception as e:
            self._log(f"Discovery error: {e}")
            import traceback
            self._log(traceback.format_exc())

        finally:
            self.root.after(0, self._reset_buttons)

    def _update_account_ui(self, result: dict):
        """Update the UI with account information."""
        account_hash_short = result['account_hash'][:24] + "..."
        self.account_label.configure(
            text=(
                f"Account: {account_hash_short}\n"
                f"Characters: {result['character_count']}\n"
                f"Ready for automation"
            )
        )
        self.start_btn.configure(state=tk.NORMAL)

    def _start_automation(self):
        """Start main automation in a separate thread."""
        if self.current_task and self.current_task.is_alive():
            self._log("Task already running. Press END to stop.")
            return

        if self.account_info is None:
            self._log("Please discover account first (F11)")
            return

        self.stop_event.clear()
        self.current_task = threading.Thread(target=self._automation_worker, daemon=True)
        self.current_task.start()

        self.discover_btn.configure(state=tk.DISABLED)
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)

    def _automation_worker(self):
        """Worker thread for main automation."""
        self._log("=" * 50)
        self._log("Starting main automation...")
        self._log(f"Account: {self.account_info['account_hash'][:24]}...")
        self._log(f"Characters: {self.account_info['character_count']}")

        try:
            # Main automation loop would go here
            # For now, just simulate work
            import time

            for i in range(10):
                if self.stop_event.is_set():
                    self._log("Automation stopped by user")
                    return

                self._log(f"Processing character {i + 1}...")
                time.sleep(0.5)

            self._log("Automation completed!")

        except Exception as e:
            self._log(f"Automation error: {e}")
            import traceback
            self._log(traceback.format_exc())

        finally:
            self.root.after(0, self._reset_buttons)

    def _stop_task(self):
        """Stop the current task."""
        self._log("Stopping current task...")
        self.stop_event.set()

        if self.current_task and self.current_task.is_alive():
            self.current_task.join(timeout=2.0)

        self._reset_buttons()
        self._log("Task stopped")

    def _reset_buttons(self):
        """Reset button states after task completion."""
        self.discover_btn.configure(state=tk.NORMAL)
        self.start_btn.configure(
            state=tk.NORMAL if self.account_info else tk.DISABLED
        )
        self.stop_btn.configure(state=tk.DISABLED)

    def run(self):
        """Run the main event loop."""
        self._log("FerrumBot Launcher started")
        self._log("Press F11 to discover account or F10 to start automation")
        self.root.mainloop()


def main():
    """Main entry point."""
    # Check if running in headless mode (for testing)
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Running in test mode...")
        # Test mode: just verify imports work
        try:
            from modules.character_detector import CharacterDetector
            print("CharacterDetector imported successfully")

            detector = CharacterDetector()
            print(f"CharacterDetector created: {detector}")

            # Check for required methods
            assert hasattr(detector, 'create_or_get_account_index')
            assert hasattr(detector, 'discover_account')
            assert hasattr(detector, 'cache_character_screenshot')
            assert hasattr(detector, 'load_cached_characters')
            print("All required methods present")

            print("Test mode completed successfully")
            return 0
        except Exception as e:
            print(f"Test failed: {e}")
            import traceback
            traceback.print_exc()
            return 1

    # Normal GUI mode
    launcher = FerrumBotLauncher()
    launcher.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
