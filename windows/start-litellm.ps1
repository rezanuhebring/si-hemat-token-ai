# ==============================
# LiteLLM Safe Starter (Windows)
# ==============================

Write-Host "Starting LiteLLM with safe UTF-8 environment..." -ForegroundColor Green

# Force UTF-8 for Python
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

# Optional: prevent weird Windows encoding issues
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Go to script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Check config exists
if (!(Test-Path "config.yaml")) {
    Write-Host "ERROR: config.yaml not found!" -ForegroundColor Red
    exit 1
}

# Start LiteLLM
while ($true) {
    try {
        Write-Host "Launching LiteLLM server..." -ForegroundColor Cyan

        litellm --config config.yaml --port 4000

        Write-Host "LiteLLM stopped. Restarting in 3 seconds..." -ForegroundColor Yellow
        Start-Sleep -Seconds 3
    }
    catch {
        Write-Host "LiteLLM crashed: $_" -ForegroundColor Red
        Write-Host "Restarting in 5 seconds..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }
}
