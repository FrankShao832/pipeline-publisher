"""Locate the cache (USD) source that belongs to a department work file.

Publishing a ``cache`` artifact never starts from the work file itself: the
artist works in ``<shot>/<dept>/<name>.hip`` and the exported USDs land in
``<shot>/<dept>/cache/`` next to it. The publish tree mirrors that shape
(``<shot>/<dept>/cache/v001/``), so "which file do I publish" has exactly one
answer — the newest cache file sitting beside the work file.

This module is deliberately Qt-free: the dialog that asks the artist to confirm
belongs to the widget, the *decision* belongs here and is unit-tested. The
publisher still copies files and never converts; exporting the USD stays the
DCC's job, and when there is nothing to copy we say so instead of publishing a
stale file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

#: Extensions a ``cache`` publish may copy. Deliberately narrow: a cache
#: publish is a USD hand-off, so ``.abc``/``.bgeo`` are *not* picked up
#: silently — widening this is a product decision, not a convenience.
CACHE_EXTENSIONS: tuple[str, ...] = ('.usd', '.usda', '.usdc', '.usdz')

#: Folder name that holds the exported caches, beside the work file.
CACHE_DIR_NAME: str = 'cache'

_DATETIME_FORMAT = '%Y-%m-%d %H:%M'


@dataclass(frozen=True)
class CacheCandidate:
    """One file found inside the cache folder."""

    path: Path
    created: float    # birth time when the filesystem reports one, else mtime
    modified: float   # mtime — used only to tell whether the cache is stale

    @property
    def filename(self) -> str:
        """Return the bare filename."""
        return self.path.name

    @property
    def created_text(self) -> str:
        """Return the creation time formatted for the confirmation dialog."""
        return datetime.fromtimestamp(self.created).strftime(_DATETIME_FORMAT)

    def is_older_than(self, other_path: str | os.PathLike) -> bool:
        """True when this cache was modified before *other_path* was.

        Comparing modification times (not birth times) keeps the staleness
        check honest on filesystems where birth time is unavailable, and it is
        the direction that matters: a cache written before the work file was
        last saved no longer represents the scene.

        Args:
            other_path: The work file (usually the open ``.hip``).

        Returns:
            True if the cache predates ``other_path``; False otherwise or when
            either timestamp cannot be read.
        """
        try:
            other_modified = os.path.getmtime(other_path)
        except OSError:
            return False
        return self.modified < other_modified


@dataclass(frozen=True)
class CacheLookup:
    """Result of asking the filesystem for a publishable cache file."""

    cache_dir: Path
    candidate: Optional[CacheCandidate]

    @property
    def found(self) -> bool:
        """True when a cache file is available to publish."""
        return self.candidate is not None


def is_cache_file(path: str | os.PathLike) -> bool:
    """Return True when *path* has a cache extension (USD family)."""
    return Path(path).suffix.lower() in CACHE_EXTENSIONS


def cache_dir_for_source(
    source_path: str | os.PathLike,
) -> Optional[Path]:
    """Return the cache folder that belongs to *source_path*.

    The folder is a sibling of the work file::
        <shot>/<dept>/<name>.hip      -> <shot>/<dept>/cache/
        <shot>/<dept>/houdini/<n>.hip -> <shot>/<dept>/houdini/cache/

    A source that already lives inside a ``cache`` folder returns that folder
    unchanged, so re-applying the rule never invents ``cache/cache``.

    Args:
        source_path: Current source file path (may be empty).

    Returns:
        The cache directory as a Path (it need not exist), or None when there
        is no source path to derive from.
    """
    text = str(source_path or '').strip()
    if not text:
        return None
    parent = Path(text).parent
    if parent.name.lower() == CACHE_DIR_NAME:
        return parent
    return parent / CACHE_DIR_NAME


def _created_timestamp(path: Path) -> float:
    """Return birth time when available, otherwise mtime."""
    stat_result = path.stat()
    birth = getattr(stat_result, 'st_birthtime', 0.0) or 0.0
    return birth or stat_result.st_mtime


def newest_cache_file(cache_dir: Optional[Path]) -> Optional[CacheCandidate]:
    """Return the newest cache file inside *cache_dir*.

    "Newest" is the creation date, with the filename as a tie-breaker so the
    pick is deterministic on filesystems that report identical timestamps.

    Args:
        cache_dir: Folder to scan. Missing folders are treated as empty.

    Returns:
        A CacheCandidate, or None when the folder is missing or holds no
        cache-extension file. Sub-folders are never descended into.
    """
    if cache_dir is None or not cache_dir.is_dir():
        return None

    candidates: list[CacheCandidate] = []
    for entry in cache_dir.iterdir():
        try:
            if not entry.is_file() or not is_cache_file(entry):
                continue
            stat_result = entry.stat()
        except OSError:
            continue  # unreadable entry — skip, never fail the lookup
        candidates.append(
            CacheCandidate(
                path=entry,
                created=_created_timestamp(entry),
                modified=stat_result.st_mtime,
            )
        )

    if not candidates:
        return None
    return max(candidates, key=lambda c: (c.created, c.filename))


def lookup_cache_source(
    source_path: str | os.PathLike,
) -> Optional[CacheLookup]:
    """Resolve the cache sibling of *source_path*.

    Args:
        source_path: Current source file path (may be empty).

    Returns:
        A CacheLookup whose ``candidate`` is None when nothing is exportable,
        or None itself when there is no source path to start from.
    """
    cache_dir = cache_dir_for_source(source_path)
    if cache_dir is None:
        return None
    return CacheLookup(cache_dir=cache_dir, candidate=newest_cache_file(cache_dir))
