<#
    Create the ARGUS role and databases on a locally installed PostgreSQL,
    then load the authoritative schema (and optionally the demo seed).

    Usage:
        ./scripts/setup_db.ps1 -SuperUserPassword 'postgres'
        ./scripts/setup_db.ps1 -SuperUserPassword 'postgres' -Seed

    Requires: a running PostgreSQL server. psql is auto-located under
    C:\Program Files\PostgreSQL\<v>\bin if not already on PATH.
#>
[CmdletBinding()]
param(
    [string]$SuperUser = "postgres",
    [string]$SuperUserPassword = $env:PGPASSWORD,
    [string]$DbHost = "localhost",
    [int]$Port = 5432,
    [string]$AppUser = "argus",
    [string]$AppPassword = "argus_password",
    [string]$AppDb = "argus",
    [string]$TestDb = "argus_test",
    [switch]$Seed
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Find-Psql {
    $cmd = Get-Command psql -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $found = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\psql.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending
    if ($found) { return $found[0].FullName }
    throw "psql not found. Install PostgreSQL or add its bin folder to PATH."
}

$psql = Find-Psql
Write-Host "Using psql: $psql"

if (-not $SuperUserPassword) {
    $sec = Read-Host "Password for PostgreSQL superuser '$SuperUser'" -AsSecureString
    $SuperUserPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
}

# Run psql without letting its stderr NOTICEs abort the script (PS 5.1 quirk).
function Invoke-Psql {
    param([string]$User, [string]$Password, [string]$Database,
          [string[]]$ExtraArgs, [string]$StdinText)
    $env:PGPASSWORD = $Password
    $psqlArgs = @("-h", $DbHost, "-p", $Port, "-U", $User, "-d", $Database,
                  "-v", "ON_ERROR_STOP=1", "--no-psqlrc") + $ExtraArgs
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    if ($StdinText) { $out = $StdinText | & $psql @psqlArgs 2>&1 }
    else            { $out = & $psql @psqlArgs 2>&1 }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $old
    $out | ForEach-Object { Write-Host "  $_" }
    if ($code -ne 0) { throw "psql exited $code (user=$User db=$Database)" }
}

$bootstrap = @"
DO `$`$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$AppUser') THEN
        CREATE ROLE $AppUser LOGIN PASSWORD '$AppPassword';
    END IF;
END
`$`$;
SELECT 'CREATE DATABASE $AppDb OWNER $AppUser'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$AppDb')\gexec
SELECT 'CREATE DATABASE $TestDb OWNER $AppUser'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$TestDb')\gexec
"@

Write-Host "Creating role '$AppUser' and databases '$AppDb', '$TestDb'..."
Invoke-Psql -User $SuperUser -Password $SuperUserPassword -Database "postgres" `
    -ExtraArgs @() -StdinText $bootstrap

# Give the app user ownership of the public schema in each database so it can
# create/own tables (PG 15+ locks down public by default).
foreach ($d in @($AppDb, $TestDb)) {
    Invoke-Psql -User $SuperUser -Password $SuperUserPassword -Database $d -ExtraArgs @(
        "-c", "ALTER SCHEMA public OWNER TO $AppUser",
        "-c", "GRANT ALL ON DATABASE $d TO $AppUser")
}

Write-Host "Loading database/init.sql into '$AppDb' (as $AppUser)..."
Invoke-Psql -User $AppUser -Password $AppPassword -Database $AppDb `
    -ExtraArgs @("-f", (Join-Path $root "database/init.sql"))

# The test database schema is owned by tests/conftest.py (create_all/drop_all),
# so it is intentionally left empty here.

if ($Seed) {
    Write-Host "Loading database/seed.sql into '$AppDb' (as $AppUser)..."
    Invoke-Psql -User $AppUser -Password $AppPassword -Database $AppDb `
        -ExtraArgs @("-f", (Join-Path $root "database/seed.sql"))
}

Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
Write-Host "`nDone. App connection string:"
Write-Host "  postgresql+psycopg://${AppUser}:${AppPassword}@${DbHost}:${Port}/${AppDb}"
