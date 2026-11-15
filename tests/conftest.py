"""Pytest bootstrap: make the repository root importable.

The ``publisher`` package lives at the repo root (flat layout, no src/),
so tests need the project root on ``sys.path`` regardless of the working
directory pytest is invoked from.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
