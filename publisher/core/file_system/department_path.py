"""Department-first resolution of a shot's work directory.

Two axes meet here:

* ``department`` is the **data axis** — it owns paths, version counters,
  approvals and farm pools.
* ``dcc`` is the **runtime axis** — which application opened the file.

A department may own more than one application, so a shot's work directory
has one canonical shape per department plus one legacy shape:

    <shot>/<department>/<dcc>    most specific — fx opened in houdini
    <shot>/<department>          the common case
    <shot>/<dcc>                 legacy tree written before the vocabulary fix

Resolution is **department first** on purpose: dcc -> department is 1:N, so a
directory named after an application cannot tell us who owns the data. The
legacy shape stays readable as a compatibility layer, but it never decides
identity — a legacy hit still publishes under ``department``.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

# Application names that are allowed to appear as a path segment *inside* a
# department. Anything outside this set is treated as a department segment, so
# a stray directory can never be mistaken for an application.
DCC_TOKENS = frozenset({
    'maya',
    'houdini',
    'nuke',
    'nukestudio',
    'katana',
    'blender',
    'standalone',
})


def normalize_dcc(value: Union[str, None]) -> str:
    """Normalize a DCC name to its lowercase path token.

    Accepts both the enum value (``houdini``) and the UI display name
    (``Houdini``), plus the friendly ``Nuke Studio`` spelling.

    Returns an empty string when the value is unknown/empty, so callers can use
    a plain truthiness test.
    """
    if not value:
        return ''
    token = str(value).strip().lower().replace(' ', '')
    return token if token in DCC_TOKENS else ''


def is_dcc_token(value: str) -> bool:
    """True when *value* names an application rather than a department."""
    return bool(value) and value.strip().lower() in DCC_TOKENS


@dataclass(frozen=True)
class SourceDir:
    """A resolved work directory plus the publish path stem it implies."""

    path: Path
    stem: str                  # "fx/houdini" (nested) or "comp" (flat)
    department: str
    dcc: Optional[str] = None  # set only when the directory is nested
    legacy: bool = False       # resolved through the old <shot>/<dcc> shape


def shot_dir(project_root: str, project: str, sequence: str, shot: str) -> Path:
    """Build the per-shot directory that contains all department folders."""
    return Path(project_root) / project / sequence / shot


def resolve_source_dir(
    project_root: str,
    project: str,
    sequence: str,
    shot: str,
    department: str,
    dcc: str = '',
) -> Optional[SourceDir]:
    """Locate the work directory for *department* inside a shot.

    Order: ``<dept>/<dcc>`` -> ``<dept>`` -> ``<dcc>`` (legacy).

    Returns ``None`` when the shot has no directory for that department at all,
    which is the normal state for a shot before any work is started.
    """
    if not all([project_root, project, sequence, shot, department]):
        return None

    root = shot_dir(project_root, project, sequence, shot)
    token = normalize_dcc(dcc)

    if token:
        nested = root / department / token
        if nested.is_dir():
            return SourceDir(
                path=nested,
                stem=f'{department}/{token}',
                department=department,
                dcc=token,
            )

    flat = root / department
    if flat.is_dir():
        return SourceDir(path=flat, stem=department, department=department)

    if token:
        legacy = root / token
        if legacy.is_dir():
            # Compatibility only: readable, but the data still belongs to the
            # department, so the publish stem stays department-keyed.
            return SourceDir(
                path=legacy,
                stem=department,
                department=department,
                legacy=True,
            )

    return None


def publish_stem_for_source(
    source_path: Union[str, Path],
    project_root: str,
    project: str,
    sequence: str,
    shot: str,
    department: str,
) -> str:
    """Derive the publish path stem from where the source file actually lives.

    Reading the source's own location beats guessing from the department->dcc
    map: a shot may hold ``fx/houdini`` while another keeps ``comp`` flat, and
    the publish tree should mirror the work tree it came from.

    Falls back to the bare ``department`` when the source lives outside the
    shot (or in a legacy ``<shot>/<dcc>`` folder), so a publish can never
    silently invent a nesting level.
    """
    try:
        rel = Path(source_path).parent.resolve().relative_to(
            shot_dir(project_root, project, sequence, shot).resolve()
        )
    except (ValueError, OSError):
        return department

    parts = rel.parts
    if not parts or parts[0] != department:
        return department
    if len(parts) >= 2 and is_dcc_token(parts[1]):
        return f'{department}/{parts[1]}'
    return department


def split_stem(stem: str) -> tuple:
    """Split a publish stem into ``(department, dcc_or_None)``."""
    parts = Path(stem).parts
    if len(parts) >= 2 and is_dcc_token(parts[1]):
        return parts[0], normalize_dcc(parts[1])
    return (parts[0] if parts else stem), None
