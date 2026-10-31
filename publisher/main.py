"""
Unified entry point for Pipeline Publisher.

Supports multiple modes:
- Standalone mode: python -m publisher.main
- DCC integration: import publisher.main; publisher.main.launch()
- Programmatic usage: Flexible API for various use cases

Design: This module is a thin coordinator that delegates to specialized modules:
  - DCC detection  -> publisher.dcc.dcc_detector
  - Version info   -> publisher.core.version
  - UI icon/utils  -> publisher.ui.ui_utils
  - DCC launchers  -> publisher.dcc.launcher
"""

import sys
from pathlib import Path
from typing import Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal

from publisher.ui.main_window import MainWindow
from publisher.dcc.dcc_detector import DCCDetector, DCCType
from publisher.core.version import get_version_info
from publisher.core.controller import PublisherController
from publisher.ui.utils.ui_utils import get_app_icon


class PublisherLauncher(QObject):
    """
    Publisher application lifecycle manager.
    
    Responsibilities:
    - Create/manage QApplication instance
    - Create publisher window
    - Manage application event loop
    - Cleanup resources
    
    Delegates to:
    - DCCDetector for environment detection
    - MainWindow for UI
    - version module for version info
    """
    
    # Signals for lifecycle events
    window_created = Signal(object)
    application_ready = Signal()
    window_closed = Signal()
    
    def __init__(self, standalone_mode: bool = True, parent: Optional[QObject] = None):
        """Initialize publisher launcher."""
        super().__init__(parent)
        
        self.standalone_mode = standalone_mode
        self.controller = PublisherController(standalone_mode=standalone_mode)
        self.application: Optional[QApplication] = None
        self.window: Optional[MainWindow] = None
        self.is_running = False
    
    def create_application(self) -> QApplication:
        """Create or get existing QApplication instance."""
        existing_app = QApplication.instance()
        if existing_app:
            return existing_app
        
        app = QApplication(sys.argv)
        app.setApplicationName("Y Publisher")
        app.setApplicationVersion("2.1.0")
        app.setOrganizationName("Frank")
        app.setStyle('Fusion')
        
        # Set window icon
        try:
            app.setWindowIcon(get_app_icon())
        except Exception:
            pass  # Icon is optional
        
        return app
    
    def create_window(self) -> MainWindow:
        """Create main window instance with controller."""
        window = MainWindow(controller=self.controller)
        window.setWindowTitle("Y Publisher V 2.1.0")
        
        # Connect window ready signal
        if hasattr(window, 'window_ready'):
            window.window_ready.connect(self._on_window_ready)
        
        # Handle window close
        original_close = window.closeEvent
        
        def close_handler(event):
            self.window_closed.emit()
            if original_close:
                original_close(event)
        
        window.closeEvent = close_handler
        
        return window
    
    def _on_window_ready(self):
        """Handle window ready signal."""
        self.application_ready.emit()
    
    def launch(self, show: bool = True) -> Tuple[Optional[QApplication], MainWindow]:
        """
        Launch Pipeline Publisher.
        
        Args:
            show: Whether to show the window immediately
        
        Returns:
            Tuple of (application, window). Application may be None in DCC mode.
        """
        # Detect environment and auto-switch mode if needed
        dcc_type = DCCDetector.detect()
        if dcc_type != DCCType.STANDALONE and self.standalone_mode:
            print(f"Detected {dcc_type.display_name} environment, switching to DCC mode")
            self.standalone_mode = False
        
        # Create application
        self.application = self.create_application()
        
        # Create window
        self.window = self.create_window()
        self.window_created.emit(self.window)
        
        # Update window title with environment
        env_label = "Standalone" if self.standalone_mode else dcc_type.display_name
        self.window.setWindowTitle(f"Y Publisher - {env_label}")
        
        # Show window
        if show:
            self.window.show()
            self.window.raise_()
            self.window.activateWindow()
        
        self.is_running = True
        return (self.application, self.window)
    
    def exec_loop(self) -> int:
        """Execute application event loop (standalone mode only)."""
        if not self.standalone_mode:
            print("Event loop should be managed by DCC application")
            return 0
        
        if not self.application:
            print("No application instance created")
            return 1
        
        return self.application.exec()
    
    def cleanup(self):
        """Clean up resources."""
        if self.window and hasattr(self.window, 'cleanup'):
            self.window.cleanup()
        self.is_running = False
    
    def get_version_info(self) -> dict:
        """Get version information (delegated to version module)."""
        return get_version_info()


# Global launcher instance
_launcher: Optional[PublisherLauncher] = None


def launch(standalone_mode: Optional[bool] = None, show: bool = True) -> Tuple[Optional[QApplication], MainWindow]:
    """
    Launch Pipeline Publisher window.
    
    This is the main entry point for launching the publisher.
    Automatically detects the runtime environment unless mode is explicitly specified.
    
    Args:
        standalone_mode: Force standalone mode (auto-detect if None)
        show: Whether to show the window immediately
    
    Returns:
        Tuple of (application, window). Application is None in DCC mode.
    
    Examples:
        >>> app, window = launch()
        >>> app.exec()
        
        >>> _, window = launch(standalone_mode=False)
    """
    global _launcher
    
    # Auto-detect mode if not specified
    if standalone_mode is None:
        dcc_type = DCCDetector.detect()
        standalone_mode = (dcc_type == DCCType.STANDALONE)
    
    # Create and launch
    _launcher = PublisherLauncher(standalone_mode=standalone_mode)
    return _launcher.launch(show=show)


def launch_standalone(show: bool = True) -> Tuple[QApplication, MainWindow]:
    """Launch Publisher in explicit standalone mode."""
    return launch(standalone_mode=True, show=show)


def launch_dcc(show: bool = True) -> Tuple[None, MainWindow]:
    """Launch Publisher in explicit DCC mode."""
    return launch(standalone_mode=False, show=show)


def get_launcher() -> Optional[PublisherLauncher]:
    """Get the current launcher instance (or None if not launched)."""
    return _launcher


def cleanup():
    """Clean up resources from current launcher instance."""
    global _launcher
    if _launcher:
        _launcher.cleanup()
        _launcher = None


def main() -> int:
    """
    Main entry point for standalone execution.
    
    Called when running:
        python -m publisher.main
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        app, window = launch_standalone(show=True)
        app.aboutToQuit.connect(cleanup)
        return app.exec()
    
    except KeyboardInterrupt:
        print("\nPublisher interrupted by user")
        cleanup()
        return 130
    
    except Exception as e:
        print(f"Error launching Publisher: {e}")
        cleanup()
        return 1


if __name__ == "__main__":
    sys.exit(main())
