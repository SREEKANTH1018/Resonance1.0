# Backend Engineer Handoff

## Status

| Area                                   | State |
| -------------------------------------- | ----- |
| FastAPI app (routers/services/config)  | done  |
| PostgreSQL schema + trigger + indexes  | done  |
| SQLAlchemy models (parity with SQL)    | done  |
| Pydantic request + response contracts  | done  |
| `POST /decisions`                      | done  |
| `POST /decisions/generate` (AI wired)  | done  |
| `GET /decisions` (list, paged)         | done  |
| `GET /decisions/{id}` (nested shape)   | done  |
| `GET /decisions/{id}/audit`            | done  |
| `GET /decisions/{id}/evidence`         | done  |
| `GET /dashboard`                       | done  |
| `POST /decisions/{id}/review`          | done  |
| `/health` + CORS + error handlers      | done  |
| AI boundary (Protocol + factory stub)  | done  |
| pytest suite (29 tests, real Postgres) | done  |
| Docker Compose + healthcheck           | done  |
| Seed data (`database/seed.sql`)        | done  |

Verified locally against PostgreSQL 17: `pytest` (29 passed) and
`scripts/smoke_test.ps1` (14 checks) both green.

Docker path is **installed but not yet run-verified** on the dev box:
Docker Desktop 4.89.0 + `wsl --install` were installed 2026-09-07, but Windows
has a **reboot pending** and WSL2 will not start until then. After a reboot:

1. Launch **Docker Desktop**, accept the licence, wait for "Engine running".
2. `./scripts/run_docker.ps1`  — builds the image, waits for the `api` container
   to report healthy, runs the 14-check smoke test.
3. If the image build fails, the likely cause is a `requirements.txt` pin without
   a `cp313` wheel on `python:3.13-slim` — loosen that pin or bump the base tag.

`Dockerfile`, `docker-compose.yml`, `.dockerignore` are complete.

## How to run locally (no Docker)

```powershell
winget install -e --id PostgreSQL.PostgreSQL.17      # superuser pw: postgres
./scripts/setup_db.ps1 -SuperUserPassword "postgres" -Seed
./scripts/run_local.ps1                               # http://localhost:8000/docs
./scripts/smoke_test.ps1                              # in a second terminal
```

## Next integration steps

1. **Member 3** adds a real provider in `app/ai_service.py::_PROVIDERS` and sets
   `AI_PROVIDER`. The flat return contract is documented at the top of that file;
   keep it unchanged. Nothing in `main.py` / `services.py` / models changes.
2. **Member 1** consumes the REST endpoints — see `docs/INTEGRATION.md`. IDs are
   UUID strings (the `ARG-001` in `API_CONTRACT.md` is illustrative).
3. **Member 4** runs `pytest`, the Docker stack, and `smoke_test.ps1` against the
   deployed URL; wires `/health` into orchestration.
4. Add replay/versioning (`MODEL_REPLAY` audit event is reserved) after the MVP
   pipeline is stable.

## Rules

- No model-generation logic inside routers, `services.py`, or the database layer.
- No `os.getenv` outside `app/config.py`.
- `database/init.sql` is authoritative; keep `app/models.py` in lock-step
  (column-by-column) with it.
