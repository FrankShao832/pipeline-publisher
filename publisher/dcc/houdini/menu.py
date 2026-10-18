"""
Houdini pipeline menu integration.

Creates a "Pipeline" top-level menu in the Houdini menu bar
with a "Publish..." action that launches the Publisher UI.

Safe to call multiple times — guards against duplicate menu creation.

NOTE: Houdini 20.5's hou.ui does NOT expose addMenu() for the main
menu bar. We use Qt directly: get Houdini's main window via
hou.qt.mainWindow(), find the QMenuBar child widget, and add a QMenu.

TIMING: HOUDINI_STARTUP_PYTHON runs before the UI is fully ready, so
hou.qt.mainWindow() may return None during initial startup. We schedule
menu creation via QTimer.singleShot to run after the event loop starts.
"""

from __future__ import annotations

import hou

from .publisher import HoudiniPublisher

# Module-level reference to prevent duplicate menu creation
_PIPELINE_MENU = None
_PIPELINE_ACTION = None


def create_pipeline_menu() -> None:
    """Create the 'Pipeline' menu in the Houdini main menu bar.

    Safe to call multiple times — the menu is only created once.
    """
    global _PIPELINE_MENU, _PIPELINE_ACTION

    if _PIPELINE_MENU is not None:
        return

    # Defer to next event loop iteration so the main window is ready
    from PySide2.QtCore import QTimer
    QTimer.singleShot(0, _create_menu)


def _create_menu() -> None:
    """Internal: actually create the menu (called after main window is ready)."""
    global _PIPELINE_MENU, _PIPELINE_ACTION

    if _PIPELINE_MENU is not None:
        return

    try:
        # PySide2 — must match Houdini's internal Qt binding
        from PySide2.QtWidgets import QMenu, QMenuBar

        main_window = hou.qt.mainWindow()
        if main_window is None:
            print("[Pipeline Publisher] Houdini main window not ready — will retry.")
            # Schedule another attempt
            from PySide2.QtCore import QTimer
            QTimer.singleShot(500, _create_menu)
            return

        # Houdini's main window is a plain QWidget (not QMainWindow), so
        # menuBar() is not available. Find the QMenuBar as a child widget.
        menu_bar = main_window.findChild(QMenuBar)
        if menu_bar is None:
            print("[Pipeline Publisher] Could not find Houdini menu bar (QMenuBar) — skipping menu creation.")
            return

        # Create the Pipeline menu
        pipeline_menu = QMenu("Pipeline", main_window)

        # Add Publish... action
        publish_action = pipeline_menu.addAction("Publish...")
        publish_action.triggered.connect(_on_publish)

        # Insert before the "Help" menu if possible, otherwise append
        help_actions = menu_bar.actions()
        help_menu = None
        for a in help_actions:
            if a.text() == "Help":
                help_menu = a
                break

        if help_menu is not None:
            menu_bar.insertMenu(help_menu, pipeline_menu)
        else:
            menu_bar.addMenu(pipeline_menu)

        _PIPELINE_MENU = pipeline_menu
        _PIPELINE_ACTION = publish_action

        print("[Pipeline Publisher] 'Pipeline > Publish...' menu created.")

    except Exception as e:
        print(f"[Pipeline Publisher] Failed to create menu: {e}")


def _on_publish() -> None:
    """Slot: launched when user clicks Pipeline > Publish..."""
    try:
        HoudiniPublisher.launch()
    except Exception as e:
        print(f"[Pipeline Publisher] Publish launch failed: {e}")


def remove_pipeline_menu() -> None:
    """Remove the Pipeline menu from Houdini (cleanup/teardown)."""
    global _PIPELINE_MENU, _PIPELINE_ACTION

    if _PIPELINE_MENU is not None:
        try:
            _PIPELINE_MENU.deleteLater()
            _PIPELINE_MENU = None
            _PIPELINE_ACTION = None
            print("[Pipeline Publisher] Pipeline menu removed.")
        except Exception as e:
            print(f"[Pipeline Publisher] Failed to remove menu: {e}")
