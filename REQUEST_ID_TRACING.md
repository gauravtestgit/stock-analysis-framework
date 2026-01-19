# Request ID Tracing for Batch Analysis

## Overview

Each stock analysis in a batch now gets a unique request ID that propagates through all layers (UI → API → Orchestrator → Analyzers), enabling complete end-to-end tracing.

## Request ID Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    BATCH ANALYSIS WORKFLOW                       │
└─────────────────────────────────────────────────────────────────┘

User clicks "Analyze All Watchlist Stocks"
         ↓
    Session ID: sess_abc123def456
         ↓
┌────────────────────────────────────────────────────────────────┐
│  UI: analyze_watchlist_batch()                                  │
│  - Logs batch start with session ID                            │
│  - Creates ThreadPoolExecutor with 4 workers                   │
└────────────────────────────────────────────────────────────────┘
         ↓
    Parallel execution for each ticker
         ↓
┌────────────────────────────────────────────────────────────────┐
│  UI: analyze_single_stock_api(ticker="AAPL")                   │
│  1. Generate unique request ID: req_xyz789abc123               │
│  2. Set in context: set_request_id(request_id)                 │
│  3. Log API call with request_id in metadata                   │
│  4. Send HTTP request with X-Request-ID header                 │
└────────────────────────────────────────────────────────────────┘
         ↓
    HTTP POST to http://localhost:8000/analyze/AAPL
    Headers: {'X-Request-ID': 'req_xyz789abc123'}
         ↓
┌────────────────────────────────────────────────────────────────┐
│  API: LoggingMiddleware                                         │
│  1. Extract X-Request-ID from headers                          │
│  2. Set in context: set_request_id(request_id)                 │
│  3. Log request received with request_id                       │
│  4. Pass to endpoint handler                                   │
└────────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────────┐
│  API: /analyze/{ticker} endpoint                                │
│  - Request ID available via get_request_id()                   │
│  - Calls AnalysisOrchestrator with request context            │
└────────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────────┐
│  Orchestrator: AnalysisOrchestrator                            │
│  - Request ID available in context                             │
│  - Calls individual analyzers                                  │
│  - Each analyzer can log with request_id                       │
└────────────────────────────────────────────────────────────────┘
         ↓
    Response with batch_analysis_id
         ↓
┌────────────────────────────────────────────────────────────────┐
│  API: LoggingMiddleware                                         │
│  1. Log response with request_id                               │
│  2. Add X-Request-ID to response headers                       │
│  3. Clear context                                              │
└────────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────────┐
│  UI: analyze_single_stock_api()                                │
│  1. Receive response                                           │
│  2. Log API response with request_id                           │
│  3. Return (ticker, data) to batch processor                   │
└────────────────────────────────────────────────────────────────┘
         ↓
    All tickers complete
         ↓
┌────────────────────────────────────────────────────────────────┐
│  UI: analyze_watchlist_batch()                                 │
│  - Log batch complete with statistics                          │
│  - Display results                                             │
└────────────────────────────────────────────────────────────────┘
```

## Request ID Format

- **UI Request ID**: `req_xyz789abc123` (12 hex characters)
- **Session ID**: `sess_abc123def456` (12 hex characters)
- **Generated by**: `generate_request_id()` function

## Example Log Trace

### Batch Analysis for 3 Stocks (AAPL, MSFT, GOOGL)

```
[2024-12-20T10:30:15.123Z] [INFO] [UI] [dashboard] - User action: BATCH_ANALYSIS_CLICKED
  session_id: sess_abc123def456
  metadata: {stock_count: 3, analyzers: ['dcf', 'technical'], llm_provider: 'openai', llm_model: 'gpt-4'}

[2024-12-20T10:30:15.234Z] [INFO] [UI] [dashboard] - Batch analysis started
  session_id: sess_abc123def456
  metadata: {stock_count: 3, tickers: 'AAPL,MSFT,GOOGL', analyzers: 'dcf,technical', max_workers: 3}

# AAPL Analysis (Worker 1)
[2024-12-20T10:30:15.345Z] [INFO] [UI] [dashboard] - API call: POST /analyze/AAPL
  session_id: sess_abc123def456
  request_id: req_aaa111bbb222
  metadata: {ticker: 'AAPL', analyzers: ['dcf', 'technical']}

[2024-12-20T10:30:15.456Z] [INFO] [API] [api] - Request received: POST /analyze/AAPL
  request_id: req_aaa111bbb222
  metadata: {method: 'POST', path: '/analyze/AAPL', client_host: '127.0.0.1'}

[2024-12-20T10:30:18.567Z] [INFO] [API] [api] - Request completed: POST /analyze/AAPL - 200
  request_id: req_aaa111bbb222
  metadata: {status_code: 200, duration_seconds: 3.111}

[2024-12-20T10:30:18.678Z] [INFO] [UI] [dashboard] - API response: /analyze/AAPL - 200
  session_id: sess_abc123def456
  request_id: req_aaa111bbb222
  metadata: {ticker: 'AAPL', status_code: 200, duration_seconds: 3.222, success: true}

