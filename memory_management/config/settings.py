"""
Configuration management for the Memory Management Module.

Handles environment variables, database connections, and application settings
with proper validation and defaults.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RedisConfig:
    """Redis database configuration."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    socket_timeout: int = 30
    socket_connect_timeout: int = 30
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[str, int] = field(default_factory=dict)
    connection_pool_max_connections: int = 50
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    
    @classmethod
    def from_env(cls) -> 'RedisConfig':
        """Create Redis configuration from environment variables."""
        return cls(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD'),
            socket_timeout=int(os.getenv('REDIS_SOCKET_TIMEOUT', '30')),
            socket_connect_timeout=int(os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', '30')),
            connection_pool_max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', '50')),
            retry_on_timeout=os.getenv('REDIS_RETRY_ON_TIMEOUT', 'true').lower() == 'true',
            health_check_interval=int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', '30'))
        )
    
    @property
    def url(self) -> str:
        """Get Redis connection URL."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class Neo4jConfig:
    """Neo4j database configuration."""
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"
    max_connection_lifetime: int = 3600
    max_connection_pool_size: int = 100
    connection_acquisition_timeout: int = 60
    connection_timeout: int = 30
    max_retry_time: int = 30
    initial_retry_delay: float = 1.0
    retry_delay_multiplier: float = 2.0
    retry_delay_jitter_factor: float = 0.2
    
    @classmethod
    def from_env(cls) -> 'Neo4jConfig':
        """Create Neo4j configuration from environment variables."""
        return cls(
            uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            username=os.getenv('NEO4J_USERNAME', 'neo4j'),
            password=os.getenv('NEO4J_PASSWORD', 'password'),
            database=os.getenv('NEO4J_DATABASE', 'neo4j'),
            max_connection_lifetime=int(os.getenv('NEO4J_MAX_CONNECTION_LIFETIME', '3600')),
            max_connection_pool_size=int(os.getenv('NEO4J_MAX_CONNECTION_POOL_SIZE', '100')),
            connection_acquisition_timeout=int(os.getenv('NEO4J_CONNECTION_ACQUISITION_TIMEOUT', '60')),
            connection_timeout=int(os.getenv('NEO4J_CONNECTION_TIMEOUT', '30')),
            max_retry_time=int(os.getenv('NEO4J_MAX_RETRY_TIME', '30'))
        )


@dataclass
class OllamaConfig:
    """Ollama LLM service configuration."""
    base_url: str = "http://localhost:11434"
    timeout: int = 120
    max_retries: int = 3
    retry_delay: float = 1.0
    default_model: str = "qwq:32b"
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    
    @classmethod
    def from_env(cls) -> 'OllamaConfig':
        """Create Ollama configuration from environment variables."""
        return cls(
            base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
            timeout=int(os.getenv('OLLAMA_TIMEOUT', '120')),
            max_retries=int(os.getenv('OLLAMA_MAX_RETRIES', '3')),
            retry_delay=float(os.getenv('OLLAMA_RETRY_DELAY', '1.0')),
            default_model=os.getenv('OLLAMA_DEFAULT_MODEL', 'deepseek-r1:8b'),
            temperature=float(os.getenv('OLLAMA_TEMPERATURE', '0.1')),
            max_tokens=int(os.getenv('OLLAMA_MAX_TOKENS')) if os.getenv('OLLAMA_MAX_TOKENS') else None
        )


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    log_file: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_console: bool = True
    enable_file: bool = False
    
    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        """Create logging configuration from environment variables."""
        return cls(
            level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            format=os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            date_format=os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S'),
            log_file=os.getenv('LOG_FILE'),
            max_file_size=int(os.getenv('LOG_MAX_FILE_SIZE', str(10 * 1024 * 1024))),
            backup_count=int(os.getenv('LOG_BACKUP_COUNT', '5')),
            enable_console=os.getenv('LOG_ENABLE_CONSOLE', 'true').lower() == 'true',
            enable_file=os.getenv('LOG_ENABLE_FILE', 'false').lower() == 'true'
        )


@dataclass
class APIConfig:
    """API server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    workers: int = 1
    timeout: int = 30
    max_request_size: int = 16 * 1024 * 1024  # 16MB
    cors_enabled: bool = True
    cors_origins: list = field(default_factory=lambda: ["*"])
    
    @classmethod
    def from_env(cls) -> 'APIConfig':
        """Create API configuration from environment variables."""
        cors_origins = os.getenv('API_CORS_ORIGINS', '*').split(',')
        return cls(
            host=os.getenv('API_HOST', '0.0.0.0'),
            port=int(os.getenv('API_PORT', '8000')),
            debug=os.getenv('API_DEBUG', 'false').lower() == 'true',
            workers=int(os.getenv('API_WORKERS', '1')),
            timeout=int(os.getenv('API_TIMEOUT', '30')),
            max_request_size=int(os.getenv('API_MAX_REQUEST_SIZE', str(16 * 1024 * 1024))),
            cors_enabled=os.getenv('API_CORS_ENABLED', 'true').lower() == 'true',
            cors_origins=cors_origins
        )


@dataclass
class MemoryConfig:
    """Memory management specific configuration."""
    stm_ttl_hours: int = 24
    ltm_confidence_threshold: float = 0.7
    max_related_concepts: int = 10
    scenario_id_format: str = "{domain}_{requirement}_{concept}"
    rule_id_format: str = "{policy}_{concept}_{version:02d}"
    enable_traceability: bool = True
    enable_version_history: bool = True
    
    @classmethod
    def from_env(cls) -> 'MemoryConfig':
        """Create memory configuration from environment variables."""
        return cls(
            stm_ttl_hours=int(os.getenv('MEMORY_STM_TTL_HOURS', '24')),
            ltm_confidence_threshold=float(os.getenv('MEMORY_LTM_CONFIDENCE_THRESHOLD', '0.7')),
            max_related_concepts=int(os.getenv('MEMORY_MAX_RELATED_CONCEPTS', '10')),
            scenario_id_format=os.getenv('MEMORY_SCENARIO_ID_FORMAT', '{domain}_{requirement}_{concept}'),
            rule_id_format=os.getenv('MEMORY_RULE_ID_FORMAT', '{policy}_{concept}_{version:02d}'),
            enable_traceability=os.getenv('MEMORY_ENABLE_TRACEABILITY', 'true').lower() == 'true',
            enable_version_history=os.getenv('MEMORY_ENABLE_VERSION_HISTORY', 'true').lower() == 'true'
        )


@dataclass
class Settings:
    """Main application settings."""
    redis: RedisConfig = field(default_factory=RedisConfig)
    neo4j: Neo4jConfig = field(default_factory=Neo4jConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    api: APIConfig = field(default_factory=APIConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    
    # Environment settings
    environment: str = "development"
    debug: bool = False
    testing: bool = False
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """Create settings from environment variables."""
        return cls(
            redis=RedisConfig.from_env(),
            neo4j=Neo4jConfig.from_env(),
            ollama=OllamaConfig.from_env(),
            logging=LoggingConfig.from_env(),
            api=APIConfig.from_env(),
            memory=MemoryConfig.from_env(),
            environment=os.getenv('ENVIRONMENT', 'development'),
            debug=os.getenv('DEBUG', 'false').lower() == 'true',
            testing=os.getenv('TESTING', 'false').lower() == 'true'
        )
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        errors = []
        
        # Validate Redis configuration
        if not (1 <= self.redis.port <= 65535):
            errors.append("Redis port must be between 1 and 65535")
        
        if not (0 <= self.redis.db <= 15):
            errors.append("Redis database must be between 0 and 15")
        
        # Validate Neo4j configuration
        if not self.neo4j.uri.startswith(('bolt://', 'neo4j://', 'bolt+s://', 'neo4j+s://')):
            errors.append("Neo4j URI must use bolt:// or neo4j:// protocol")
        
        # Validate API configuration
        if not (1 <= self.api.port <= 65535):
            errors.append("API port must be between 1 and 65535")
        
        if self.api.workers < 1:
            errors.append("API workers must be at least 1")
        
        # Validate memory configuration
        if self.memory.stm_ttl_hours < 1:
            errors.append("STM TTL must be at least 1 hour")
        
        if not (0.0 <= self.memory.ltm_confidence_threshold <= 1.0):
            errors.append("LTM confidence threshold must be between 0.0 and 1.0")
        
        # Validate logging configuration
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.logging.level not in valid_log_levels:
            errors.append(f"Log level must be one of: {', '.join(valid_log_levels)}")
        
        if errors:
            for error in errors:
                logging.error(f"Configuration validation error: {error}")
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            'redis': {
                'host': self.redis.host,
                'port': self.redis.port,
                'db': self.redis.db,
                'url': self.redis.url
            },
            'neo4j': {
                'uri': self.neo4j.uri,
                'username': self.neo4j.username,
                'database': self.neo4j.database
            },
            'ollama': {
                'base_url': self.ollama.base_url,
                'default_model': self.ollama.default_model,
                'timeout': self.ollama.timeout
            },
            'api': {
                'host': self.api.host,
                'port': self.api.port,
                'debug': self.api.debug
            },
            'memory': {
                'stm_ttl_hours': self.memory.stm_ttl_hours,
                'ltm_confidence_threshold': self.memory.ltm_confidence_threshold,
                'enable_traceability': self.memory.enable_traceability
            },
            'environment': self.environment,
            'debug': self.debug,
            'testing': self.testing
        }


# Global settings instance
settings = Settings.from_env()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment variables."""
    global settings
    settings = Settings.from_env()
    return settings


def validate_environment() -> bool:
    """Validate that all required environment variables are set."""
    required_vars = [
        'REDIS_HOST',
        'NEO4J_URI',
        'NEO4J_USERNAME', 
        'NEO4J_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    return True


def setup_logging(config: LoggingConfig = None) -> None:
    """Set up logging configuration."""
    if config is None:
        config = settings.logging
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt=config.format,
        datefmt=config.date_format
    )
    
    # Console handler
    if config.enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if config.enable_file and config.log_file:
        from logging.handlers import RotatingFileHandler
        
        # Ensure log directory exists
        log_path = Path(config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            config.log_file,
            maxBytes=config.max_file_size,
            backupCount=config.backup_count
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger('neo4j').setLevel(logging.WARNING)
    logging.getLogger('redis').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def get_database_health_check_config() -> Dict[str, Any]:
    """Get configuration for database health checks."""
    return {
        'redis': {
            'enabled': True,
            'timeout': 5,
            'interval': settings.redis.health_check_interval
        },
        'neo4j': {
            'enabled': True,
            'timeout': 10,
            'interval': 30
        },
        'ollama': {
            'enabled': True,
            'timeout': 15,
            'interval': 60
        }
    }