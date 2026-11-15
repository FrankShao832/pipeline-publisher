"""Window geometry that always fits the screen it opens on.

The publisher window stacks five blocks vertically (context, dev tools,
publish, log, footer). Their natural minimum is ~1225 px tall, which was fine
on a 3008x1692 logical desktop and is *not* fine on 1920x1080 (1055 px of
usable height): the bottom of the window ended up off-screen and the screen
edge sliced the last visible row in half — what looked like "the font is cut".

Two rules, both tested here:

* the initial size never exceeds the screen's available area;
* the minimum height stays small enough that the window can always be shrunk —
  the content scrolls instead of being clipped.

Kept Qt-free so the arithmetic can be pinned by unit tests.
"""

from __future__ import annotations

#: Preferred window width / height (the shape the UI was designed in).
DEFAULT_WIDTH = 520
PREFERRED_HEIGHT = 1224

#: Never touch the screen edges: menu bar, dock and shadows need room.
SCREEN_MARGIN_X = 40
SCREEN_MARGIN_Y = 20

#: Hard floors — below this the layout is unreadable, scroll or not.
MIN_WIDTH = 360
MIN_HEIGHT = 240


def fit_window_to_screen(avail_width: int, avail_height: int) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return ``((min_w, min_h), (width, height))`` for the available screen.

    Args:
        avail_width: Screen's available width in logical pixels.
        avail_height: Screen's available height in logical pixels (menu bar and
            dock already excluded).

    Returns:
        A ``(minimum_size, initial_size)`` pair. The initial size never exceeds
        the available area; the minimum never exceeds the initial size.
    """
    width = min(DEFAULT_WIDTH, max(MIN_WIDTH, avail_width - SCREEN_MARGIN_X))
    height = min(PREFERRED_HEIGHT, max(MIN_HEIGHT, avail_height - SCREEN_MARGIN_Y))
    minimum = (min(MIN_WIDTH, width), min(MIN_HEIGHT, height))
    return minimum, (width, height)
