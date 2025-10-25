# Build script for creating Windows executable with PyInstaller

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Steam Shortcuts Editor - Build Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

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

# Setup virtual environment if it doesn't exist
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    try {
        python -m venv .venv
        Write-Host "Virtual environment created successfully" -ForegroundColor Green
    } catch {
        Write-Host "Error: Failed to create virtual environment" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& ".venv\Scripts\Activate.ps1"

# Install dependencies including PyInstaller
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Cyan
try {
    python -m pip install --upgrade pip --quiet
    pip install -r requirements.txt
    pip install pyinstaller
    Write-Host "Dependencies installed successfully" -ForegroundColor Green
} catch {
    Write-Host "Error: Failed to install dependencies" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Clean previous builds
Write-Host ""
Write-Host "Cleaning previous builds..." -ForegroundColor Cyan
if (Test-Path "dist") {
    Remove-Item -Path "dist" -Recurse -Force
}
if (Test-Path "build") {
    Remove-Item -Path "build" -Recurse -Force
}

# Build the executable
Write-Host ""
Write-Host "Building executable with PyInstaller..." -ForegroundColor Cyan
Write-Host "This may take a few minutes..." -ForegroundColor Yellow
Write-Host ""

try {
    pyinstaller steam_shortcuts_editor.spec

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Build completed successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "The executable can be found at:" -ForegroundColor Cyan
    $exePath = Join-Path $PSScriptRoot "dist\SteamShortcutsEditor.exe"
    Write-Host "  $exePath" -ForegroundColor White
    Write-Host ""
    Write-Host "You can distribute this .exe file as a standalone application." -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "Error: Build failed!" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Read-Host "Press Enter to exit"
