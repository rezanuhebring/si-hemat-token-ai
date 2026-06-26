#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($env:OS -ne 'Windows_NT') {
    Write-Error 'This script is intended for Windows. Use scripts/deploy-stack.sh on Linux.'
    exit 1
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Test-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Wait-ForHttp {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 | Out-Null
            return $true
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }

    return $false
}

function Ensure-Docker {
    if (Test-Command docker) {
        try {
            docker compose version | Out-Null
            return
        }
        catch {
        }
    }

    if (-not (Test-Command winget)) {
        throw 'Docker is not available and winget is not installed. Install Docker Desktop manually, then rerun this script.'
    }

    Write-Host 'Installing Docker Desktop...' -ForegroundColor Yellow
    winget install --id Docker.DockerDesktop -e --accept-package-agreements --accept-source-agreements

    if (-not (Test-Command docker)) {
        throw 'Docker installation finished, but the docker command is still unavailable. Open a new terminal and rerun the script.'
    }

    try {
        docker compose version | Out-Null
    }
    catch {
        throw 'Docker is installed, but the compose plugin is unavailable. Finish Docker Desktop setup and rerun the script.'
    }
}

function Ensure-Ollama {
    try {
        Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 3 | Out-Null
        return
    }
    catch {
    }

    if (-not (Test-Command ollama)) {
        if (-not (Test-Command winget)) {
            throw 'Ollama is not available and winget is not installed. Install Ollama manually, then rerun this script.'
        }

        Write-Host 'Installing Ollama...' -ForegroundColor Yellow
        winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements

        if (-not (Test-Command ollama)) {
            throw 'Ollama installation finished, but the ollama command is still unavailable. Open a new terminal and rerun the script.'
        }
    }

    Write-Host 'Starting Ollama locally...' -ForegroundColor Yellow
    Start-Process -FilePath 'ollama' -ArgumentList 'serve' -WindowStyle Hidden | Out-Null

    if (-not (Wait-ForHttp -Url 'http://localhost:11434/api/tags' -TimeoutSeconds 90)) {
        throw 'Ollama did not become ready on http://localhost:11434. Start Ollama manually, then rerun the script.'
    }
}

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
}

Ensure-Docker
Ensure-Ollama

$env:OLLAMA_BASE_URL = 'http://host.docker.internal:11434'

Write-Host 'Deploying Windows stack against local Ollama...' -ForegroundColor Cyan
docker compose up -d --build
docker compose ps