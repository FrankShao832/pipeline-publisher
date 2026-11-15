"""UI text sizing must not follow the screen's logical DPI.

Symptom this pins (2026-11-15): after switching the display to 1920x1080 the
publisher's fonts grew but the boxes around them did not, slicing glyphs in
half. The mechanism is a unit mismatch inside a single widget:

* ``font-size: 14pt`` in QSS converts through the screen's logical DPI — 17 px
  tall at 72 dpi, 22 px at 96 dpi (measured, see the two rows below);
* ``setFixedHeight(30)`` / ``setFixedSize(16, 16)`` are device-independent
  pixels and never move.

So the font gained ~30% while its container stayed put. Two rules keep that
from coming back:

1. stylesheets size text in **px** (DPI-invariant, same unit as the boxes);
2. text-bearing widgets take their room from their own metrics instead of a
   frozen pixel box.

The squeeze scan below fails on the two widgets that were actually clipping:
the dev-tools status bar (fixed 30 px against a 36 px requirement) and the
context status dot (fixed 16 x 16 against an 18 x 19 glyph).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

# Qt must see this before it creates a platform plugin, hence module import time.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

UI_DIR = Path(__file__).resolve().parents[1] / "publisher" / "ui"


# ── Rule 1: no point-sized fonts in any publisher stylesheet ────────────


def test_no_point_sized_font_sizes_remain():
    """A single `pt` is enough to make text drift away from its container."""
    offenders: list[str] = []
    for path in sorted(UI_DIR.rglob("*.py")):
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r"font-size:\s*[\d.]+pt", line):
                offenders.append(f"{path.relative_to(UI_DIR)}:{lineno}  {line.strip()}")

    assert offenders == [], (
        "QSS font sizes must be px, not pt (pt scales with logical DPI while "
        "every fixed size around it stays in px):\n" + "\n".join(offenders)
    )


# ── Rule 2: no panel squeezes its own labels or buttons ─────────────────


@pytest.fixture(scope="module")
def qt_app():
    """One offscreen QApplication for the whole module."""
    qt_widgets = pytest.importorskip("PySide6.QtWidgets")
    application = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])
    yield application


def _panels():
    """Instantiate the four panels a publisher window is built from."""
    from publisher.ui.widgets.context_widget import ContextWidget
    from publisher.ui.widgets.dev_tools_widget import DevToolsWidget
    from publisher.ui.widgets.log_widget import LogWidget
    from publisher.ui.widgets.publish_widget import PublishWidget

    return [
        ("Publish", PublishWidget),
        ("Context", ContextWidget),
        ("Log", LogWidget),
        ("DevTools", DevToolsWidget),
    ]


def test_panels_do_not_squeeze_their_text(qt_app):
    """Every visible label/button must get at least its own size hint."""
    from PySide6.QtWidgets import QLabel, QPushButton

    squeezed: list[str] = []

    for tag, widget_class in _panels():
        panel = widget_class()
        panel.resize(560, 620)
        panel.show()
        qt_app.processEvents()

        for widget in panel.findChildren(QLabel) + panel.findChildren(QPushButton):
            if not widget.isVisible() or not widget.text().strip():
                continue
            hint = widget.sizeHint()
            clipped_h = widget.height() < hint.height()
            clipped_w = isinstance(widget, QPushButton) and widget.width() < hint.width()
            if clipped_h or clipped_w:
                squeezed.append(
                    f"{tag}/{widget.__class__.__name__} "
                    f"{widget.width()}x{widget.height()} needs "
                    f"{hint.width()}x{hint.height()}: "
                    f"{widget.text().replace(chr(10), ' ')[:30]!r}"
                )

        panel.close()

    assert squeezed == [], "text widgets are clipped by their container:\n" + "\n".join(squeezed)
