"""
DCC integration layer for Pipeline Publisher.

Provides DCC detection and adapters for cross-application compatibility.

Sub-packages:
    dcc.houdini — Houdini menu creation and in-DCC publisher launch
    dcc.maya    — Maya in-DCC publisher launch
    dcc.nuke    — Nuke in-DCC publisher launch (and the pre-publish save hook)
"""

from .dcc_detector import DCCDetector, DCCType
from . import launcher

# DCC subpackages are importable directly:
#   from publisher.dcc.houdini import HoudiniPublisher, create_pipeline_menu
#   from publisher.dcc.nuke import NukePublisher

__all__ = [
    'DCCDetector',
    'DCCType',
    'launcher',
]
