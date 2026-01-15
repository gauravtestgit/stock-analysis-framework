-- Migration: Add batch_jobs table and update analysis_history
-- Date: 2024-01-15
-- Description: Add batch job tracking system

-- 1. Create batch_jobs table
CREATE TABLE IF NOT EXISTS batch_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200),
    exchange VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending',
    total_stocks INTEGER DEFAULT 0,
    completed_stocks INTEGER DEFAULT 0,
    failed_stocks INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    created_by VARCHAR(100),
    input_file VARCHAR(500),
    output_file VARCHAR(500)
);

-- 2. Create indexes on batch_jobs
CREATE INDEX IF NOT EXISTS idx_batch_jobs_id ON batch_jobs(id);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_exchange ON batch_jobs(exchange);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_status ON batch_jobs(status);

-- 3. Add batch_job_id column to analysis_history
ALTER TABLE analysis_history 
ADD COLUMN IF NOT EXISTS batch_job_id UUID;

-- 4. Create foreign key constraint
ALTER TABLE analysis_history
ADD CONSTRAINT fk_analysis_history_batch_job
FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(id)
ON DELETE SET NULL;

-- 5. Create index on batch_job_id
CREATE INDEX IF NOT EXISTS idx_analysis_history_batch_job_id ON analysis_history(batch_job_id);

-- Verify migration
SELECT 'Migration completed successfully' AS status;
