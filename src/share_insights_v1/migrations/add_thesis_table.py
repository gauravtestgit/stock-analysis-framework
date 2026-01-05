"""
Database migration script for Phase 2 - Thesis Storage
Adds InvestmentThesis table to existing database schema
"""

from sqlalchemy import create_engine
from ...models.database import DATABASE_URL
from ...models.strategy_models import InvestmentThesis

def migrate_database():
    """Add InvestmentThesis table to existing database"""
    engine = create_engine(DATABASE_URL)
    
    # Create the new table
    InvestmentThesis.__table__.create(engine, checkfirst=True)
    
    print("✅ Database migration completed - InvestmentThesis table added")

if __name__ == "__main__":
    migrate_database()