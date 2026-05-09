-- ============================================================
--  Morphic Database Schema  (v2)
--  Runs automatically when the PostgreSQL container starts via
--  the Docker volume mount in docker-compose.yml
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
    timestamp        TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Triage / RCA fields
    service          VARCHAR(255),
    classification   VARCHAR(255),
    root_cause       TEXT,
    blast_radius     VARCHAR(20) CHECK (blast_radius IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    impact           TEXT,
    confidence_score DECIMAL(4,3) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    summary          TEXT,
    rca_json         JSONB,

    -- Lifecycle
    status           VARCHAR(20) DEFAULT 'active'
                         CHECK (status IN ('active', 'resolved', 'investigating', 'healed')),

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
    action_type  VARCHAR(50) NOT NULL,  -- 'email', 'github_pr', 'runtime_fix'
    status       VARCHAR(20) DEFAULT 'pending'
                     CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    details      JSONB,
    started_at   TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
--  Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_incidents_trace_id   ON incidents(trace_id);
CREATE INDEX IF NOT EXISTS idx_incidents_timestamp  ON incidents(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_status     ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_blast      ON incidents(blast_radius);
CREATE INDEX IF NOT EXISTS idx_incidents_service    ON incidents(service);

CREATE INDEX IF NOT EXISTS idx_inc_logs_incident_id ON incident_logs(incident_id);
CREATE INDEX IF NOT EXISTS idx_inc_logs_timestamp   ON incident_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_inc_logs_orphan      ON incident_logs(async_orphan) WHERE async_orphan = TRUE;

CREATE INDEX IF NOT EXISTS idx_rem_actions_incident ON remediation_actions(incident_id);
CREATE INDEX IF NOT EXISTS idx_rem_actions_type     ON remediation_actions(action_type);
CREATE INDEX IF NOT EXISTS idx_rem_actions_status   ON remediation_actions(status);

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

-- ============================================================
--  Seed data (idempotent)
-- ============================================================
INSERT INTO incidents (
    trace_id, timestamp, service, classification, root_cause,
    blast_radius, impact, confidence_score, summary, status
)
VALUES (
    'sample-trace-001',
    NOW(),
    'payment-service',
    'NullPointerException',
    'Null pointer dereference in PaymentService.processPayment() when orderId is missing.',
    'MEDIUM',
    'Payment processing failed for approximately 3 users during the 14:00 UTC window.',
    0.850,
    'NullPointerException in PaymentService',
    'active'
)
ON CONFLICT (trace_id) DO NOTHING;
