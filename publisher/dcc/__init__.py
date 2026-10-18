"""
DCC integration layer for Pipeline Publisher.

Provides DCC detection and adapters for cross-application compatibility.

Sub-packages:
    dcc.houdini — Houdini menu creation and in-DCC publisher launch
"""

from .dcc_detector import DCCDetector, DCCType
from . import launcher

# Houdini subpackage is importable directly:
#   from publisher.dcc.houdini import HoudiniPublisher, create_pipeline_menu

__all__ = [
    'DCCDetector',
    'DCCType',
    'launcher',
]
