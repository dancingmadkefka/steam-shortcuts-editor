@echo off
REM Build script for creating Windows executable with PyInstaller

echo ========================================
echo Steam Shortcuts Editor - Build Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.6+ from https://www.python.org/
    pause
    exit /b 1
)

REM Setup virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies including PyInstaller
echo.
echo Installing dependencies...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt
pip install pyinstaller

if errorlevel 1 (
    echo Error: Failed to install dependencies.
    pause
    exit /b 1
)

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

REM Build the executable
echo.
echo Building executable with PyInstaller...
echo This may take a few minutes...
echo.
pyinstaller steam_shortcuts_editor.spec

if errorlevel 1 (
    echo.
    echo Error: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo The executable can be found at:
echo   %CD%\dist\SteamShortcutsEditor.exe
echo.
echo You can distribute this .exe file as a standalone application.
echo.
pause
