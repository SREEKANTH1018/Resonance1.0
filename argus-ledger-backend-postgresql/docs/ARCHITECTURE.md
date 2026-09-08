# ARGUS Backend Architecture

```text
FRONTEND
   |  HTTP / JSON  (CORS-allowed origins only)
   v
FASTAPI  app/main.py            composition root: settings, CORS, routers, error handlers
   |
   v
ROUTERS  app/routers/*.py       HTTP shape only — decisions / dashboard / health
   |
   v
SERVICES app/services.py        persistence + business rules (no HTTP, no model code)
   |                     \
   v                      \--> app/ai_service.py   AI provider (Protocol + factory)  [Member 3]
SQLALCHEMY app/models.py                                |
   |                                                    v
   v                                                  MODEL / RAG
POSTGRESQL
   +--> decisions
   +--> evidence
   +--> audit_events
   +--> resource_usage
```

## Layers

| File                  | Responsibility                                                    |
| --------------------- | ---------------------------------------------------------------- |
| `app/config.py`       | All env-driven settings (`get_settings()` singleton).           |
| `app/database.py`     | Engine, `SessionLocal`, `Base`, `get_db` dependency.            |
| `app/models.py`       | ORM tables — mirror `database/init.sql` column-for-column.      |
| `app/schemas.py`      | Pydantic request/response contracts (flat AI vs nested API).    |
| `app/services.py`     | The only place that reads/writes the ledger.                    |
| `app/ai_service.py`   | AI boundary: `AIProvider` Protocol, `StubAIProvider`, factory.  |
| `app/routers/*.py`    | Thin HTTP handlers, one module per resource.                    |
| `app/main.py`         | Wires the above; `lifespan`, CORS, DB error handlers.           |

## Ownership

- **Member 2 (this repo):** API, PostgreSQL schema, ORM, audit ledger,
  persistence/business rules.
- **Member 3:** AI model, document processing, retrieval/RAG, evidence
  generation — behind `app/ai_service.py` only.
- **Member 1:** consumes the REST endpoints; never queries PostgreSQL directly.
- **Member 4:** integration, tests, deployment, end-to-end validation.

## Why the audit ledger lives in the backend

Every decision is recorded independently of the model implementation
(`DECISION_CREATED`, `AI_GENERATED`, `HUMAN_REVIEW`, …). The AI model can be
replaced without rebuilding the database/API layer — the flat contract in
`app/ai_service.py` is the only coupling point.

## Request lifecycle — `POST /decisions/generate`

1. `routers/decisions.py` validates `AIGenerateRequest`.
2. `ai_service.get_ai_provider()` returns the configured provider; `.generate()`
   yields the flat dict (provider errors → `502`).
3. `services.persist_ai_decision()` maps it to `DecisionCreate`, writes the
   decision + evidence + resource_usage + audit events in one transaction.
4. `services.to_decision_response()` reshapes the stored row into the nested
   contract; the router returns it as `201`.
