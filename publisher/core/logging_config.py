"""
Logging configuration for Pipeline Publisher.

Provides structured logging setup with support for:
- Console output with color coding
- File logging with rotation
- Different log levels per component
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from .config.settings import LoggingConfig


# Color codes for console output
COLOR_MAP = {
    'DEBUG': '\033[36m',      # Cyan
    'INFO': '\033[32m',       # Green
    'WARNING': '\033[33m',    # Yellow
    'ERROR': '\033[31m',      # Red
    'CRITICAL': '\033[41m',   # Red background
    'RESET': '\033[0m',       # Reset
}


class ColoredFormatter(logging.Formatter):
    """Custom formatter with console color support."""

    def format(self, record: logging.LogRecord) -> str:
        level_color = COLOR_MAP.get(record.levelname, '')
        reset = COLOR_MAP['RESET']

        # Add color to level name and message
        original_levelname = record.levelname
        original_msg = record.msg

        record.levelname = f"{level_color}{record.levelname}{reset}"
        record.msg = f"{level_color}{record.msg}{reset}"

        result = super().format(record)

        # Restore original values
        record.levelname = original_levelname
        record.msg = original_msg

        return result


class LoggerManager:
    """
    Logging manager for Pipeline Publisher.

    Provides centralized logging configuration with:
    - Console output with optional color coding
    - File output with rotation
    - Configurable log levels
    """

    _initialized = False
    _loggers: dict = {}

    def __init__(self):
        self._config = None

    @classmethod
    def initialize(cls, config: Optional[LoggingConfig] = None):
        """
        Initialize the logging system.

        Args:
            config: Logging configuration. Uses defaults if not provided.
        """
        if cls._initialized:
            return

        config = config or LoggingConfig()

        # Get root logger
        root_logger = logging.getLogger('publisher')
        root_logger.setLevel(getattr(logging, config.level.upper(), logging.INFO))

        # Remove existing handlers
        root_logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.level.upper(), logging.INFO))

        if sys.stdout.isatty():
            # Terminal supports colors
            console_formatter = ColoredFormatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%H:%M:%S'
            )
        else:
            console_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%H:%M:%S'
            )

        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler (if configured)
        if config.file_path:
            log_path = Path(config.file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                filename=str(log_path),
                maxBytes=config.max_file_size_mb * 1024 * 1024,
                backupCount=config.backup_count,
            )
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

        cls._initialized = True

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        Get a named logger instance.

        Args:
            name: Logger name (e.g., 'publisher.services.publish')

        Returns:
            Configured logger instance
        """
        if not LoggerManager._initialized:
            LoggerManager.initialize()

        logger = logging.getLogger(f'publisher.{name}')
        LoggerManager._loggers[name] = logger
        return logger

    @staticmethod
    def set_level(level: str):
        """Change log level at runtime."""
        root_logger = logging.getLogger('publisher')
        root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        for handler in root_logger.handlers:
            handler.setLevel(getattr(logging, level.upper(), logging.INFO))


# Convenience function for quick access
def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    return LoggerManager.get_logger(name)
