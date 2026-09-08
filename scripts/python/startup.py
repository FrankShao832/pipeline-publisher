"""
Houdini startup script for Pipeline Publisher.

Primary menu path: this script (HOUDINI_STARTUP_PYTHON, injected by
pipeline_hatch) imports the Qt menu builder and schedules the
'Pipeline > Publish...' menu via QTimer (Houdini 20.5 UI-ready timing).

MainMenuCommon.xml remains as an optional XML discovery path only
(loaded if a pipeline_publisher.json package ever adds the publisher
root to HOUDINI_PATH); startup does not depend on it.
"""

import sys
from pathlib import Path


def _get_publisher_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _install_pipeline_menu() -> None:
    """Create the Houdini 'Pipeline' menu (guarded, non-fatal on failure)."""
    try:
        from publisher.dcc.houdini.menu import create_pipeline_menu
        create_pipeline_menu()
    except Exception as exc:  # noqa: BLE001 — never break a Houdini session
        print(f"[Pipeline Publisher] Menu install skipped: {exc}")


def main() -> None:
    root = _get_publisher_root()
    root_str = str(root)

    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    _install_pipeline_menu()

    print(f"[Pipeline Publisher] Initialized. Root: {root_str}")


main()
