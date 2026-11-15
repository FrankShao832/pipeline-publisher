"""The publisher window must fit whatever screen it opens on.

Regression this pins (2026-11-15): the window asked for 500x1224 with a layout
minimum around 1225 px. On a 3008x1692 logical desktop that was fine; after the
display was set to 1920x1080 (1055 px usable) the window's bottom sat 170 px
below the screen edge, and the edge cut the last visible row in half — which
looks exactly like a font being sliced.

The arithmetic is Qt-free on purpose: what matters is that the initial size
never exceeds the available area and that the minimum stays small enough for
the scroll area to take over.
"""

from __future__ import annotations

import pytest

from publisher.ui.window_geometry import (
    DEFAULT_WIDTH,
    MIN_HEIGHT,
    MIN_WIDTH,
    PREFERRED_HEIGHT,
    fit_window_to_screen,
)


def test_1080p_screen_gets_a_window_that_fits():
    """1920x1080 leaves 1055 px of usable height — the window must stay inside."""
    minimum, initial = fit_window_to_screen(1920, 1055)

    width, height = initial
    assert height <= 1055, "window taller than the usable screen area"
    assert width <= 1920
    assert height < PREFERRED_HEIGHT, "should have been clamped below the preferred height"
    assert width == DEFAULT_WIDTH

    # And it must still be shrinkable, because the content is ~1225 px tall.
    assert minimum[1] <= height


def test_large_desktop_keeps_the_designed_size():
    """On a big desktop nothing changes: the preferred shape is kept."""
    minimum, initial = fit_window_to_screen(3008, 1667)

    assert initial == (DEFAULT_WIDTH, PREFERRED_HEIGHT)
    assert minimum == (MIN_WIDTH, MIN_HEIGHT)


def test_tiny_screen_falls_back_to_the_floors():
    """A comically small area must not produce zero or negative sizes."""
    minimum, initial = fit_window_to_screen(400, 300)

    width, height = initial
    assert width >= MIN_WIDTH
    assert height >= MIN_HEIGHT
    assert width <= 400
    assert height <= 300


@pytest.mark.parametrize(
    "avail",
    [(1920, 1055), (2560, 1400), (3840, 2100), (1280, 700), (800, 500)],
)
def test_initial_never_exceeds_the_screen_and_minimum_never_exceeds_initial(avail):
    """Universal invariant across every screen size we care about."""
    (min_w, min_h), (width, height) = fit_window_to_screen(*avail)

    assert width <= avail[0]
    assert height <= avail[1]
    assert min_w <= width
    assert min_h <= height
