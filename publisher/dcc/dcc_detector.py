"""
DCC detector for Pipeline Publisher.

Automatically detects the currently running DCC application.
"""

import sys
from typing import Optional
from enum import Enum


class DCCType(Enum):
    """Supported DCC applications."""
    MAYA = "maya"
    HOUDINI = "houdini" 
    NUKE = "nuke"
    STANDALONE = "standalone"


class DCCDetector:
    """Detects the currently running DCC application."""
    
    @staticmethod
    def detect() -> DCCType:
        """Detect the current DCC application."""
        # Check for Maya
        if DCCDetector._is_maya():
            return DCCType.MAYA
        
        # Check for Houdini
        if DCCDetector._is_houdini():
            return DCCType.HOUDINI
        
        # Check for Nuke
        if DCCDetector._is_nuke():
            return DCCType.NUKE
        
        # Default to standalone
        return DCCType.STANDALONE
    
    @staticmethod
    def _is_maya() -> bool:
        """Check if running in Maya."""
        try:
            import maya.cmds as cmds
            return True
        except ImportError:
            return False
    
    @staticmethod
    def _is_houdini() -> bool:
        """Check if running in Houdini."""
        try:
            import hou
            return True
        except ImportError:
            return False
    
    @staticmethod
    def _is_nuke() -> bool:
        """Check if running in Nuke."""
        try:
            import nuke
            return True
        except ImportError:
            return False
    
    @staticmethod
    def get_dcc_info(dcc_type: DCCType) -> dict:
        """Get information about the DCC."""
        info = {
            'type': dcc_type.value,
            'name': dcc_type.value.upper(),
            'available': False,
            'version': 'unknown'
        }
        
        try:
            if dcc_type == DCCType.MAYA:
                import maya.cmds as cmds
                info['available'] = True
                info['version'] = cmds.about(version=True)
                
            elif dcc_type == DCCType.HOUDINI:
                import hou
                info['available'] = True
                info['version'] = hou.applicationVersionString()
                
            elif dcc_type == DCCType.NUKE:
                import nuke
                info['available'] = True
                info['version'] = nuke.NUKE_VERSION_STRING
                
            elif dcc_type == DCCType.STANDALONE:
                info['available'] = True
                info['version'] = f"Python {sys.version.split()[0]}"
                
        except Exception as e:
            info['error'] = str(e)
        
        return info