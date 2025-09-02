import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from contextvars import ContextVar

import orjson
from pythonjsonlogger import jsonlogger

# Context variable to store correlation ID for the current request
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

class OrjsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter using orjson for better performance."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON using orjson."""
        # Get correlation ID from context
        current_correlation_id = correlation_id.get()
        
        # Prepare log data
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'correlation_id': current_correlation_id,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # Use orjson for serialization
        return orjson.dumps(log_data, option=orjson.OPT_INDENT_2).decode('utf-8')

class StructuredLogger:
    """Structured logger that provides consistent logging interface."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log_with_extra(self, level: int, message: str, **kwargs):
        """Log with extra fields."""
        extra_fields = {k: v for k, v in kwargs.items() if v is not None}
        if extra_fields:
            self.logger.log(level, message, extra={'extra_fields': extra_fields})
        else:
            self.logger.log(level, message)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with extra fields."""
        self._log_with_extra(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with extra fields."""
        self._log_with_extra(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with extra fields."""
        self._log_with_extra(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with extra fields."""
        self._log_with_extra(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with extra fields."""
        self._log_with_extra(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, exc_info: bool = True, **kwargs):
        """Log exception with traceback."""
        extra_fields = {k: v for k, v in kwargs.items() if v is not None}
        if extra_fields:
            self.logger.exception(message, extra={'extra_fields': extra_fields})
        else:
            self.logger.exception(message)

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True
) -> None:
    """Setup logging with structured JSON format.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        enable_console: Whether to enable console logging
    """
    # Parse log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatter
    formatter = OrjsonFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set aiogram logging level
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    # Log successful setup
    logger = StructuredLogger(__name__)
    logger.info("Logging configured successfully", 
                log_level=log_level, 
                log_file=log_file,
                enable_console=enable_console)

def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)

def set_correlation_id(corr_id: str) -> None:
    """Set correlation ID for the current context.
    
    Args:
        corr_id: Correlation ID string
    """
    correlation_id.set(corr_id)

def get_correlation_id() -> Optional[str]:
    """Get current correlation ID.
    
    Returns:
        Current correlation ID or None
    """
    return correlation_id.get()

def generate_correlation_id() -> str:
    """Generate a new correlation ID.
    
    Returns:
        New correlation ID string
    """
    return str(uuid.uuid4())
