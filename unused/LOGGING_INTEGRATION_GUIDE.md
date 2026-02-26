# Logging Integration Guide for thesis_generation_full.py

## Import Statement (Add at top after existing imports)
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
```

## Logging Points to Add

### 1. Page Load (in show_thesis_generation function, after title)
```python
# After: st.markdown("*Generate comprehensive investment theses with full analysis capabilities*")
log_page_view('thesis_generation', metadata={'mode': 'initial_load'})
```

### 2. Batch Analysis Button Click (in show_thesis_generation, when button clicked)
```python
# After: if st.button("Analyze All Watchlist Stocks"):
log_user_action(
    action='BATCH_ANALYSIS_CLICKED',
    page='thesis_generation',
    metadata={
        'stock_count': len(watchlist),
        'analyzers': batch_analyzers,
        'llm_provider': selected_provider_name,
        'llm_model': selected_model
    }
)
```

### 3. Batch Analysis Start (in analyze_watchlist_batch function, before parallel execution)
```python
# After: batch_start = time.time()
log_batch_analysis_start(
    watchlist=watchlist,
    analyzers=selected_analyzers or [],
    metadata={
        'max_workers': max_workers,
        'llm_provider': llm_provider,
        'llm_model': llm_model,
        'max_news_articles': max_news_articles
    }
)
```

### 4. Individual API Call (in analyze_single_stock_api function, before requests.post)
```python
# Before: response = requests.post(endpoint, json=request_data)
log_api_call(
    endpoint=endpoint,
    method='POST',
    ticker=ticker,
    metadata={
        'analyzers': selected_analyzers,
        'llm_provider': llm_provider,
        'llm_model': llm_model
    }
)
```

### 5. API Response (in analyze_single_stock_api function, after response)
```python
# After: if response.status_code == 200:
log_api_response(
    endpoint=endpoint,
    status_code=response.status_code,
    duration=stock_end - stock_start,
    success=True,
    metadata={'ticker': ticker}
)
# Also add for error case:
# else:
log_api_response(
    endpoint=endpoint,
    status_code=response.status_code,
    duration=stock_end - stock_start,
    success=False,
    error=response.text,
    metadata={'ticker': ticker}
)
```

### 6. Batch Analysis Complete (in analyze_watchlist_batch function, after batch_end)
```python
# After: batch_end = time.time()
successful = len([r for r in results.values() if 'error' not in r])
failed = len(results) - successful

log_batch_analysis_complete(
    stock_count=len(watchlist),
    success_count=successful,
    failed_count=failed,
    duration=total_batch_time,
    metadata={
        'max_workers': max_workers,
        'avg_time_per_stock': total_batch_time / len(watchlist) if watchlist else 0
    }
)
```

### 7. Error Handling (in analyze_single_stock_api exception block)
```python
# In: except Exception as e:
log_error(
    error_type='API_CALL_EXCEPTION',
    error_message=str(e),
    page='thesis_generation',
    metadata={'ticker': ticker, 'endpoint': endpoint}
)
```

## Summary
These logging points will capture:
- Page views and navigation
- User actions (button clicks)
- Batch analysis lifecycle (start, progress, completion)
- Individual API calls and responses
- Errors and exceptions

All logs will include:
- UTC timestamps
- Session IDs (from Streamlit session)
- Request IDs (when available from API)
- Contextual metadata (tickers, analyzers, timing, etc.)
