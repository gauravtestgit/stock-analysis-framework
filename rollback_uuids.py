#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

def rollback_batch_analysis_ids():
    """Rollback batch_analysis_id values to null"""
    try:
        from src.share_insights_v1.models.database import SessionLocal
        from src.share_insights_v1.models.strategy_models import AnalysisHistory
        
        db = SessionLocal()
        try:
            # Count records with batch_analysis_id
            with_uuid = db.query(AnalysisHistory).filter(
                AnalysisHistory.batch_analysis_id.isnot(None)
            ).count()
            
            print(f"Found {with_uuid} analyses with batch_analysis_id")
            
            if with_uuid == 0:
                print("No records to rollback")
                return
            
            # Confirm rollback
            confirm = input(f"Set {with_uuid} batch_analysis_id values to null? (y/N): ")
            if confirm.lower() != 'y':
                print("Rollback cancelled")
                return
            
            # Set all batch_analysis_id to null
            updated = db.query(AnalysisHistory).filter(
                AnalysisHistory.batch_analysis_id.isnot(None)
            ).update({AnalysisHistory.batch_analysis_id: None})
            
            db.commit()
            print(f"✅ Successfully rolled back {updated} analyses")
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    rollback_batch_analysis_ids()