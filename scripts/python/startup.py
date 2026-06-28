"""
Houdini startup script for Pipeline Publisher (safety net).

The Pipeline menu is defined by MainMenuCommon.xml and loaded via
HOUDINI_PATH. This startup script provides additional safeguards:

    1. Ensures sys.path includes the publisher root
    2. Any future per-session initialization

This script is optional — the menu works without it.
"""

import sys
from pathlib import Path


def _get_publisher_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def main() -> None:
    root = _get_publisher_root()
    root_str = str(root)

    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    print(f"[Pipeline Publisher] Initialized. Root: {root_str}")


main()
