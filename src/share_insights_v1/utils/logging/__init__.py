"""
Logging utilities for Stock Analysis Framework
"""
from .logger import setup_logger, log_with_context, UTCFormatter, JSONFormatter
from .request_context import (
    generate_request_id,
    generate_session_id,
    set_request_id,
    get_request_id,
    set_session_id,
    get_session_id,
    clear_context
)
from .ui_logger import (
    get_or_create_session_id,
    log_page_view,
    log_user_action,
    log_batch_analysis_start,
    log_batch_analysis_complete,
    log_api_call,
    log_api_response,
    log_error
)
from .api_middleware import LoggingMiddleware

__all__ = [
    # Core logging
    'setup_logger',
    'log_with_context',
    'UTCFormatter',
    'JSONFormatter',
    # Request context
    'generate_request_id',
    'generate_session_id',
    'set_request_id',
    'get_request_id',
    'set_session_id',
    'get_session_id',
    'clear_context',
    # UI logging
    'get_or_create_session_id',
    'log_page_view',
    'log_user_action',
    'log_batch_analysis_start',
    'log_batch_analysis_complete',
    'log_api_call',
    'log_api_response',
    'log_error',
    # API middleware
    'LoggingMiddleware'
]
