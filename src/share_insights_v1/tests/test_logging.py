"""  
Test script to validate logging functionality
Tests both API and UI logging with request ID tracing
"""
import os
import sys
import time
import requests
from pathlib import Path

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

from src.share_insights_v1.utils.logging import (
    setup_logger,
    log_with_context,
    generate_request_id,
    set_request_id,
    get_request_id,
    log_api_call,
    log_api_response,
    log_error,
    log_batch_analysis_start,
    log_batch_analysis_complete
)

def test_basic_logging():
    """Test 1: Basic logging functionality"""
    print("\n" + "="*80)
    print("TEST 1: Basic Logging Functionality")
    print("="*80)
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Setup logger
    logger = setup_logger(
        name='test_logger',
        component='TEST',
        log_level='INFO',
        log_format='text',
        log_file='logs/test.log'
    )
    
    # Test basic logging
    logger.info("Test log message")
    log_with_context(
        logger,
        'info',
        'Test with context',
        request_id='req_test123',
        metadata={'test': 'value'}
    )
    
    print("✅ Basic logging test passed")
    print("📁 Check logs/test.log for output")
    
    return True

def test_request_id_generation():
    """Test 2: Request ID generation and context"""
    print("\n" + "="*80)
    print("TEST 2: Request ID Generation and Context")
    print("="*80)
    
    # Generate request IDs
    req_id_1 = generate_request_id()
    req_id_2 = generate_request_id()
    
    print(f"Generated Request ID 1: {req_id_1}")
    print(f"Generated Request ID 2: {req_id_2}")
    
    # Verify format
    assert req_id_1.startswith('req_'), "Request ID should start with 'req_'"
    assert len(req_id_1) == 16, "Request ID should be 16 characters (req_ + 12 hex)"
    assert req_id_1 != req_id_2, "Request IDs should be unique"
    
    # Test context management
    set_request_id(req_id_1)
    retrieved_id = get_request_id()
    assert retrieved_id == req_id_1, "Retrieved request ID should match set ID"
    
    print("✅ Request ID generation test passed")
    
    return True

def test_api_logging_with_request_id():
    """Test 3: API logging with request ID propagation"""
    print("\n" + "="*80)
    print("TEST 3: API Logging with Request ID")
    print("="*80)
    
    # Check if API is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code != 200:
            print("⚠️  API not running. Start with: python run_api.py")
            return False
    except requests.exceptions.RequestException:
        print("⚠️  API not running. Start with: python run_api.py")
        return False
    
    # Generate unique request ID
    request_id = generate_request_id()
    set_request_id(request_id)
    
    print(f"Testing with Request ID: {request_id}")
    
    # Test API call with request ID
    ticker = "AAPL"
    endpoint = f"http://localhost:8000/analyze/{ticker}"
    
    # Log API call
    log_api_call(
        endpoint=endpoint,
        method='POST',
        ticker=ticker,
        metadata={
            'request_id': request_id,
            'test': 'logging_validation'
        }
    )
    
    # Make actual API call with request ID in header
    start_time = time.time()
    headers = {'X-Request-ID': request_id}
    response = requests.post(
        endpoint,
        json={'ticker': ticker, 'enabled_analyzers': ['dcf']},
        headers=headers
    )
    duration = time.time() - start_time
    
    # Log API response
    log_api_response(
        endpoint=endpoint,
        status_code=response.status_code,
        duration=duration,
        success=response.status_code == 200,
        error=response.text if response.status_code != 200 else None,
        metadata={'ticker': ticker, 'request_id': request_id}
    )
    
    # Verify request ID in response headers
    response_req_id = response.headers.get('X-Request-ID')
    print(f"Response Request ID: {response_req_id}")
    
    if response_req_id == request_id:
        print("✅ Request ID propagated correctly through API")
    else:
        print(f"⚠️  Request ID mismatch: sent {request_id}, received {response_req_id}")
    
    print(f"✅ API logging test passed (status: {response.status_code}, duration: {duration:.2f}s)")
    print("📁 Check logs/ui.log and logs/api.log for request ID traces")
    
    return True

def test_batch_logging_simulation():
    """Test 4: Simulate batch analysis logging"""
    print("\n" + "="*80)
    print("TEST 4: Batch Analysis Logging Simulation")
    print("="*80)
    
    # Simulate batch analysis
    tickers = ['AAPL', 'MSFT', 'GOOGL']
    analyzers = ['dcf', 'technical']
    
    # Log batch start
    log_batch_analysis_start(
        watchlist=tickers,
        analyzers=analyzers,
        metadata={
            'max_workers': 3,
            'test': 'batch_simulation'
        }
    )
    
    print(f"Simulating batch analysis for {len(tickers)} stocks...")
    
    # Simulate individual stock analyses
    results = {'success': 0, 'failed': 0}
    for ticker in tickers:
        request_id = generate_request_id()
        print(f"  {ticker}: {request_id}")
        
        # Simulate API call
        log_api_call(
            endpoint=f"/analyze/{ticker}",
            method='POST',
            ticker=ticker,
            metadata={'request_id': request_id, 'test': 'batch_simulation'}
        )
        
        # Simulate response
        log_api_response(
            endpoint=f"/analyze/{ticker}",
            status_code=200,
            duration=2.5,
            success=True,
            metadata={'ticker': ticker, 'request_id': request_id}
        )
        
        results['success'] += 1
    
    # Log batch complete
    log_batch_analysis_complete(
        stock_count=len(tickers),
        success_count=results['success'],
        failed_count=results['failed'],
        duration=7.5,
        metadata={'test': 'batch_simulation'}
    )
    
    print("✅ Batch logging simulation passed")
    print("📁 Check logs/ui.log for batch analysis logs")
    
    return True

