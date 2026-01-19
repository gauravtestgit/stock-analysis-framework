"""
FastAPI middleware for request/response logging
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
from typing import Callable
import os

from src.share_insights_v1.utils.logging.logger import setup_logger, log_with_context
from src.share_insights_v1.utils.logging.request_context import (
    generate_request_id, set_request_id, get_request_id, clear_context
)

# Initialize API logger with dedicated file
api_logger = setup_logger(
    name='api',
    component='API',
    log_file='logs/api.log'  # Always use api.log for API logs
)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests and responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if request ID was provided by client (e.g., from UI)
        request_id = request.headers.get('X-Request-ID')
        
        if not request_id:
            # Generate new request ID if not provided
            request_id = generate_request_id()
        
        set_request_id(request_id)
        
        # Extract request details
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        
        # Log request
        log_with_context(
            api_logger,
            'info',
            f"Request received: {method} {path}",
            request_id=request_id,
            metadata={
                'method': method,
                'path': path,
                'query_params': query_params,
                'client_host': request.client.host if request.client else None
            }
        )
        
        # Process request and measure time
        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log response
            log_with_context(
                api_logger,
                'info',
                f"Request completed: {method} {path} - {response.status_code}",
                request_id=request_id,
                metadata={
                    'method': method,
                    'path': path,
                    'status_code': response.status_code,
                    'duration_seconds': round(duration, 3)
                }
            )
            
            # Add request ID to response headers
            response.headers['X-Request-ID'] = request_id
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Log error
            log_with_context(
                api_logger,
                'error',
                f"Request failed: {method} {path}",
                request_id=request_id,
                metadata={
                    'method': method,
                    'path': path,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'duration_seconds': round(duration, 3)
                }
            )
            raise
        finally:
            # Clear context
            clear_context()
