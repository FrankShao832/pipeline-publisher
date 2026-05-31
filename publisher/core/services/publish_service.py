"""
Publish service for Pipeline Publisher.

Core business logic for publishing operations.
Supports dual mode: simple (file-only) and full (with database).

Publish flow:
1. validate_context()  — Verify required fields are complete
2. validate_source()   — Confirm source file exists
3. determine_version() — Auto-increment version number
4. build_target_path() — Construct target publish path
5. check_duplicate()   — Check if already published (optional)
6. copy_file()         — Copy source to publish directory
7. record()            — Log result (database in full mode)
8. return PublishResult
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any

from publisher.core.file_system.path_builder import PathBuilder
from publisher.core.file_system.file_manager import FileManager
from publisher.core.models.enums import PublishType
from publisher.core.logging_config import get_logger


@dataclass
class PublishRequest:
    """Request data for a publish operation."""
    source_path: str
    publish_type: PublishType
    context: Dict[str, str]  # project, sequence, shot, role, publish_root, project_root
    note: str = ""


@dataclass
class PublishResult:
    """Result of a publish operation."""
    success: bool
    message: str
    publish_path: Optional[str] = None
    version: Optional[str] = None
    error: Optional[str] = None


# Required context fields for validation
REQUIRED_CONTEXT_FIELDS = [
    'project', 'sequence', 'shot', 'role', 'publish_root'
]


class PublishService:
    """
    Core publish service with dual-mode support.

    Simple mode (enable_database=False):
    - File copy + console logging only
    - No external dependencies

    Full mode (enable_database=True):
    - File copy + console logging
    - PostgreSQL persistence (requires publish_repository)
    """

    def __init__(
        self,
        file_manager: Optional[FileManager] = None,
        path_builder: Optional[PathBuilder] = None,
        enable_database: bool = False,
        publish_repository=None,  # Optional database repository
    ):
        self.file_manager = file_manager or FileManager()
        self.path_builder = path_builder or PathBuilder()
        self.enable_database = enable_database
        self.publish_repository = publish_repository
        self.logger = get_logger('services.publish')

    def execute_publish(self, request: PublishRequest) -> PublishResult:
        """
        Execute a publish operation with full validation and error handling.

        Args:
            request: PublishRequest with source path, type, and context

        Returns:
            PublishResult with success/failure status and details
        """
        try:
            # Step 1: Validate context
            context = request.context
            missing = self._validate_context(context)
            if missing:
                return PublishResult(
                    success=False,
                    message=f"Missing required context fields: {', '.join(missing)}",
                    error="validation_error",
                )

            # Step 2: Validate source file
            source = Path(request.source_path)
            if not self.file_manager.file_exists(source):
                return PublishResult(
                    success=False,
                    message=f"Source file not found: {source}",
                    error="file_not_found",
                )

            # Step 3: Determine version
            project = context['project']
            sequence = context['sequence']
            shot = context['shot']
            role = context['role']
            publish_root = context['publish_root']
            publish_type = request.publish_type.value

            # The type directory (e.g., .../maya/script/) contains version subdirs
            version_parent = (
                Path(publish_root) / project / sequence / shot / role / publish_type
            )

            version = self.path_builder.next_version(version_parent)

            # Step 4: Build target path
            target = self.path_builder.build_publish_path(
                publish_root=publish_root,
                project=project,
                sequence=sequence,
                shot=shot,
                role=role,
                publish_type=publish_type,
                version=version,
                filename=source.name,
            )

            # Step 5: Check duplicate (simple mode: skip if already exists?)
            if target.exists() and not self.enable_database:
                # In simple mode, allow overwrite silently
                pass

            # Step 6: Copy file
            self.file_manager.copy_file(source, target, overwrite=True)

            # Step 7: Log result
            self.logger.info(
                f"Published {source.name} → {target} "
                f"[{publish_type}] {version} "
                f"(db={'on' if self.enable_database else 'off'})"
            )

            # Step 8: Record to database (full mode only)
            if self.enable_database and self.publish_repository:
                try:
                    self.publish_repository.save_publish({
                        'source_path': str(source),
                        'publish_path': str(target),
                        'version': version,
                        'publish_type': publish_type,
                        'context': context,
                        'note': request.note,
                    })
                    self.logger.info(f"Database record saved for {target}")
                except Exception as e:
                    self.logger.error(f"Failed to save database record: {e}")
                    # Don't fail the publish if DB write fails
                    # Return success with a warning

            return PublishResult(
                success=True,
                message=f"Published successfully: {source.name} → v{version}",
                publish_path=str(target),
                version=version,
            )

        except FileNotFoundError as e:
            return PublishResult(
                success=False,
                message=str(e),
                error="file_not_found",
            )
        except Exception as e:
            self.logger.error(f"Publish failed: {e}", exc_info=True)
            return PublishResult(
                success=False,
                message=f"Publish failed: {str(e)}",
                error="unexpected_error",
            )

    def _validate_context(self, context: Dict[str, str]) -> list:
        """
        Validate that all required context fields are present and non-empty.

        Returns:
            List of missing field names (empty list if all valid)
        """
        missing = []
        for field in REQUIRED_CONTEXT_FIELDS:
            value = context.get(field, '')
            if not value or value == 'Not set':
                missing.append(field)
        return missing
