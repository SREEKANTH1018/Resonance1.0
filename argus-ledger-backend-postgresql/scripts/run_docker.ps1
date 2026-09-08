<#
    Bring up the full containerised stack (API + PostgreSQL) and smoke-test it.
    Prerequisite: Docker Desktop installed and RUNNING (whale icon steady).

    Usage:  ./scripts/run_docker.ps1            # build, up -d, wait, smoke test
            ./scripts/run_docker.ps1 -Down      # tear the stack down (-v)
            ./scripts/run_docker.ps1 -Foreground
#>
[CmdletBinding()]
param(
    [switch]$Down,
    [switch]$Foreground,
    [int]$TimeoutSec = 240
)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Resolve-Docker {
    $c = Get-Command docker -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    $p = "$env:ProgramFiles\Docker\Docker\resources\bin\docker.exe"
    if (Test-Path $p) { return $p }
    throw "docker CLI not found. Install Docker Desktop, then open a NEW terminal."
}
$docker = Resolve-Docker

# Run docker without native stderr aborting the script (PS 5.1 + EAP=Stop quirk).
function Invoke-Docker {
    param([Parameter(ValueFromRemainingArguments)] [string[]]$DockerArgs,
          [switch]$PassThruOutput)
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        if ($PassThruOutput) { $out = & $docker @DockerArgs 2>&1; $out | ForEach-Object { "$_" } }
        else                 { & $docker @DockerArgs 2>&1 | ForEach-Object { Write-Host $_ } }
    } finally { $ErrorActionPreference = $old }
    return $LASTEXITCODE
}

if ($Down) {
    exit (Invoke-Docker compose down -v)
}

# 1. Engine reachable?
if ((Invoke-Docker info) -ne 0) {
    Write-Host ""
    Write-Host "Docker engine is not responding." -ForegroundColor Red
    Write-Host "Start Docker Desktop and wait until it says 'Engine running', then re-run."
    exit 1
}
$serverOs = (& $docker info --format '{{.OSType}}' 2>$null)
Write-Host "Docker engine OK (OSType: $serverOs)"
if ($serverOs -and $serverOs -ne "linux") {
    Write-Host "Switch Docker Desktop to Linux containers (tray menu) and re-run." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

# 2. Build + start
if ($Foreground) { exit (Invoke-Docker compose up --build) }

if ((Invoke-Docker compose up --build -d) -ne 0) {
    Write-Host "compose up failed (see build output above)." -ForegroundColor Red
    exit 1
}

# 3. Wait for the api container healthcheck
Write-Host "Waiting for the api container to become healthy (max ${TimeoutSec}s)..."
$deadline = (Get-Date).AddSeconds($TimeoutSec)
while ($true) {
    Start-Sleep -Seconds 3
    $state = (& $docker inspect -f '{{.State.Health.Status}}' argus-api 2>$null)
    if (-not $state) { $state = "starting (no container yet)" }
    Write-Host "  api health: $state"
    if ($state -eq "healthy") { break }
    if ((Get-Date) -gt $deadline) {
        Write-Host "`n--- docker compose ps ---";   Invoke-Docker compose ps            | Out-Null
        Write-Host "`n--- api logs (tail 60) ---";   Invoke-Docker compose logs --tail 60 api | Out-Null
        throw "Timed out waiting for the api container to become healthy."
    }
}

# 4. Smoke test through the published port
& (Join-Path $PSScriptRoot "smoke_test.ps1") -BaseUrl "http://localhost:8000"
$rc = $LASTEXITCODE

Write-Host ""
Write-Host "Stack is up.  API docs: http://localhost:8000/docs"
Write-Host "Tear down:      ./scripts/run_docker.ps1 -Down"
exit $rc
