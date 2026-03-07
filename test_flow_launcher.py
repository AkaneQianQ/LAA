"""
Interactive Test Flow Launcher for FerrumBot

F1-driven test interface for manual testing with AI guidance.
Provides semi-transparent overlay for test instruction display.
"""

import sys
import os
import argparse
import io
from pathlib import Path

# Set UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.interactive.test_runner import TestRunner
from tests.interactive.scenarios import list_scenarios_with_descriptions


def check_dependencies():
    """Check for required dependencies and provide helpful error messages."""
    errors = []

    # Check tkinter
    try:
        import tkinter as tk
    except ImportError:
        errors.append("tkinter is not installed. Please install python3-tk package.")

    # Check keyboard
    try:
        import keyboard
    except ImportError:
        errors.append("keyboard library not installed. Run: pip install keyboard")

    if errors:
        print("Error: Missing dependencies")
        for error in errors:
            print(f"  - {error}")
        return False

    return True


def list_scenarios():
    """List all available scenarios and exit."""
    print("=" * 50)
    print("Available Test Scenarios")
    print("=" * 50)
    print()

    scenarios = list_scenarios_with_descriptions()
    for i, (name, description) in enumerate(scenarios, 1):
        print(f"{i}. {name}")
        print(f"   {description}")
        print()

    return 0


def main():
    """Main entry point for test flow launcher."""
    parser = argparse.ArgumentParser(
        description="FerrumBot Interactive Test Flow Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Controls:
  1-2: Select test scenario
  F1:  Continue / Next step
  Y:   Mark step as passed
  N:   Mark step as failed
  END: Terminate test
        """
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available scenarios and exit"
    )

    parser.add_argument(
        "--scenario", "-s",
        type=str,
        metavar="NAME",
        help="Skip selection, run specific scenario"
    )

    parser.add_argument(
        "--no-overlay",
        action="store_true",
        help="Run in console mode (for headless testing)"
    )

    args = parser.parse_args()

    # Handle list command
    if args.list:
        return list_scenarios()

    # Check dependencies
    if not check_dependencies():
        return 1

    # Print banner
    print("=" * 50)
    print("FerrumBot Interactive Test Flow")
    print("=" * 50)
    print()

    if args.scenario:
        print(f"Selected scenario: {args.scenario}")
    else:
        print("Controls:")
        print("  1-2: Select test scenario")
        print("  F1:  Continue / Next step")
        print("  Y:   Mark step as passed")
        print("  N:   Mark step as failed")
        print("  END: Terminate test")
    print()

    # Check keyboard permissions (Windows-specific note)
    try:
        import keyboard
        # Try to register a test hotkey to verify permissions
        keyboard.add_hotkey('ctrl+shift+f12', lambda: None)
        keyboard.remove_hotkey('ctrl+shift+f12')
    except Exception as e:
        print("Warning: Keyboard hotkeys may require administrator privileges.")
        print(f"Error: {e}")
        print()

    try:
        runner = TestRunner()

        # If scenario specified, pre-select it
        if args.scenario:
            from tests.interactive.scenarios import get_scenario_by_name
            scenario = get_scenario_by_name(args.scenario)
            if scenario is None:
                print(f"Error: Unknown scenario '{args.scenario}'")
                print("Run with --list to see available scenarios.")
                return 1
            runner.selected_scenario = scenario

        runner.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
