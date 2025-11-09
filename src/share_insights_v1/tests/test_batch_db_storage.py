#!/usr/bin/env python3
"""Test batch analysis service with database storage"""

import os
from ..services.batch.batch_analysis_service import BatchAnalysisService

def test_batch_with_db_storage():
    """Test batch analysis with database storage enabled"""
    
    # Create test CSV content
    test_csv_path = "test_batch_db.csv"
    csv_content = """Symbol,Security Name
AAPL,Apple Inc.
MSFT,Microsoft Corporation
GOOGL,Alphabet Inc.
"""
    
    # Write test CSV
    with open(test_csv_path, 'w') as f:
        f.write(csv_content)
    
    try:
        # Test with database storage enabled
        print("Testing batch analysis WITH database storage...")
        service_with_db = BatchAnalysisService(save_to_db=True)
        
        output_path = "batch_results_with_db.csv"
        service_with_db.process_csv(test_csv_path, output_path, max_stocks=3)
        
        print(f"✓ Batch analysis completed with DB storage")
        print(f"✓ Results saved to: {output_path}")
        
        # Test without database storage
        print("\nTesting batch analysis WITHOUT database storage...")
        service_without_db = BatchAnalysisService(save_to_db=False)
        
        output_path_no_db = "batch_results_no_db.csv"
        service_without_db.process_csv(test_csv_path, output_path_no_db, max_stocks=3)
        
        print(f"✓ Batch analysis completed without DB storage")
        print(f"✓ Results saved to: {output_path_no_db}")
        
        # Verify database storage
        print("\nVerifying database storage...")
        from ..models.database import SessionLocal
        from ..models.strategy_models import AnalysisHistory
        from sqlalchemy import desc
        
        db = SessionLocal()
        try:
            recent_analyses = db.query(AnalysisHistory).order_by(
                desc(AnalysisHistory.analysis_date)
            ).limit(10).all()
            
            if recent_analyses:
                print(f"✓ Found {len(recent_analyses)} recent analyses in database:")
                for analysis in recent_analyses[:5]:
                    print(f"  {analysis.ticker}: {analysis.analysis_type} - {analysis.recommendation}")
            else:
                print("✗ No analyses found in database")
        finally:
            db.close()
            
    finally:
        # Clean up test files
        if os.path.exists(test_csv_path):
            os.remove(test_csv_path)

if __name__ == "__main__":
    test_batch_with_db_storage()