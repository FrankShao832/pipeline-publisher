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
from publisher.core.file_system.department_path import (
    normalize_dcc,
    resolve_source_dir,
)


def detect_source_file(
    context: dict,
    project_root: Optional[str] = None,
) -> Optional[Tuple[str, str]]:
    """Scan work directory for a source file matching current pipeline context.

    The work directory is resolved department-first through the three shapes
    ``<shot>/<dept>/<dcc>`` -> ``<shot>/<dept>`` -> ``<shot>/<dcc>`` (see
    publisher.core.file_system.department_path), so a shot whose work lives in
    ``fx/houdini`` is found as reliably as one that lives in ``comp``.

    Args:
        context: Pipeline context dict with keys:
                 'project', 'sequence', 'shot', 'department'
                 plus optional 'dcc' (used to disambiguate multi-app departments)
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

    # Explicit dcc wins; otherwise fall back to the department's usual app.
    dcc = normalize_dcc(context.get('dcc')) or get_dcc_for_department(department)
    resolved = resolve_source_dir(
        project_root, project, sequence, shot, department, dcc,
    )
    if resolved is None:
        return None
    source_dir = resolved.path

    patterns = get_extensions_for_dcc(dcc)

    matches = []
    for pattern in patterns:
        matches.extend(f for f in source_dir.glob(pattern) if f.is_file())

    # Fallback: scan all files if no DCC-specific match
    if not matches:
        matches = sorted(f for f in source_dir.iterdir() if f.is_file())

    if not matches:
        return None

    # Deterministic pick: highest numeric version, then newest mtime.
    def _key(f: Path):
        ver = _extract_version(f.stem)
        num = int(ver[1:]) if ver else -1
        return (num, f.stat().st_mtime)

    best = max(matches, key=_key)
    version = _extract_version(best.stem)
    return (str(best), version)


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
