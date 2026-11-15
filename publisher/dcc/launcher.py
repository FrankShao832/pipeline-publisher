"""
DCC-specific launcher functions for Pipeline Publisher.

Provides convenience functions for launching the publisher
from specific DCC environments (Maya, Houdini, Nuke).
"""

from __future__ import annotations

from typing import Optional, Tuple, Any
from PySide6.QtWidgets import QApplication


def _launch_dcc_shell(
    standalone_mode: bool = False,
    show: bool = True,
    title_suffix: Optional[str] = None,
) -> Tuple[Optional[QApplication], MainWindow]:
    """
    Internal helper for launching publisher in DCC context.

    Args:
        standalone_mode: Whether to run in standalone mode
        show: Whether to show the window immediately
        title_suffix: Optional suffix for window title

    Returns:
        Tuple of (application, window). Application may be None in DCC mode.
    """
    from publisher.main import launch
    from publisher.ui.main_window import MainWindow

    _, window = launch(standalone_mode=standalone_mode, show=show)
    if window and title_suffix:
        window.setWindowTitle(f"Y Publisher - {title_suffix}")

    return (None, window)


def launch_maya(show: bool = True) -> Tuple[None, MainWindow]:
    """
    Launch Publisher for Maya integration.

    Sets the window title to indicate Maya mode.

    Args:
        show: Whether to show the window immediately

    Returns:
        Tuple of (None, window) - Application is None in DCC mode
    """
    return _launch_dcc_shell(standalone_mode=False, show=show, title_suffix="Maya")


def launch_houdini(show: bool = True) -> Tuple[None, MainWindow]:
    """
    Launch Publisher for Houdini integration.

    Sets the window title to indicate Houdini mode.

    Args:
        show: Whether to show the window immediately

    Returns:
        Tuple of (None, window) - Application is None in DCC mode
    """
    return _launch_dcc_shell(standalone_mode=False, show=show, title_suffix="Houdini")


def launch_nuke(show: bool = True) -> Tuple[None, MainWindow]:
    """
    Launch Publisher for Nuke integration.

    Delegates to :class:`publisher.dcc.nuke.publisher.NukePublisher`, which adds
    the one thing the generic shell cannot know: a pre-publish hook. Without it
    the publish copies whatever Nuke last wrote to disk — on 2026-11-08 that was
    a 190-byte template while the session held 2,573 bytes of nodes.

    Args:
        show: Whether to show the window immediately

    Returns:
        Tuple of (None, window) - Application is None in DCC mode
    """
    from publisher.dcc.nuke.publisher import NukePublisher

    return (None, NukePublisher.launch(show=show))
