# Testing the Logging Infrastructure

## Quick Start

### Option 1: Run the Logging Test Script (Recommended)
```bash
cd c:\Users\x_gau\source\repos\agentic\langchain\tutorials\finance-app
python src\share_insights_v1\tests\test_logging.py
```

This will:
- ✅ Test basic logging functionality
- ✅ Test request ID generation
- ✅ Test API logging (if API is running)
- ✅ Simulate batch analysis logging
- ✅ Test error logging
- ✅ Verify log files were created
- ✅ Show sample log entries

### Option 2: Test with Real Dashboard

#### Step 1: Start the API
```bash
python run_api.py
```

#### Step 2: Start the Dashboard
```bash
python run_dashboard.py
```

#### Step 3: Perform Batch Analysis
1. Navigate to "Investment Thesis Generator" page
2. Add stocks to watchlist (e.g., AAPL, MSFT, GOOGL)
3. Click "Analyze All Watchlist Stocks"
4. Wait for analysis to complete

#### Step 4: Check Logs
```bash
# View UI logs
type logs\ui.log

# View API logs
type logs\api.log

# Search for request IDs
findstr "req_" logs\*.log

# Search for specific ticker
findstr "AAPL" logs\ui.log
```

## What to Look For

### 1. Log File Creation
Check that these files exist:
```
logs/
├── ui.log      # UI/Dashboard logs
├── api.log     # API logs
└── test.log    # Test script logs
```

### 2. Log Format
Each log entry should have:
```
[2024-12-20T10:30:15.123Z] [INFO] [UI] [dashboard] - Message
  session_id: sess_abc123def456
  request_id: req_xyz789abc123
  metadata: {key: value}
```

### 3. Request ID Tracing
For batch analysis, you should see:
```
# Batch start
[10:30:15] Batch analysis started
  session_id: sess_abc123

# Individual stock analyses with unique request IDs
[10:30:15] API call: POST /analyze/AAPL
  request_id: req_aaa111
  
[10:30:15] API call: POST /analyze/MSFT
  request_id: req_bbb222
  
[10:30:16] API call: POST /analyze/GOOGL
  request_id: req_ccc333

# Responses with matching request IDs
[10:30:18] API response: /analyze/AAPL - 200
  request_id: req_aaa111
  
[10:30:19] API response: /analyze/MSFT - 200
  request_id: req_bbb222
  
[10:30:19] API response: /analyze/GOOGL - 200
  request_id: req_ccc333

# Batch complete
[10:30:19] Batch analysis completed
  session_id: sess_abc123
```

### 4. API Logs
In `logs/api.log`, you should see matching request IDs:
```
[10:30:15] Request received: POST /analyze/AAPL
  request_id: req_aaa111
  
[10:30:18] Request completed: POST /analyze/AAPL - 200
  request_id: req_aaa111
```

## Validation Commands

### Check Log File Sizes
```bash
dir logs
```

### Count Log Entries
```bash
# Count total log lines
find /c /v "" logs\ui.log

# Count request IDs
findstr /c:"request_id" logs\ui.log | find /c /v ""
```

### Trace Specific Request
```bash
# Find request ID for a ticker
findstr "AAPL" logs\ui.log | findstr "API call"

# Trace all logs for that request ID
findstr "req_aaa111bbb222" logs\*.log
```

### View Recent Logs
```bash
# Last 20 lines of UI log
powershell "Get-Content logs\ui.log -Tail 20"

# Last 20 lines of API log
powershell "Get-Content logs\api.log -Tail 20"
```

### Monitor Logs in Real-Time
```bash
# Watch UI logs (requires PowerShell)
powershell "Get-Content logs\ui.log -Wait -Tail 10"

# Watch API logs
powershell "Get-Content logs\api.log -Wait -Tail 10"
```

## Test Scenarios

### Scenario 1: Single Stock Analysis
1. Open dashboard
2. Enter ticker (e.g., AAPL)
3. Click "Analyze Stock"
4. Check logs for:
   - Page view log
   - API call log with request ID
   - API response log with same request ID

### Scenario 2: Batch Analysis (3 stocks)
1. Add AAPL, MSFT, GOOGL to watchlist
2. Click "Analyze All Watchlist Stocks"
3. Check logs for:
   - Batch start log
   - 3 unique request IDs (one per stock)
   - 3 API call logs
   - 3 API response logs
   - Batch complete log with statistics

### Scenario 3: Error Handling
1. Analyze invalid ticker (e.g., INVALID)
2. Check logs for:
   - API call log
   - Error log with exception details
   - Failed API response log

## Expected Output

### Test Script Output
```
================================================================================
LOGGING VALIDATION TEST SUITE
================================================================================

TEST 1: Basic Logging Functionality
================================================================================
✅ Basic logging test passed
📁 Check logs/test.log for output

TEST 2: Request ID Generation and Context
================================================================================
Generated Request ID 1: req_abc123def456
Generated Request ID 2: req_xyz789abc123
✅ Request ID generation test passed

TEST 3: API Logging with Request ID
================================================================================
Testing with Request ID: req_test123abc456
Response Request ID: req_test123abc456
✅ Request ID propagated correctly through API
✅ API logging test passed (status: 200, duration: 3.45s)
📁 Check logs/ui.log and logs/api.log for request ID traces

TEST 4: Batch Analysis Logging Simulation
================================================================================
Simulating batch analysis for 3 stocks...
  AAPL: req_aaa111bbb222
  MSFT: req_bbb222ccc333
  GOOGL: req_ccc333ddd444
✅ Batch logging simulation passed
📁 Check logs/ui.log for batch analysis logs

TEST 5: Error Logging
================================================================================
✅ Error logging test passed
📁 Check logs/ui.log for error log entry

================================================================================
TEST SUMMARY
================================================================================
✅ PASSED: Basic Logging
✅ PASSED: Request ID Generation
✅ PASSED: API Logging
✅ PASSED: Batch Logging Simulation
✅ PASSED: Error Logging

Total: 5/5 tests passed

🎉 All tests passed! Logging infrastructure is working correctly.
```

## Troubleshooting

### No Log Files Created
- Check that `logs/` directory exists
- Verify LOG_FILE_PATH environment variable
- Check file permissions

### Request IDs Not Matching
- Verify API middleware is installed
- Check that X-Request-ID header is being sent
- Ensure API is using the logging middleware

### Empty Log Files
- Check LOG_LEVEL environment variable (should be INFO or DEBUG)
- Verify logger is properly initialized
- Check console output for errors

### API Logs Missing
- Ensure API is running: `python run_api.py`
- Check that LoggingMiddleware is added to FastAPI app
- Verify API log file path configuration

## Environment Variables

Set these in `.env` file or system environment:
```bash
LOG_LEVEL=INFO
LOG_FORMAT=text
LOG_FILE_PATH=logs/ui.log
LOG_MAX_SIZE=52428800
LOG_BACKUP_COUNT=14
```

## Success Criteria

✅ Log files created in `logs/` directory  
✅ Each log entry has UTC timestamp  
✅ Session IDs present in UI logs  
✅ Request IDs unique for each stock in batch  
✅ Request IDs match between UI and API logs  
✅ Batch statistics logged correctly  
✅ Errors logged with full context  

## Next Steps

After validating logging:
1. Deploy to EC2 and test production logging
2. Configure CloudWatch log shipping
3. Set up log rotation and retention
4. Create log analysis dashboards
5. Set up alerts for error patterns
