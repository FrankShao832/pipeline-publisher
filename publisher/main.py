"""
Unified entry point for Pipeline Publisher.

Supports multiple modes:
- Standalone mode: python -m publisher.main
- DCC integration: import publisher.main; publisher.main.launch()
- Programmatic usage: Flexible API for various use cases
"""

import sys
import os
from pathlib import Path
from typing import Optional, Tuple, Any

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Signal, QObject
import PySide6

from publisher.ui.main_window import MainWindow
from publisher.dcc.dcc_detector import DCCDetector, DCCType

# Version information
__version__ = "2.0.0"
__author__ = "Frank"


class PublisherLauncher(QObject):
    """
    Publisher launcher for managing application lifecycle.
    
    Handles window creation, event loop management, and cleanup.
    Provides a clean interface for both standalone and DCC-integrated usage.
    """
    
    # Signals for lifecycle events
    window_created = Signal(object)  # Emitted when window is created
    application_ready = Signal()   # Emitted when app is ready
    window_closed = Signal()        # Emitted when window is closed
    
    def __init__(self, standalone_mode: bool = True, parent: Optional[QObject] = None):
        """Initialize publisher launcher."""
        super().__init__(parent)
        
        self.standalone_mode = standalone_mode
        self.application = None
        self.window = None
        self.is_running = False
    
    def detect_environment(self) -> str:
        """Detect current runtime environment."""
        try:
            import maya.cmds as cmds
            return "maya"
        except ImportError:
            pass
        
        try:
            import hou
            return "houdini"
        except ImportError:
            pass
        
        try:
            import nuke
            return "nuke"
        except ImportError:
            pass
        
        return "standalone"
    
    def create_application(self) -> QApplication:
        """Create or get existing QApplication instance."""
        existing_app = QApplication.instance()
        
        if existing_app:
            return existing_app
        
        app = QApplication(sys.argv)
        app.setApplicationName("Pipeline Publisher")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("Pipeline Team")
        
        # Set dark theme style
        app.setStyle('Fusion')
        
        # Configure application
        self._configure_application(app)
        
        return app
    
    def _configure_application(self, app: QApplication):
        """Configure application settings."""
        # For Qt6, high DPI scaling is enabled by default
        # No need for manual configuration anymore
        
        # Set application metadata
        try:
            app.setWindowIcon(self._get_app_icon())
        except Exception:
            pass  # Icon is optional
    
    def _get_app_icon(self):
        """Get application icon."""
        from PySide6.QtGui import QIcon
        icon_path = Path(__file__).parent / "ui" / "imgs" / "app_icon.png"
        if icon_path.exists():
            return QIcon(str(icon_path))
        return QIcon()
    
    def _get_qt_version(self) -> str:
        """Get Qt version."""
        try:
            from PySide6.QtCore import QT_VERSION_STR
            return QT_VERSION_STR
        except ImportError:
            return "unknown"
    
    def _get_pyside6_version(self) -> str:
        """Get PySide6 version."""
        try:
            import PySide6
            return PySide6.__version__
        except (ImportError, AttributeError):
            return "unknown"
    
    def create_window(self) -> MainWindow:
        """Create main window instance."""
        window = MainWindow(standalone_mode=self.standalone_mode)
        window.setWindowTitle(f"Pipeline Publisher v1.0.0")
        
        # Connect window signals
        if hasattr(window, 'window_ready'):
            window.window_ready.connect(self._on_window_ready)
        
        # Handle window close
        window.closeEvent = self._create_close_handler(window.closeEvent)
        
        return window
    
    def _create_close_handler(self, original_close_event):
        """Create custom close event handler."""
        def close_handler(event):
            self.window_closed.emit()
            original_close_event(event)
        return close_handler
    
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
        # Detect environment
        environment = self.detect_environment()
        
        # Auto-detect mode if not explicitly set
        if environment != "standalone" and self.standalone_mode:
            print(f"Detected {environment} environment, switching to DCC mode")
            self.standalone_mode = False
        
        # Create application
        self.application = self.create_application()
        
        # Create window
        self.window = self.create_window()
        
        # Emit signal
        self.window_created.emit(self.window)
        
        # Show window
        if show:
            self.window.show()
            self.window.raise_()
            self.window.activateWindow()
        
        # Update window title with environment
        env_label = "Standalone" if self.standalone_mode else environment.upper()
        self.window.setWindowTitle(f"Pipeline Publisher - {env_label}")
        
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
        if self.window:
            if hasattr(self.window, 'cleanup'):
                self.window.cleanup()
        
        self.is_running = False
    
    def get_dcc_info(self) -> dict:
        """Get detailed DCC information."""
        from publisher.dcc.dcc_detector import DCCDetector, DCCType
        
        dcc_type = self._detect_dcc_type()
        return DCCDetector.get_dcc_info(dcc_type)
    
    def get_version_info(self) -> dict:
        """Get version information."""
        return {
            'publisher_version': __version__,
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'qt_version': self._get_qt_version(),
            'pyside6_version': self._get_pyside6_version()
        }
    
    def _detect_dcc_type(self):
        """Detect current DCC type."""
        from publisher.dcc.dcc_detector import DCCDetector, DCCType
        return DCCDetector.detect()


