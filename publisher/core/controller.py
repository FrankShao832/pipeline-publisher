"""
Application controller for Pipeline Publisher.

Manages application-level dependencies and configuration.
Serves as the bridge between the UI layer and the service/infrastructure layers.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from publisher.core.config.settings import ConfigManager
from publisher.core.services import PublishService
from publisher.core.file_system.path_builder import PathBuilder
from publisher.core.file_system.file_manager import FileManager
from publisher.core.database.service import DatabaseService
from publisher.core.database.repository import PublishRepository
from publisher.core.logging_config import get_logger


@dataclass
class UserInfo:
    """Current user information."""
    name: str = "unknown"
    role: str = "artist"
    is_developer: bool = False


class PublisherController:
    """
    Application controller managing core dependencies.

    Encapsulates:
    - Configuration management (ConfigManager)
    - Publish service lifecycle
    - Database service lifecycle (connection pool, Level 2)
    - User information detection

    Designed to be created once and injected into MainWindow
    and other components that need access to shared services.
    """

    def __init__(self, standalone_mode: bool = True):
        """Initialize controller with all core dependencies.

        Args:
            standalone_mode: Whether running as standalone application
                             (vs embedded in DCC)
        """
        self.standalone_mode = standalone_mode
        self.user = self._detect_user()
        self._logger = get_logger('controller')

        # Initialize configuration
        self.config_manager = ConfigManager()

        # Initialize services
        config = self.config_manager.get_config()
        database_repo = self._init_database(config)

        self.publish_service = PublishService(
            file_manager=FileManager(),
            path_builder=PathBuilder(),
            enable_database=config.enable_database,
            publish_repository=database_repo,
        )

    # ── Public Methods ──

    def reload_config(self):
        """Reload configuration and update services."""
        self.config_manager.reload()
        config = self.config_manager.get_config()

        # Reinitialize database if mode changed
        if config.enable_database and not DatabaseService.is_initialized():
            self._init_database(config)

        self.publish_service.enable_database = config.enable_database
        if config.enable_database and DatabaseService.is_initialized():
            self.publish_service.publish_repository = PublishRepository()

    def get_publish_root(self) -> str:
        """Get publish root path from config (with env var fallback).

        Returns:
            Publish root directory path
        """
        config = self.config_manager.get_config()
        return (
            config.publish_root
            or os.getenv('PUBLISH_ROOT')
            or '/Volumes/Projects/y_pipeline_publish/Test'
        )

    def get_project_root(self) -> str:
        """Get project root path from config (with env var fallback).

        Returns:
            Project root directory path
        """
        config = self.config_manager.get_config()
        return (
            config.project_root
            or os.getenv('PROJECT_ROOT')
            or '/Volumes/Projects/y_pipeline_projects/Test'
        )

    def cleanup(self):
        """Clean up controller resources (DCC shutdown equivalent).

        Closes database connection pool if initialized — Level 2 shutdown.
        """
        if DatabaseService.is_initialized():
            self._logger.info("Shutting down database pool...")
            DatabaseService.close_all()

    # ── Internal Methods ──

    def _init_database(self, config) -> Optional[PublishRepository]:
        """Initialize database connection pool and repository.

        Args:
            config: Current PublisherConfig

        Returns:
            PublishRepository instance if database mode enabled, else None
        """
        if not config.enable_database:
            self._logger.info("Database mode disabled — file-only mode")
            return None

        try:
            DatabaseService.initialize(config.database)
            self._logger.info(
                "Database mode enabled — "
                f"connected to {config.database.database}@{config.database.host}"
            )
            return PublishRepository()
        except Exception as e:
            self._logger.error(
                f"Database initialization failed: {e}\n"
                f"Falling back to file-only mode"
            )
            return None

    def _detect_user(self) -> UserInfo:
        """Detect current user information from environment variables.

        Returns:
            UserInfo with name, role, and developer flag
        """
        user_name = os.getenv('USER', os.getenv('USERNAME', 'unknown'))
        # Frank is Admin by default; others controlled by PUBLISHER_ROLE env var
        default_role = 'admin' if user_name.lower() == 'frank' else 'artist'
        user_role = os.getenv('PUBLISHER_ROLE', default_role).lower()
        is_developer = user_role in ('admin', 'developer', 'td')

        return UserInfo(
            name=user_name,
            role=user_role,
            is_developer=is_developer,
        )
