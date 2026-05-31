"""
Path construction utilities for Pipeline Publisher.

Builds consistent pipeline paths for source (work) and publish directories.
Supports multi-DCC directory structure where role = DCC name (maya/houdini/nuke).

Path patterns:
  Work:     {project_root}/{project}/{seq}/{shot}/{role}/{filename}
  Publish:  {publish_root}/{project}/{seq}/{shot}/{role}/{type}/v{XXX}/{filename}
"""

from pathlib import Path
from typing import List, Optional


class PathBuilder:
    """Pipeline path construction and version scanning."""

    @staticmethod
    def build_work_path(
        project_root: str,
        project: str,
        sequence: str,
        shot: str,
        role: str,
        filename: str,
    ) -> Path:
        """
        Build source file path in the project workspace.

        Args:
            project_root: Root directory for all projects (e.g., /Volumes/Projects/y_pipeline_projects/Test)
            project: Project name (e.g., test_project)
            sequence: Sequence name (e.g., seq001)
            shot: Shot name (e.g., shot001)
            role: DCC role folder (e.g., maya, houdini, nuke)
            filename: Source filename (e.g., shot001_v001.ma)

        Returns:
            Path: {project_root}/{project}/{seq}/{shot}/{role}/{filename}
        """
        return Path(project_root) / project / sequence / shot / role / filename

    @staticmethod
    def build_publish_path(
        publish_root: str,
        project: str,
        sequence: str,
        shot: str,
        role: str,
        publish_type: str,
        version: str,
        filename: str,
    ) -> Path:
        """
        Build target publish file path.

        Args:
            publish_root: Root directory for all published files
            project: Project name
            sequence: Sequence name
            shot: Shot name
            role: DCC role folder
            publish_type: Type of publish (script, cache, render)
            version: Version string (e.g., v001, v002)
            filename: Source filename to publish

        Returns:
            Path: {publish_root}/{project}/{seq}/{shot}/{role}/{type}/v{XXX}/{filename}
        """
        return (
            Path(publish_root)
            / project
            / sequence
            / shot
            / role
            / publish_type
            / version
            / filename
        )

    @staticmethod
    def build_publish_version_dir(
        publish_root: str,
        project: str,
        sequence: str,
        shot: str,
        role: str,
        publish_type: str,
        version: str,
    ) -> Path:
        """
        Build publish version directory path (without filename).

        Returns:
            Path: {publish_root}/{project}/{seq}/{shot}/{role}/{type}/v{XXX}/
        """
        return (
            Path(publish_root)
            / project
            / sequence
            / shot
            / role
            / publish_type
            / version
        )

    @staticmethod
    def scan_existing_versions(
        publish_version_parent: Path, padding: int = 3
    ) -> List[str]:
        """
        Scan existing version directories and return sorted version list.

        Looks for directories matching pattern vXXX (e.g., v001, v002).
        The input path is the parent directory that contains version folders.

        Args:
            publish_version_parent: Directory containing version subdirectories
                                  (e.g., .../role/script/)
            padding: Zero-padding width for version numbers (default: 3)

        Returns:
            Sorted list of version strings (e.g., ['v001', 'v002'])
        """
        if not publish_version_parent.exists():
            return []

        versions = []
        for entry in publish_version_parent.iterdir():
            if entry.is_dir() and entry.name.startswith("v"):
                num_part = entry.name[1:]
                if num_part.isdigit():
                    versions.append(entry.name)

        # Sort numerically by extracted number
        def _version_key(v: str) -> int:
            return int(v[1:])

        return sorted(versions, key=_version_key)

    @staticmethod
    def next_version(
        publish_version_parent: Path, padding: int = 3
    ) -> str:
        """
        Determine the next version number by scanning existing versions.

        Args:
            publish_version_parent: Directory containing version subdirectories
            padding: Zero-padding width (default: 3 → v001, v002)

        Returns:
            Next version string (e.g., 'v001' if none exist, 'v003' if v001, v002 exist)
        """
        existing = PathBuilder.scan_existing_versions(
            publish_version_parent, padding
        )

        if not existing:
            return f"v{'1'.zfill(padding)}"

        # Extract highest version number
        max_num = 0
        for v in existing:
            num = int(v[1:])
            if num > max_num:
                max_num = num

        next_num = max_num + 1
        return f"v{str(next_num).zfill(padding)}"