# Global launcher instance
_launcher = None


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
        >>> # Standalone mode
        >>> app, window = launch()
        >>> app.exec()
        
        >>> # DCC integration
        >>> _, window = launch(standalone_mode=False)
        
        >>> # With auto-detection
        >>> _, window = launch()  # Auto-detects environment
    """
    global _launcher
    
    # Detect environment if mode not specified
    if standalone_mode is None:
        launcher = PublisherLauncher(standalone_mode=True)
        environment = launcher.detect_environment()
        standalone_mode = (environment == "standalone")
    
    # Create launcher with determined mode
    _launcher = PublisherLauncher(standalone_mode=standalone_mode)
    
    # Launch publisher
    return _launcher.launch(show=show)


def launch_standalone(show: bool = True) -> Tuple[QApplication, MainWindow]:
    """
    Launch Publisher in standalone mode.
    
    Convenience function for explicit standalone mode launching.
    
    Args:
        show: Whether to show the window immediately
    
    Returns:
        Tuple of (application, window)
    """
    return launch(standalone_mode=True, show=show)


def launch_dcc(show: bool = True) -> Tuple[None, MainWindow]:
    """
    Launch Publisher in DCC mode.
    
    Convenience function for DCC-integrated launching.
    
    Args:
        show: Whether to show the window immediately
    
    Returns:
        Tuple of (None, window) - Application is None in DCC mode
    """
    return launch(standalone_mode=False, show=show)


# DCC-specific convenience functions
def launch_maya(show: bool = True) -> Tuple[None, MainWindow]:
    """Launch Publisher for Maya integration."""
    _, window = launch(standalone_mode=False, show=show)
    if window:
        window.setWindowTitle("Pipeline Publisher - Maya")
    return (None, window)


def launch_houdini(show: bool = True) -> Tuple[None, MainWindow]:
    """Launch Publisher for Houdini integration."""
    _, window = launch(standalone_mode=False, show=show)
    if window:
        window.setWindowTitle("Pipeline Publisher - Houdini")
    return (None, window)


def launch_nuke(show: bool = True) -> Tuple[None, MainWindow]:
    """Launch Publisher for Nuke integration."""
    _, window = launch(standalone_mode=False, show=show)
    if window:
        window.setWindowTitle("Pipeline Publisher - Nuke")
    return (None, window)


def get_launcher() -> Optional[PublisherLauncher]:
    """
    Get the current launcher instance.
    
    Returns:
        Current PublisherLauncher instance or None if not launched
    """
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
    
    This function is called when running the module as a script:
    python -m publisher.main
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Launch publisher in standalone mode
        app, window = launch_standalone(show=True)
        
        # Connect cleanup on quit
        app.aboutToQuit.connect(cleanup)
        
        # Run application
        return app.exec()
    
    except KeyboardInterrupt:
        print("\nPublisher interrupted by user")
        cleanup()
        return 130
    
    except Exception as e:
        print(f"Error launching Publisher: {e}")
        cleanup()
        return 1


def test_launch():
    """
    Test function for development and debugging.
    
    Launches publisher with additional debugging output.
    """
    print("=" * 60)
    print("Pipeline Publisher - Test Launch")
    print("=" * 60)
    
    # Create launcher with detailed info
    launcher = PublisherLauncher(standalone_mode=True)
    
    # Detect environment
    environment = launcher.detect_environment()
    print(f"Detected environment: {environment}")
    print(f"Standalone mode: {launcher.standalone_mode}")
    
    # Launch with signals
    launcher.window_created.connect(lambda w: print(f"✓ Window created: {w}"))
    launcher.application_ready.connect(lambda: print("✓ Application ready"))
    
    # Launch publisher
    app, window = launcher.launch()
    
    print("✓ Publisher launched successfully")
    print("=" * 60)
    
    return app, window


if __name__ == "__main__":
    sys.exit(main())