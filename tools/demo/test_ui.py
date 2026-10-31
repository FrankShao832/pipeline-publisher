#!/usr/bin/env python
"""
Standalone launcher for Pipeline Publisher UI testing.

This script provides a simple way to test the ContextWidget
and MainWindow in standalone mode.
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from publisher.ui.main_window import MainWindow


def main():
    """Main entry point for standalone testing."""
    print("Starting Pipeline Publisher - Standalone Mode")
    print("=" * 50)
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Pipeline Publisher")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Pipeline Team")
    
    # Apply dark theme
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MainWindow(standalone_mode=True)
    
    # Connect signals for testing
    window.window_ready.connect(lambda: print("✓ Window is ready"))
    window.test_completed.connect(lambda success, msg: 
        print(f"✓ Test completed: {success} - {msg}"))
    
    window.show()
    print("✓ Window displayed successfully")
    print("\nAvailable test operations:")
    print("  1. Set Test Environment - Loads sample data")
    print("  2. Refresh Context - Updates context info")
    print("  3. Validate Context - Checks required fields")
    print("  4. Test Environment - Tests system setup")
    print("  5. Show Context Data - Displays current context")
    print("  6. Clear Environment - Clears test data")
    print("\nClose the window to exit.")
    print("=" * 50)
    
    # Run application
    return app.exec()


if __name__ == "__main__":
    exit_code = main()
    print(f"\nPipeline Publisher exited with code: {exit_code}")
    sys.exit(exit_code)