"""Unit tests for PathBuilder — the version/publish filename core.

These helpers are on the dangerous path: every publish rewrites artist
filenames and version directories. Regressions here corrupt publish trees,
so the suite pins both the documented behavior AND the historical bugs:

- same-version publish_filename must not append a second suffix
  (fixed 2026-06-14: "源文件版本与目标版本相同时误追加第二个版本号")
- next_version must take the max, not the count (gap tolerance)
"""

from pathlib import Path

import pytest

from publisher.core.file_system.path_builder import PathBuilder


# ---------------------------------------------------------------------------
# publish_filename
# ---------------------------------------------------------------------------


class TestPublishFilename:
    def test_replaces_existing_version(self):
        assert PathBuilder.publish_filename("shot001_v001.ma", "v010") == "shot001_v010.ma"

    def test_appends_when_no_version(self):
        assert PathBuilder.publish_filename("shot001.ma", "v010") == "shot001_v010.ma"

    def test_inserts_before_extension(self):
        assert PathBuilder.publish_filename("script.py", "v010") == "script_v010.py"

    def test_same_version_no_double_suffix(self):
        """Regression: publishing at the same version must be idempotent."""
        assert PathBuilder.publish_filename("shot001_v001.ma", "v001") == "shot001_v001.ma"

    def test_no_extension(self):
        assert PathBuilder.publish_filename("shot001_v001", "v002") == "shot001_v002"

    def test_only_trailing_version_is_replaced(self):
        assert PathBuilder.publish_filename("shot001_v002_v010.ma", "v011") == "shot001_v002_v011.ma"

    def test_version_without_underscore_is_not_replaced(self):
        # 'shot001v010' does not match the '_v\\d+$' convention: the version
        # is appended instead. Documented current behavior.
        assert PathBuilder.publish_filename("shot001v010.ma", "v011") == "shot001v010_v011.ma"


# ---------------------------------------------------------------------------
# extract_version
# ---------------------------------------------------------------------------


class TestExtractVersion:
    def test_extracts_trailing_version(self):
        assert PathBuilder.extract_version("shot001_v010.ma") == "v010"

    def test_no_version_returns_none(self):
        assert PathBuilder.extract_version("shot001.ma") is None

    def test_no_extension(self):
        assert PathBuilder.extract_version("shot001_v010") == "v010"

    def test_multi_digit_version(self):
        assert PathBuilder.extract_version("shot001_v0012.ma") == "v0012"

    def test_trailing_version_wins(self):
        assert PathBuilder.extract_version("shot_v001_v002.ma") == "v002"

    def test_bare_version_prefix_without_underscore_returns_none(self):
        # stem 'v010' has no '_v' boundary; documented current behavior.
        assert PathBuilder.extract_version("v010.ma") is None


# ---------------------------------------------------------------------------
# version_up_filename
# ---------------------------------------------------------------------------


class TestVersionUpFilename:
    def test_increments_version(self):
        assert PathBuilder.version_up_filename("shot001_v010.ma") == "shot001_v011.ma"

    def test_starts_at_v001_when_no_version(self):
        assert PathBuilder.version_up_filename("shot001.ma") == "shot001_v001.ma"

    def test_starts_at_v001_for_plain_script(self):
        assert PathBuilder.version_up_filename("script.py") == "script_v001.py"

    def test_no_extension(self):
        assert PathBuilder.version_up_filename("shot001_v001") == "shot001_v002"

    def test_padding_widens_short_versions(self):
        assert PathBuilder.version_up_filename("shot_v01.ma") == "shot_v002.ma"

    def test_padding_does_not_truncate_long_versions(self):
        assert PathBuilder.version_up_filename("shot001_v999.ma") == "shot001_v1000.ma"

    def test_custom_padding(self):
        assert PathBuilder.version_up_filename("shot_v0009.ma", padding=4) == "shot_v0010.ma"

    def test_only_trailing_version_increments(self):
        assert PathBuilder.version_up_filename("shot001_v002_v010.ma") == "shot001_v002_v011.ma"


# ---------------------------------------------------------------------------
# scan_existing_versions / next_version
# ---------------------------------------------------------------------------


