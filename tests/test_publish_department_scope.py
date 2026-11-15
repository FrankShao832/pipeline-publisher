"""Publish-path tests for the department/dcc split.

Everything here pins the same promise from the outside: **a publish lands in a
department-keyed tree, and its version counter belongs to that department (and
publish type) alone.** The dcc may appear as an inner segment when the work dir
is nested, but it never takes the department slot, and two departments
publishing the "same" houdini script must not share a counter.

Historical defect (fixed 2026-10-31): ``path_builder``'s ``department`` slot
received the DCC name, so every fx and lighting houdini publish went to one
``houdini/script/`` counter and silently overwrote each other.
"""

from pathlib import Path

import pytest

from publisher.core.file_system.path_builder import PathBuilder
from publisher.core.models.enums import PublishType
from publisher.core.services.publish_service import PublishRequest, PublishService


@pytest.fixture
def roots(tmp_path):
    project_root = tmp_path / 'projects'
    publish_root = tmp_path / 'publish'
    (project_root / 'Demo' / 'seq01' / 'shot001').mkdir(parents=True)
    publish_root.mkdir()
    return project_root, publish_root


def _write_source(project_root: Path, *parts: str, name: str) -> Path:
    folder = project_root.joinpath(*parts)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text('# fake scene\n')
    return path


def _context(project_root: Path, publish_root: Path, department: str, dcc: str = '') -> dict:
    return {
        'project': 'Demo',
        'sequence': 'seq01',
        'shot': 'shot001',
        'department': department,
        'dcc': dcc,
        'project_root': str(project_root),
        'publish_root': str(publish_root),
    }


def _publish(source: Path, context: dict, publish_type=PublishType.SCRIPT):
    service = PublishService()
    result = service.execute_publish(
        PublishRequest(
            source_path=str(source),
            publish_type=publish_type,
            context=context,
        )
    )
    assert result.success, result.message
    return result


# ---------------------------------------------------------------------------
# path_builder: optional dcc segment
# ---------------------------------------------------------------------------


class TestPathBuilderDccSegment:
    def test_flat(self):
        path = PathBuilder.build_publish_path(
            '/pub', 'Demo', 'seq01', 'shot001', 'comp', 'script', 'v001', 'a.nk',
        )
        assert path == Path('/pub/Demo/seq01/shot001/comp/script/v001/a.nk')

    def test_nested_dcc_goes_inside_department(self):
        path = PathBuilder.build_publish_path(
            '/pub', 'Demo', 'seq01', 'shot001', 'fx', 'script', 'v001', 'a.hip',
            dcc='houdini',
        )
        assert path == Path('/pub/Demo/seq01/shot001/fx/houdini/script/v001/a.hip')

    def test_type_dir_is_the_counter_scope(self):
        flat = PathBuilder.build_publish_type_dir('/pub', 'D', 's', 'sh', 'fx', 'script')
        nested = PathBuilder.build_publish_type_dir(
            '/pub', 'D', 's', 'sh', 'fx', 'script', dcc='houdini',
        )
        assert flat == Path('/pub/D/s/sh/fx/script')
        assert nested == Path('/pub/D/s/sh/fx/houdini/script')


# ---------------------------------------------------------------------------
# publish service: end-to-end tree shape
# ---------------------------------------------------------------------------


class TestPublishTreeShape:
    def test_nested_work_dir_publishes_nested(self, roots):
        project_root, publish_root = roots
        src = _write_source(
            project_root, 'Demo', 'seq01', 'shot001', 'fx', 'houdini',
            name='shot001_v001.hip',
        )
        result = _publish(src, _context(project_root, publish_root, 'fx', 'Houdini'))
        assert result.publish_path == str(
            publish_root / 'Demo' / 'seq01' / 'shot001' / 'fx' / 'houdini'
            / 'script' / 'v001' / 'shot001_v001.hip'
        )
        assert Path(result.publish_path).is_file()

    def test_flat_work_dir_publishes_flat(self, roots):
        project_root, publish_root = roots
        src = _write_source(
            project_root, 'Demo', 'seq01', 'shot001', 'comp', name='shot001_v001.nk',
        )
        result = _publish(src, _context(project_root, publish_root, 'comp', 'Nuke'))
        assert result.publish_path == str(
            publish_root / 'Demo' / 'seq01' / 'shot001' / 'comp'
            / 'script' / 'v001' / 'shot001_v001.nk'
        )

    def test_legacy_dcc_work_dir_publishes_under_department(self, roots):
        project_root, publish_root = roots
        src = _write_source(
            project_root, 'Demo', 'seq01', 'shot001', 'houdini', name='shot001_v007.hip',
        )
        result = _publish(src, _context(project_root, publish_root, 'fx', 'houdini'))
        # The legacy <shot>/houdini folder is readable, but the publish is keyed
        # by department: fx/script/v001 — and the publish version (v001) is what
        # gets embedded in the filename, not the source's v007.
        assert result.publish_path == str(
            publish_root / 'Demo' / 'seq01' / 'shot001' / 'fx'
            / 'script' / 'v001' / 'shot001_v001.hip'
        )


class TestVersionCounterScope:
    def test_departments_do_not_share_a_counter(self, roots):
        """fx and lighting both publish houdini scripts — each counts alone."""
        project_root, publish_root = roots
        fx_src = _write_source(
            project_root, 'Demo', 'seq01', 'shot001', 'fx', 'houdini',
            name='shot001_fx_v001.hip',
        )
        light_src = _write_source(
            project_root, 'Demo', 'seq01', 'shot001', 'lighting', 'houdini',
            name='shot001_lt_v001.hip',
        )
        fx = _publish(fx_src, _context(project_root, publish_root, 'fx', 'houdini'))
        light = _publish(light_src, _context(project_root, publish_root, 'lighting', 'houdini'))

        assert fx.version == 'v001'
        assert light.version == 'v001'
        assert '/fx/houdini/script/v001/' in fx.publish_path
        assert '/lighting/houdini/script/v001/' in light.publish_path

    def test_second_publish_increments_within_its_department(self, roots):
        project_root, publish_root = roots
        first = _write_source(
            project_root, 'Demo', 'seq01', 'shot001', 'fx', 'houdini',
            name='shot001_v001.hip',
        )
        _publish(first, _context(project_root, publish_root, 'fx', 'houdini'))

        second = _write_source(
            project_root, 'Demo', 'seq01', 'shot001', 'fx', 'houdini',
            name='shot001_v002.hip',
        )
        result = _publish(second, _context(project_root, publish_root, 'fx', 'houdini'))
        assert result.version == 'v002'
        assert '/fx/houdini/script/v002/shot001_v002.hip' in result.publish_path

    def test_publish_types_do_not_share_a_counter(self, roots):
        project_root, publish_root = roots
        script = _write_source(
            project_root, 'Demo', 'seq01', 'shot001', 'fx', 'houdini',
            name='shot001_v001.hip',
        )
        cache = _write_source(
            project_root, 'Demo', 'seq01', 'shot001', 'fx', 'houdini',
            name='shot001_v001.bgeo.sc',
        )
        s = _publish(script, _context(project_root, publish_root, 'fx', 'houdini'))
        c = _publish(cache, _context(project_root, publish_root, 'fx', 'houdini'),
                     publish_type=PublishType.CACHE)
        assert s.version == 'v001'
        assert c.version == 'v001'
        assert '/fx/houdini/script/v001/' in s.publish_path
        assert '/fx/houdini/cache/v001/' in c.publish_path
