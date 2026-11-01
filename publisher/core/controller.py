"""
Application controller for Pipeline Publisher.

Manages application-level dependencies and configuration.
Serves as the bridge between the UI layer and the service/infrastructure layers.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from publisher.core.config.settings import ConfigManager, platform_dev_root
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

        # Log resolved publish roots + source. Inside a DCC launched by hatch the
        # PROJECT_ROOT/PUBLISH_ROOT env vars win (env > config); standalone falls
        # back to the publisher.yaml default (Test) on purpose.
        self._logger.info(
            "Publisher roots -> project: %s (env: %s) | publish: %s (env: %s)",
            config.project_root, bool(os.getenv('PROJECT_ROOT')),
            config.publish_root, bool(os.getenv('PUBLISH_ROOT')),
        )

        database_repo = self._init_database(config)

        # ── Asset Manager integration ────────────────────────
        record_publish = self._init_asset_manager(config)

        self.publish_service = PublishService(
            file_manager=FileManager(),
            path_builder=PathBuilder(),
            enable_database=config.enable_database,
            publish_repository=database_repo,
            record_publish=record_publish,
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
            or str(platform_dev_root() / 'projects' / 'y_pipeline_publish' / 'Test')
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
            or str(platform_dev_root() / 'projects' / 'y_pipeline_projects' / 'Test')
        )

    def _init_asset_manager(self, config):
        """Create a record_publish callback writing to the Asset Manager DB.

        Preferred path: import asset_manager in-process (works when this
        process has sqlalchemy/psycopg2, e.g. standalone python env).

        Fallback path: Houdini's bundled python has no DB libs, so we spawn
        asset_manager's own env python (scripts/record_publish.py) as a remote
        recorder and pass the context via env vars.
        """
        if not config.enable_database:
            return None

        am_root = platform_dev_root() / 'tools' / 'pipeline' / 'asset_manager'

        # ── Preferred: in-process recording ────────────────────
        try:
            import sys as _sys
            _am_path = str(am_root / 'src')
            if _am_path not in _sys.path:
                _sys.path.insert(0, _am_path)

            from asset_manager.core.services.db_asset_service import DatabaseAssetService
            from asset_manager.dal.database import DEFAULT_DATABASE_URL

            _svc = DatabaseAssetService()
            _user_name = self.user.name

            self._logger.info(
                f"Asset Manager integration enabled (in-process) → {DEFAULT_DATABASE_URL}"
            )

            def _record(context, file_path, version, note):
                project = context.get('project', '')
                sequence = context.get('sequence', '')
                shot = context.get('shot', '')
                department = context.get('department', '')
                dcc = context.get('dcc', '')
                if not all([project, sequence, shot, department]):
                    self._logger.warning(
                        f"Incomplete context for asset record: {context}"
                    )
                    return
                try:
                    asset = _svc.ensure_asset(project, sequence, shot, department,
                                              dcc=dcc)
                    _svc.add_version(
                        asset_name=asset.name,
                        file_path=file_path,
                        created_by=_user_name,
                        publish_note=note,
                    )
                    self._logger.info(
                        f"Asset version created: {asset.name} {version}"
                    )
                except Exception as e:
                    self._logger.error(f"Asset record failed: {e}")

            return _record

        except Exception as exc:  # noqa: BLE001
            self._logger.warning(
                f"Asset Manager in-process integration unavailable ({exc}); "
                f"falling back to remote recorder subprocess."
            )

        # ── Fallback: remote recorder (asset_manager env python) ──
        _py = am_root / 'env' / 'bin' / 'python'
        _script = am_root / 'scripts' / 'record_publish.py'
        if not (_py.is_file() and _script.is_file()):
            self._logger.error(
                f"Remote asset recorder not found ({_script}) — "
                f"publish will NOT write the DB."
            )
            return None

        import subprocess  # noqa: PLC0415

        def _record(context, file_path, version, note):
            project = context.get('project', '')
            sequence = context.get('sequence', '')
            shot = context.get('shot', '')
            department = context.get('department', '')
            if not all([project, sequence, shot, department]):
                self._logger.warning(
                    f"Incomplete context for asset record: {context}"
                )
                return
            env = os.environ.copy()
            env['SHOW'] = project
            env['SEQ'] = sequence
            env['SHOT'] = shot
            env['DEPARTMENT'] = department
            env['PIPELINE_DEPARTMENT'] = department
            # Provenance: the recorder stores this as assets.dcc_type. Empty
            # is tolerated (older callers), but the publish knows its DCC.
            dcc = context.get('dcc', '')
            env['DCC'] = dcc
            env['PIPELINE_DCC'] = dcc
            cmd = [str(_py), str(_script), file_path]
            if note:
                cmd.append(note)
            try:
                res = subprocess.run(cmd, env=env, capture_output=True,
                                     text=True, timeout=90)
                if res.returncode == 0:
                    self._logger.info(
                        f"Asset version recorded (remote): {res.stdout.strip()}"
                    )
                else:
                    self._logger.error(
                        f"Asset record failed (remote rc={res.returncode}): "
                        f"{(res.stderr or res.stdout).strip()}"
                    )
            except Exception as exc:  # noqa: BLE001
                self._logger.error(f"Asset record failed (remote spawn): {exc}")

        self._logger.info(
            f"Asset Manager integration enabled (remote recorder: {_script})"
        )
        return _record

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
