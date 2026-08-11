@echo off
REM Orion Codex - Windows batch launcher
REM This file should be placed in a directory in your PATH

@echo off
set BACKEND_PATH=%~dp0backend
set PYTHONPATH=%BACKEND_PATH%;%PYTHONPATH%

REM Check if Python is available
where python >nul 2>nul
if errorlevel 1 (
    echo Error: Python not found in PATH
    echo Please install Python 3.10+ and add it to your PATH
    exit /b 1
)

REM Run the CLI
python -m backend.cli.main %*