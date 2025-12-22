#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Starts both backend and frontend development servers concurrently.

.DESCRIPTION
    Launches FastAPI backend (uvicorn) and React frontend (npm run dev) in parallel processes.
    Press Ctrl+C to stop both servers.
#>

Write-Host "Starting Student Helper development servers..." -ForegroundColor Green

# Get project root (2 levels up from script location)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)

Write-Host "Project root: $projectRoot" -ForegroundColor Gray

# Find Python executable
try {
    $pythonPath = (Get-Command python -ErrorAction Stop).Source
    Write-Host "Found Python at: $pythonPath" -ForegroundColor Cyan
} catch {
    Write-Host "ERROR: Python not found in PATH. Please install Python and add it to your PATH." -ForegroundColor Red
    exit 1
}

# Find npm executable
try {
    $npmPath = (Get-Command npm -ErrorAction Stop).Source
    Write-Host "Found npm at: $npmPath" -ForegroundColor Cyan
} catch {
    Write-Host "ERROR: npm not found in PATH. Please install Node.js and add it to your PATH." -ForegroundColor Red
    exit 1
}

# Start backend server in a new window
$backendJob = Start-Process pwsh -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$projectRoot'; Write-Host 'Starting Backend Server...' -ForegroundColor Cyan; & '$pythonPath' -m uvicorn backend.api.main:app --reload"
) -PassThru

# Start frontend server in a new window
$frontendJob = Start-Process pwsh -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$projectRoot'; Write-Host 'Starting Frontend Server...' -ForegroundColor Cyan; cd study-buddy-ai; & '$npmPath' run dev"
) -PassThru

Write-Host "`nServers started!" -ForegroundColor Green
Write-Host "Backend: http://localhost:8000" -ForegroundColor Yellow
Write-Host "Frontend: http://localhost:5173 (or port shown in frontend window)" -ForegroundColor Yellow
Write-Host "`nClose the terminal windows to stop the servers." -ForegroundColor Gray
