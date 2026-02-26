#!/usr/bin/env python3
"""Test script to check database data directly"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.share_insights_v1.services.storage.historical_analysis_service import HistoricalAnalysisService
import pandas as pd

def test_database_direct():
    """Test database service directly"""
    ticker = "AAPL"
    
    try:
        service = HistoricalAnalysisService()
        
        # Get timeline data
        timeline_data = service.get_recommendation_timeline(ticker)
        print(f"Timeline records: {len(timeline_data)}")
        
        if timeline_data:
            # Show first few records
            print("\nFirst 3 records:")
            for i, record in enumerate(timeline_data[:3]):
                print(f"Record {i+1}: {record}")
            
            # Convert to DataFrame
            df = pd.DataFrame(timeline_data)
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
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_database_direct()