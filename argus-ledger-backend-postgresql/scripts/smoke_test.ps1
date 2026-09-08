<#
    End-to-end smoke test against a RUNNING ARGUS API.
    Start the server first (scripts/run_local.ps1), then:  ./scripts/smoke_test.ps1
#>
[CmdletBinding()]
param([string]$BaseUrl = "http://localhost:8000")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pass = 0
$fail = 0

function Check($name, $condition) {
    if ($condition) { Write-Host "  PASS  $name" -ForegroundColor Green; $script:pass++ }
    else            { Write-Host "  FAIL  $name" -ForegroundColor Red;   $script:fail++ }
}

Write-Host "ARGUS smoke test -> $BaseUrl`n"

# 1. Health
$health = Invoke-RestMethod "$BaseUrl/health"
Check "health status ok"        ($health.status -eq "ok")
Check "health db ok"            ($health.database -eq "ok")

# 2. Create a decision from the sample payload
$payload = Get-Content (Join-Path $root "scripts/sample_request.json") -Raw
$created = Invoke-RestMethod "$BaseUrl/decisions" -Method Post -ContentType "application/json" -Body $payload
$id = $created.decision_id
Check "create returns decision_id" ([bool]$id)

# 3. Read it back in the nested contract shape
$got = Invoke-RestMethod "$BaseUrl/decisions/$id"
Check "get decision matches"    ($got.decision -eq "APPROVED")
Check "nested model shape"      ($got.model.name -eq "Model-A" -and $got.model.version -eq "1.2")
Check "nested policy shape"     ($got.policy.name -eq "Policy-01")
Check "resource persisted"      ($got.resource.tokens -eq 1820)

# 4. Audit + evidence
$audit = Invoke-RestMethod "$BaseUrl/decisions/$id/audit"
Check "audit has DECISION_CREATED" ($audit[0].event -eq "DECISION_CREATED")
$evidence = Invoke-RestMethod "$BaseUrl/decisions/$id/evidence"
Check "evidence returned"       ($evidence.Count -ge 1)

# 5. Human review
$review = @{ reviewer = "smoke.bot"; decision = "REJECTED"; reason = "smoke test override" } | ConvertTo-Json
Invoke-RestMethod "$BaseUrl/decisions/$id/review" -Method Post -ContentType "application/json" -Body $review | Out-Null
$after = Invoke-RestMethod "$BaseUrl/decisions/$id"
Check "review changed decision" ($after.decision -eq "REJECTED")
Check "review recorded reviewer" ($after.human_review.reviewer -eq "smoke.bot")

# 6. AI generate path
$gen = Invoke-RestMethod "$BaseUrl/decisions/generate" -Method Post -ContentType "application/json" `
    -Body (Get-Content (Join-Path $root "scripts/sample_generate.json") -Raw)
Check "generate returns decision" ($gen.decision -in @("APPROVED", "REJECTED"))

# 7. Dashboard
$dash = Invoke-RestMethod "$BaseUrl/dashboard"
Check "dashboard total >= 2"    ($dash.total_decisions -ge 2)

# 8. CORS preflight for the frontend origin
$resp = Invoke-WebRequest "$BaseUrl/decisions" -Method Options -UseBasicParsing -Headers @{
    "Origin" = "http://localhost:5173"
    "Access-Control-Request-Method" = "POST"
}
Check "CORS allow-origin echoed" ($resp.Headers["Access-Control-Allow-Origin"] -eq "http://localhost:5173")

Write-Host "`n$pass passed, $fail failed"
if ($fail -gt 0) { exit 1 }
