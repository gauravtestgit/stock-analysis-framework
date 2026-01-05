"""
Database inspection script for thesis storage
View stored theses and validate database contents
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.share_insights_v1.models.database import SessionLocal
from src.share_insights_v1.models.strategy_models import InvestmentThesis

def inspect_thesis_database():
    """Inspect thesis database contents"""
    
    db = SessionLocal()
    try:
        # Get all theses
        theses = db.query(InvestmentThesis).order_by(InvestmentThesis.created_at.desc()).all()
        
        print(f"📊 Database Inspection - Found {len(theses)} theses")
        print("=" * 60)
        
        if not theses:
            print("No theses found in database")
            return
        
        for thesis in theses:
            print(f"ID: {thesis.id}")
            print(f"Ticker: {thesis.ticker}")
            print(f"Type: {thesis.thesis_type}")
            print(f"LLM: {thesis.llm_provider} - {thesis.llm_model}")
            print(f"Created: {thesis.created_at}")
            print(f"Content: {thesis.content[:100]}...")
            if thesis.previous_thesis_id:
                print(f"Chained from: {thesis.previous_thesis_id}")
            print("-" * 40)
            
    except Exception as e:
        print(f"Error inspecting database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_thesis_database()