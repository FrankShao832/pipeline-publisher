"""Standalone-session context: environment first, config file as the fallback.

Historical defect (fixed 2026-11-08): started standalone (no Pipeline Hatch to
inject ``PIPELINE_*``), every context field rendered ``Not set`` and the
publish button died on ``Missing required context fields`` — plus
``config/publisher.yaml`` pointed its roots one level too deep
(``.../y_pipeline_projects/Test``), so the work dir was built as
``Test/<project>/<sequence>/<shot>`` and never existed.

The promise pinned here: a standalone session resolves a *usable* context from
the config file, the environment always wins when present, and the configured
roots are the parent of the shows (the path builders append
``<project>/<sequence>/<shot>``).
"""

from pathlib import Path

import pytest

from publisher.core.config.settings import ConfigManager, PublisherConfig
from publisher.core.context_resolver import (
    NOT_SET,
    SOURCE_ENV,
    SOURCE_NONE,
    SOURCE_YAML,
    resolve_context,
)
from publisher.core.models.enums import PublishType
from publisher.core.services.publish_service import PublishRequest, PublishService

REPO_CONFIG = Path(__file__).resolve().parents[1] / 'config' / 'publisher.yaml'


def _config(**overrides) -> PublisherConfig:
    """A PublisherConfig with only the standalone fallback filled in."""
    config = PublisherConfig()
    config.standalone_context = {
        'project': 'Demo',
        'sequence': 'seq01',
        'shot': 'shot001',
        'department': 'fx',
        'dcc': 'houdini',
    }
    config.project_root = '/data/projects'
    config.publish_root = '/data/publish'
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


# ── Resolution rules ──────────────────────────────────────────────


def test_environment_wins_over_the_config_file():
    env = {
        'PIPELINE_PROJECT': 'CyberPunk',
        'PIPELINE_SEQUENCE': 'cy_seq',
        'PIPELINE_SHOT': 'cy_shot_0010',
        'PIPELINE_DEPARTMENT': 'comp',
        'PIPELINE_DCC': 'nuke',
        'PROJECT_ROOT': '/env/projects',
        'PUBLISH_ROOT': '/env/publish',
    }
    data = resolve_context(env=env, config=_config())

    assert data['project'] == 'CyberPunk'
    assert data['sequence'] == 'cy_seq'
    assert data['shot'] == 'cy_shot_0010'
    assert data['department'] == 'comp'
    assert data['dcc'] == 'nuke'
    assert data['project_root'] == '/env/projects'
    assert data['publish_root'] == '/env/publish'
    assert data['source'] == SOURCE_ENV


def test_legacy_environment_names_still_work():
    env = {'SHOW': 'RainPool', 'SEQ': 'rp_seq', 'SHOT': 'rp_pond_0010', 'ROLE': 'fx'}
    data = resolve_context(env=env, config=_config())

    assert (data['project'], data['sequence'], data['shot']) == (
        'RainPool', 'rp_seq', 'rp_pond_0010'
    )
    assert data['department'] == 'fx'


def test_config_fills_only_the_missing_fields():
    env = {'PIPELINE_PROJECT': 'Demo'}
    data = resolve_context(env=env, config=_config())

    assert data['project'] == 'Demo'          # env
    assert data['shot'] == 'shot001'          # config
    assert data['project_root'] == '/data/projects'
    assert data['source'] == SOURCE_YAML


def test_nothing_resolves_without_env_or_config():
    data = resolve_context(env={}, config=None)

    assert data['project'] == NOT_SET
    assert data['project_root'] == NOT_SET
    assert data['source'] == SOURCE_NONE


def test_department_and_dcc_are_lowercased():
    env = {'PIPELINE_DEPARTMENT': 'FX', 'PIPELINE_DCC': 'Houdini'}
    data = resolve_context(env=env, config=_config())

    assert data['department'] == 'fx'
    assert data['dcc'] == 'houdini'


def test_blank_environment_values_do_not_win():
    env = {'PIPELINE_SHOT': '   '}
    data = resolve_context(env=env, config=_config())

    assert data['shot'] == 'shot001'


# ── The repository config file itself ─────────────────────────────


@pytest.fixture
def repo_config() -> PublisherConfig:
    assert REPO_CONFIG.is_file(), REPO_CONFIG
    return ConfigManager(config_path=REPO_CONFIG).get_config()


def test_configured_roots_are_the_parent_of_the_shows(repo_config):
    # The bug being pinned: .../y_pipeline_projects/Test is one level too deep,
    # because the path builders append <project>/<sequence>/<shot> themselves.
    assert Path(repo_config.project_root).name == 'y_pipeline_projects'
    assert Path(repo_config.publish_root).name == 'y_pipeline_publish'


def test_repo_config_provides_a_standalone_context(repo_config):
    data = resolve_context(env={}, config=repo_config)

    assert data['source'] == SOURCE_YAML
    for field in ('project', 'sequence', 'shot', 'department', 'project_root',
                  'publish_root'):
        assert data[field] != NOT_SET, field


def test_standalone_context_publishes_into_a_mirrored_tree(repo_config, tmp_path):
    """End-to-end: config-only context → real file → publish path."""
    data = resolve_context(env={}, config=repo_config)

    project_root = tmp_path / 'projects'
    source_dir = (
        project_root / data['project'] / data['sequence'] / data['shot']
        / data['department']
    )
    source_dir.mkdir(parents=True)
    source = source_dir / 'standalone_test.hip'
    source.write_text('# fake scene\n')

    publish_root = tmp_path / 'publish'
    publish_root.mkdir()

    context = dict(
        project=data['project'],
        sequence=data['sequence'],
        shot=data['shot'],
        department=data['department'],
        publish_root=str(publish_root),
        project_root=str(project_root),
    )
    result = PublishService().execute_publish(
        PublishRequest(
            source_path=str(source),
            publish_type=PublishType.SCRIPT,
            context=context,
        )
    )

    assert result.success, result.message
    assert result.version == 'v001'
    published = Path(result.publish_path)
    assert published.parent == (
        publish_root / data['project'] / data['sequence'] / data['shot']
        / data['department'] / 'script' / 'v001'
    )
    assert published.name == 'standalone_test_v001.hip'
