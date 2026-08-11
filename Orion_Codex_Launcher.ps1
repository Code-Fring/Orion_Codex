<# 
.SYNOPSIS
    Orion Codex Desktop Launcher for PowerShell
    
.DESCRIPTION
    Place this file on your Desktop and double-click to launch Orion Codex TUI.
    Right-click and "Run with PowerShell" to launch.
#>

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Find Orion Codex installation
$OrionDirs = @(
    $ScriptDir,
    "$ScriptDir\..",
    "$env:USERPROFILE\Desktop\OrionCodex",
    "$env:USERPROFILE\Documents\OrionCodex",
    "$env:USERPROFILE\OrionCodex",
    "$env:LOCALAPPDATA\OrionCodex",
    "$env:PROGRAMFILES\OrionCodex"
)

$OrionDir = $null
foreach ($dir in $OrionDirs) {
    if (Test-Path "$dir\backend\cli\main.py") {
        $OrionDir = $dir
        break
    }
}

if (-not $OrionDir) {
    Write-Error "Could not find Orion Codex installation."
    Write-Host "Please run install.py first or place this launcher in the OrionCodex folder."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Starting Orion Codex from $OrionDir..." -ForegroundColor Green
Set-Location $OrionDir

$env:BACKEND_PATH = "$OrionDir\backend"
$env:PYTHONPATH = "$env:BACKEND_PATH;$env:PYTHONPATH"

# Launch with TUI by default
try {
    python -m backend.cli.main --tui
} catch {
    Write-Error "Error launching Orion: $_"
    Read-Host "Press Enter to exit"
    exit 1
}

Read-Host "Press Enter to close"