#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

def verify_uuid_in_database():
    """Verify that batch_analysis_id is stored in database"""
    try:
        from src.share_insights_v1.models.database import SessionLocal
        from src.share_insights_v1.models.strategy_models import AnalysisHistory
        
        db = SessionLocal()
        try:
            # Check total records
            total = db.query(AnalysisHistory).count()
            print(f"Total analysis records: {total}")
            
            # Check records with batch_analysis_id
            with_uuid = db.query(AnalysisHistory).filter(AnalysisHistory.batch_analysis_id.isnot(None)).count()
            print(f"Records with batch_analysis_id: {with_uuid}")
            
            # Show recent records
            recent = db.query(AnalysisHistory).filter(
                AnalysisHistory.batch_analysis_id.isnot(None)
            ).order_by(AnalysisHistory.analysis_date.desc()).limit(3).all()
            
            print("Recent records with batch_analysis_id:")
            for r in recent:
                print(f"  {r.ticker} - {r.analysis_type} - UUID: {r.batch_analysis_id}")
            
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verify_uuid_in_database()