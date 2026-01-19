# Logging Utilities

Centralized logging infrastructure for the Stock Analysis Framework with UTC timestamps, request tracing, and structured logging support.

## Structure

```
utils/logging/
├── __init__.py           # Package exports
├── logger.py             # Core logging configuration
├── request_context.py    # Request/session tracking
├── ui_logger.py          # Streamlit UI logging
└── api_middleware.py     # FastAPI middleware
```

## Quick Start

### UI Logging (Streamlit)
```python
from src.share_insights_v1.utils.logging import (
    log_page_view,
    log_user_action,
    log_batch_analysis_start,
    log_batch_analysis_complete,
    log_api_call,
    log_api_response,
    log_error
)

# Log page view
log_page_view('thesis_generation')

# Log user action
log_user_action('ANALYZE_CLICKED', 'thesis_generation', metadata={'ticker': 'AAPL'})

# Log batch analysis
log_batch_analysis_start(['AAPL', 'MSFT'], ['fundamental', 'technical'])
log_batch_analysis_complete(2, 2, 0, 45.3)
```

### API Logging (FastAPI)
```python
from src.share_insights_v1.utils.logging import LoggingMiddleware

app = FastAPI()
app.add_middleware(LoggingMiddleware)
```

### Custom Logger
```python
from src.share_insights_v1.utils.logging import setup_logger, log_with_context

logger = setup_logger('my_component', 'COMPONENT')
log_with_context(logger, 'info', 'Processing data', metadata={'count': 100})
```

## Features

- **UTC Timestamps**: All logs use ISO 8601 format (YYYY-MM-DDTHH:MM:SS.fffZ)
- **Request Tracing**: Unique request IDs propagate through all layers
- **Session Tracking**: Streamlit session IDs for user journey tracking
- **Structured Logging**: JSON format support for log aggregation
- **Rotating Files**: 50MB max size, 14 backup files
- **Environment Config**: LOG_LEVEL, LOG_FORMAT, LOG_FILE_PATH

## Environment Variables

```bash
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=text                   # text or json
LOG_FILE_PATH=logs/app.log        # Log file location
LOG_MAX_SIZE=52428800             # 50MB in bytes
LOG_BACKUP_COUNT=14               # Number of backup files
```

## Log Locations

- **Local Development**: `logs/` directory
- **EC2 Production**: `/var/log/share-insights/`
- **AWS CloudWatch**: `/aws/ec2/share-insights/` log groups

## Integration Guide

See [LOGGING_INTEGRATION_GUIDE.md](../../../LOGGING_INTEGRATION_GUIDE.md) for step-by-step integration instructions.
