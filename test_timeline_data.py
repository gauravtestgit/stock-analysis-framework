#!/usr/bin/env python3
"""Test script to check timeline data directly from API"""

import requests
import json
import pandas as pd

def test_timeline_api():
    """Test the timeline API directly"""
    ticker = "AAPL"
    
    try:
        # Test timeline endpoint
        response = requests.get(f"http://localhost:8000/api/history/{ticker}/timeline")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Records returned: {len(data)}")
            
            if data:
                # Show first few records
                print("\nFirst 3 records:")
                for i, record in enumerate(data[:3]):
                    print(f"Record {i+1}: {json.dumps(record, indent=2)}")
                
                # Convert to DataFrame for analysis
                df = pd.DataFrame(data)
                print(f"\nDataFrame shape: {df.shape}")
                print(f"Columns: {list(df.columns)}")
                
                if 'target_price' in df.columns:
                    print(f"\nTarget price stats:")
                    print(f"Min: {df['target_price'].min()}")
                    print(f"Max: {df['target_price'].max()}")
                    print(f"Mean: {df['target_price'].mean():.2f}")
                    print(f"Unique values: {df['target_price'].nunique()}")
                    print(f"Sample values: {df['target_price'].head(10).tolist()}")
                
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    print(f"\nDate range: {df['date'].min()} to {df['date'].max()}")
                
                if 'recommendation' in df.columns:
                    print(f"\nRecommendation counts:")
                    print(df['recommendation'].value_counts())
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_timeline_api()