class TestScanExistingVersions:
    def test_missing_dir_returns_empty(self, tmp_path):
        assert PathBuilder.scan_existing_versions(tmp_path / "nope") == []

    def test_empty_dir_returns_empty(self, tmp_path):
        assert PathBuilder.scan_existing_versions(tmp_path) == []

    def test_scans_version_dirs_sorted_numerically(self, tmp_path):
        for name in ("v002", "v001", "v010"):
            (tmp_path / name).mkdir()
        assert PathBuilder.scan_existing_versions(tmp_path) == ["v001", "v002", "v010"]

    def test_ignores_non_version_dirs_and_files(self, tmp_path):
        (tmp_path / "v001").mkdir()
        (tmp_path / "backup").mkdir()
        (tmp_path / "v_abc").mkdir()
        (tmp_path / "v00x").mkdir()
        (tmp_path / "v003").write_text("not a dir")  # file, not version dir
        assert PathBuilder.scan_existing_versions(tmp_path) == ["v001"]

    def test_numeric_not_lexicographic_sort(self, tmp_path):
        # Lexicographic sort would give ['v1', 'v10', 'v2'].
        for name in ("v2", "v10", "v1"):
            (tmp_path / name).mkdir()
        assert PathBuilder.scan_existing_versions(tmp_path) == ["v1", "v2", "v10"]


class TestNextVersion:
    def test_first_version_when_empty(self, tmp_path):
        assert PathBuilder.next_version(tmp_path) == "v001"

    def test_first_version_when_missing(self, tmp_path):
        assert PathBuilder.next_version(tmp_path / "nope") == "v001"

    def test_increments_from_existing(self, tmp_path):
        for name in ("v001", "v002"):
            (tmp_path / name).mkdir()
        assert PathBuilder.next_version(tmp_path) == "v003"

    def test_takes_max_not_count(self, tmp_path):
        """Gap tolerance: v003 deleted must not resurrect its number."""
        for name in ("v001", "v003"):
            (tmp_path / name).mkdir()
        assert PathBuilder.next_version(tmp_path) == "v004"

    def test_custom_padding(self, tmp_path):
        (tmp_path / "v0009").mkdir()
        assert PathBuilder.next_version(tmp_path, padding=4) == "v0010"

    def test_unpadded_dirs_still_numeric(self, tmp_path):
        for name in ("v2", "v10"):
            (tmp_path / name).mkdir()
        assert PathBuilder.next_version(tmp_path) == "v011"


# ---------------------------------------------------------------------------
# path builders
# ---------------------------------------------------------------------------


class TestPathBuilders:
    def test_build_work_path(self):
        p = PathBuilder.build_work_path(
            "/proj", "demo", "seq001", "shot010", "fx", "shot010_v001.hip"
        )
        assert p == Path("/proj/demo/seq001/shot010/fx/shot010_v001.hip")

    def test_build_publish_path(self):
        p = PathBuilder.build_publish_path(
            "/pub", "demo", "seq001", "shot010", "fx", "script", "v003", "shot010_v003.py"
        )
        assert p == Path("/pub/demo/seq001/shot010/fx/script/v003/shot010_v003.py")

    def test_build_publish_version_dir(self):
        p = PathBuilder.build_publish_version_dir(
            "/pub", "demo", "seq001", "shot010", "fx", "cache", "v003"
        )
        assert p == Path("/pub/demo/seq001/shot010/fx/cache/v003")


# ---------------------------------------------------------------------------
# round trip: the artist-facing lifecycle in one breath
# ---------------------------------------------------------------------------


class TestVersionRoundTrip:
    def test_work_to_publish_lifecycle(self):
        # artist saves -> version up -> publish next -> extract back
        work = "shot010.hip"
        up = PathBuilder.version_up_filename(work)          # shot010_v001.hip
        version = PathBuilder.extract_version(up)            # v001
        published = PathBuilder.publish_filename(up, "v002")  # shot010_v002.hip

        assert up == "shot010_v001.hip"
        assert version == "v001"
        assert published == "shot010_v002.hip"
        assert PathBuilder.extract_version(published) == "v002"

    def test_repeated_publish_same_version_is_stable(self):
        f = "shot010_v003.hip"
        assert PathBuilder.publish_filename(f, "v003") == f
