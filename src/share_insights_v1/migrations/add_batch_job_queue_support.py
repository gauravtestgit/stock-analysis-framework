#!/usr/bin/env python3
"""Run database migration to add batch-job queue support (pid, created_at,
thread_count on batch_jobs; a new batch_settings singleton table) for the
Batch Analysis UI feature."""

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

    print("Adding pid/created_at/thread_count columns to batch_jobs...")

    cursor.execute("""
        ALTER TABLE batch_jobs
        ADD COLUMN IF NOT EXISTS pid INTEGER;
    """)

    cursor.execute("""
        ALTER TABLE batch_jobs
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    """)

    cursor.execute("""
        ALTER TABLE batch_jobs
        ADD COLUMN IF NOT EXISTS thread_count INTEGER DEFAULT 2;
    """)

    # started_at is now set at promotion time (not row creation), so it must be nullable
    cursor.execute("""
        ALTER TABLE batch_jobs
        ALTER COLUMN started_at DROP NOT NULL;
    """)

    print("Creating batch_settings table...")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS batch_settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            concurrency_limit INTEGER NOT NULL DEFAULT 1,
            CONSTRAINT single_row CHECK (id = 1)
        );
    """)

    cursor.execute("""
        INSERT INTO batch_settings (id, concurrency_limit)
        VALUES (1, 1)
        ON CONFLICT (id) DO NOTHING;
    """)

    conn.commit()

    # Verify
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'batch_jobs'
        AND column_name IN ('pid', 'created_at', 'thread_count')
        ORDER BY column_name;
    """)
    for column_name, data_type in cursor.fetchall():
        print(f"✓ batch_jobs.{column_name} ({data_type})")

    cursor.execute("SELECT concurrency_limit FROM batch_settings WHERE id = 1;")
    row = cursor.fetchone()
    if row:
        print(f"✓ batch_settings ready (concurrency_limit={row[0]})")
    else:
        print("✗ batch_settings row not found")

    cursor.close()

except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
