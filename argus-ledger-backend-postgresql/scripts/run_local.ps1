<#
    Run the ARGUS API locally against a locally installed PostgreSQL
    (no Docker). One-time DB setup: ./scripts/setup_db.ps1 -SuperUserPassword ...
#>
[CmdletBinding()]
param(
    [int]$Port = 8000,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Creating virtual environment (.venv)..."
    py -3 -m venv .venv
}

& $python -m pip install --disable-pip-version-check -q -r requirements-dev.txt

# Fail fast with a clear message if the database is unreachable.
& $python -c @"
import sys
from sqlalchemy import create_engine, text
from app.config import get_settings
try:
    create_engine(get_settings().database_url).connect().execute(text('select 1'))
except Exception as exc:
    sys.exit(f'Cannot reach database: {exc}\nRun scripts/setup_db.ps1 first.')
print('Database reachable.')
"@
if ($LASTEXITCODE -ne 0) { exit 1 }

$reload = if ($NoReload) { @() } else { @("--reload") }
& $python -m uvicorn app.main:app --host 0.0.0.0 --port $Port @reload
