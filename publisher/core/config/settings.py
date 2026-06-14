"""
Configuration management for Pipeline Publisher.

Reads YAML configuration files and provides typed access to settings.
Supports multiple config sources with override priority:
1. Environment variables (highest priority)
2. User config file (~/.publisher/config.yaml)
3. Project config file (./publisher.yaml)
4. Default values (lowest priority)
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
    """PostgreSQL database connection configuration."""
    host: str = "localhost"
    port: int = 5432
    database: str = "pipeline_publisher"
    user: str = "pipeline"
    password: str = field(default="", repr=False)  # Mask password in repr/logging
    min_connections: int = 2
    max_connections: int = 10
    connection_timeout: int = 30

    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string (contains password - use with care)."""
        return (
            f"host={self.host} port={self.port} "
            f"dbname={self.database} user={self.user} "
            f"password={self.password} "
            f"connect_timeout={self.connection_timeout}"
        )

    @property
    def safe_connection_string(self) -> str:
        """Get connection string with masked password (safe for logging)."""
        return (
            f"host={self.host} port={self.port} "
            f"dbname={self.database} user={self.user} "
            f"password=**** "
            f"connect_timeout={self.connection_timeout}"
        )

    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Create config from environment variables with fallback defaults."""
        return cls(
            host=os.getenv('PGHOST', 'localhost'),
            port=int(os.getenv('PGPORT', '5432')),
            database=os.getenv('PGDATABASE', 'pipeline_publisher'),
            user=os.getenv('PGUSER', 'pipeline'),
            password=os.getenv('PGPASSWORD', ''),
        )


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    file_path: Optional[str] = None
    max_file_size_mb: int = 10
    backup_count: int = 5
    format_string: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


@dataclass
class PublisherConfig:
    """Main publisher configuration."""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    enable_database: bool = False  # 双模式开关：False=简单模式(仅文件), True=完整模式(含数据库)
    publish_root: Optional[str] = None
    project_root: Optional[str] = None
    version_padding: int = 3  # v001, v002, etc.
    max_publish_history: int = 50
    auto_save_before_publish: bool = True


class ConfigManager:
    """
    Configuration manager with layered override system.
    
    Priority order (highest first):
    1. Environment variables
    2. User config file (~/.publisher/config.yaml)
    3. Project config file (./publisher.yaml)
    4. Default values
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self._config: Optional[PublisherConfig] = None
        self._config_path = config_path or self._find_config_file()
    
    @staticmethod
    def _find_config_file() -> Optional[Path]:
        """Find configuration file in standard locations."""
        # Check project root
        project_config = Path.cwd() / "config" / "publisher.yaml"
        if project_config.exists():
            return project_config
        
        # Check user home
        user_config = Path.home() / ".publisher" / "config.yaml"
        if user_config.exists():
            return user_config
        
        return None
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load YAML configuration file if available."""
        if not self._config_path or not self._config_path.exists():
            return {}
        
        try:
            import yaml
        except ImportError:
            return {}

        try:
            with open(self._config_path, 'r') as f:
                result = yaml.safe_load(f)
                return result if isinstance(result, dict) else {}
        except (yaml.YAMLError, OSError):
            return {}
    
    def get_config(self) -> PublisherConfig:
        """Get merged configuration."""
        if self._config is not None:
            return self._config
        
        # Start with defaults
        config = PublisherConfig()
        
        # Override from YAML file
        yaml_config = self._load_yaml_config()
        if yaml_config:
            self._apply_yaml_overrides(config, yaml_config)
        
        # Override from environment variables
        self._apply_env_overrides(config)
        
        self._config = config
        return config
    
    def _apply_yaml_overrides(self, config: PublisherConfig, yaml_config: Dict[str, Any]):
        """Apply YAML config overrides."""
        if 'database' in yaml_config:
            db = yaml_config['database']
            if 'host' in db:
                config.database.host = db['host']
            if 'port' in db:
                config.database.port = int(db['port'])
            if 'database' in db:
                config.database.database = db['database']
            if 'user' in db:
                config.database.user = db['user']
            if 'password' in db:
                config.database.password = db['password']
        
        if 'logging' in yaml_config:
            log = yaml_config['logging']
            if 'level' in log:
                config.logging.level = log['level']
            if 'file_path' in log:
                config.logging.file_path = log['file_path']
        
        if 'enable_database' in yaml_config:
            config.enable_database = bool(yaml_config['enable_database'])
        if 'publish_root' in yaml_config:
            config.publish_root = yaml_config['publish_root']
        if 'project_root' in yaml_config:
            config.project_root = yaml_config['project_root']
        if 'version_padding' in yaml_config:
            config.version_padding = int(yaml_config['version_padding'])
    
    def _apply_env_overrides(self, config: PublisherConfig):
        """Apply environment variable overrides."""
        # Database
        if os.getenv('PGHOST'):
            config.database.host = os.getenv('PGHOST')
        if os.getenv('PGPORT'):
            config.database.port = int(os.getenv('PGPORT'))
        if os.getenv('PGDATABASE'):
            config.database.database = os.getenv('PGDATABASE')
        if os.getenv('PGUSER'):
            config.database.user = os.getenv('PGUSER')
        if os.getenv('PGPASSWORD'):
            config.database.password = os.getenv('PGPASSWORD')
        
        # Publish paths
        if os.getenv('PUBLISH_ROOT'):
            config.publish_root = os.getenv('PUBLISH_ROOT')
        if os.getenv('PROJECT_ROOT'):
            config.project_root = os.getenv('PROJECT_ROOT')
        
        # Database mode
        if os.getenv('PUBLISHER_ENABLE_DATABASE'):
            config.enable_database = os.getenv('PUBLISHER_ENABLE_DATABASE').lower() in ('true', '1', 'yes')
        
        # Logging
        if os.getenv('PUBLISHER_LOG_LEVEL'):
            config.logging.level = os.getenv('PUBLISHER_LOG_LEVEL')
    
    def reload(self):
        """Force configuration reload on next access."""
        self._config = None
