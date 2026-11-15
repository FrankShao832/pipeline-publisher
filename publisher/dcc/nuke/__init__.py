"""
Nuke integration for Pipeline Publisher.

Provides the in-DCC publisher launch for Nuke, including the pre-publish hook
that flushes the open script to disk before anything is copied.

Usage inside Nuke (from ``~/.nuke/menu.py``):
    from publisher.dcc.launcher import launch_nuke
    launch_nuke()

Or programmatically:
    from publisher.dcc.nuke import NukePublisher
    NukePublisher.launch()
"""

from .publisher import NukePublisher

__all__ = [
    "NukePublisher",
]
