-- Migration: Add enabled field to monitors table
-- This script adds the enabled field to existing monitors if it doesn't exist

DO $$
BEGIN
    -- Check if the enabled column exists
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name='monitors' 
        AND column_name='enabled'
    ) THEN
        -- Add the enabled column with default value true
        ALTER TABLE monitors ADD COLUMN enabled BOOLEAN DEFAULT true;
        
        -- Update existing monitors to be enabled by default
        UPDATE monitors SET enabled = true WHERE enabled IS NULL;
        
        -- Add comment
        COMMENT ON COLUMN monitors.enabled IS 'Whether the monitor is enabled for checking';
        
        RAISE NOTICE 'Added enabled column to monitors table';
    ELSE
        RAISE NOTICE 'enabled column already exists in monitors table';
    END IF;
END $$;
