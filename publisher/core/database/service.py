"""
Database service — connection pool singleton (Level 2).

Big-studio standard approach:
  DCC launch → DatabaseService.initialize(config) → pool ready
  All tools share the pool via class methods
  DCC shutdown → DatabaseService.close_all() → pool closed

Uses psycopg2's ThreadedConnectionPool for safe multi-thread access.
"""

import logging
from typing import Optional
from dataclasses import dataclass

import psycopg2
from psycopg2 import pool as pg_pool

from publisher.core.config.settings import DatabaseConfig
from publisher.core.logging_config import get_logger


class DatabaseService:
    """Connection pool singleton for PostgreSQL.

    Usage:
        # On DCC startup
        DatabaseService.initialize(config)

        # Anywhere in the session
        conn = DatabaseService.get_connection()
        try:
            # ... use conn ...
        finally:
            DatabaseService.return_connection(conn)

        # On DCC shutdown
        DatabaseService.close_all()
    """

    _pool: Optional[pg_pool.ThreadedConnectionPool] = None
    _config: Optional[DatabaseConfig] = None
    _logger: Optional[logging.Logger] = None

    # ── Lifecycle ──

    @classmethod
    def initialize(cls, config: DatabaseConfig) -> None:
        """Initialize the connection pool.

        Safe to call multiple times — subsequent calls are no-ops
        if already initialized. Call close_all() first to reinitialize.
        """
        if cls._pool is not None:
            return  # Already initialized

        cls._logger = get_logger('database.service')
        cls._config = config
        cls._logger.info(
            f"Initializing database pool → "
            f"{config.safe_connection_string}"
        )

        try:
            cls._pool = pg_pool.ThreadedConnectionPool(
                minconn=config.min_connections,
                maxconn=config.max_connections,
                host=config.host,
                port=config.port,
                dbname=config.database,
                user=config.user,
                password=config.password,
                connect_timeout=config.connection_timeout,
            )
            # Verify connection works
            conn = cls._pool.getconn()
            cls._pool.putconn(conn)
            cls._logger.info(
                f"Database pool ready "
                f"(min={config.min_connections}, "
                f"max={config.max_connections})"
            )
        except Exception as e:
            cls._logger.error(f"Failed to initialize database pool: {e}")
            cls._pool = None
            raise

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if the pool is ready."""
        return cls._pool is not None

    @classmethod
    def close_all(cls) -> None:
        """Close all connections and shut down the pool."""
        if cls._pool is None:
            return
        cls._log_info("Closing database pool...")
        try:
            cls._pool.closeall()
        except Exception as e:
            cls._log_warning(f"Error closing pool: {e}")
        finally:
            cls._pool = None
            cls._config = None

    # ── Connection management ──

    @classmethod
    def get_connection(cls):
        """Get a connection from the pool.

        Raises:
            RuntimeError: If pool not initialized
            psycopg2.pool.PoolError: If pool exhausted
        """
        if cls._pool is None:
            raise RuntimeError(
                "Database pool not initialized. Call DatabaseService.initialize() first."
            )
        try:
            return cls._pool.getconn()
        except Exception as e:
            cls._log_error(f"Failed to get connection from pool: {e}")
            raise

    @classmethod
    def return_connection(cls, conn) -> None:
        """Return a connection to the pool."""
        if cls._pool is None:
            cls._log_warning("Pool not initialized, closing connection directly")
            try:
                conn.close()
            except Exception:
                pass
            return
        try:
            cls._pool.putconn(conn)
        except Exception as e:
            cls._log_warning(f"Failed to return connection to pool: {e}")
            try:
                conn.close()
            except Exception:
                pass

    # ── Context manager for safe usage ──

    @classmethod
    def connection(cls):
        """Context manager for auto return.

        Usage:
            with DatabaseService.connection() as conn:
                conn.execute(...)
        """
        return _DatabaseConnectionContext()

    # ── Helpers ──

    @classmethod
    def _log_info(cls, msg: str) -> None:
        if cls._logger:
            cls._logger.info(msg)

    @classmethod
    def _log_warning(cls, msg: str) -> None:
        if cls._logger:
            cls._logger.warning(msg)

    @classmethod
    def _log_error(cls, msg: str) -> None:
        if cls._logger:
            cls._logger.error(msg)


class _DatabaseConnectionContext:
    """Context manager for DatabaseService connections."""

    def __enter__(self):
        self.conn = DatabaseService.get_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        DatabaseService.return_connection(self.conn)
        return False  # Don't suppress exceptions
