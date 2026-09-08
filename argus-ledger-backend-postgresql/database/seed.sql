-- ARGUS Ledger — demo seed data.
-- Run ONCE against the `argus` (dev) database after database/init.sql:
--   psql "postgresql://argus:argus_password@localhost:5432/argus" -f database/seed.sql
-- Safe to re-run: it clears the four tables first.

BEGIN;

TRUNCATE resource_usage, audit_events, evidence, decisions RESTART IDENTITY CASCADE;

-- 1) Normal approved decision -------------------------------------------------
WITH d AS (
    INSERT INTO decisions
        (input_text, decision, confidence, model, model_version, status,
         reasons, policy_name, policy_version, human_review_required)
    VALUES
        ('Customer application: eligibility satisfied; risk below threshold.',
         'APPROVED', 0.91, 'Model-A', '1.2', 'COMPLETED',
         '["Eligibility satisfied", "Risk below threshold"]'::jsonb,
         'Policy-01', '3.1', FALSE)
    RETURNING id
)
INSERT INTO evidence (decision_id, source, page, content, relevance, reason)
SELECT id, 'policy.pdf', 4, 'Eligibility requirements are satisfied.', 0.96,
       'Eligibility requirement'
FROM d;

INSERT INTO audit_events (decision_id, event, actor, details)
SELECT id, 'DECISION_CREATED', 'backend',
       '{"model": "Model-A", "model_version": "1.2"}'::jsonb
FROM decisions WHERE decision = 'APPROVED';

INSERT INTO resource_usage (decision_id, model, latency_ms, tokens, energy_wh, carbon_g)
SELECT id, 'Model-A', 720, 1820, 0.02, 0.01
FROM decisions WHERE decision = 'APPROVED';

-- 2) Rejected decision ------------------------------------------------------
WITH d AS (
    INSERT INTO decisions
        (input_text, decision, confidence, model, model_version, reasons,
         policy_name, policy_version, human_review_required)
    VALUES
        ('Application flagged: sanction list match detected.',
         'REJECTED', 0.88, 'Model-A', '1.2',
         '["Sanction list match", "Risk above threshold"]'::jsonb,
         'Policy-01', '3.1', FALSE)
    RETURNING id
)
INSERT INTO audit_events (decision_id, event, actor, details)
SELECT id, 'DECISION_CREATED', 'backend',
       '{"model": "Model-A", "model_version": "1.2"}'::jsonb
FROM d;

-- 3) Low-confidence decision auto-flagged for human review -----------------
WITH d AS (
    INSERT INTO decisions
        (input_text, decision, confidence, model, model_version, reasons,
         human_review_required)
    VALUES
        ('Ambiguous application: incomplete documentation.',
         'APPROVED', 0.61, 'Model-A', '1.2',
         '["Partial eligibility", "Documentation incomplete"]'::jsonb,
         TRUE)
    RETURNING id
)
INSERT INTO audit_events (decision_id, event, actor, details)
SELECT id, 'DECISION_CREATED', 'backend',
       '{"confidence": 0.61, "auto_review_flagged": true}'::jsonb
FROM d;

-- 4) Decision that has already been human-reviewed -----------------------
WITH d AS (
    INSERT INTO decisions
        (input_text, decision, confidence, model, model_version, status,
         reasons, human_review_required, human_reviewer)
    VALUES
        ('Escalated application: manual override requested.',
         'APPROVED', 0.55, 'Model-A', '1.2', 'REVIEWED',
         '["Overridden after manual review"]'::jsonb, FALSE, 'analyst.jordan')
    RETURNING id
)
INSERT INTO audit_events (decision_id, event, actor, details)
SELECT id, 'HUMAN_REVIEW', 'analyst.jordan',
       '{"previous_decision": "REJECTED", "new_decision": "APPROVED", "reason": "Additional documents provided"}'::jsonb
FROM d;

-- 5) Decision produced by the AI provider ------------------------------
WITH d AS (
    INSERT INTO decisions
        (input_text, decision, confidence, model, model_version, reasons)
    VALUES
        ('New applicant: standard onboarding request.',
         'APPROVED', 0.82, 'ARGUS-Stub', '0.1.0',
         '["Eligibility criteria satisfied", "Risk below threshold"]'::jsonb)
    RETURNING id
)
INSERT INTO audit_events (decision_id, event, actor, details)
SELECT id, 'AI_GENERATED', 'ai:ARGUS-Stub', '{"model_version": "0.1.0"}'::jsonb
FROM d;

COMMIT;
