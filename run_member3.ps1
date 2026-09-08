$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.13 -m venv .venv
}

& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r ai_engine\requirements.txt
& ".venv\Scripts\python.exe" -m integration.smoke_test
& ".venv\Scripts\python.exe" -m uvicorn ai_engine.main:app --reload --port 8100
