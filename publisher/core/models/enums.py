"""
Enumerations for Pipeline Publisher domain models.

Defines all enum types used across the application for type safety
and consistency between different DCC environments.
"""

from enum import Enum, auto


class DCCType(Enum):
    """Supported DCC application types."""
    MAYA = "maya"
    HOUDINI = "houdini"
    NUKE = "nuke"
    STANDALONE = "standalone"

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        names = {
            'maya': 'Maya',
            'houdini': 'Houdini',
            'nuke': 'Nuke',
            'standalone': 'Standalone',
        }
        return names.get(self.value, self.value)


class PublishType(Enum):
    """Types of publish operations."""
    SCRIPT = "script"          # Scene/script file publish
    RENDER = "render"          # Rendered output publish
    CACHE = "cache"            # Cache file publish
    REFERENCE = "reference"    # Reference/asset publish
    TEXTURE = "texture"        # Texture publish
    OTHER = "other"            # Other file types

    def __str__(self) -> str:
        return self.value


class EntityType(Enum):
    """Types of publishable entities."""
    SCENE = "scene"            # Full scene file (.ma, .hip, .nk)
    ASSET = "asset"            # Individual asset
    SHOT = "shot"              # Shot-level publish
    SEQUENCE = "sequence"      # Sequence-level publish
    OUTPUT = "output"          # Render/Cache output
    DEPENDENCY = "dependency"  # External dependency

    def __str__(self) -> str:
        return self.value


class VersionStrategy(Enum):
    """Version management strategies for publishing."""
    AUTO_INCREMENT = auto()    # Auto-increment: v001 -> v002
    MANUAL = auto()            # User-specified version
    OVERWRITE = auto()         # Overwrite current version
    DATE_BASED = auto()        # Date-based: 20260530_001

    def __str__(self) -> str:
        return self.name.lower().replace('_', ' ')

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        names = {
            'AUTO_INCREMENT': 'Auto Increment',
            'MANUAL': 'Manual',
            'OVERWRITE': 'Overwrite',
            'DATE_BASED': 'Date Based',
        }
        return names.get(self.name, self.name)


class PublishStatus(Enum):
    """Status of a publish record."""
    CURRENT = "current"        # Current active version
    ARCHIVED = "archived"      # Archived (still accessible)
    OBSOLETE = "obsolete"      # Obsolete (superseded)
    FAILED = "failed"          # Publish failed

    def __str__(self) -> str:
        return self.value
