#!/usr/bin/env python3

from sqlalchemy.orm import Session
from sqlalchemy import text
from ..models.database import get_db
from ..models.strategy_models import AnalysisHistory
from ..services.database.database_service import DatabaseService

def migrate_current_price():
    """Update historical current_price from technical analysis data"""
    
    db_service = DatabaseService()
    
    with next(get_db()) as db:
        # Use bulk update with raw SQL for better performance
        result = db.execute(text("""
            UPDATE analysis_history 
            SET current_price = consensus.current_price
            FROM (
                SELECT ticker, DATE(analysis_date) as analysis_day, 
                       CAST(raw_data->>'current_price' AS FLOAT) as current_price
                FROM analysis_history 
                WHERE analysis_type = 'analyst_consensus' 
                AND raw_data->>'current_price' IS NOT NULL
            ) consensus
            WHERE analysis_history.ticker = consensus.ticker 
            AND DATE(analysis_history.analysis_date) = consensus.analysis_day
            AND analysis_history.current_price IS NULL
        """))
        
        db.commit()
        print(f"Migration complete: Updated {result.rowcount} records")

if __name__ == "__main__":
    migrate_current_price()