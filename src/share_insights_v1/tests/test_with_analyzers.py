#!/usr/bin/env python3
"""Test script with specific analyzers"""

import requests
import time
import os

API_BASE = "http://localhost:8000"
TEST_CSV_PATH = "src/share_insights_v1/resources/test_stocks.csv"

def test_with_analyzers():
    """Test with specific analyzers"""
    
    print("🚀 Testing with specific analyzers...")
    
    with open(TEST_CSV_PATH, 'rb') as f:
        files = {'file': ('test_stocks.csv', f, 'text/csv')}
        data = {
            'enabled_analyzers': 'technical,analyst_consensus',  # Just 2 analyzers
            'job_name': 'Analyzer Test'
        }
        
        response = requests.post(f"{API_BASE}/batch/upload", files=files, data=data)
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            job_id = result['job_id']
            print(f"✅ Job created: {job_id}")
            
            # Wait and check status
            time.sleep(5)
            status_response = requests.get(f"{API_BASE}/batch/{job_id}/status")
            print(f"Status: {status_response.json()}")
            
            # Get results
            results_response = requests.get(f"{API_BASE}/batch/{job_id}/results")
            if results_response.status_code == 200:
                results = results_response.json()
                csv_path = results['results'].get('csv_output_path')
                print(f"CSV Path: {csv_path}")
                
                if csv_path and os.path.exists(csv_path):
                    with open(csv_path, 'r') as f:
                        print("CSV Content:")
                        print(f.read())

if __name__ == "__main__":
    test_with_analyzers()