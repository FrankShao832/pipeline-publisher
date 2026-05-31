"""
DCC integration layer for Pipeline Publisher.

Provides DCC detection and adapters for cross-application compatibility.
"""

from .dcc_detector import DCCDetector, DCCType
from . import launcher

__all__ = [
    'DCCDetector',
    'DCCType',
    'launcher',
]
