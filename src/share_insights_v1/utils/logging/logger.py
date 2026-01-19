"""
Central logging configuration with UTC timestamps and structured logging
"""
import logging
import logging.handlers
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import os

class UTCFormatter(logging.Formatter):
    """Custom formatter that uses UTC timestamps"""
    
    def formatTime(self, record, datefmt=None):
        """Override to use UTC time"""
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat(timespec='milliseconds')
    
    def format(self, record):
        """Format log record with optional context fields"""
        # Format base message
        result = super().format(record)
        
        # Add optional context fields on new lines
        if hasattr(record, 'session_id') and record.session_id:
            result += f"\n  session_id: {record.session_id}"
        if hasattr(record, 'request_id') and record.request_id:
            result += f"\n  request_id: {record.request_id}"
        if hasattr(record, 'metadata') and record.metadata:
            result += f"\n  metadata: {record.metadata}"
        
        return result

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec='milliseconds'),
            'level': record.levelname,
            'component': getattr(record, 'component', 'UNKNOWN'),
            'message': record.getMessage(),
        }
        
        # Add optional fields
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'session_id'):
            log_data['session_id'] = record.session_id
        if hasattr(record, 'metadata'):
            log_data['metadata'] = record.metadata
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)

def setup_logger(
    name: str,
    component: str,
    log_level: str = None,
    log_format: str = None,
    log_file: str = None
) -> logging.Logger:
    """
    Setup logger with UTC timestamps and optional JSON formatting
    
    Args:
        name: Logger name
        component: Component identifier (UI, API, LLM, etc.)
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'text')
        log_file: Optional log file path
        
    Returns:
        Configured logger instance
    """
    # Get configuration from environment or use defaults
    log_level = log_level or os.getenv('LOG_LEVEL', 'INFO')
    log_format = log_format or os.getenv('LOG_FORMAT', 'text')
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatter
    if log_format.lower() == 'json':
        formatter = JSONFormatter()
    else:
        formatter = UTCFormatter(
            fmt='[%(asctime)s] [%(levelname)s] [%(component)s] [%(name)s] - %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S.%fZ'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified or from env)
    log_file = log_file or os.getenv('LOG_FILE_PATH')
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=int(os.getenv('LOG_MAX_SIZE', '52428800')),  # 50MB default
            backupCount=int(os.getenv('LOG_BACKUP_COUNT', '14'))
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Add component to all log records
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.component = component
        return record
    
    logging.setLogRecordFactory(record_factory)
    
    return logger

def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log message with additional context
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        request_id: Optional request ID
        session_id: Optional session ID
        metadata: Optional metadata dictionary
    """
    extra = {}
    if request_id:
        extra['request_id'] = request_id
    if session_id:
        extra['session_id'] = session_id
    if metadata:
        extra['metadata'] = metadata
    
    log_func = getattr(logger, level.lower())
    log_func(message, extra=extra)
