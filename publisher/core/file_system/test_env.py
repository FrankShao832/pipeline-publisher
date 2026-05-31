"""
Test environment initialization for Pipeline Publisher.

Creates test directory structures and mock source files for local development.
Only used as fallback when no YAML config file and no environment variables are set.

Priority order:
1. config/publisher.yaml (ConfigManager)
2. Environment variables
3. This module's fallback defaults
"""

import os
from pathlib import Path
from typing import Optional

# Fallback defaults (only when no config and no env vars)
FALLBACK_PROJECT_ROOT = Path("/Volumes/Projects/y_pipeline_projects/Test")
FALLBACK_PUBLISH_ROOT = Path("/Volumes/Projects/y_pipeline_publish/Test")

# Shot subdirectories named after DCC tools
DCC_ROLES = ['maya', 'houdini', 'nuke']
# Publish type subdirectories under each role
PUBLISH_TYPES = ['script', 'cache', 'render']


def ensure_test_environment(
    project_root: Optional[Path] = None,
    publish_root: Optional[Path] = None,
) -> bool:
    """
    Ensure test directories exist and set default environment variables.

    Creates source files and publish directories for each DCC role.
    Only creates files if they don't already exist.

    Args:
        project_root: Project root path. Uses FALLBACK_PROJECT_ROOT if None.
        publish_root: Publish root path. Uses FALLBACK_PUBLISH_ROOT if None.

    Returns:
        True if environment was initialized
    """
    project_root = project_root or FALLBACK_PROJECT_ROOT
    publish_root = publish_root or FALLBACK_PUBLISH_ROOT

    created_any = False

    # --- Create source files for each DCC ---
    dcc_files = {
        'maya': ('shot001_v001.ma', '# Maya scene file\n'),
        'houdini': ('shot001_v001.hip', '# Houdini hip file\n'),
        'nuke': ('shot001_v001.nk', '# Nuke script\n'),
    }

    for role, (filename, content) in dcc_files.items():
        source_dir = project_root / 'test_project' / 'seq001' / 'shot001' / role
        source_file = source_dir / filename

        if not source_file.exists():
            source_dir.mkdir(parents=True, exist_ok=True)
            source_file.write_text(content)
            created_any = True

    # --- Create publish directories ---
    for role in DCC_ROLES:
        for publish_type in PUBLISH_TYPES:
            version_dir = (
                publish_root
                / 'test_project'
                / 'seq001'
                / 'shot001'
                / role
                / publish_type
                / 'v001'
            )
            if not version_dir.exists():
                version_dir.mkdir(parents=True, exist_ok=True)
                created_any = True

    # --- Set environment variables if not already set ---
    env_defaults = {
        'SHOW': 'test_project',
        'SEQ': 'seq001',
        'SHOT': 'shot001',
        'ROLE': 'maya',
        'PROJECT_ROOT': str(project_root),
        'PUBLISH_ROOT': str(publish_root),
    }

    for key, value in env_defaults.items():
        if key not in os.environ:
            os.environ[key] = value

    return created_any
