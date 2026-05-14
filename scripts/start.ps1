# ClaudeOS Startup Script — Windows PowerShell
# Usage: .\scripts\start.ps1

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "  ClaudeOS v1.0.0 — Starting..." -ForegroundColor Green
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
        $pid = $parts[-1]
        if ($pid -match "^\d+$" -and $pid -ne "0") {
            taskkill /F /PID $pid 2>$null | Out-Null
        }
    }
}

Start-Sleep 1

# Run migrations
Write-Host "Running migrations..." -ForegroundColor Cyan
Set-Location $ROOT
python scripts\migrate.py
if ($LASTEXITCODE -ne 0) { Write-Host "Migration failed." -ForegroundColor Red; exit 1 }

# Start Flask API via waitress in background
Write-Host "Starting API on :$FLASK_PORT ..." -ForegroundColor Cyan
$apiJob = Start-Job -ScriptBlock {
    param($root, $port)
    Set-Location $root
    python -c "from waitress import serve; from core.api.app import create_app; serve(create_app(), host='0.0.0.0', port=$port)"
} -ArgumentList $ROOT, $FLASK_PORT

Start-Sleep 3

# Verify API health
try {
    $health = Invoke-RestMethod -Uri "http://localhost:$FLASK_PORT/api/v1/health" -TimeoutSec 5
    if ($health.status -eq "ok") {
        Write-Host "  API: RUNNING on :$FLASK_PORT  (v$($health.version))" -ForegroundColor Green
    } else {
        Write-Host "  API: unexpected response" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  API: FAILED to start — check logs/api.log" -ForegroundColor Red
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
