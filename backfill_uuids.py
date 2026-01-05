#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

def backfill_batch_analysis_ids():
    """Backfill missing batch_analysis_id for existing analyses"""
    try:
        from src.share_insights_v1.models.database import SessionLocal
        from src.share_insights_v1.models.strategy_models import AnalysisHistory
        from sqlalchemy import and_, func
        import uuid
        from datetime import timedelta
        
        db = SessionLocal()
        try:
            # Find analyses without batch_analysis_id
            null_analyses = db.query(AnalysisHistory).filter(
                AnalysisHistory.batch_analysis_id.is_(None)
            ).order_by(AnalysisHistory.ticker, AnalysisHistory.analysis_date).all()
            
            print(f"Found {len(null_analyses)} analyses without batch_analysis_id")
            
            # Group by ticker and find analysis sessions (within 5-minute windows)
            groups = {}
            for analysis in null_analyses:
                ticker = analysis.ticker
                analysis_time = analysis.analysis_date
                
                # Find if this analysis belongs to an existing group (within 5 minutes)
                group_found = False
                for group_key, group_data in groups.items():
                    if (group_data['ticker'] == ticker and 
                        abs((analysis_time - group_data['base_time']).total_seconds()) <= 300):  # 5 minutes
                        groups[group_key]['analyses'].append(analysis)
                        group_found = True
                        break
                
                # Create new group if not found
                if not group_found:
                    group_key = f"{ticker}_{analysis_time.strftime('%Y%m%d_%H%M%S')}"
                    groups[group_key] = {
                        'ticker': ticker,
                        'base_time': analysis_time,
                        'analyses': [analysis]
                    }
            
            print(f"Grouped into {len(groups)} analysis sessions")
            
            # Show grouping summary
            for group_key, group_data in list(groups.items())[:5]:  # Show first 5
                print(f"  {group_key}: {len(group_data['analyses'])} analyses")
            if len(groups) > 5:
                print(f"  ... and {len(groups) - 5} more groups")
            
            # Assign UUIDs to each group
            updated_count = 0
            for group_key, group_data in groups.items():
                group_uuid = uuid.uuid4()
                analyses = group_data['analyses']
                
                for analysis in analyses:
                    analysis.batch_analysis_id = group_uuid
                    updated_count += 1
            
            # Commit changes
            db.commit()
            print(f"SUCCESS: Successfully updated {updated_count} analyses with batch_analysis_id")
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    backfill_batch_analysis_ids()