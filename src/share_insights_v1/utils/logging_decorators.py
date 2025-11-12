"""
Logging decorators for automatic instrumentation
"""
import time
import functools
from typing import Callable, Any
from .logger import get_logger, log_analysis_start, log_analysis_complete, log_analysis_error

def log_analysis(analysis_type: str):
    """Decorator to automatically log analysis operations"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Extract ticker from arguments
            ticker = None
            if args and hasattr(args[0], '__class__'):
                # Method call - ticker might be in kwargs or args[1]
                ticker = kwargs.get('ticker') or (args[1] if len(args) > 1 else None)
            else:
                # Function call - ticker might be first arg
                ticker = args[0] if args else kwargs.get('ticker')
            
            user_id = kwargs.get('user_id')
            
            # Log start
            if ticker:
                log_analysis_start(ticker, analysis_type, user_id)
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log completion
                if ticker:
                    log_analysis_complete(ticker, analysis_type, execution_time, user_id)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                # Log error
                if ticker:
                    log_analysis_error(ticker, analysis_type, str(e), user_id)
                
                raise
        
        return wrapper
    return decorator

def log_api_endpoint(endpoint_name: str):
    """Decorator to log API endpoint calls"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            from .logger import log_api_request
            
            # Extract request info
            method = "POST"  # Default for most analysis endpoints
            user_id = kwargs.get('user_id')
            
            log_api_request(endpoint_name, method, user_id)
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger = get_logger()
                logger.info(
                    f"API {endpoint_name} completed in {execution_time:.2f}s",
                    endpoint=endpoint_name,
                    execution_time=execution_time,
                    user_id=user_id,
                    event_type="api_complete"
                )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                logger = get_logger()
                logger.error(
                    f"API {endpoint_name} failed after {execution_time:.2f}s: {str(e)}",
                    endpoint=endpoint_name,
                    execution_time=execution_time,
                    error_message=str(e),
                    user_id=user_id,
                    event_type="api_error"
                )
                
                raise
        
        return wrapper
    return decorator

def log_batch_operation(operation_name: str):
    """Decorator to log batch operations"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            from .logger import log_batch_job
            
            job_id = kwargs.get('job_id', 'unknown')
            user_id = kwargs.get('user_id')
            
            log_batch_job(job_id, "started", user_id=user_id)
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Extract stock count from result if available
                stock_count = None
                if isinstance(result, dict):
                    stock_count = result.get('processed_count')
                elif isinstance(result, list):
                    stock_count = len(result)
                
                log_batch_job(job_id, "completed", stock_count, user_id)
                
                logger = get_logger()
                logger.info(
                    f"Batch operation {operation_name} completed in {execution_time:.2f}s",
                    operation=operation_name,
                    job_id=job_id,
                    execution_time=execution_time,
                    stock_count=stock_count,
                    user_id=user_id,
                    event_type="batch_complete"
                )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                log_batch_job(job_id, "failed", user_id=user_id)
                
                logger = get_logger()
                logger.error(
                    f"Batch operation {operation_name} failed after {execution_time:.2f}s: {str(e)}",
                    operation=operation_name,
                    job_id=job_id,
                    execution_time=execution_time,
                    error_message=str(e),
                    user_id=user_id,
                    event_type="batch_error"
                )
                
                raise
        
        return wrapper
    return decorator