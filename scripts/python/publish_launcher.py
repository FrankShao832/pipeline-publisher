"""
Pipeline Publisher — Houdini menu launcher.

Called by Houdini's main menu when the user clicks Pipeline > Publish...
The MainMenuCommon.xml scriptPath points to this file.

NOTE: Houdini runs scriptPath scripts via exec(), which does NOT set
      __file__. We use inspect.getsourcefile() with fallback to the
      PIPELINE_PUBLISHER env var set by the launcher.

QT COMPATIBILITY: Houdini 20.5 ships with PySide2+Qt5. The publisher UI
uses PySide6 imports. publisher.pyside_patch redirects PySide6.QtWidgets,
PySide6.QtCore, and PySide6.QtGui to their PySide2 equivalents so
existing UI imports work without changes.
"""

import inspect
import os
import sys
from pathlib import Path


def _get_publisher_root() -> Path:
    """Determine the pipeline_publisher root directory.

    Strategies (in order):
        1. inspect.getsourcefile(lambda: None) — works in most Houdini contexts
        2. PIPELINE_PUBLISHER env var — set by pipeline_hatch launcher
    """
    try:
        frame_path = inspect.getsourcefile(lambda: None)
        if frame_path:
            return Path(frame_path).resolve().parent.parent.parent
    except (TypeError, OSError):
        pass

    env_path = os.environ.get("PIPELINE_PUBLISHER", "")
    if env_path:
        return Path(env_path).resolve()

    raise RuntimeError(
        "[Pipeline Publisher] Cannot determine root — "
        "PIPELINE_PUBLISHER not set and inspect.getsourcefile() failed."
    )


def main() -> None:
    """Entry point — launch the Pipeline Publisher UI inside Houdini."""
    root = _get_publisher_root()
    root_str = str(root)

    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    try:
        # PySide6→PySide2 redirect must run before any PySide6 imports
        import publisher.pyside_patch  # noqa: F401

        from publisher.dcc.houdini import HoudiniPublisher
        HoudiniPublisher.launch()
    except Exception as e:
        print(f"[Pipeline Publisher] Failed to launch: {e}")
        import traceback
        traceback.print_exc()


main()
