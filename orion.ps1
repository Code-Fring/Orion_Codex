<# 
.SYNOPSIS
    Orion Codex - Terminal-first AI Coding Agent launcher for PowerShell

.DESCRIPTION
    This script launches the Orion Codex CLI from any directory.
    It sets up the Python path and runs the backend CLI module.

.EXAMPLE
    orion
    orion ask "How do I fix this bug?"
    orion tui
#>

param(
    [string[]]$Arguments = @()
)

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$BackendPath = Join-Path $ScriptDir "backend"

# Add backend to Python path
$env:PYTHONPATH = "$BackendPath;$env:PYTHONPATH"

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    if (-not $pythonVersion) {
        throw "Python not found"
    }
} catch {
    Write-Error "Error: Python not found in PATH"
    Write-Error "Please install Python 3.10+ and add it to your PATH"
    exit 1
}

# Run the CLI
python -m backend.cli.main @Arguments