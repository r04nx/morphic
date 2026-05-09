-- Initialize Morphic Database Schema
-- This file runs automatically when PostgreSQL container starts

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create incidents table
CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trace_id VARCHAR(255) NOT NULL UNIQUE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    classification VARCHAR(100),
    root_cause TEXT,
    blast_radius VARCHAR(20) CHECK (blast_radius IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    impact TEXT,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'resolved', 'investigating')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create incident_logs table for log timeline
CREATE TABLE IF NOT EXISTS incident_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID REFERENCES incidents(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    service VARCHAR(100),
    endpoint VARCHAR(255),
    log_level VARCHAR(20),
    message TEXT,
    raw_log JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create remediation_actions table
CREATE TABLE IF NOT EXISTS remediation_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID REFERENCES incidents(id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL, -- 'email', 'github_pr', 'restart', etc.
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    details JSONB,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create monitors table
CREATE TABLE IF NOT EXISTS monitors (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    logs_url TEXT,
    auth_type VARCHAR(20) DEFAULT 'NONE' CHECK (auth_type IN ('NONE', 'BEARER', 'BASIC')),
    status VARCHAR(20) DEFAULT 'UP' CHECK (status IN ('UP', 'DOWN', 'UNKNOWN')),
    uptime_pct DECIMAL(5,2) DEFAULT 100.0,
    latency_ms INTEGER DEFAULT 0,
    last_check TIMESTAMP WITH TIME ZONE,
    notifications JSONB DEFAULT '[]'::jsonb,
    workflows JSONB DEFAULT '[]'::jsonb,
    github_repo TEXT,
    github_token TEXT,
    github_branch VARCHAR(255) DEFAULT 'main',
    log_tail_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_anomaly_at TIMESTAMP WITH TIME ZONE,
    agent_run_status VARCHAR(50)
);

-- Create agent_runs table for tracking automated RCA/remediation
CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    monitor_id VARCHAR(50) REFERENCES monitors(id) ON DELETE CASCADE,
    trace_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'QUEUED' CHECK (status IN ('QUEUED', 'RUNNING', 'ANALYZING', 'PR_CREATED', 'FAILED', 'COMPLETED')),
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    github_repo TEXT,
    github_pr_url TEXT,
    github_pr_number INTEGER,
    log_snapshot JSONB,
    anomalies JSONB,
    rca_summary TEXT,
    rca_md TEXT,
    claude_output TEXT,
    error_message TEXT
);

-- Create monitor_history table for uptime/latency tracking
CREATE TABLE IF NOT EXISTS monitor_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    monitor_id VARCHAR(50) REFERENCES monitors(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL,
    latency_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create monitor_log_entries table for storing tailed logs
CREATE TABLE IF NOT EXISTS monitor_log_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    monitor_id VARCHAR(50) REFERENCES monitors(id) ON DELETE CASCADE,
    log_level VARCHAR(20),
    message TEXT,
    raw JSONB,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    anomaly_score DECIMAL(3,2),
    is_anomaly BOOLEAN DEFAULT false
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_incidents_trace_id ON incidents(trace_id);
CREATE INDEX IF NOT EXISTS idx_incidents_timestamp ON incidents(timestamp);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incident_logs_incident_id ON incident_logs(incident_id);
CREATE INDEX IF NOT EXISTS idx_incident_logs_timestamp ON incident_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_remediation_actions_incident_id ON remediation_actions(incident_id);
CREATE INDEX IF NOT EXISTS idx_monitors_created_at ON monitors(created_at);

-- Settings table for global configuration
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_monitor_history_monitor_id ON monitor_history(monitor_id);
CREATE INDEX IF NOT EXISTS idx_monitor_history_created_at ON monitor_history(created_at);
CREATE INDEX IF NOT EXISTS idx_monitor_log_entries_monitor_id ON monitor_log_entries(monitor_id);
CREATE INDEX IF NOT EXISTS idx_monitor_log_entries_fetched_at ON monitor_log_entries(fetched_at);
CREATE INDEX IF NOT EXISTS idx_agent_runs_monitor_id ON agent_runs(monitor_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_triggered_at ON agent_runs(triggered_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for incidents table
CREATE TRIGGER update_incidents_updated_at 
    BEFORE UPDATE ON incidents 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data (optional)
INSERT INTO incidents (trace_id, timestamp, classification, root_cause, blast_radius, impact, confidence_score)
VALUES 
    ('sample-trace-001', NOW(), 'NullPointerException', 'Null pointer in PaymentService', 'MEDIUM', 'Payment processing failed for 3 users', 0.85)
ON CONFLICT (trace_id) DO NOTHING;
