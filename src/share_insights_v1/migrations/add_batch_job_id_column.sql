-- Check if column exists
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'analysis_history' 
AND column_name = 'batch_job_id';

-- Add column (run this if column doesn't exist)
ALTER TABLE analysis_history ADD COLUMN batch_job_id UUID;

-- Add foreign key
ALTER TABLE analysis_history
ADD CONSTRAINT fk_analysis_history_batch_job
FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(id)
ON DELETE SET NULL;

-- Create index
CREATE INDEX idx_analysis_history_batch_job_id ON analysis_history(batch_job_id);

-- Verify
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'analysis_history' 
AND column_name = 'batch_job_id';
