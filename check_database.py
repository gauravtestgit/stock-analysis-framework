#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def check_database():
    """Check database connection and show current database info"""
    
    # Load environment variables
    load_dotenv()
    
    database_url = os.getenv('DATABASE_URL', 'sqlite:///strategy_framework.db')
    print(f"Database URL: {database_url}")
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            if 'postgresql' in database_url:
                # PostgreSQL queries
                result = conn.execute(text("SELECT current_database()"))
                current_db = result.fetchone()[0]
                print(f"Connected to PostgreSQL database: {current_db}")
                
                # List tables
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                tables = result.fetchall()
                print(f"Tables in database: {len(tables)}")
                for table in tables:
                    print(f"  - {table[0]}")
                    
            else:
                # SQLite queries
                print("Connected to SQLite database")
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = result.fetchall()
                print(f"Tables in database: {len(tables)}")
                for table in tables:
                    print(f"  - {table[0]}")
        
        print("✅ Database connection successful!")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    check_database()