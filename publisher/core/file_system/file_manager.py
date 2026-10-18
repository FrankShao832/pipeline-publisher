"""
File management utilities for Pipeline Publisher.

Handles file operations such as copying, validation, and hashing.
"""

import hashlib
import shutil
from pathlib import Path
from typing import Optional


class FileManager:
    """File system operations for publishing."""

    @staticmethod
    def copy_file(
        source: Path, target: Path, overwrite: bool = False
    ) -> bool:
        """
        Copy a file from source to target, creating parent directories as needed.

        Args:
            source: Source file path
            target: Target file path
            overwrite: Whether to overwrite existing target file

        Returns:
            True if copy succeeded, False otherwise

        Raises:
            FileNotFoundError: If source does not exist
            FileExistsError: If target exists and overwrite is False
        """
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        if target.exists() and not overwrite:
            raise FileExistsError(
                f"Target already exists (use overwrite=True to replace): {target}"
            )

        # Create parent directories
        target.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy2(str(source), str(target))
        return True

    @staticmethod
    def file_exists(path: Path) -> bool:
        """Check if a file exists and is a regular file."""
        return path.is_file()

    @staticmethod
    def directory_exists(path: Path) -> bool:
        """Check if a directory exists."""
        return path.is_dir()

    @staticmethod
    def get_file_hash(path: Path) -> Optional[str]:
        """
        Compute MD5 hash of a file.

        Args:
            path: Path to the file

        Returns:
            MD5 hex digest string, or None if file doesn't exist
        """
        if not path.is_file():
            return None

        hash_md5 = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def ensure_directory(path: Path) -> bool:
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            path: Directory path to ensure

        Returns:
            True if directory exists or was created successfully
        """
        path.mkdir(parents=True, exist_ok=True)
        return True

    @staticmethod
    def get_file_size(path: Path) -> Optional[int]:
        """Get file size in bytes. Returns None if file doesn't exist."""
        if not path.is_file():
            return None
        return path.stat().st_size
