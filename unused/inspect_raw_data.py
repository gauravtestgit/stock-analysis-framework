#!/usr/bin/env python3
"""Debug script to inspect raw_data structure"""

from src.share_insights_v1.models.database import SessionLocal
from src.share_insights_v1.models.strategy_models import AnalysisHistory

def inspect_raw_data():
    db = SessionLocal()
    try:
        # Get a sample analysis record
        analysis = db.query(AnalysisHistory).first()
        
        if analysis:
            print(f"Ticker: {analysis.ticker}")
            print(f"Analysis Type: {analysis.analysis_type}")
            print(f"Target Price: {analysis.target_price}")
            print(f"Current Price: {analysis.current_price}")
            print(f"\nRaw Data Keys:")
            if analysis.raw_data and isinstance(analysis.raw_data, dict):
                for key in analysis.raw_data.keys():
                    print(f"  - {key}")
                
                # Check for analyst data
                print(f"\nAnalyst Data:")
                print(f"  professional_target_price: {analysis.raw_data.get('professional_target_price')}")
                print(f"  analyst_price: {analysis.raw_data.get('analyst_price')}")
                print(f"  analyst_count: {analysis.raw_data.get('analyst_count')}")
                
                # Show full raw_data for one record
                print(f"\nFull raw_data sample:")
                import json
                print(json.dumps(analysis.raw_data, indent=2)[:500])
            else:
                print("  No raw_data or not a dict")
        else:
            print("No analysis records found")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_raw_data()
