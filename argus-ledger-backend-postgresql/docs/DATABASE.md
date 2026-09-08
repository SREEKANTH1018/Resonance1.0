# PostgreSQL Database

`database/init.sql` is the **authoritative schema**. `app/models.py` mirrors it
column-for-column; `Base.metadata.create_all` runs on API startup only as a
local-dev convenience and is a no-op against an initialised database.

## Databases

| Name         | Purpose                          | Schema owner                         |
| ------------ | -------------------------------- | ------------------------------------ |
| `argus`      | dev / Docker / production        | `database/init.sql`                  |
| `argus_test` | pytest (`TEST_DATABASE_URL`)     | `tests/conftest.py` (create/drop)    |

`scripts/setup_db.ps1` creates the `argus` role (owns `public` in both DBs so it
can create tables), loads `init.sql` into `argus`, and with `-Seed` loads
`database/seed.sql`.

## Tables

### decisions
Primary AI decision: `decision`, `confidence`, `model`/`model_version`,
`status`, `reasons` (JSONB), optional `policy_name`/`policy_version`,
`human_review_required`, `human_reviewer`, `created_at`, `updated_at`.
`CHECK (confidence BETWEEN 0 AND 1)`. `updated_at` is kept current by the
`trg_decisions_updated_at` trigger (and the ORM `onupdate`).

### evidence
Sources supporting a decision: `source`, `page`, `content`, `relevance`
(`CHECK 0–1 or NULL`), `reason`. FK → `decisions` `ON DELETE CASCADE`.

### audit_events
Append-only lifecycle log. `event` values in use:
`DECISION_CREATED`, `AI_GENERATED`, `HUMAN_REVIEW`
(reserved for later: `MODEL_REPLAY`, `EVIDENCE_ADDED`). `details` is JSONB.

### resource_usage
Per-decision cost: `latency_ms`, `tokens`, `energy_wh`, `carbon_g`, plus `model`.

## Indexes

FK columns (`idx_evidence_decision_id`, `idx_audit_decision_id`,
`idx_resource_decision_id`), `idx_decisions_created_at`,
`idx_decisions_decision`, and a partial `idx_decisions_human_review_required`
(`WHERE human_review_required`).

## Useful queries

```sql
SELECT * FROM decisions ORDER BY created_at DESC;

SELECT event, actor, details, created_at
FROM audit_events WHERE decision_id = '<UUID>' ORDER BY created_at;

SELECT * FROM evidence WHERE decision_id = '<UUID>';

SELECT decision, COUNT(*), ROUND(AVG(confidence)::numeric, 3)
FROM decisions GROUP BY decision;
```
