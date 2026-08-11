@echo off
REM Orion Codex Desktop Launcher
REM Place this file on your Desktop and double-click to launch Orion

title Orion Codex
cd /d "%~dp0"

REM Check if we're in the OrionCodex directory
if exist "backend\cli\main.py" (
    set ORION_DIR=%CD%
) else if exist "..\backend\cli\main.py" (
    set ORION_DIR=%CD%\..
) else (
    REM Try to find Orion Codex in common locations
    for %%D in (
        "%USERPROFILE%\Desktop\OrionCodex"
        "%USERPROFILE%\Documents\OrionCodex"
        "%USERPROFILE%\OrionCodex"
        "%LOCALAPPDATA%\OrionCodex"
        "%PROGRAMFILES%\OrionCodex"
    ) do (
        if exist "%%D\backend\cli\main.py" set ORION_DIR=%%D
    )
)

if not defined ORION_DIR (
    echo Error: Could not find Orion Codex installation.
    echo Please run install.py first or place this launcher in the OrionCodex folder.
    pause
    exit /b 1
)

echo Starting Orion Codex from %ORION_DIR%...
cd /d "%ORION_DIR%"
set BACKEND_PATH=%ORION_DIR%\backend
set PYTHONPATH=%BACKEND_PATH%;%PYTHONPATH%

REM Launch with TUI by default
python -m backend.cli.main --tui

if errorlevel 1 (
    echo.
    echo Orion exited with error. Press any key to close.
    pause >nul
)