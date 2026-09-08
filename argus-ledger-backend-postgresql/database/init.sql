CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ARGUS Ledger core tables.
-- JSONB is used for flexible AI reasons/details while important query fields
-- remain normal PostgreSQL columns.

CREATE TABLE IF NOT EXISTS decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    input_text TEXT NOT NULL,
    decision VARCHAR(50) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    model VARCHAR(255) NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'COMPLETED',
    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    policy_name VARCHAR(255),
    policy_version VARCHAR(100),
    human_review_required BOOLEAN NOT NULL DEFAULT FALSE,
    human_reviewer VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id UUID NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    source VARCHAR(500) NOT NULL,
    page INTEGER,
    content TEXT,
    relevance DOUBLE PRECISION CHECK (relevance IS NULL OR (relevance >= 0 AND relevance <= 1)),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id UUID NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    event VARCHAR(100) NOT NULL,
    actor VARCHAR(255) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS resource_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id UUID NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    model VARCHAR(255) NOT NULL,
    latency_ms INTEGER,
    tokens INTEGER,
    energy_wh DOUBLE PRECISION,
    carbon_g DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_decision_id ON evidence(decision_id);
CREATE INDEX IF NOT EXISTS idx_audit_decision_id ON audit_events(decision_id);
CREATE INDEX IF NOT EXISTS idx_resource_decision_id ON resource_usage(decision_id);
CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON decisions(created_at);
CREATE INDEX IF NOT EXISTS idx_decisions_decision ON decisions(decision);
CREATE INDEX IF NOT EXISTS idx_decisions_human_review_required
    ON decisions(human_review_required)
    WHERE human_review_required;

-- Keep decisions.updated_at current on every UPDATE. The ORM also sets this via
-- onupdate; the trigger covers raw SQL / psql edits.
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_decisions_updated_at ON decisions;
CREATE TRIGGER trg_decisions_updated_at
    BEFORE UPDATE ON decisions
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();
