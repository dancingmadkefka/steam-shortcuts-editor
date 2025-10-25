@echo off
REM Steam Shortcuts Editor - Windows Launcher Script

echo Starting Steam Shortcuts Editor...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.6+ from https://www.python.org/
    pause
    exit /b 1
)

REM Check if uv is installed (optional)
uv --version >nul 2>&1
set UV_AVAILABLE=%errorlevel%

REM Setup virtual environment if it doesn't exist
if not exist ".venv" (
    echo Setting up virtual environment...
    if %UV_AVAILABLE%==0 (
        echo Using uv for faster setup...
        uv venv .venv
    ) else (
        echo Using standard Python venv...
        python -m venv .venv
    )
    if errorlevel 1 (
        echo Error: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM Install dependencies
echo Installing/updating dependencies...
if %UV_AVAILABLE%==0 (
    call .venv\Scripts\activate.bat
    uv pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

if errorlevel 1 (
    echo Error: Failed to install dependencies.
    pause
    exit /b 1
)

REM Run the application
echo.
echo Running Steam Shortcuts Editor...
python steam_shortcuts_editor.py

REM Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
