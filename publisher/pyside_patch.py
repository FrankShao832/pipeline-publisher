"""PySide6 → PySide2 compatibility patch.

Run this BEFORE any import of PySide6 to redirect all
'from PySide6.xxx import yyy' statements to use PySide2
(which is what Houdini ships with).

Usage in Houdini entry point (publish_launcher.py):

    import publisher.pyside_patch   # must be FIRST import
    from publisher.dcc.houdini import HoudiniPublisher
    HoudiniPublisher.launch()
"""

import sys

# ── Detect available binding ──

_binding = None
for _candidate in ("PySide6", "PySide2"):
    try:
        __import__(f"{_candidate}.QtWidgets")
        _binding = _candidate
        break
    except ImportError:
        continue

if _binding is None:
    raise ImportError(
        "No Qt binding found. Install PySide6 or PySide2."
    )

# ── Create aliases so 'from PySide6.xxx import yyy' works ──

if _binding == "PySide6":
    # Already using PySide6 — nothing to patch
    pass
elif _binding == "PySide2":
    # Redirect PySide6 → PySide2 in sys.modules
    import importlib

    _pyside6 = type(sys)("PySide6")
    _pyside6.__path__ = []  # mark as package
    sys.modules["PySide6"] = _pyside6

    _mapped_modules = {
        "QtWidgets": "PySide2.QtWidgets",
        "QtCore":    "PySide2.QtCore",
        "QtGui":     "PySide2.QtGui",
    }

    for _sub_name, _pyside2_path in _mapped_modules.items():
        _mod = importlib.import_module(_pyside2_path)
        sys.modules[f"PySide6.{_sub_name}"] = _mod

# Export the binding name for diagnostics
BINDING = _binding
