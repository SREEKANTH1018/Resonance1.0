# ARGUS Ledger — Backend + PostgreSQL

Backend and database slice of **PS19 ARGUS Ledger**. It owns the audit ledger:
it persists every AI decision, its evidence, its resource cost and an append-only
event history, and serves that back to the frontend over REST.

## Stack

FastAPI · PostgreSQL 16/17 · SQLAlchemy 2 · Pydantic v2 · Docker Compose

## Architecture

```
FRONTEND ──HTTP/JSON──▶ FASTAPI (routers ─▶ services ─▶ SQLAlchemy) ──▶ POSTGRESQL
                             │
                             └─▶ app/ai_service.py  (AI provider — Member 3)
```

Model generation never touches the persistence layer. It lives behind
`app/ai_service.py::get_ai_provider`, the single swap point for Member 3.

## Run it — local, no Docker (Windows / PowerShell)

Requires a local PostgreSQL server. Install one with
`winget install -e --id PostgreSQL.PostgreSQL.17` (superuser password `postgres`
by default), then:

```powershell
# 1. one-time: create the argus role + argus / argus_test databases, load schema + demo data
./scripts/setup_db.ps1 -SuperUserPassword "postgres" -Seed

# 2. install deps + run the API (creates .env and .venv if missing)
./scripts/run_local.ps1

# 3. in another terminal: end-to-end check against the running server
./scripts/smoke_test.ps1
```

API docs: <http://localhost:8000/docs>

## Run it — Docker

Needs Docker Desktop installed and **running**.

```powershell
./scripts/run_docker.ps1            # build, start detached, wait for healthy, smoke test
./scripts/run_docker.ps1 -Down      # tear down (removes volumes)
```

or plain:

```bash
cp .env.example .env
docker compose up --build
```

`database/init.sql` is mounted into the Postgres container (which creates the
`argus` role/DB from `POSTGRES_*`) and is the authoritative schema. The API
waits for the DB healthcheck before starting. `.dockerignore` keeps `.venv/` and
friends out of the build context.

## Tests

```powershell
.venv\Scripts\python -m pytest
```

Runs against the real `argus_test` database (`TEST_DATABASE_URL`); the ORM uses
PostgreSQL-specific types, so there is no SQLite mode. Each test runs in a
rolled-back transaction. 27 tests cover the contract, decision lifecycle, human
review, dashboard, AI-generate path and failure cases from `docs/TEST_CASES.md`.

## API

| Method | Path                          | Purpose                                        |
| ------ | ----------------------------- | ---------------------------------------------- |
| GET    | `/health`                     | Liveness + DB reachability                     |
| POST   | `/decisions`                  | Persist a decision produced elsewhere          |
| POST   | `/decisions/generate`         | Run the configured AI provider, then persist   |
| GET    | `/decisions`                  | List decision summaries (newest first, paged)  |
| GET    | `/decisions/{id}`             | Full decision in the nested contract shape     |
| GET    | `/decisions/{id}/audit`       | Append-only event history                      |
| GET    | `/decisions/{id}/evidence`    | Supporting evidence rows                       |
| GET    | `/dashboard`                  | Aggregate metrics for the frontend             |
| POST   | `/decisions/{id}/review`      | Record a human override                        |

See `docs/API_CONTRACT.md` for payloads and `docs/INTEGRATION.md` for the
frontend / DevOps hand-off.
