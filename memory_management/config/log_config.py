"""
Structured logging configuration for the Memory Management Module.

Provides centralized logging setup with proper formatting, handlers,
and integration with the configuration system.
"""

import logging
import logging.handlers
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import contextmanager

from .settings import LoggingConfig, get_settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


class MemoryManagementLogger:
    """Centralized logger for the Memory Management Module."""
    
    def __init__(self, config: Optional[LoggingConfig] = None):
        """Initialize the logging system."""
        self.config = config or get_settings().logging
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.level))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Add handlers
        if self.config.enable_console:
            self._add_console_handler(root_logger)
        
        if self.config.enable_file and self.config.log_file:
            self._add_file_handler(root_logger)
        
        # Configure third-party loggers
        self._configure_third_party_loggers()
        
        # Log startup message
        logger = logging.getLogger(__name__)
        logger.info("Logging system initialized", extra={
            'log_level': self.config.level,
            'console_enabled': self.config.enable_console,
            'file_enabled': self.config.enable_file,
            'log_file': self.config.log_file
        })
    
    def _add_console_handler(self, logger: logging.Logger) -> None:
        """Add console handler to logger."""
        console_handler = logging.StreamHandler(sys.stdout)
        
        if get_settings().environment == 'production':
            # Use structured JSON logging in production
            formatter = StructuredFormatter()
        else:
            # Use human-readable format in development
            formatter = logging.Formatter(
                fmt=self.config.format,
                datefmt=self.config.date_format
            )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    def _add_file_handler(self, logger: logging.Logger) -> None:
        """Add rotating file handler to logger."""
        # Ensure log directory exists
        log_path = Path(self.config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            self.config.log_file,
            maxBytes=self.config.max_file_size,
            backupCount=self.config.backup_count
        )
        
        # Always use structured format for file logs
        formatter = StructuredFormatter()
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    def _configure_third_party_loggers(self) -> None:
        """Configure logging levels for third-party libraries."""
        third_party_loggers = {
            'neo4j': logging.WARNING,
            'redis': logging.WARNING,
            'requests': logging.WARNING,
            'urllib3': logging.WARNING,
            'httpx': logging.WARNING,
            'asyncio': logging.WARNING
        }
        
        for logger_name, level in third_party_loggers.items():
            logging.getLogger(logger_name).setLevel(level)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance with the given name."""
        return logging.getLogger(name)
    
    @contextmanager
    def log_context(self, **context):
        """Context manager for adding structured context to logs."""
        logger = logging.getLogger()
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            for key, value in context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        try:
            yield
        finally:
            logging.setLogRecordFactory(old_factory)


class PerformanceLogger:
    """Logger for performance metrics and monitoring."""
    
    def __init__(self):
        self.logger = logging.getLogger('memory_management.performance')
    
    def log_operation_time(self, operation: str, duration: float, **context):
        """Log operation timing information."""
        self.logger.info(
            f"Operation completed: {operation}",
            extra={
                'operation': operation,
                'duration_ms': round(duration * 1000, 2),
                'performance_metric': True,
                **context
            }
        )
    
    def log_database_query(self, database: str, query_type: str, duration: float, **context):
        """Log database query performance."""
        self.logger.info(
            f"Database query: {database} {query_type}",
            extra={
                'database': database,
                'query_type': query_type,
                'duration_ms': round(duration * 1000, 2),
                'database_metric': True,
                **context
            }
        )
    
    def log_llm_request(self, model: str, tokens_used: Optional[int], duration: float, **context):
        """Log LLM request performance."""
        self.logger.info(
            f"LLM request: {model}",
            extra={
                'model': model,
                'tokens_used': tokens_used,
                'duration_ms': round(duration * 1000, 2),
                'llm_metric': True,
                **context
            }
        )


class AuditLogger:
    """Logger for audit trail and compliance tracking."""
    
    def __init__(self):
        self.logger = logging.getLogger('memory_management.audit')
    
    def log_stm_operation(self, operation: str, scenario_id: str, user_id: Optional[str] = None, **context):
        """Log STM operations for audit trail."""
        self.logger.info(
            f"STM {operation}: {scenario_id}",
            extra={
                'audit_type': 'stm_operation',
                'operation': operation,
                'scenario_id': scenario_id,
                'user_id': user_id,
                **context
            }
        )
    
    def log_ltm_operation(self, operation: str, rule_id: str, user_id: Optional[str] = None, **context):
        """Log LTM operations for audit trail."""
        self.logger.info(
            f"LTM {operation}: {rule_id}",
            extra={
                'audit_type': 'ltm_operation',
                'operation': operation,
                'rule_id': rule_id,
                'user_id': user_id,
                **context
            }
        )
    
    def log_data_access(self, resource_type: str, resource_id: str, access_type: str, 
                       user_id: Optional[str] = None, **context):
        """Log data access for compliance tracking."""
        self.logger.info(
            f"Data access: {access_type} {resource_type} {resource_id}",
            extra={
                'audit_type': 'data_access',
                'resource_type': resource_type,
                'resource_id': resource_id,
                'access_type': access_type,
                'user_id': user_id,
                **context
            }
        )
    
    def log_configuration_change(self, component: str, change_type: str, 
                               user_id: Optional[str] = None, **context):
        """Log configuration changes."""
        self.logger.warning(
            f"Configuration change: {component} {change_type}",
            extra={
                'audit_type': 'configuration_change',
                'component': component,
                'change_type': change_type,
                'user_id': user_id,
                **context
            }
        )


class ErrorLogger:
    """Specialized logger for error tracking and alerting."""
    
    def __init__(self):
        self.logger = logging.getLogger('memory_management.errors')
    
    def log_database_error(self, database: str, operation: str, error: Exception, **context):
        """Log database errors with context."""
        self.logger.error(
            f"Database error in {database}: {operation}",
            extra={
                'error_type': 'database_error',
                'database': database,
                'operation': operation,
                'error_class': error.__class__.__name__,
                'error_message': str(error),
                **context
            },
            exc_info=True
        )
    
    def log_llm_error(self, model: str, operation: str, error: Exception, **context):
        """Log LLM service errors."""
        self.logger.error(
            f"LLM error with {model}: {operation}",
            extra={
                'error_type': 'llm_error',
                'model': model,
                'operation': operation,
                'error_class': error.__class__.__name__,
                'error_message': str(error),
                **context
            },
            exc_info=True
        )
    
    def log_validation_error(self, component: str, validation_type: str, error: Exception, **context):
        """Log data validation errors."""
        self.logger.error(
            f"Validation error in {component}: {validation_type}",
            extra={
                'error_type': 'validation_error',
                'component': component,
                'validation_type': validation_type,
                'error_class': error.__class__.__name__,
                'error_message': str(error),
                **context
            },
            exc_info=True
        )
    
    def log_api_error(self, endpoint: str, method: str, status_code: int, error: Exception, **context):
        """Log API errors."""
        self.logger.error(
            f"API error: {method} {endpoint} -> {status_code}",
            extra={
                'error_type': 'api_error',
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'error_class': error.__class__.__name__,
                'error_message': str(error),
                **context
            },
            exc_info=True
        )


# Global logger instances
_memory_logger = None
_performance_logger = None
_audit_logger = None
_error_logger = None


def setup_logging(config: Optional[LoggingConfig] = None) -> MemoryManagementLogger:
    """Set up the logging system and return the main logger."""
    global _memory_logger
    _memory_logger = MemoryManagementLogger(config)
    return _memory_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    if _memory_logger is None:
        setup_logging()
    return _memory_logger.get_logger(name)


def get_performance_logger() -> PerformanceLogger:
    """Get the performance logger instance."""
    global _performance_logger
    if _performance_logger is None:
        _performance_logger = PerformanceLogger()
    return _performance_logger


def get_audit_logger() -> AuditLogger:
    """Get the audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def get_error_logger() -> ErrorLogger:
    """Get the error logger instance."""
    global _error_logger
    if _error_logger is None:
        _error_logger = ErrorLogger()
    return _error_logger


@contextmanager
def log_context(**context):
    """Context manager for adding structured context to logs."""
    if _memory_logger is None:
        setup_logging()
    
    with _memory_logger.log_context(**context):
        yield


def log_startup_info():
    """Log system startup information."""
    logger = get_logger(__name__)
    settings = get_settings()
    
    logger.info("Memory Management Module starting up", extra={
        'environment': settings.environment,
        'debug': settings.debug,
        'redis_host': settings.redis.host,
        'neo4j_uri': settings.neo4j.uri,
        'ollama_url': settings.ollama.base_url,
        'api_port': settings.api.port
    })


def log_shutdown_info():
    """Log system shutdown information."""
    logger = get_logger(__name__)
    logger.info("Memory Management Module shutting down")