"""
UI-specific logging utilities for Streamlit dashboard
"""
import streamlit as st
from typing import Any, Dict, List, Optional
import os

from .logger import setup_logger, log_with_context
from .request_context import (
    get_session_id, set_session_id, generate_session_id, get_request_id
)

# Initialize UI logger
log_file_path = os.getenv('LOG_FILE_PATH', 'logs/ui.log')
ui_logger = setup_logger(
    name='dashboard',
    component='UI',
    log_file=log_file_path
)

def get_or_create_session_id() -> str:
    """Get or create session ID from Streamlit session state"""
    if 'logging_session_id' not in st.session_state:
        st.session_state.logging_session_id = generate_session_id()
        ui_logger.info(f"New session created: {st.session_state.logging_session_id}")
    
    set_session_id(st.session_state.logging_session_id)
    return st.session_state.logging_session_id

def log_page_view(page_name: str, metadata: Optional[Dict[str, Any]] = None):
    """Log page view event"""
    session_id = get_or_create_session_id()
    log_with_context(
        ui_logger,
        'info',
        f"Page viewed: {page_name}",
        session_id=session_id,
        metadata=metadata or {}
    )

def log_user_action(
    action: str,
    page: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log user action (button click, form submission, etc.)
    
    Args:
        action: Action name (e.g., 'ANALYZE_CLICKED', 'THESIS_GENERATED')
        page: Page name where action occurred
        metadata: Additional context (ticker, analyzers, etc.)
    """
    session_id = get_or_create_session_id()
    request_id = get_request_id()
    
    log_with_context(
        ui_logger,
        'info',
        f"User action: {action}",
        request_id=request_id,
        session_id=session_id,
        metadata={
            'page': page,
            'action': action,
            **(metadata or {})
        }
    )

def log_batch_analysis_start(
    watchlist: List[str],
    analyzers: List[str],
    metadata: Optional[Dict[str, Any]] = None
):
    """Log batch analysis start"""
    session_id = get_or_create_session_id()
    
    log_with_context(
        ui_logger,
        'info',
        f"Batch analysis started",
        session_id=session_id,
        metadata={
            'stock_count': len(watchlist),
            'tickers': ','.join(watchlist[:5]) + ('...' if len(watchlist) > 5 else ''),
            'analyzers': ','.join(analyzers),
            'analyzer_count': len(analyzers),
            **(metadata or {})
        }
    )

def log_batch_analysis_complete(
    stock_count: int,
    success_count: int,
    failed_count: int,
    duration: float,
    metadata: Optional[Dict[str, Any]] = None
):
    """Log batch analysis completion"""
    session_id = get_or_create_session_id()
    
    log_with_context(
        ui_logger,
        'info',
        f"Batch analysis completed",
        session_id=session_id,
        metadata={
            'stock_count': stock_count,
            'success_count': success_count,
            'failed_count': failed_count,
            'duration_seconds': round(duration, 2),
            'success_rate': round((success_count / stock_count * 100) if stock_count > 0 else 0, 1),
            **(metadata or {})
        }
    )

def log_api_call(
    endpoint: str,
    method: str,
    ticker: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Log API call from UI"""
    session_id = get_or_create_session_id()
    request_id = get_request_id()
    
    log_with_context(
        ui_logger,
        'info',
        f"API call: {method} {endpoint}",
        request_id=request_id,
        session_id=session_id,
        metadata={
            'endpoint': endpoint,
            'method': method,
            'ticker': ticker,
            **(metadata or {})
        }
    )

def log_api_response(
    endpoint: str,
    status_code: int,
    duration: float,
    success: bool,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Log API response"""
    session_id = get_or_create_session_id()
    request_id = get_request_id()
    
    level = 'info' if success else 'error'
    
    log_with_context(
        ui_logger,
        level,
        f"API response: {endpoint} - {status_code}",
        request_id=request_id,
        session_id=session_id,
        metadata={
            'endpoint': endpoint,
            'status_code': status_code,
            'duration_seconds': round(duration, 2),
            'success': success,
            'error': error,
            **(metadata or {})
        }
    )

def log_error(
    error_type: str,
    error_message: str,
    page: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """Log UI error"""
    session_id = get_or_create_session_id()
    request_id = get_request_id()
    
    log_with_context(
        ui_logger,
        'error',
        f"UI error: {error_type}",
        request_id=request_id,
        session_id=session_id,
        metadata={
            'error_type': error_type,
            'error_message': error_message,
            'page': page,
            **(metadata or {})
        }
    )
