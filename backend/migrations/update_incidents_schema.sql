-- Update incidents table schema to match incident service expectations
-- This migration adds fields for better incident tracking and Claude agent integration

-- Add new columns to incidents table
ALTER TABLE incidents 
ADD COLUMN IF NOT EXISTS title VARCHAR(500),
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS error_type VARCHAR(100),
ADD COLUMN IF NOT EXISTS service VARCHAR(100),
ADD COLUMN IF NOT EXISTS rca_json JSONB,
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Update status check constraint to include new statuses
ALTER TABLE incidents 
DROP CONSTRAINT IF EXISTS incidents_status_check;

ALTER TABLE incidents 
ADD CONSTRAINT incidents_status_check 
CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'FAILED', 'INVESTIGATING'));

-- Update the default status
ALTER TABLE incidents 
ALTER COLUMN status SET DEFAULT 'OPEN';

-- Add index on service for faster queries
CREATE INDEX IF NOT EXISTS idx_incidents_service ON incidents(service);
CREATE INDEX IF NOT EXISTS idx_incidents_error_type ON incidents(error_type);
CREATE INDEX IF NOT EXISTS idx_incidents_status_new ON incidents(status);

-- Add notification_channels table if it doesn't exist
CREATE TABLE IF NOT EXISTS notification_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(20) NOT NULL CHECK (type IN ('NTFY', 'EMAIL', 'TELEGRAM', 'SLACK')),
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create trigger for notification_channels
CREATE TRIGGER update_notification_channels_updated_at 
    BEFORE UPDATE ON notification_channels 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add index on notification_channels
CREATE INDEX IF NOT EXISTS idx_notification_channels_type ON notification_channels(type);
CREATE INDEX IF NOT EXISTS idx_notification_channels_enabled ON notification_channels(enabled);
