-- ============================================================
--  Morphic Database Schema  (v2.1)
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
--  incidents
-- ============================================================
CREATE TABLE IF NOT EXISTS incidents (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trace_id         VARCHAR(255) NOT NULL UNIQUE,
    timestamp        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Triage / RCA fields
    title            VARCHAR(255),
    description      TEXT,
    service          VARCHAR(255),
    classification   VARCHAR(255),
    root_cause       TEXT,
    blast_radius     VARCHAR(20) CHECK (blast_radius IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    impact           TEXT,
    confidence_score DECIMAL(4,3) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    summary          TEXT,
    rca_json         JSONB,
    metadata         JSONB,

    -- Lifecycle
    status           VARCHAR(20) DEFAULT 'active',
    -- Note: Supports both legacy 'active/resolved' and modern 'OPEN/RESOLVED' via mapping in routes

    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
--  incident_logs  (raw log timeline per trace)
-- ============================================================
CREATE TABLE IF NOT EXISTS incident_logs (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id  UUID REFERENCES incidents(id) ON DELETE CASCADE,
    timestamp    TIMESTAMP WITH TIME ZONE NOT NULL,
    service      VARCHAR(255),
    endpoint     VARCHAR(512),
    log_level    VARCHAR(20),
    message      TEXT,
    raw_log      JSONB,
    async_orphan BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
--  remediation_actions
-- ============================================================
CREATE TABLE IF NOT EXISTS remediation_actions (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id  UUID REFERENCES incidents(id) ON DELETE CASCADE,
    action_type  VARCHAR(50) NOT NULL,
    status       VARCHAR(20) DEFAULT 'pending'
                     CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    details      JSONB,
    started_at   TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
--  monitors
-- ============================================================
CREATE TABLE IF NOT EXISTS monitors (
    id               VARCHAR(50) PRIMARY KEY,
    name             VARCHAR(255) NOT NULL,
    url              TEXT NOT NULL,
    logs_url         TEXT,
    auth_type        VARCHAR(20) DEFAULT 'NONE' CHECK (auth_type IN ('NONE', 'BEARER', 'BASIC')),
    status           VARCHAR(20) DEFAULT 'UP' CHECK (status IN ('UP', 'DOWN', 'UNKNOWN', 'DEGRADED')),
    uptime_pct       DECIMAL(5,2) DEFAULT 100.0,
    latency_ms       INTEGER DEFAULT 0,
    last_check       TIMESTAMP WITH TIME ZONE,
    notifications    JSONB DEFAULT '[]'::jsonb,
    workflows        JSONB DEFAULT '[]'::jsonb,
    github_repo      TEXT,
    github_token     TEXT,
    github_owner     VARCHAR(255),
    github_branch    VARCHAR(255) DEFAULT 'main',
    log_tail_enabled BOOLEAN DEFAULT true,
    enabled          BOOLEAN DEFAULT true,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_anomaly_at  TIMESTAMP WITH TIME ZONE,
    agent_run_status VARCHAR(50)
);

-- ============================================================
--  monitor_history (uptime/latency tracking)
-- ============================================================
CREATE TABLE IF NOT EXISTS monitor_history (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    monitor_id  VARCHAR(50) REFERENCES monitors(id) ON DELETE CASCADE,
    status      VARCHAR(20) NOT NULL,
    latency_ms  INTEGER DEFAULT 0,
    timestamp   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
--  monitor_log_entries (tailed logs)
-- ============================================================
CREATE TABLE IF NOT EXISTS monitor_log_entries (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    monitor_id    VARCHAR(50) REFERENCES monitors(id) ON DELETE CASCADE,
    log_level     VARCHAR(20),
    message       TEXT,
    raw           JSONB,
    timestamp     TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fetched_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    anomaly_score DECIMAL(3,2),
    is_anomaly    BOOLEAN DEFAULT false
);

-- ============================================================
--  monitor_analysis (LogAI results)
-- ============================================================
CREATE TABLE IF NOT EXISTS monitor_analysis (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    monitor_id      VARCHAR(50) REFERENCES monitors(id) ON DELETE CASCADE,
    analyzed_at     TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    composite_score DECIMAL(4,3),
    semantic_score  DECIMAL(4,3),
    iso_score       DECIMAL(4,3),
    ts_score        DECIMAL(4,3),
    error_rate      DECIMAL(4,3),
    anomaly_detected BOOLEAN DEFAULT FALSE,
    top_patterns    JSONB DEFAULT '[]'::jsonb,
    signals         JSONB DEFAULT '[]'::jsonb,
    metadata        JSONB DEFAULT '{}'::jsonb
);

-- ============================================================
--  agent_runs
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_runs (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    monitor_id       VARCHAR(50) REFERENCES monitors(id) ON DELETE CASCADE,
    trace_id         VARCHAR(255) NOT NULL,
    status           VARCHAR(50) DEFAULT 'QUEUED' CHECK (status IN ('QUEUED', 'RUNNING', 'ANALYZING', 'PR_CREATED', 'FAILED', 'COMPLETED')),
    triggered_at     TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at     TIMESTAMP WITH TIME ZONE,
    github_repo      TEXT,
    github_pr_url    TEXT,
    github_pr_number INTEGER,
    log_snapshot     JSONB,
    anomalies        JSONB,
    rca_summary      TEXT,
    rca_md           TEXT,
    claude_output    TEXT,
    error_message    TEXT,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
--  Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_incidents_trace_id   ON incidents(trace_id);
CREATE INDEX IF NOT EXISTS idx_incidents_timestamp  ON incidents(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_status     ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_blast      ON incidents(blast_radius);
CREATE INDEX IF NOT EXISTS idx_inc_logs_incident_id ON incident_logs(incident_id);
CREATE INDEX IF NOT EXISTS idx_inc_logs_timestamp   ON incident_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_rem_actions_incident ON remediation_actions(incident_id);
CREATE INDEX IF NOT EXISTS idx_monitors_created_at  ON monitors(created_at);
CREATE INDEX IF NOT EXISTS idx_monitor_history_mid  ON monitor_history(monitor_id);
CREATE INDEX IF NOT EXISTS idx_monitor_analysis_mid ON monitor_analysis(monitor_id);
CREATE INDEX IF NOT EXISTS idx_monitor_analysis_at  ON monitor_analysis(analyzed_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_runs_mid       ON agent_runs(monitor_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_trace     ON agent_runs(trace_id);

-- ============================================================
--  updated_at auto-trigger
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

DROP TRIGGER IF EXISTS update_incidents_updated_at ON incidents;
CREATE TRIGGER update_incidents_updated_at
    BEFORE UPDATE ON incidents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
