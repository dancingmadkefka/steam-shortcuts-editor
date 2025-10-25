# Steam Shortcuts Editor - PowerShell Launcher Script
# Requires PowerShell 5.0 or higher

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "Starting Steam Shortcuts Editor..." -ForegroundColor Cyan

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.6+ from https://www.python.org/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if uv is available (optional fast package manager)
$uvAvailable = $false
try {
    $null = uv --version 2>&1
    $uvAvailable = $true
    Write-Host "UV package manager detected - will use for faster setup" -ForegroundColor Green
} catch {
    Write-Host "UV not found - using standard pip (install UV for faster setup)" -ForegroundColor Yellow
}

# Setup virtual environment if it doesn't exist
if (-not (Test-Path ".venv")) {
    Write-Host "Setting up virtual environment..." -ForegroundColor Cyan

    try {
        if ($uvAvailable) {
            uv venv .venv
        } else {
            python -m venv .venv
        }
        Write-Host "Virtual environment created successfully" -ForegroundColor Green
    } catch {
        Write-Host "Error: Failed to create virtual environment" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Activate virtual environment and install dependencies
Write-Host "Installing/updating dependencies..." -ForegroundColor Cyan

try {
    # Activate virtual environment
    & ".venv\Scripts\Activate.ps1"

    if ($uvAvailable) {
        uv pip install -r requirements.txt
    } else {
        python -m pip install --upgrade pip --quiet
        pip install -r requirements.txt
    }

    Write-Host "Dependencies installed successfully" -ForegroundColor Green
} catch {
    Write-Host "Error: Failed to install dependencies" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Run the application
Write-Host ""
Write-Host "Running Steam Shortcuts Editor..." -ForegroundColor Cyan
Write-Host ""

try {
    python steam_shortcuts_editor.py
} catch {
    Write-Host ""
    Write-Host "Application exited with an error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
