"""
Source file detection utilities for Pipeline Publisher UI.

Provides functions to scan work directories for source files
matching the current pipeline context and DCC type.

Uses centralized constants for DCC extensions and department→DCC mapping.
See publisher.core.constants for the authoritative definitions.
"""

import os
import re
from pathlib import Path
from typing import Optional, Tuple

from publisher.core.constants import (
    DCC_EXTENSIONS,
    DEPARTMENT_DCC_MAP,
    get_extensions_for_dcc,
    get_dcc_for_department,
)


def detect_source_file(
    context: dict,
    project_root: Optional[str] = None,
) -> Optional[Tuple[str, str]]:
    """Scan work directory for a source file matching current pipeline context.

    Constructs the path {project_root}/{project}/{seq}/{shot}/{department}/ and
    looks for DCC-specific files using the department→DCC mapping.

    Args:
        context: Pipeline context dict with keys:
                 'project', 'sequence', 'shot', 'department'
        project_root: Optional project root path (falls back to env var
                      PROJECT_ROOT if not provided)

    Returns:
        Tuple of (source_path, version_string) if a matching file is found,
        e.g. ('/path/to/shot001_v001.hip', 'v001').
        Returns None if no matching file is found or context is incomplete.
    """
    project = context.get('project', '')
    sequence = context.get('sequence', '')
    shot = context.get('shot', '')
    department = context.get('department', '')

    if not project_root:
        project_root = os.getenv('PROJECT_ROOT', '')

    if not all([project, sequence, shot, department, project_root]):
        return None

    source_dir = Path(project_root) / project / sequence / shot / department
    if not source_dir.exists():
        return None

    # Determine likely DCC from department, then get extension patterns
    dcc = get_dcc_for_department(department)
    patterns = get_extensions_for_dcc(dcc)

    matches = []
    for pattern in patterns:
        matches.extend(source_dir.glob(pattern))

    # Fallback: scan all files if no DCC-specific match
    if not matches:
        matches = sorted(source_dir.iterdir())

    if not matches:
        return None

    # Extract version from filename (e.g., shot001_v001.hip → v001)
    source_path = str(matches[0])
    version = _extract_version(matches[0].stem)

    return (source_path, version)


def _extract_version(filename_stem: str) -> Optional[str]:
    """Extract version string from filename stem.

    Looks for pattern _v001, _v002, etc. (case insensitive).

    Args:
        filename_stem: Filename without extension (e.g., 'shot001_v001')

    Returns:
        Version string like 'v001', or None if no version pattern found.
    """
    match = re.search(r'_v(\d+)', filename_stem, re.IGNORECASE)
    if match:
        padding = len(match.group(1))
        num = int(match.group(1))
        return f"v{str(num).zfill(padding)}"
    return None
