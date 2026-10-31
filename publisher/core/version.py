"""
Version information for Pipeline Publisher.

Provides unified access to all version-related information
about the publisher and its runtime environment.
"""

import sys
from typing import Dict


# Publisher version
__version__ = "2.1.0"
__author__ = "Frank"


def get_publisher_version() -> str:
    """Get the publisher application version."""
    return __version__


def get_python_version() -> str:
    """Get the current Python version string."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def get_qt_version() -> str:
    """Get the Qt framework version."""
    try:
        from PySide6.QtCore import QT_VERSION_STR
        return QT_VERSION_STR
    except ImportError:
        return "unknown"


def get_pyside6_version() -> str:
    """Get the PySide6 version."""
    try:
        import PySide6
        return PySide6.__version__
    except (ImportError, AttributeError):
        return "unknown"


def get_version_info() -> Dict[str, str]:
    """
    Get complete version information as a dictionary.
    
    Returns:
        Dictionary with all version components
    """
    return {
        'publisher_version': __version__,
        'python_version': get_python_version(),
        'qt_version': get_qt_version(),
        'pyside6_version': get_pyside6_version(),
    }


def print_version_info():
    """Print version information to console."""
    info = get_version_info()
    print(f"Pipeline Publisher v{info['publisher_version']}")
    print(f"Python: {info['python_version']}")
    print(f"Qt: {info['qt_version']}")
    print(f"PySide6: {info['pyside6_version']}")
