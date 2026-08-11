<# 
.SYNOPSIS
    Orion Codex Launcher - Starts both backend and frontend
.DESCRIPTION
    Launches the Orion Codex platform with backend (FastAPI) on port 8000
    and frontend (Vite/React) on port 3000.
#>

param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [string]$ProjectRoot = "C:\Users\ABHINAV SHANKAR\OneDrive\Desktop\OrionCodex"
)

Write-Host "===========================================" -ForegroundColor Green
Write-Host "   Orion Codex - Autonomous Software Engineering Platform" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""

# Check prerequisites
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ ERROR: Python not found in PATH" -ForegroundColor Red
    Write-Host "  Please install Python 3.10+ from https://python.org" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

try {
    $nodeVersion = node --version 2>&1
    Write-Host "✓ Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ ERROR: Node.js not found in PATH" -ForegroundColor Red
    Write-Host "  Please install Node.js 18+ from https://nodejs.org" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "Starting backend on port $BackendPort..." -ForegroundColor Yellow

# Start backend
$backendProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c python -m uvicorn backend.main:app --host 0.0.0.0 --port $BackendPort" -WorkingDirectory $ProjectRoot -PassThru -WindowStyle Normal

Write-Host "Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check if backend is running
$backendRunning = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$BackendPort/health" -Method Get -ErrorAction Stop
        if ($response.status -eq "healthy") {
            $backendRunning = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $backendRunning) {
    Write-Host "✗ Backend failed to start" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✓ Backend running at http://localhost:$BackendPort" -ForegroundColor Green

Write-Host ""
Write-Host "Starting frontend on port $FrontendPort..." -ForegroundColor Yellow

# Start frontend
$frontendProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev -- --host 0.0.0.0 --port $FrontendPort" -WorkingDirectory "$ProjectRoot\frontend" -PassThru -WindowStyle Normal

Write-Host "Waiting for frontend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host "   Orion Codex is running!" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:$BackendPort" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:$FrontendPort" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:$BackendPort/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop all services..." -ForegroundColor Yellow
Write-Host ""

# Wait for user to stop
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} catch {
    Write-Host ""
    Write-Host "Stopping all Orion Codex services..." -ForegroundColor Yellow
    
    # Kill processes
    if ($backendProcess) { Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($frontendProcess) { Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue }
    
    # Also kill by window title as backup
    Get-Process | Where-Object { $_.MainWindowTitle -like "Orion Codex*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Write-Host "All services stopped." -ForegroundColor Green
}