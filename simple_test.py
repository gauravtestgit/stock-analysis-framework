#!/usr/bin/env python3
"""Simple test script for batch analysis API"""

import requests
import time
import os

API_BASE = "http://localhost:8000"
TEST_CSV_PATH = "src/share_insights_v1/resources/test_stocks.csv"

def test_batch_analysis():
    """Test the complete batch analysis workflow"""
    
    print("🚀 Starting simple batch analysis test...")
    
    # Upload CSV and create batch job
    print("\n📤 Uploading CSV file...")
    with open(TEST_CSV_PATH, 'rb') as f:
        files = {'file': ('test_stocks.csv', f, 'text/csv')}
        data = {
            'enabled_analyzers': 'technical,dcf,analyst_consensus',
            'job_name': 'Simple Test'
        }
        
        response = requests.post(f"{API_BASE}/batch/upload", files=files, data=data)
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            job_id = result['job_id']
            print(f"✅ Job created: {job_id}")
            
            # Check status once
            time.sleep(2)
            status_response = requests.get(f"{API_BASE}/batch/{job_id}/status")
            print(f"Status: {status_response.json()}")

if __name__ == "__main__":
    test_batch_analysis()