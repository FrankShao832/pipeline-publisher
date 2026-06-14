"""
UI utilities for Pipeline Publisher.

Helper functions and constants for UI development.
"""

from pathlib import Path
from PySide6.QtGui import QIcon


def get_app_icon() -> QIcon:
    """
    Get application icon from the imgs directory.

    Returns:
        QIcon instance. Returns empty QIcon if icon file not found.
    """
    icon_path = Path(__file__).parent.parent / "imgs" / "app_icon.png"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()


def center_window_on_screen(window):
    """
    Center a window on the primary screen.

    Args:
        window: QMainWindow or QWidget instance to center
    """
    from PySide6.QtWidgets import QApplication
    screen = QApplication.primaryScreen()
    if not screen:
        return

    screen_geometry = screen.availableGeometry()
    x = (screen_geometry.width() - window.width()) // 2
    y = (screen_geometry.height() - window.height()) // 2
    window.move(x, y)
