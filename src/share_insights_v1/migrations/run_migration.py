#!/usr/bin/env python3
"""Run database migration to add batch_job_id column"""

import psycopg2
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Parse DATABASE_URL
db_url = os.getenv('DATABASE_URL')
if not db_url:
    raise ValueError("DATABASE_URL environment variable not set")

result = urlparse(db_url)

# Database connection
conn = psycopg2.connect(
    host=result.hostname,
    database=result.path[1:],
    user=result.username,
    password=result.password,
    port=result.port or 5432
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