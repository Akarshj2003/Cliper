<#
.SYNOPSIS
ClipViral Local Development Helper Script for Windows PowerShell
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("dev", "backend", "web", "test", "install", "up", "down", "help")]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host ""
    Write-Host "================ ClipViral Dev Helper (Windows) ================" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 install     - Install backend and web dependencies"
    Write-Host "  .\run.ps1 backend     - Run FastAPI backend locally (port 8000)"
    Write-Host "  .\run.ps1 web         - Run Next.js web frontend locally (port 3000)"
    Write-Host "  .\run.ps1 dev         - Run both backend and web in new consoles"
    Write-Host "  .\run.ps1 test        - Run backend test suite"
    Write-Host "  .\run.ps1 up          - Start Postgres & Redis containers (if Docker installed)"
    Write-Host "  .\run.ps1 down        - Stop docker containers"
    Write-Host "=================================================================" -ForegroundColor Cyan
    Write-Host ""
}

switch ($Command) {
    "install" {
        Write-Host "Installing backend dependencies..." -ForegroundColor Green
        cd backend
        python -m pip install -r requirements.txt
        cd ..
        Write-Host "Installing web dependencies..." -ForegroundColor Green
        cd web
        npm install
        cd ..
    }
    "backend" {
        Write-Host "Starting FastAPI backend at http://localhost:8000 ..." -ForegroundColor Green
        cd backend
        python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    }
    "web" {
        Write-Host "Starting Next.js frontend at http://localhost:3000 ..." -ForegroundColor Green
        cd web
        npm run dev
    }
    "dev" {
        Write-Host "Launching Backend and Web dev servers..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd web; npm run dev"
    }
    "test" {
        Write-Host "Running backend tests..." -ForegroundColor Green
        cd backend
        python -m pytest -v
    }
    "up" {
        docker compose up -d postgres redis
    }
    "down" {
        docker compose down
    }
    Default {
        Show-Help
    }
}
