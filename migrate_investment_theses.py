#!/usr/bin/env python3
"""
Database migration script to update investment_theses table
- Add batch_analysis_id UUID column
- Remove analysis_data_id foreign key column
"""

import psycopg2
import os
from dotenv import load_dotenv
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from urllib.parse import urlparse

def run_migration():
    """Execute the database migration"""
    
    # Load environment variables
    load_dotenv()
    
    # Parse DATABASE_URL
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    result = urlparse(db_url)
    conn_params = {
        'host': result.hostname,
        'database': result.path[1:],
        'user': result.username,
        'password': result.password,
        'port': result.port or 5432
    }
    
    try:
        # Connect to database
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Starting migration of investment_theses table...")
        
        # Step 1: Add batch_analysis_id column
        print("Adding batch_analysis_id column...")
        cursor.execute("""
            ALTER TABLE investment_theses 
            ADD COLUMN batch_analysis_id UUID;
        """)
        
        # Step 2: Create index on batch_analysis_id
        print("Creating index on batch_analysis_id...")
        cursor.execute("""
            CREATE INDEX ix_investment_theses_batch_analysis_id 
            ON investment_theses (batch_analysis_id);
        """)
        
        # Step 3: Drop foreign key constraint on analysis_data_id
        print("Dropping foreign key constraint...")
        cursor.execute("""
            ALTER TABLE investment_theses 
            DROP CONSTRAINT IF EXISTS investment_theses_analysis_data_id_fkey;
        """)
        
        # Step 4: Drop analysis_data_id column
        print("Dropping analysis_data_id column...")
        cursor.execute("""
            ALTER TABLE investment_theses 
            DROP COLUMN IF EXISTS analysis_data_id;
        """)
        
        print("Migration completed successfully!")
        
        # Verify the changes
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'investment_theses' 
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print("\nUpdated table structure:")
        for col_name, data_type, nullable in columns:
            print(f"  - {col_name}: {data_type} ({'NULL' if nullable == 'YES' else 'NOT NULL'})")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migration()