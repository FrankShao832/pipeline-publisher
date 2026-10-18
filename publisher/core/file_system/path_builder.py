"""
Path construction utilities for Pipeline Publisher.

Builds consistent pipeline paths for source (work) and publish directories.

Path patterns:
  Work:     {project_root}/{project}/{seq}/{shot}/{department}/{filename}
  Publish:  {publish_root}/{project}/{seq}/{shot}/{department}/{type}/v{XXX}/{filename}

Department replaces the ambiguous 'role' field — see publisher.core.constants.
"""

from pathlib import Path
from typing import List, Optional
import re


class PathBuilder:
    """Pipeline path construction and version scanning."""

    @staticmethod
    def build_work_path(
        project_root: str,
        project: str,
        sequence: str,
        shot: str,
        department: str,
        filename: str,
    ) -> Path:
        """
        Build source file path in the project workspace.

        Args:
            project_root: Root directory for all projects
            project: Project name (e.g., test_project)
            sequence: Sequence name (e.g., seq001)
            shot: Shot name (e.g., shot001)
            department: Department/工种 (e.g., fx, anim, lighting)
            filename: Source filename (e.g., shot001_v001.hip)

        Returns:
            Path: {project_root}/{project}/{seq}/{shot}/{department}/{filename}
        """
        return Path(project_root) / project / sequence / shot / department / filename

    @staticmethod
    def build_publish_path(
        publish_root: str,
        project: str,
        sequence: str,
        shot: str,
        department: str,
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
            department: Department/工种
            publish_type: Type of publish (script, cache, render)
            version: Version string (e.g., v001, v002)
            filename: Source filename to publish

        Returns:
            Path: {publish_root}/{project}/{seq}/{shot}/{department}/{type}/v{XXX}/{filename}
        """
        return (
            Path(publish_root)
            / project
            / sequence
            / shot
            / department
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
        department: str,
        publish_type: str,
        version: str,
    ) -> Path:
        """
        Build publish version directory path (without filename).

        Returns:
            Path: {publish_root}/{project}/{seq}/{shot}/{department}/{type}/{version}
        """
        return (
            Path(publish_root)
            / project
            / sequence
            / shot
            / department
            / publish_type
            / version
        )

    @staticmethod
    def publish_filename(source_name: str, version: str) -> str:
        """Generate publish filename with version embedded in the name.

        Replaces any existing _vXXX suffix with the publish version.
        If no version suffix exists, appends the publish version.

        Examples:
            'shot001_v001.ma', 'v010'  → 'shot001_v010.ma'
            'shot001.ma',       'v010'  → 'shot001_v010.ma'
            'script.py',        'v010'  → 'script_v010.py'

        Args:
            source_name: Original source filename
            version: Publish version string (e.g. 'v010')

        Returns:
            Filename with publish version embedded
        """
        p = Path(source_name)
        stem = p.stem
        ext = p.suffix

        # Replace existing _vXXX pattern, or append new version suffix
        if re.search(r'_v\d+$', stem):
            new_stem = re.sub(r'_v\d+$', f'_{version}', stem)
        else:
            new_stem = f'{stem}_{version}'

        return f'{new_stem}{ext}'

    @staticmethod
    def extract_version(filename: str) -> Optional[str]:
        """Extract version string from a filename.

        Looks for _vXXX pattern at the end of the stem.

        Examples:
            'shot001_v010.ma' → 'v010'
            'shot001.ma'      → None

        Args:
            filename: Filename to extract version from

        Returns:
            Version string (e.g. 'v010') or None
        """
        p = Path(filename)
        match = re.search(r'_v(\d+)$', p.stem)
        if match:
            return f"v{match.group(1)}"
        return None

    @staticmethod
    def version_up_filename(filename: str, padding: int = 3) -> str:
        """Increment the version number in a filename by 1.

        Examples:
            'shot001_v010.ma' → 'shot001_v011.ma'
            'shot001.ma'      → 'shot001_v001.ma'  (if no version, start at v001)

        Args:
            filename: Source filename
            padding: Zero-padding width (default: 3)

        Returns:
            Filename with incremented version
        """
        p = Path(filename)
        stem = p.stem
        ext = p.suffix

        match = re.search(r'_v(\d+)$', stem)
        if match:
            current_num = int(match.group(1))
            next_num = current_num + 1
            new_stem = re.sub(r'_v\d+$', f'_v{str(next_num).zfill(padding)}', stem)
        else:
            new_stem = f'{stem}_v{str(1).zfill(padding)}'

        return f'{new_stem}{ext}'

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
                                  (e.g., .../fx/script/)
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
