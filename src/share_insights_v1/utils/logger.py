"""
Centralized logging configuration for Stock Analysis Framework
Supports local files, AWS CloudWatch, and structured logging
"""
import logging
import logging.handlers
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'ticker'):
            log_entry['ticker'] = record.ticker
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'analysis_type'):
            log_entry['analysis_type'] = record.analysis_type
        if hasattr(record, 'execution_time'):
            log_entry['execution_time'] = record.execution_time
        if hasattr(record, 'error_code'):
            log_entry['error_code'] = record.error_code
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)

class CloudWatchHandler(logging.Handler):
    """Custom handler for AWS CloudWatch Logs"""
    
    def __init__(self, log_group: str, log_stream: str, region: str = 'us-east-1'):
        super().__init__()
        self.log_group = log_group
        self.log_stream = log_stream
        self.region = region
        self.client = None
        self.sequence_token = None
        
        try:
            self.client = boto3.client('logs', region_name=region)
            self._ensure_log_group_exists()
            self._ensure_log_stream_exists()
        except (ClientError, NoCredentialsError) as e:
            print(f"CloudWatch logging disabled: {e}")
            self.client = None
    
    def _ensure_log_group_exists(self):
        """Create log group if it doesn't exist"""
        try:
            self.client.create_log_group(logGroupName=self.log_group)
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                raise
    
    def _ensure_log_stream_exists(self):
        """Create log stream if it doesn't exist"""
        try:
            self.client.create_log_stream(
                logGroupName=self.log_group,
                logStreamName=self.log_stream
            )
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                raise
    
    def emit(self, record):
        """Send log record to CloudWatch"""
        if not self.client:
            return
            
        try:
            log_event = {
                'timestamp': int(record.created * 1000),
                'message': self.format(record)
            }
            
            kwargs = {
                'logGroupName': self.log_group,
                'logStreamName': self.log_stream,
                'logEvents': [log_event]
            }
            
            if self.sequence_token:
                kwargs['sequenceToken'] = self.sequence_token
                
            response = self.client.put_log_events(**kwargs)
            self.sequence_token = response.get('nextSequenceToken')
            
        except Exception as e:
            print(f"Failed to send log to CloudWatch: {e}")

class StockAnalysisLogger:
    """Central logger for Stock Analysis Framework"""
    
    def __init__(self, 
                 name: str = "stock_analysis",
                 level: str = "INFO",
                 log_to_file: bool = True,
                 log_to_cloudwatch: bool = False,
                 cloudwatch_config: Optional[Dict] = None):
        
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler with structured format
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(console_handler)
        
        # File handler for local development
        if log_to_file:
            self._add_file_handler()
        
        # CloudWatch handler for production
        if log_to_cloudwatch and cloudwatch_config:
            self._add_cloudwatch_handler(cloudwatch_config)
    
    def _add_file_handler(self):
        """Add rotating file handler"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=f"{log_dir}/stock_analysis.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(file_handler)
    
    def _add_cloudwatch_handler(self, config: Dict):
        """Add CloudWatch handler"""
        cloudwatch_handler = CloudWatchHandler(
            log_group=config.get('log_group', '/aws/stock-analysis'),
            log_stream=config.get('log_stream', f"instance-{datetime.now().strftime('%Y%m%d-%H%M%S')}"),
            region=config.get('region', 'us-east-1')
        )
        cloudwatch_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(cloudwatch_handler)
    
    def info(self, message: str, **kwargs):
        """Log info message with extra context"""
        self.logger.info(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with extra context"""
        self.logger.error(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with extra context"""
        self.logger.warning(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with extra context"""
        self.logger.debug(message, extra=kwargs)

# Global logger instance
_logger_instance = None

def get_logger() -> StockAnalysisLogger:
    """Get or create global logger instance"""
    global _logger_instance
    if _logger_instance is None:
        # Configuration from environment
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        log_to_cloudwatch = os.getenv('LOG_TO_CLOUDWATCH', 'false').lower() == 'true'
        
        cloudwatch_config = None
        if log_to_cloudwatch:
            cloudwatch_config = {
                'log_group': os.getenv('CLOUDWATCH_LOG_GROUP', '/aws/stock-analysis'),
                'log_stream': os.getenv('CLOUDWATCH_LOG_STREAM', f"instance-{datetime.now().strftime('%Y%m%d-%H%M%S')}"),
                'region': os.getenv('AWS_REGION', 'us-east-1')
            }
        
        _logger_instance = StockAnalysisLogger(
            level=log_level,
            log_to_cloudwatch=log_to_cloudwatch,
            cloudwatch_config=cloudwatch_config
        )
    
    return _logger_instance

# Convenience functions
def log_analysis_start(ticker: str, analysis_type: str, user_id: str = None):
    """Log analysis start"""
    logger = get_logger()
    logger.info(
        f"Starting {analysis_type} analysis for {ticker}",
        ticker=ticker,
        analysis_type=analysis_type,
        user_id=user_id,
        event_type="analysis_start"
    )

def log_analysis_complete(ticker: str, analysis_type: str, execution_time: float, user_id: str = None):
    """Log analysis completion"""
    logger = get_logger()
    logger.info(
        f"Completed {analysis_type} analysis for {ticker} in {execution_time:.2f}s",
        ticker=ticker,
        analysis_type=analysis_type,
        execution_time=execution_time,
        user_id=user_id,
        event_type="analysis_complete"
    )

def log_analysis_error(ticker: str, analysis_type: str, error: str, user_id: str = None):
    """Log analysis error"""
    logger = get_logger()
    logger.error(
        f"Error in {analysis_type} analysis for {ticker}: {error}",
        ticker=ticker,
        analysis_type=analysis_type,
        error_message=error,
        user_id=user_id,
        event_type="analysis_error"
    )

def log_api_request(endpoint: str, method: str, user_id: str = None, params: Dict = None):
    """Log API request"""
    logger = get_logger()
    logger.info(
        f"{method} {endpoint}",
        endpoint=endpoint,
        method=method,
        user_id=user_id,
        params=params,
        event_type="api_request"
    )

def log_batch_job(job_id: str, status: str, stock_count: int = None, user_id: str = None):
    """Log batch job events"""
    logger = get_logger()
    logger.info(
        f"Batch job {job_id} status: {status}",
        job_id=job_id,
        status=status,
        stock_count=stock_count,
        user_id=user_id,
        event_type="batch_job"
    )