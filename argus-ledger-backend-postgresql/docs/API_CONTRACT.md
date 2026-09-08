# Decision Object Contract

## `GET /decisions/{id}` — nested decision object

What the frontend renders and what `app/services.py::to_decision_response`
produces from stored rows.

```json
{
  "decision_id": "d2958547-abeb-4ec8-a5cd-7d694c5c42a1",
  "decision": "APPROVED",
  "confidence": 0.91,
  "status": "COMPLETED",
  "reasons": ["Eligibility satisfied", "Risk below threshold"],
  "evidence": [
    { "source": "policy.pdf", "page": 4, "content": "...", "relevance": 0.96, "reason": "Eligibility requirement" }
  ],
  "model": { "name": "Model-A", "version": "1.2" },
  "policy": { "name": "Policy-01", "version": "3.1" },
  "resource": { "latency_ms": 720, "tokens": 1820, "energy_wh": 0.02, "carbon_g": 0.01 },
  "human_review": { "required": false, "reviewer": null },
  "timestamp": "2026-09-07T18:15:00+00:00"
}
```

> `decision_id` is a **UUID string**. The `ARG-001` used in early drafts is
> illustrative only — do not build prefix parsing against it.
> `policy` and `resource` are `null` when absent.

## `POST /decisions` — persist a decision produced elsewhere

Request body (`app/schemas.py::DecisionCreate`):

```json
{
  "input_text": "Customer application: eligibility satisfied; risk below threshold.",
  "decision": "APPROVED",
  "confidence": 0.91,
  "reasons": ["Eligibility satisfied", "Risk below threshold"],
  "evidence": [
    { "source": "policy.pdf", "page": 4, "content": "...", "relevance": 0.96, "reason": "Eligibility requirement" }
  ],
  "model": "Model-A",
  "model_version": "1.2",
  "policy_name": "Policy-01",
  "policy_version": "3.1",
  "human_review_required": false,
  "resource": { "latency_ms": 720, "tokens": 1820, "energy_wh": 0.02, "carbon_g": 0.01 }
}
```

Response: `201 { "decision_id": "<uuid>", "status": "created" }`.
`human_review_required` is forced `true` when
`confidence <= HUMAN_REVIEW_CONFIDENCE_THRESHOLD` (default 0.7), and a
`DECISION_CREATED` audit event is written.

## `POST /decisions/generate` — AI provider then persist

Request: `{ "input_text": "...", "policy_name": null, "policy_version": null }`.
Runs `app/ai_service.py::get_ai_provider()`, persists the result and returns the
**nested decision object** above (`201`). Writes `DECISION_CREATED` +
`AI_GENERATED` audit events. Provider exceptions surface as `502`.

## `GET /decisions` — list

Array of flat summaries, newest first. Query params: `limit` (1–200, default 50),
`offset`. Fields: `decision_id`, `decision`, `confidence`, `status`, `model`,
`model_version`, `human_review_required`, `created_at`.

## `POST /decisions/{id}/review` — human override

Request: `{ "reviewer": "analyst.jordan", "decision": "APPROVED", "reason": "..." }`.
Sets the new decision, records `human_reviewer`, clears the review flag, sets
`status = "REVIEWED"`, writes a `HUMAN_REVIEW` audit event carrying
`previous_decision` / `new_decision` / `reason`.
Response: `200 { "decision_id": "<uuid>", "status": "reviewed" }`.

## `GET /decisions/{id}/audit` · `GET /decisions/{id}/evidence`

Arrays ordered by `created_at`. Audit events:
`{ id, decision_id, event, actor, details, created_at }`.

## `GET /dashboard`

```json
{
  "total_decisions": 42,
  "high_risk_decisions": 7,
  "pending_human_review": 3,
  "average_trust_score": 0.83,
  "decisions_by_outcome": { "APPROVED": 30, "REJECTED": 12 }
}
```

---

Frontend asks for this JSON · Backend stores it · AI produces the flat form ·
Integration connects the pieces.
