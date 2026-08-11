@echo off
REM Orion Codex CLI entry point for Windows

set BACKEND_PATH=%~dp0backend
set PYTHONPATH=%BACKEND_PATH%;%PYTHONPATH%

python -m backend.cli.main %*