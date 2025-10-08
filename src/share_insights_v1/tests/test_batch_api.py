#!/usr/bin/env python3
"""Test script for batch analysis API"""

import requests
import time
import os

API_BASE = "http://localhost:8000"
TEST_CSV_PATH = "src/share_insights_v1/resources/test_stocks.csv"

def test_batch_analysis():
    """Test the complete batch analysis workflow"""
    
    # 1. Check if test file exists
    if not os.path.exists(TEST_CSV_PATH):
        print(f"❌ Test file not found: {TEST_CSV_PATH}")
        return
    
    print("🚀 Starting comprehensive batch analysis test...")
    
    # 2. Upload CSV and create batch job with all analyzers
    print("\n📤 Uploading CSV file...")
    with open(TEST_CSV_PATH, 'rb') as f:
        files = {'file': ('test_stocks.csv', f, 'text/csv')}
        data = {
            'enabled_analyzers': 'dcf,comparable,technical,ai_insights,analyst_consensus',  # All analyzers
            'job_name': 'Comprehensive Test Analysis'
        }
        
        response = requests.post(f"{API_BASE}/batch/upload", files=files, data=data)
        
        if response.status_code != 200:
            print(f"❌ Failed to create batch job: {response.text}")
            return
        
        result = response.json()
        job_id = result['job_id']
        print(f"✅ Batch job created: {job_id}")
    
    # 3. Monitor job status
    print(f"\n👀 Monitoring job status...")
    while True:
        response = requests.get(f"{API_BASE}/batch/{job_id}/status")
        if response.status_code != 200:
            print(f"❌ Failed to get job status: {response.text}")
            return
        
        status = response.json()
        print(f"Status: {status['status']} | Completed: {status['completed_tickers']}/{status['total_tickers']}")
        
        if status['status'].upper() in ['COMPLETED', 'FAILED']:
            break
        
        time.sleep(2)
    
    # 4. Get final results
    print(f"\n📊 Getting final results...")
    response = requests.get(f"{API_BASE}/batch/{job_id}/results")
    if response.status_code != 200:
        print(f"❌ Failed to get results: Status {response.status_code}")
        print(f"Response: {response.text}")
        # Still try to check CSV file directly
        print("\n🔍 Checking for CSV file directly...")
        import glob
        csv_files = glob.glob("src/share_insights_v1/resources/stock_analyses/batch_analysis_*.csv")
        if csv_files:
            latest_csv = max(csv_files, key=os.path.getctime)
            print(f"✅ Found CSV file: {latest_csv}")
            _validate_csv_file(latest_csv)
        return
    
    results = response.json()
    print(f"✅ Job completed!")
    print(f"CSV Output: {results['results'].get('csv_output_path', 'Not generated')}")
    print(f"Summary: {results['summary']}")
    
    # 5. Check CSV file was created and validate format
    csv_path = results['results'].get('csv_output_path')
    if csv_path and os.path.exists(csv_path):
        _validate_csv_file(csv_path)
    else:
        print("❌ CSV file not found")

def _validate_csv_file(csv_path):
    """Validate CSV file format"""
    print(f"✅ CSV file created: {csv_path}")
    with open(csv_path, 'r') as f:
        lines = f.readlines()
        print(f"📄 CSV contains {len(lines)} lines (including header)")
        
        # Show header and first data row
        if len(lines) > 0:
            print(f"📋 Header: {lines[0].strip()}")
        if len(lines) > 1:
            print(f"📊 Sample row: {lines[1].strip()}")
            
        # Validate expected columns
        expected_cols = ['Ticker', 'Current_Price', 'DCF_Price', 'Comparable_Price', 
                       'Technical_Price', 'AI_Insights_Price', 'Analyst_Price', 
                       'Final_Recommendation', 'Analyst_Recommendation']
        if len(lines) > 0:
            header_cols = lines[0].strip().split(',')
            missing_cols = [col for col in expected_cols if col not in header_cols]
            if missing_cols:
                print(f"⚠️ Missing expected columns: {missing_cols}")
            else:
                print("✅ All expected columns present")

if __name__ == "__main__":
    test_batch_analysis()