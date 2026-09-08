#!/usr/bin/env bash
# Run the full stack (API + PostgreSQL) with Docker Compose.
# For a no-Docker local run on Windows use scripts/run_local.ps1 instead.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

docker compose up --build
