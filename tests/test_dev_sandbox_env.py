"""The DevTools "Init env" button must not write into a real show.

Historical defect (fixed 2026-11-08): ``ensure_test_environment`` built its
mock shot as ``<project_root>/test_project/seq001/shot001/...``. While the
configured ``project_root`` still pointed one level too deep that landed in a
scratch folder; once the root was corrected to the parent of the shows the same
code started writing into ``y_pipeline_projects/test_project`` — a show that
actually exists on the dev volume.

Everything the button creates now lives under the dedicated
:data:`SANDBOX_SHOW`, so it can be deleted at any time and never mixes with
authored data.
"""

import os
from pathlib import Path

import pytest

from publisher.core.file_system.test_env import (
    PUBLISH_TYPES,
    SANDBOX_SHOW,
    TEST_DEPARTMENTS,
    ensure_test_environment,
)


@pytest.fixture
def roots(tmp_path):
    projects = tmp_path / 'projects'
    publish = tmp_path / 'publish'
    projects.mkdir()
    publish.mkdir()
    return projects, publish


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Start with no pipeline env and restore whatever was there afterwards.

    ``monkeypatch.delenv`` records nothing when the key is already absent, so a
    bare delete would let ``ensure_test_environment``'s own ``os.environ``
    writes leak into the next test module — they did: the config-roots test
    then saw ``PROJECT_ROOT=<tmp>/projects``. Registering the key with
    ``setenv`` first gives the undo something to restore.
    """
    for key in ('SHOW', 'SEQ', 'SHOT', 'PIPELINE_DEPARTMENT',
                'PROJECT_ROOT', 'PUBLISH_ROOT'):
        monkeypatch.setenv(key, '')  # records the original (possibly absent) value
        del os.environ[key]


def test_writes_only_inside_the_sandbox_show(roots):
    projects, publish = roots
    (projects / 'test_project').mkdir()  # a real show, must stay untouched

    assert ensure_test_environment(projects, publish) is True

    for department in TEST_DEPARTMENTS:
        assert (
            projects / SANDBOX_SHOW / 'seq001' / 'shot001' / department
        ).is_dir()
    assert not any((projects / 'test_project').iterdir())


def test_publish_skeleton_mirrors_the_sandbox_shot(roots):
    projects, publish = roots
    ensure_test_environment(projects, publish)

    for department in TEST_DEPARTMENTS:
        for publish_type in PUBLISH_TYPES:
            assert (
                publish / SANDBOX_SHOW / 'seq001' / 'shot001'
                / department / publish_type / 'v001'
            ).is_dir()


def test_mock_source_files_are_created_with_known_names(roots):
    projects, publish = roots
    ensure_test_environment(projects, publish)

    shot = projects / SANDBOX_SHOW / 'seq001' / 'shot001'
    assert (shot / 'anim' / 'shot001_v001.ma').is_file()
    assert (shot / 'fx' / 'shot001_v001.hip').is_file()
    assert (shot / 'comp' / 'shot001_v001.nk').is_file()


def test_second_call_is_idempotent_and_keeps_content(roots):
    projects, publish = roots
    ensure_test_environment(projects, publish)

    marker = projects / SANDBOX_SHOW / 'seq001' / 'shot001' / 'anim' / 'shot001_v001.ma'
    marker.write_text('# edited by the dev\n')

    assert ensure_test_environment(projects, publish) is False
    assert marker.read_text() == '# edited by the dev\n'


def test_context_env_defaults_point_at_the_sandbox(roots):
    projects, publish = roots
    ensure_test_environment(projects, publish)

    assert os.environ['SHOW'] == SANDBOX_SHOW
    assert os.environ['SEQ'] == 'seq001'
    assert os.environ['SHOT'] == 'shot001'
    assert os.environ['PROJECT_ROOT'] == str(projects)
    assert os.environ['PUBLISH_ROOT'] == str(publish)


def test_existing_environment_is_not_overridden(roots, monkeypatch):
    projects, publish = roots
    monkeypatch.setenv('SHOW', 'CyberPunk')
    ensure_test_environment(projects, publish)

    assert os.environ['SHOW'] == 'CyberPunk'
