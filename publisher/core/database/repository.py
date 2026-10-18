"""
Publish repository — data access for publish operations.

Maps PublishService data to the publish_tasks table.
Uses DatabaseService singleton for connection pool access.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from publisher.core.database.service import DatabaseService
from publisher.core.logging_config import get_logger


class PublishRepository:
    """Repository for publish_tasks table operations."""

    def __init__(self):
        self.logger = get_logger('database.repository')

    # ── Public API ──

    def save_publish(self, data: Dict[str, Any]) -> int:
        """Record a publish operation in the database.

        Args:
            data: Dictionary with keys:
                - source_path: str
                - publish_path: str
                - version: str (e.g. 'v011')
                - publish_type: str
                - context: dict with 'project'
                - note: str (optional)

        Returns:
            The inserted record's ID

        Raises:
            RuntimeError: If database pool not initialized
            ValueError: If project or user not found
        """
        if not DatabaseService.is_initialized():
            raise RuntimeError(
                "Database not initialized. "
                "Enable database in config or run with --enable-db."
            )

        project_name = data.get('context', {}).get('project', '')
        username = 'frank'  # TODO: derive from actual user session

        with DatabaseService.connection() as conn:
            project_id = self._lookup_project_id(conn, project_name)
            if project_id is None:
                raise ValueError(f"Project not found: '{project_name}'")

            user_id = self._lookup_user_id(conn, username)
            if user_id is None:
                raise ValueError(f"User not found: '{username}'")

            now = datetime.now()
            record_id = self._insert_publish_task(
                conn=conn,
                project_id=project_id,
                user_id=user_id,
                source_path=data['source_path'],
                target_path=data['publish_path'],
                publish_type=data.get('publish_type', ''),
                version=data.get('version', ''),
                note=data.get('note', ''),
                status='completed',
                created_at=now,
                completed_at=now,
            )

            conn.commit()
            self.logger.info(
                f"Database record #{record_id} saved "
                f"for {data['publish_path']} [{data.get('version', '?')}]"
            )
            return record_id

    # ── Internal lookups ──

    def _lookup_project_id(self, conn, project_name: str) -> Optional[int]:
        """Find project ID by name."""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM projects WHERE name = %s",
                (project_name,)
            )
            row = cur.fetchone()
            return row[0] if row else None

    def _lookup_user_id(self, conn, username: str) -> Optional[int]:
        """Find user ID by username."""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM users WHERE username = %s",
                (username,)
            )
            row = cur.fetchone()
            return row[0] if row else None

    def _insert_publish_task(
        self,
        conn,
        project_id: int,
        user_id: int,
        source_path: str,
        target_path: str,
        publish_type: str,
        version: str,
        note: str,
        status: str,
        created_at: datetime,
        completed_at: datetime,
    ) -> int:
        """Insert a publish_tasks record and return its ID."""
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO publish_tasks
                    (project_id, user_id, source_path, target_path,
                     publish_type, version, notes, status,
                     created_at, completed_at)
                VALUES
                    (%s, %s, %s, %s,
                     %s, %s, %s, %s,
                     %s, %s)
                RETURNING id
                """,
                (
                    project_id, user_id, source_path, target_path,
                    publish_type, version, note, status,
                    created_at, completed_at,
                ),
            )
            return cur.fetchone()[0]
