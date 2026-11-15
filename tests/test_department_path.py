"""Unit tests for the department-first work-directory resolver.

The resolver is what keeps ``department`` (data axis) and ``dcc`` (runtime
axis) from trading places. It is pinned here because every publish path and
version counter is derived from its answer:

- department dir wins over a dcc-named dir (dcc -> department is 1:N)
- a nested ``<dept>/<dcc>`` must be found before the flat ``<dept>``
- the legacy ``<shot>/<dcc>`` shape stays readable but never decides identity
"""

from pathlib import Path

import pytest

from publisher.core.file_system.department_path import (
    DCC_TOKENS,
    is_dcc_token,
    normalize_dcc,
    publish_stem_for_source,
    resolve_source_dir,
    shot_dir,
    split_stem,
)


@pytest.fixture
def shot(tmp_path):
    """A fake project root with one shot folder."""
    root = tmp_path / 'projects'
    (root / 'Demo' / 'seq01' / 'shot001').mkdir(parents=True)
    return root, 'Demo', 'seq01', 'shot001'


def _mk(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# normalize_dcc / is_dcc_token
# ---------------------------------------------------------------------------


class TestNormalizeDcc:
    @pytest.mark.parametrize('raw,expected', [
        ('houdini', 'houdini'),
        ('Houdini', 'houdini'),
        ('NUKE', 'nuke'),
        ('Nuke Studio', 'nukestudio'),
        ('  maya  ', 'maya'),
    ])
    def test_accepts_tokens_and_display_names(self, raw, expected):
        assert normalize_dcc(raw) == expected

    @pytest.mark.parametrize('raw', ['', None, 'fx', 'lighting', 'Photoshop'])
    def test_rejects_departments_and_unknowns(self, raw):
        assert normalize_dcc(raw) == ''

    def test_is_dcc_token(self):
        assert is_dcc_token('houdini')
        assert is_dcc_token('Maya')
        assert not is_dcc_token('comp')
        assert not is_dcc_token('')

    def test_tokens_are_lowercase(self):
        assert all(t == t.lower() for t in DCC_TOKENS)


# ---------------------------------------------------------------------------
# resolve_source_dir
# ---------------------------------------------------------------------------


class TestResolveSourceDir:
    def test_nested_dept_dcc_wins(self, shot):
        root, proj, seq, sh = shot
        target = _mk(shot_dir(root, proj, seq, sh) / 'fx' / 'houdini')
        resolved = resolve_source_dir(root, proj, seq, sh, 'fx', 'houdini')
        assert resolved is not None
        assert resolved.path == target
        assert resolved.stem == 'fx/houdini'
        assert resolved.dcc == 'houdini'
        assert resolved.legacy is False

    def test_flat_department(self, shot):
        root, proj, seq, sh = shot
        target = _mk(shot_dir(root, proj, seq, sh) / 'comp')
        resolved = resolve_source_dir(root, proj, seq, sh, 'comp', 'nuke')
        assert resolved is not None
        assert resolved.path == target
        assert resolved.stem == 'comp'
        assert resolved.dcc is None

    def test_flat_department_beats_legacy_dcc_dir(self, shot):
        """Both shapes exist -> the department keyed one is the truth."""
        root, proj, seq, sh = shot
        _mk(shot_dir(root, proj, seq, sh) / 'fx' / 'houdini')
        _mk(shot_dir(root, proj, seq, sh) / 'houdini')
        resolved = resolve_source_dir(root, proj, seq, sh, 'fx', 'houdini')
        assert resolved.stem == 'fx/houdini'
        assert resolved.legacy is False

    def test_legacy_dcc_dir_is_readable_but_not_authoritative(self, shot):
        root, proj, seq, sh = shot
        _mk(shot_dir(root, proj, seq, sh) / 'houdini')
        resolved = resolve_source_dir(root, proj, seq, sh, 'fx', 'houdini')
        assert resolved is not None
        assert resolved.legacy is True
        assert resolved.stem == 'fx'          # never 'houdini'
        assert resolved.dcc is None

    def test_missing_department_returns_none(self, shot):
        root, proj, seq, sh = shot
        assert resolve_source_dir(root, proj, seq, sh, 'lighting', 'houdini') is None

    def test_incomplete_context_returns_none(self, shot):
        root, proj, seq, sh = shot
        assert resolve_source_dir(root, proj, seq, sh, '') is None
        assert resolve_source_dir('', proj, seq, sh, 'fx') is None


# ---------------------------------------------------------------------------
# publish_stem_for_source
# ---------------------------------------------------------------------------


class TestPublishStemForSource:
    def test_nested_source_keeps_dcc_level(self, shot):
        root, proj, seq, sh = shot
        src = _mk(shot_dir(root, proj, seq, sh) / 'fx' / 'houdini') / 'shot001_v001.hip'
        assert publish_stem_for_source(src, root, proj, seq, sh, 'fx') == 'fx/houdini'

    def test_flat_source_stays_flat(self, shot):
        root, proj, seq, sh = shot
        src = _mk(shot_dir(root, proj, seq, sh) / 'comp') / 'shot001_v001.nk'
        assert publish_stem_for_source(src, root, proj, seq, sh, 'comp') == 'comp'

    def test_legacy_dcc_source_publishes_under_department(self, shot):
        root, proj, seq, sh = shot
        src = _mk(shot_dir(root, proj, seq, sh) / 'houdini') / 'shot001_v001.hip'
        assert publish_stem_for_source(src, root, proj, seq, sh, 'fx') == 'fx'

    def test_second_level_must_be_a_known_dcc(self, shot):
        """A non-dcc subfolder (e.g. fx/wip) never becomes a publish segment."""
        root, proj, seq, sh = shot
        src = _mk(shot_dir(root, proj, seq, sh) / 'fx' / 'wip') / 'shot001_v001.hip'
        assert publish_stem_for_source(src, root, proj, seq, sh, 'fx') == 'fx'

    def test_source_outside_shot_falls_back_to_department(self, shot, tmp_path):
        root, proj, seq, sh = shot
        outside = tmp_path / 'elsewhere' / 'shot001_v001.hip'
        outside.parent.mkdir()
        assert publish_stem_for_source(outside, root, proj, seq, sh, 'fx') == 'fx'

    def test_mismatched_department_segment_falls_back(self, shot):
        root, proj, seq, sh = shot
        src = _mk(shot_dir(root, proj, seq, sh) / 'lighting') / 'shot001_v001.hip'
        assert publish_stem_for_source(src, root, proj, seq, sh, 'fx') == 'fx'


# ---------------------------------------------------------------------------
# split_stem
# ---------------------------------------------------------------------------


class TestSplitStem:
    def test_nested(self):
        assert split_stem('fx/houdini') == ('fx', 'houdini')

    def test_flat(self):
        assert split_stem('comp') == ('comp', None)

    def test_non_dcc_second_level_is_ignored(self):
        assert split_stem('fx/wip') == ('fx', None)
