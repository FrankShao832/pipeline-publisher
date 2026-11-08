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
import sys
from pathlib import Path
from typing import Optional

# Data-volume root per OS (macOS dev volume / Linux share mirror).
_DEV_ROOT = Path("/Volumes/Development" if sys.platform == "darwin" else "/srv/share/dev")

# Fallback defaults (only when no config and no env vars).
# Roots are the parent of the shows: the path builders append
# <project>/<sequence>/<shot> themselves.
FALLBACK_PROJECT_ROOT = _DEV_ROOT / "projects" / "y_pipeline_projects"
FALLBACK_PUBLISH_ROOT = _DEV_ROOT / "projects" / "y_pipeline_publish"

#: Dedicated sandbox show for dev clicks ("Init env" in DevTools).
#: The old code wrote into ``<root>/test_project``, which is a *real* show on
#: the dev volume — a dev button must never leave droppings in shipped data.
SANDBOX_SHOW = '_publisher_sandbox'

# Shot subdirectories named after departments (not DCC names)
TEST_DEPARTMENTS = ['anim', 'fx', 'comp']
# Publish type subdirectories under each department
PUBLISH_TYPES = ['script', 'cache', 'render']


def ensure_test_environment(
    project_root: Optional[Path] = None,
    publish_root: Optional[Path] = None,
) -> bool:
    """
    Ensure test directories exist and set default environment variables.

    Creates source files and publish directories for each department inside
    :data:`SANDBOX_SHOW` — a show that exists only for this button, so a dev
    click can never write into a real show. Only creates files if they don't
    already exist.

    Args:
        project_root: Project root path. Uses FALLBACK_PROJECT_ROOT if None.
        publish_root: Publish root path. Uses FALLBACK_PUBLISH_ROOT if None.

    Returns:
        True if environment was initialized
    """
    project_root = project_root or FALLBACK_PROJECT_ROOT
    publish_root = publish_root or FALLBACK_PUBLISH_ROOT

    created_any = False

    # --- Create source files for each department ---
    dept_files = {
        'anim': ('shot001_v001.ma', '# Maya scene file\n'),
        'fx':   ('shot001_v001.hip', '# Houdini hip file\n'),
        'comp': ('shot001_v001.nk', '# Nuke script\n'),
    }

    for department, (filename, content) in dept_files.items():
        source_dir = project_root / SANDBOX_SHOW / 'seq001' / 'shot001' / department
        source_file = source_dir / filename

        if not source_file.exists():
            source_dir.mkdir(parents=True, exist_ok=True)
            source_file.write_text(content)
            created_any = True

    # --- Create publish directories ---
    for department in TEST_DEPARTMENTS:
        for publish_type in PUBLISH_TYPES:
            version_dir = (
                publish_root
                / SANDBOX_SHOW
                / 'seq001'
                / 'shot001'
                / department
                / publish_type
                / 'v001'
            )
            if not version_dir.exists():
                version_dir.mkdir(parents=True, exist_ok=True)
                created_any = True

    # --- Set environment variables if not already set ---
    env_defaults = {
        'SHOW': SANDBOX_SHOW,
        'SEQ': 'seq001',
        'SHOT': 'shot001',
        'PIPELINE_DEPARTMENT': 'fx',
        'PROJECT_ROOT': str(project_root),
        'PUBLISH_ROOT': str(publish_root),
    }

    for key, value in env_defaults.items():
        if key not in os.environ:
            os.environ[key] = value

    return created_any
