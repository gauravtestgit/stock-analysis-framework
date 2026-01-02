#!/usr/bin/env python3
"""Test script that only checks status, not results"""

import requests
import time
import os

API_BASE = "http://localhost:8000"
TEST_CSV_PATH = "src/share_insights_v1/resources/test_stocks.csv"

def test_status_only():
    """Test with status check only to avoid serialization issues"""
    
    print("🚀 Testing batch analysis (status only)...")
    
    with open(TEST_CSV_PATH, 'rb') as f:
        files = {'file': ('test_stocks.csv', f, 'text/csv')}
        data = {
            'enabled_analyzers': 'technical,analyst_consensus',
            'job_name': 'Status Test'
        }
        
        response = requests.post(f"{API_BASE}/batch/upload", files=files, data=data)
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            job_id = result['job_id']
            print(f"✅ Job created: {job_id}")
            
            # Monitor status until completion
            while True:
                time.sleep(2)
                status_response = requests.get(f"{API_BASE}/batch/{job_id}/status")
                if status_response.status_code == 200:
                    status = status_response.json()
                    print(f"Status: {status['status']} | Progress: {status['completed_tickers']}/{status['total_tickers']}")
                    
                    if status['status'] in ['COMPLETED', 'FAILED']:
                        break
                else:
                    print(f"Status check failed: {status_response.status_code}")
                    break
            
            # Check CSV file directly
            print("\n📄 Checking CSV output...")
            csv_files = [f for f in os.listdir("src/share_insights_v1/resources/stock_analyses") 
                        if f.startswith("batch_analysis_") and f.endswith(".csv")]
            
            if csv_files:
                latest_csv = sorted(csv_files)[-1]
                csv_path = f"src/share_insights_v1/resources/stock_analyses/{latest_csv}"
                print(f"Latest CSV: {csv_path}")
                
                with open(csv_path, 'r') as f:
                    content = f.read()
                    lines = content.strip().split('\n')
                    print(f"CSV has {len(lines)} lines")
                    if len(lines) > 1:
                        print("✅ CSV contains data")
                        print("First few lines:")
                        for line in lines[:3]:
                            print(f"  {line}")
                    else:
                        print("❌ CSV is empty or only has header")

if __name__ == "__main__":
    test_status_only()