# MSFT Analysis (Worker 2)
[2024-12-20T10:30:15.789Z] [INFO] [UI] [dashboard] - API call: POST /analyze/MSFT
  session_id: sess_abc123def456
  request_id: req_bbb222ccc333
  metadata: {ticker: 'MSFT', analyzers: ['dcf', 'technical']}

[2024-12-20T10:30:15.890Z] [INFO] [API] [api] - Request received: POST /analyze/MSFT
  request_id: req_bbb222ccc333
  metadata: {method: 'POST', path: '/analyze/MSFT', client_host: '127.0.0.1'}

[2024-12-20T10:30:19.123Z] [INFO] [API] [api] - Request completed: POST /analyze/MSFT - 200
  request_id: req_bbb222ccc333
  metadata: {status_code: 200, duration_seconds: 3.233}

[2024-12-20T10:30:19.234Z] [INFO] [UI] [dashboard] - API response: /analyze/MSFT - 200
  session_id: sess_abc123def456
  request_id: req_bbb222ccc333
  metadata: {ticker: 'MSFT', status_code: 200, duration_seconds: 3.344, success: true}

# GOOGL Analysis (Worker 3)
[2024-12-20T10:30:16.012Z] [INFO] [UI] [dashboard] - API call: POST /analyze/GOOGL
  session_id: sess_abc123def456
  request_id: req_ccc333ddd444
  metadata: {ticker: 'GOOGL', analyzers: ['dcf', 'technical']}

[2024-12-20T10:30:16.123Z] [INFO] [API] [api] - Request received: POST /analyze/GOOGL
  request_id: req_ccc333ddd444
  metadata: {method: 'POST', path: '/analyze/GOOGL', client_host: '127.0.0.1'}

[2024-12-20T10:30:19.456Z] [INFO] [API] [api] - Request completed: POST /analyze/GOOGL - 200
  request_id: req_ccc333ddd444
  metadata: {status_code: 200, duration_seconds: 3.333}

[2024-12-20T10:30:19.567Z] [INFO] [UI] [dashboard] - API response: /analyze/GOOGL - 200
  session_id: sess_abc123def456
  request_id: req_ccc333ddd444
  metadata: {ticker: 'GOOGL', status_code: 200, duration_seconds: 3.444, success: true}

# Batch Complete
[2024-12-20T10:30:19.678Z] [INFO] [UI] [dashboard] - Batch analysis completed
  session_id: sess_abc123def456
  metadata: {stock_count: 3, success_count: 3, failed_count: 0, duration_seconds: 4.44, success_rate: 100.0}
```

## Tracing a Specific Stock Analysis

To trace a specific stock analysis through all layers:

### 1. Find the Request ID
```bash
# Search logs for the ticker
grep "AAPL" logs/ui.log | grep "API call"
```

Output:
```
[2024-12-20T10:30:15.345Z] [INFO] [UI] [dashboard] - API call: POST /analyze/AAPL
  request_id: req_aaa111bbb222
```

### 2. Trace All Logs for That Request ID
```bash
# Search all logs for the request ID
grep "req_aaa111bbb222" logs/*.log
```

Output shows complete flow:
```
logs/ui.log:[2024-12-20T10:30:15.345Z] [INFO] [UI] - API call: POST /analyze/AAPL
logs/ui.log:[2024-12-20T10:30:18.678Z] [INFO] [UI] - API response: /analyze/AAPL - 200
logs/api.log:[2024-12-20T10:30:15.456Z] [INFO] [API] - Request received: POST /analyze/AAPL
logs/api.log:[2024-12-20T10:30:18.567Z] [INFO] [API] - Request completed: POST /analyze/AAPL - 200
```

## Benefits

1. **End-to-End Tracing**: Follow a single stock analysis from UI click to database storage
2. **Parallel Debugging**: Distinguish between concurrent analyses in batch processing
3. **Performance Analysis**: Measure exact timing for each stock across all layers
4. **Error Isolation**: Quickly identify which specific stock failed and where
5. **Audit Trail**: Complete history of each analysis request

## Code Changes Summary

### UI Layer (thesis_generation_full.py)
- Generate unique request ID per ticker: `request_id = generate_request_id()`
- Set in context: `set_request_id(request_id)`
- Send in HTTP headers: `headers = {'X-Request-ID': request_id}`
- Include in all log metadata: `metadata={'request_id': request_id}`

### API Layer (api_middleware.py)
- Extract from headers: `request_id = request.headers.get('X-Request-ID')`
- Use client ID if provided, generate if not
- Set in context for downstream use
- Return in response headers: `response.headers['X-Request-ID'] = request_id`

### Context Management (request_context.py)
- Thread-safe storage using `contextvars`
- Accessible via `get_request_id()` anywhere in the call stack
- Automatically cleared after request completion

## Testing

### Test Batch Analysis with Logging
```python
# Run batch analysis with 3 stocks
watchlist = ['AAPL', 'MSFT', 'GOOGL']

# Check logs show unique request IDs
tail -f logs/ui.log | grep "request_id"
```

### Verify Request ID Propagation
```python
# Check API received the same request ID
grep "req_aaa111bbb222" logs/api.log
```

### Trace Complete Flow
```bash
# Get all logs for a specific request
grep "req_aaa111bbb222" logs/*.log | sort
```

This ensures complete traceability of each stock analysis through the entire system! 🎯
