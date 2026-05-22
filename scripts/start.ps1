# ClaudeOS Startup Script - Windows PowerShell
# Usage: .\scripts\start.ps1

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "  ClaudeOS v1.0.0 - Starting..." -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""

# Load .env to read ports
$FLASK_PORT = 5000
$STREAMLIT_PORT = 8501
$envFile = Join-Path $ROOT ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^FLASK_PORT=(.+)$") { $FLASK_PORT = [int]$Matches[1] }
        if ($_ -match "^STREAMLIT_PORT=(.+)$") { $STREAMLIT_PORT = [int]$Matches[1] }
    }
}

# Kill existing processes on ports
foreach ($port in @($FLASK_PORT, $STREAMLIT_PORT)) {
    $lines = netstat -ano 2>$null | Select-String ":$port\s"
    foreach ($line in $lines) {
        $parts = $line.ToString().Trim() -split "\s+"
        $procId = $parts[-1]
        if ($procId -match "^\d+$" -and $procId -ne "0") {
            try { taskkill /F /PID $procId 2>$null | Out-Null } catch {}
        }
    }
}

Start-Sleep 1

# Migrations run automatically inside Flask create_app() — no separate step needed.

# Start Flask API via waitress in background
Write-Host "Starting API on :$FLASK_PORT ..." -ForegroundColor Cyan
$apiJob = Start-Job -ScriptBlock {
    param($root, $port)
    Set-Location $root
    python scripts\serve_api.py $port
} -ArgumentList $ROOT, $FLASK_PORT

# Wait for API with retries
$apiReady = $false
Start-Sleep 1
for ($i = 1; $i -le 30; $i++) {
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:$FLASK_PORT/api/v1/health" -TimeoutSec 2
        if ($health.status -eq "ok") {
            Write-Host "  API: RUNNING on :$FLASK_PORT  (v$($health.version))" -ForegroundColor Green
            $apiReady = $true
            break
        }
    } catch {}
    Start-Sleep 1
}
if (-not $apiReady) {
    Write-Host "  API: FAILED to start - check logs/api.log" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Starting Dashboard on :$STREAMLIT_PORT ..." -ForegroundColor Cyan
Write-Host "(Press Ctrl+C to stop)" -ForegroundColor DarkGray
Write-Host ""

# Start Streamlit (foreground)
Set-Location $ROOT
$env:CLAUDEOS_DEV_API_KEY = if (Test-Path $envFile) { (Get-Content $envFile | Select-String "CLAUDEOS_DEV_API_KEY=(.+)").Matches.Groups[1].Value } else { "" }
python -m streamlit run dashboard\app.py --server.port $STREAMLIT_PORT --server.headless true
