#!/usr/bin/env python3

import requests
import json
import time

# API base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_analyzers():
    """Test analyzers endpoint"""
    print("\n🔍 Testing analyzers endpoint...")
    response = requests.get(f"{BASE_URL}/analyzers")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Available analyzers: {len(data['analyzers'])}")
        for analyzer in data['analyzers'][:3]:  # Show first 3
            print(f"  - {analyzer['name']}: {analyzer['applicable_to']}")
    return response.status_code == 200

def test_company_classification():
    """Test company classification"""
    print("\n🔍 Testing company classification...")
    ticker = "AAPL"
    response = requests.get(f"{BASE_URL}/company/{ticker}/classify")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Company: {data.get('ticker')} - {data.get('company_type')}")
        print(f"Sector: {data.get('sector')} | Industry: {data.get('industry')}")
    return response.status_code == 200

def test_quality_score():
    """Test quality score endpoint"""
    print("\n🔍 Testing quality score...")
    ticker = "AAPL"
    response = requests.get(f"{BASE_URL}/company/{ticker}/quality")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Quality Score: {data.get('quality_score')} (Grade: {data.get('grade')})")
    return response.status_code == 200

def test_stock_analysis():
    """Test full stock analysis"""
    print("\n🔍 Testing stock analysis...")
    ticker = "SDOT"
    
    # Test with all analyzers
    print(f"Analyzing {ticker} with all analyzers...")
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/analyze/{ticker}")
    end_time = time.time()
    
    print(f"Status: {response.status_code}")
    print(f"Analysis time: {end_time - start_time:.2f} seconds")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Company Type: {data.get('company_type')}")
        print(f"Analyses Run: {list(data.get('analyses', {}).keys())}")
        
        # Show final recommendation if available
        final_rec = data.get('final_recommendation')
        if final_rec:
            print(f"Final Recommendation: {final_rec.get('recommendation')} (Score: {final_rec.get('consensus_score', 0):.2f})")
    
    return response.status_code == 200

def test_selective_analysis():
    """Test analysis with selected analyzers"""
    print("\n🔍 Testing selective analysis...")
    ticker = "TSLA"
    
    # Test with only specific analyzers
    request_data = {
        "ticker": ticker,
        "enabled_analyzers": ["technical", "ai_insights", "news_sentiment"]
    }
    
    response = requests.post(
        f"{BASE_URL}/analyze/{ticker}",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        analyses = list(data.get('analyses', {}).keys())
        print(f"Requested: {request_data['enabled_analyzers']}")
        print(f"Received: {analyses}")
        
        # Check if we got only requested analyses
        if set(analyses) == set(request_data['enabled_analyzers']):
            print("✅ Selective analysis working correctly")
        else:
            print("❌ Selective analysis not working as expected")
    
    return response.status_code == 200

def run_all_tests():
    """Run all API tests"""
    print("🚀 Starting API Tests")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health),
        ("Analyzers List", test_analyzers),
        ("Company Classification", test_company_classification),
        ("Quality Score", test_quality_score),
        ("Full Stock Analysis", test_stock_analysis),
        ("Selective Analysis", test_selective_analysis)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed: {str(e)}")
            results[test_name] = False
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print("=" * 50)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(results.values())
    print(f"\nOverall: {total_passed}/{len(tests)} tests passed")

if __name__ == "__main__":
    print("Make sure the API server is running: python -m src.share_insights_v1.api.main")
    print("Starting tests in 3 seconds...")
    time.sleep(3)
    run_all_tests()