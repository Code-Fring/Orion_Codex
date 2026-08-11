<# 
.SYNOPSIS
    Creates a desktop shortcut for Orion Codex
    
.DESCRIPTION
    Run this script as Administrator to create a desktop shortcut that launches Orion Codex TUI.
    
.EXAMPLE
    .\Create_Desktop_Shortcut.ps1
#>

param(
    [string]$OrionPath = "C:\Users\ABHINAV SHANKAR\OneDrive\Desktop\OrionCodex",
    [string]$ShortcutName = "Orion Codex"
)

# Find Orion installation if not specified
if (-not (Test-Path "$OrionPath\backend\cli\main.py")) {
    $possiblePaths = @(
        "$env:USERPROFILE\Desktop\OrionCodex",
        "$env:USERPROFILE\Documents\OrionCodex",
        "$env:USERPROFILE\OrionCodex",
        "$env:LOCALAPPDATA\OrionCodex",
        "$env:PROGRAMFILES\OrionCodex"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path "$path\backend\cli\main.py") {
            $OrionPath = $path
            break
        }
    }
}

if (-not (Test-Path "$OrionPath\backend\cli\main.py")) {
    Write-Error "Could not find Orion Codex at $OrionPath"
    exit 1
}

# Create shortcut
$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = "$Desktop\$ShortcutName.lnk"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoExit -ExecutionPolicy Bypass -File `"$OrionPath\Orion_Codex_Launcher.ps1`""
$Shortcut.WorkingDirectory = $OrionPath
$Shortcut.IconLocation = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$Shortcut.Description = "Orion Codex - Terminal-first AI Coding Agent"
$Shortcut.Save()

Write-Host "Created desktop shortcut: $ShortcutPath" -ForegroundColor Green
Write-Host "You can now double-click 'Orion Codex' on your desktop to launch!" -ForegroundColor Cyan