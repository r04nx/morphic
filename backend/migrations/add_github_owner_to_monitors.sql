-- Add github_owner field to monitors table for per-monitor GitHub configuration
ALTER TABLE monitors 
ADD COLUMN IF NOT EXISTS github_owner VARCHAR(255);

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_monitors_github_owner ON monitors(github_owner);
