#!/usr/bin/env python3
"""Debug test script to check API routing"""

import requests
import os

API_BASE = "http://localhost:8000"

def debug_api():
    """Debug API endpoints"""
    
    print("🔍 Testing API endpoints...")
    
    # 1. Test health endpoint
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE}/health")
        print(f"Health Status: {response.status_code}")
        print(f"Health Response: {response.text}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return
    
    # 2. Test docs endpoint
    print("\n2. Testing docs endpoint...")
    try:
        response = requests.get(f"{API_BASE}/docs")
        print(f"Docs Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Docs failed: {e}")
    
    # 3. Test batch upload with minimal data
    print("\n3. Testing batch upload...")
    try:
        # Create minimal CSV content
        csv_content = "Symbol,Security Name\nAAPL,Apple Inc."
        
        files = {'file': ('test.csv', csv_content, 'text/csv')}
        data = {'job_name': 'Debug Test'}
        
        response = requests.post(f"{API_BASE}/batch/upload", files=files, data=data)
        print(f"Batch Upload Status: {response.status_code}")
        print(f"Batch Upload Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('job_id')
            print(f"✅ Job created: {job_id}")
            
            # Test status endpoint
            if job_id:
                status_response = requests.get(f"{API_BASE}/batch/{job_id}/status")
                print(f"Status Response: {status_response.status_code} - {status_response.text}")
        
    except Exception as e:
        print(f"❌ Batch upload failed: {e}")

if __name__ == "__main__":
    debug_api()