#!/usr/bin/env python3
"""Run database migration to add batch_job_id column"""

import psycopg2

# Database connection
conn = psycopg2.connect(
    host="localhost",
    database="strategy_framework",
    user="postgres",
    password="M3rcury1"
)

try:
    cursor = conn.cursor()
    
    print("Adding batch_job_id column to analysis_history...")
    
    # Add column
    cursor.execute("""
        ALTER TABLE analysis_history 
        ADD COLUMN IF NOT EXISTS batch_job_id UUID;
    """)
    
    # Add foreign key
    cursor.execute("""
        ALTER TABLE analysis_history
        DROP CONSTRAINT IF EXISTS fk_analysis_history_batch_job;
    """)
    
    cursor.execute("""
        ALTER TABLE analysis_history
        ADD CONSTRAINT fk_analysis_history_batch_job
        FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(id)
        ON DELETE SET NULL;
    """)
    
    # Create index
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_analysis_history_batch_job_id 
        ON analysis_history(batch_job_id);
    """)
    
    conn.commit()
    
    # Verify
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'analysis_history' 
        AND column_name = 'batch_job_id';
    """)
    
    result = cursor.fetchone()
    if result:
        print(f"✓ Column added successfully: {result[0]} ({result[1]})")
    else:
        print("✗ Column not found")
    
    cursor.close()
    
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
