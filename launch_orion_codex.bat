@echo off
title Orion Codex Launcher
color 0A

echo =============================================
echo   Orion Codex - Autonomous Software Engineering Platform
echo =============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Check if Node.js is available
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found in PATH
    echo Please install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)

echo Starting backend on port 8000...
start "Orion Codex Backend" cmd /c "cd /d "%~dp0" && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

echo Starting frontend on port 3000...
start "Orion Codex Frontend" cmd /c "cd /d "%~dp0\frontend" && npm run dev -- --host 0.0.0.0 --port 3000"

echo.
echo =============================================
echo   Orion Codex is starting up!
echo =============================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to stop all services and exit...
echo.

pause

echo.
echo Stopping all Orion Codex services...
taskkill /f /fi "WINDOWTITLE eq Orion Codex Backend*" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Orion Codex Frontend*" >nul 2>&1
echo All services stopped.
timeout /t 2 /nobreak >nul