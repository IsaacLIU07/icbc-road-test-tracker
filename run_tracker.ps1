# Runs main.py forever, restarting it if it crashes (network blips, ICBC downtime, etc).
# Intended to be run directly, or registered as a Windows Task Scheduler action
# so the tracker survives reboots/logoffs while the PC stays on.

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

while ($true) {
    Write-Host "$(Get-Date) - Starting ICBC tracker..."
    py main.py
    Write-Host "$(Get-Date) - Tracker exited (code $LASTEXITCODE), restarting in 30s..."
    Start-Sleep -Seconds 30
}
