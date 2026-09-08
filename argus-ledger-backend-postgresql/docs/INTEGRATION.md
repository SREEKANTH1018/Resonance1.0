# Integration Guide

How the other three engineers plug into this backend.

## Member 1 — Frontend

- **Base URL (local):** `http://localhost:8000`
- **CORS:** the API echoes `Access-Control-Allow-Origin` for the origins in
  `CORS_ORIGINS` (default `http://localhost:3000`, `http://localhost:5173`).
  Add your dev-server origin there if it differs. Credentials are allowed.
- **Interactive contract:** `http://localhost:8000/docs`, machine-readable at
  `/openapi.json`.
- **IDs are UUID strings.** `docs/API_CONTRACT.md` shows `"ARG-001"` — that is
  illustrative only; real `decision_id` values look like
  `d2958547-abeb-4ec8-a5cd-7d694c5c42a1`. Do not parse or assume a prefix.
- **Two decision shapes:**
  - list rows (`GET /decisions`) are flat summaries — `decision`, `confidence`,
    `status`, `model`, `model_version`, `human_review_required`, `created_at`.
  - the detail view (`GET /decisions/{id}`) is the **nested** object:
    `model: {name, version}`, `policy: {name, version} | null`,
    `resource: {...} | null`, `human_review: {required, reviewer}`.
- **Dashboard** (`GET /dashboard`): `total_decisions`, `high_risk_decisions`,
  `pending_human_review`, `average_trust_score`, `decisions_by_outcome`.
- **Errors:** `404` unknown id · `422` invalid body (FastAPI validation detail)
  · `409` conflict · `502` AI provider failed · `503` database unavailable.

Example — create then read back:

```js
const created = await fetch(`${BASE}/decisions`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload),          // see docs/API_CONTRACT.md
}).then(r => r.json());                    // -> { decision_id, status: "created" }

const decision = await fetch(`${BASE}/decisions/${created.decision_id}`)
  .then(r => r.json());                    // -> nested decision object
```

## Member 3 — AI / Decision engine

- Implement a class with `name: str` and
  `generate(input_text, *, policy_name=None, policy_version=None) -> dict`
  returning the **flat** contract documented at the top of `app/ai_service.py`.
- Register it in `app/ai_service.py::_PROVIDERS`, e.g. `{"rag": RagProvider()}`,
  and set `AI_PROVIDER=rag`.
- Nothing else changes: `app/services.py::persist_ai_decision` maps your flat
  output into `decisions` / `evidence` / `resource_usage` and writes the
  `AI_GENERATED` audit event. `POST /decisions/generate` is the live endpoint.
- Keep it importable without heavy side effects at module load (the factory is
  called per request).

## Member 4 — Integration / Eval / DevOps

- **Config** is all environment variables — see `.env.example`. Nothing reads
  `os.environ` outside `app/config.py`.
- **Health:** `GET /health` returns `{status, service, version, database}` and is
  wired as the Docker `HEALTHCHECK`. `database` is `"ok"` or `"unavailable"`.
- **DB provisioning:** `database/init.sql` is authoritative (mounted into the
  Postgres container). `scripts/setup_db.ps1` does the same for a host install
  plus creates `argus_test`. `database/seed.sql` loads demo rows.
- **Tests:** `python -m pytest` against `TEST_DATABASE_URL`. Each numbered case
  in `docs/TEST_CASES.md` maps to a test function (see that file).
- **Compose:** `docker compose up --build` (or `scripts/run_docker.ps1`, which
  also waits for `healthy` and runs the smoke test). The API waits on the DB
  healthcheck; `.dockerignore` trims the build context.
- **Smoke:** `scripts/smoke_test.ps1 -BaseUrl <url>` runs 14 end-to-end checks
  against a deployed instance.
- **Docker on the dev box:** Docker Desktop was installed 2026-09-07 but WSL2
  needs a reboot before the engine starts; `docker compose` is therefore not yet
  run-verified here. Everything else is verified against local PostgreSQL 17.
