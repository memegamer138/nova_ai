<#
.\run_desktop.ps1

Convenience script to run the Nova desktop app (Flask backend + Electron UI).
Usage: run this from the repo root in PowerShell. Requires Node/npm and Python.

What it does:
- creates a virtualenv (if missing) and installs Python deps into it
- starts the Flask server (in a new PowerShell window)
- installs UI node deps (if missing) and launches the Electron app

#>

try {
    $repo = Split-Path -Parent $MyInvocation.MyCommand.Definition
    Set-Location $repo
} catch {
    Write-Error "Failed to determine script location. Run this script from the repo root instead."
    exit 1
}

Write-Host "Repo root: $repo"

# Create venv if needed
if (-not (Test-Path "$repo\.venv")) {
    Write-Host "Creating Python virtualenv..."
    python -m venv .venv
}

$venvPython = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Error "Virtualenv Python not found at $venvPython"
    exit 1
}

Write-Host "Upgrading pip and installing Python requirements..."
& $venvPython -m pip install --upgrade pip | Out-Null
& $venvPython -m pip install -r requirements.txt

# Start server in new PowerShell window so it keeps running
$serverCmd = "Set-Location '$repo\src'; & '$venvPython' -m nova_ai.server"
Write-Host "Starting backend server in a new window..."
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit","-Command",$serverCmd

# Start Electron UI
Set-Location (Join-Path $repo "ui\desktop")
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing UI node modules (this may take a while)..."
    npm install
}

Write-Host "Launching Electron UI..."
npm run start
