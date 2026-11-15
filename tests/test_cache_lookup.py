"""Contracts for choosing the cache file that a "Cache" publish should copy.

Why these exist: choosing ``Cache`` while the source is still a work file used
to do nothing at all — the publish then copied the ``.hip`` into
``<dept>/cache/v001/`` and called it success. The publisher copies files and
never converts, so the only honest answers are "here is the exported USD, copy
this one" or "there is nothing to copy yet". These tests pin the second half of
that sentence, which is pure filesystem logic and therefore testable outside
any DCC.

Timestamps: ``sort`` uses the creation time (macOS ``st_birthtime``) and falls
back to mtime elsewhere, so the "newest wins" case below creates the files in
the same order it sets their mtimes — the expectation then holds on either
rule.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from publisher.core.file_system.cache_lookup import (
    CACHE_EXTENSIONS,
    cache_dir_for_source,
    is_cache_file,
    lookup_cache_source,
    newest_cache_file,
)


# ── Helpers ─────────────────────────────────────────────────────────────


def _write(path: Path, content: str = "#usda 1.0\n", mtime: float | None = None) -> Path:
    """Create a file, optionally stamping its mtime."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


# ── Where the cache folder lives ────────────────────────────────────────


def test_cache_dir_is_a_sibling_of_the_work_file(tmp_path):
    """A .hip at <dept>/ points at <dept>/cache/."""
    work = tmp_path / "lighting" / "usd_asset_001_lighting.hip"
    assert cache_dir_for_source(work) == tmp_path / "lighting" / "cache"


def test_cache_dir_nested_under_dcc_segment(tmp_path):
    """Only 'beside the work file' matters, however deep that is."""
    work = tmp_path / "lighting" / "houdini" / "asset.hip"
    assert cache_dir_for_source(work) == tmp_path / "lighting" / "houdini" / "cache"


def test_source_inside_cache_does_not_double_the_folder(tmp_path):
    """Re-applying the rule must not invent cache/cache."""
    usd = tmp_path / "lighting" / "cache" / "asset_v001.usd"
    assert cache_dir_for_source(usd) == tmp_path / "lighting" / "cache"


@pytest.mark.parametrize("empty", ["", "   ", None])
def test_no_source_means_no_lookup(empty):
    """An empty source field must not resolve to the CWD's cache folder."""
    assert cache_dir_for_source(empty) is None
    assert lookup_cache_source(empty) is None


# ── Nothing to publish yet ──────────────────────────────────────────────


def test_missing_cache_folder_reports_nothing_found(tmp_path):
    """The folder not existing is the normal state before the first export."""
    work = _write(tmp_path / "lighting" / "asset.hip")

    lookup = lookup_cache_source(work)

    assert lookup is not None
    assert lookup.cache_dir == tmp_path / "lighting" / "cache"
    assert lookup.found is False
    assert lookup.candidate is None


def test_empty_cache_folder_reports_nothing_found(tmp_path):
    """An existing but empty folder is still nothing to copy."""
    work = _write(tmp_path / "lighting" / "asset.hip")
    (tmp_path / "lighting" / "cache").mkdir()

    assert lookup_cache_source(work).found is False


def test_non_cache_files_do_not_count_as_a_cache(tmp_path):
    """A stray .abc/.txt/.hip in the folder must not be offered as the cache."""
    work = _write(tmp_path / "lighting" / "asset.hip")
    cache = tmp_path / "lighting" / "cache"
    _write(cache / "asset.abc")
    _write(cache / "notes.txt")
    _write(cache / "old_asset.hip")

    assert lookup_cache_source(work).found is False


def test_subfolders_are_not_descended_into(tmp_path):
    """Version sub-folders are not the cache layer; the folder stays flat."""
    work = _write(tmp_path / "lighting" / "asset.hip")
    _write(tmp_path / "lighting" / "cache" / "v001" / "asset_v001.usd")

    assert lookup_cache_source(work).found is False


# ── Picking the file ────────────────────────────────────────────────────


def test_newest_created_file_wins(tmp_path):
    """With several caches the latest export is the candidate."""
    work = _write(tmp_path / "lighting" / "asset.hip")
    cache = tmp_path / "lighting" / "cache"
    _write(cache / "asset_v001.usd", mtime=1_700_000_000)
    newest = _write(cache / "asset_v002.usd", mtime=1_700_000_900)

    candidate = lookup_cache_source(work).candidate

    assert candidate is not None
    assert candidate.path == newest
    assert candidate.filename == "asset_v002.usd"


def test_every_usd_family_extension_is_accepted(tmp_path):
    """usd/usda/usdc/usdz all count — they are the same hand-off format."""
    cache = tmp_path / "cache"
    for name in ("a.usd", "b.usda", "c.usdc", "d.usdz"):
        _write(cache / name)

    for suffix in CACHE_EXTENSIONS:
        assert is_cache_file(f"anything{suffix}")

    candidate = newest_cache_file(cache)
    assert candidate is not None
    assert candidate.path.suffix in CACHE_EXTENSIONS


def test_uppercase_extension_is_accepted(tmp_path):
    """Artists type .USD on macOS sometimes; the check is case-insensitive."""
    assert is_cache_file("asset_V001.USD") is True


def test_candidate_reports_a_human_readable_created_date(tmp_path):
    """The confirmation dialog shows when the cache was created."""
    work = _write(tmp_path / "lighting" / "asset.hip")
    _write(tmp_path / "lighting" / "cache" / "asset_v001.usd", mtime=1_700_000_000)

    candidate = lookup_cache_source(work).candidate

    assert candidate is not None
    # %Y-%m-%d %H:%M — exact value depends on the filesystem's birth time,
    # so pin the shape rather than a specific instant.
    assert len(candidate.created_text) == 16
    assert candidate.created_text[4] == "-" and candidate.created_text[13] == ":"


# ── Staleness (the silent-wrong-file guard) ─────────────────────────────


def test_cache_modified_before_the_work_file_is_flagged_stale(tmp_path):
    """Changed the scene after exporting? Then the cache is out of date."""
    cache_file = _write(
        tmp_path / "lighting" / "cache" / "asset_v001.usd", mtime=1_700_000_000
    )
    work = _write(tmp_path / "lighting" / "asset.hip", mtime=1_700_000_900)

    candidate = newest_cache_file(cache_file.parent)

    assert candidate is not None
    assert candidate.is_older_than(work) is True


def test_cache_modified_after_the_work_file_is_fresh(tmp_path):
    """The normal case: export then save, so the cache is the newer file."""
    work = _write(tmp_path / "lighting" / "asset.hip", mtime=1_700_000_000)
    cache_file = _write(
        tmp_path / "lighting" / "cache" / "asset_v001.usd", mtime=1_700_000_900
    )

    candidate = newest_cache_file(cache_file.parent)

    assert candidate is not None
    assert candidate.is_older_than(work) is False


def test_staleness_is_false_when_the_work_file_is_unreadable(tmp_path):
    """A missing work file must not raise — the dialog just skips the warning."""
    cache_file = _write(tmp_path / "lighting" / "cache" / "asset_v001.usd")

    candidate = newest_cache_file(cache_file.parent)

    assert candidate is not None
    assert candidate.is_older_than(tmp_path / "lighting" / "gone.hip") is False
