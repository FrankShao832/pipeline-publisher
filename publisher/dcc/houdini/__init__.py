"""
Houdini integration for Pipeline Publisher.

Provides Houdini-specific context detection, menu creation,
and in-DCC publisher launch via PublisherController + MainWindow.

Usage in Houdini (via startup.py):
    from publisher.dcc.houdini import create_pipeline_menu
    create_pipeline_menu()

Or programmatically:
    from publisher.dcc.houdini import HoudiniPublisher
    HoudiniPublisher.launch()
"""

from .menu import create_pipeline_menu
from .publisher import HoudiniPublisher

__all__ = [
    "create_pipeline_menu",
    "HoudiniPublisher",
]