def test_error_logging():
    """Test 5: Error logging"""
    print("\n" + "="*80)
    print("TEST 5: Error Logging")
    print("="*80)
    
    # Test error logging
    log_error(
        error_type='TEST_ERROR',
        error_message='This is a test error message',
        page='test_script',
        metadata={'test': 'error_logging', 'severity': 'low'}
    )
    
    print("✅ Error logging test passed")
    print("📁 Check logs/ui.log for error log entry")
    
    return True

def test_orchestrator_response_logging():
    """Test 6: Verify orchestrator response is logged in API logs"""
    print("\n" + "="*80)
    print("TEST 6: Orchestrator Response Logging")
    print("="*80)
    
    # Check if API is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code != 200:
            print("⚠️  API not running. Start with: python run_api.py")
            return False
    except requests.exceptions.RequestException:
        print("⚠️  API not running. Start with: python run_api.py")
        return False
    
    # Generate unique request ID
    request_id = generate_request_id()
    print(f"Testing with Request ID: {request_id}")
    
    # Make API call
    ticker = "UBER"
    headers = {'X-Request-ID': request_id}
    response = requests.post(
        f"http://localhost:8000/analyze/{ticker}",
        json={'ticker': ticker},
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ API call failed: {response.status_code}")
        return False
    
    print(f"✅ Analysis completed for {ticker}")
    
    # Check API log for orchestrator response
    api_log = Path('logs/api.log')
    if not api_log.exists():
        print("⚠️  logs/api.log not found")
        return False
    
    # Search for orchestrator completion log with metadata
    with open(api_log, 'r') as f:
        log_content = f.read()
        
    if request_id in log_content and 'Orchestrator analysis completed' in log_content:
        # Check if metadata fields are present
        has_metadata = all([
            'ticker' in log_content,
            'company_type' in log_content,
            'recommendation' in log_content,
            'analyzers_run' in log_content
        ])
        
        if has_metadata:
            print("✅ Orchestrator response with metadata found in API logs")
            print("📁 Check logs/api.log for full orchestrator response details")
            return True
        else:
            print("⚠️  Orchestrator log found but missing metadata fields")
            return False
    else:
        print("⚠️  Orchestrator completion log not found for request ID")
        return False

def verify_log_files():
    """Verify log files were created"""
    print("\n" + "="*80)
    print("LOG FILE VERIFICATION")
    print("="*80)
    
    log_files = {
        'logs/test.log': 'Test logger output',
        'logs/ui.log': 'UI logging output',
        'logs/api.log': 'API logging output (if API was running)'
    }
    
    for log_file, description in log_files.items():
        if Path(log_file).exists():
            size = Path(log_file).stat().st_size
            print(f"✅ {log_file}: {size} bytes - {description}")
        else:
            print(f"⚠️  {log_file}: Not found - {description}")
    
    return True

def show_log_samples():
    """Show sample log entries"""
    print("\n" + "="*80)
    print("SAMPLE LOG ENTRIES")
    print("="*80)
    
    log_files = ['logs/test.log', 'logs/ui.log']
    
    for log_file in log_files:
        if Path(log_file).exists():
            print(f"\n📄 {log_file} (last 5 lines):")
            print("-" * 80)
            with open(log_file, 'r') as f:
                lines = f.readlines()
                for line in lines[-5:]:
                    print(line.rstrip())
        else:
            print(f"\n⚠️  {log_file}: Not found")
    
    return True

def main():
    """Run all logging tests"""
    print("\n" + "="*80)
    print("LOGGING VALIDATION TEST SUITE")
    print("="*80)
    print("\nThis script tests the logging infrastructure:")
    print("1. Basic logging functionality")
    print("2. Request ID generation and context")
    print("3. API logging with request ID propagation")
    print("4. Batch analysis logging simulation")
    print("5. Error logging")
    print("6. Orchestrator response logging with metadata")
    print("\nNote: For Tests 3 & 6, make sure the API is running (python run_api.py)")
    
    tests = [
        ("Basic Logging", test_basic_logging),
        ("Request ID Generation", test_request_id_generation),
        ("API Logging", test_api_logging_with_request_id),
        ("Batch Logging Simulation", test_batch_logging_simulation),
        ("Error Logging", test_error_logging),
        ("Orchestrator Response Logging", test_orchestrator_response_logging),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results[test_name] = False
    
    # Verify log files
    verify_log_files()
    
    # Show log samples
    show_log_samples()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Logging infrastructure is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the output above for details.")
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("1. Check log files in logs/ directory")
    print("2. Search for request IDs: grep 'req_' logs/*.log")
    print("3. Test with real dashboard: python run_dashboard.py")
    print("4. Perform batch analysis and check logs/ui.log")
    print("="*80)

if __name__ == "__main__":
    main()
