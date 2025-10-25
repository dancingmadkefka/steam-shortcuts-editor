# 🎮 Steam Shortcuts Editor

A cross-platform GUI application to view and edit Steam shortcuts (non-Steam games/applications) with excellent Windows support.

> **Fork Information:** This is an enhanced fork of [DragRedSim/steam-shortcuts-editor](https://github.com/DragRedSim/steam-shortcuts-editor) with additional features developed with [Claude Code](https://claude.ai/code).

## What's New in This Fork

This fork adds robust backup and corruption detection features:

- 🛡️ **Automatic Corruption Detection** - Detects corrupted VDF files on load
  - File size validation (catches truncated files)
  - VDF structure validation
  - Comparison against backup file sizes
- 🔄 **Backup Restoration** - Easy restoration from backups
  - Interactive backup browser with validation status
  - Automatic restoration offers when corruption is detected
  - Preview backup details (timestamp, size, shortcut count)
- 💾 **Enhanced Backup Management** - Improved backup system
  - Validates all backups before restoration
  - Color-coded backup status (valid/corrupted)
  - Preserves corrupted files with timestamp before restoration

## Overview

This tool allows you to:
- View all your Steam shortcuts in a single interface
- Edit shortcut properties (name, executable path, icons, etc.)
- Delete unwanted shortcut entries
- Sort shortcuts by name or file order
- **Automatic backups** before saving changes
- Save changes directly to Steam's shortcuts.vdf file
- Automatically locate your Steam shortcuts file using Windows Registry (Windows) or standard paths (Linux/macOS)

## Quick Start (Windows)

### Option 1: Run from Source (Recommended for Development)

1. **Double-click `run.bat`** (or `run.ps1` for PowerShell users)
   - The script will automatically set up everything and launch the app!

That's it! The launcher script will:
- Check for Python installation
- Create a virtual environment
- Install required dependencies
- Launch the application

### Option 2: Build Standalone Executable

Create a standalone `.exe` file that doesn't require Python:

1. **Double-click `build_exe.bat`** (or `build_exe.ps1` for PowerShell)
2. Find the executable in `dist\SteamShortcutsEditor.exe`
3. Run the `.exe` file - no Python installation needed!

## Installation

### Windows

**Prerequisites:** Python 3.6+ ([Download from python.org](https://www.python.org/downloads/))

**Easy Setup:**
1. Clone or download this repository
2. Double-click `run.bat` to run the app
3. (Optional) Double-click `build_exe.bat` to create a standalone `.exe` file

**Manual Setup:**
```cmd
REM Create virtual environment
python -m venv .venv

REM Activate virtual environment
.venv\Scripts\activate.bat

REM Install dependencies
pip install -r requirements.txt

REM Run the application
python steam_shortcuts_editor.py
```

**Using PowerShell:**
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the application
python steam_shortcuts_editor.py
```

### Linux / macOS

**Prerequisites:** Python 3.6+

**Easy Setup:**
```bash
chmod +x run.sh
./run.sh
```

**Manual Setup:**
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # bash/zsh
# OR
source .venv/bin/activate.fish  # fish shell

# Install dependencies
pip install -r requirements.txt

# Run the application
python steam_shortcuts_editor.py
```

### Using UV Package Manager (Optional - Faster)

If you have [UV](https://github.com/astral-sh/uv) installed, the scripts will automatically use it for faster package installation.

## Features

### Core Features
- ✅ List all Steam shortcuts in one interface
- ✅ Edit all shortcut properties (name, path, icons, launch options, etc.)
- ✅ Delete unwanted shortcut entries
- ✅ Sort shortcuts by name or file order
- ✅ **Automatic backups** created before each save (keeps last 5 backups)
- ✅ **Corruption detection** with automatic restoration offers
- ✅ **Backup browser** to restore from any previous backup
- ✅ User-friendly interface with resizable panels
- ✅ Cross-platform support (Windows, Linux, macOS)

### Windows-Specific Enhancements
- ✅ Automatic Steam detection via Windows Registry
- ✅ Support for custom Steam installation locations
- ✅ Support for multiple Steam library folders
- ✅ Native Windows launcher scripts (`.bat` and `.ps1`)
- ✅ PyInstaller support for standalone `.exe` builds
- ✅ Proper error handling for Windows file permissions

## How It Works

### Automatic Steam Detection

**Windows:**
The app checks the Windows Registry for your Steam installation, then searches for your `shortcuts.vdf` file in:
1. Registry-detected Steam path
2. All Steam library folders
3. Common fallback locations: `C:\Program Files (x86)\Steam`, `C:\Program Files\Steam`

**Linux:**
- `~/.steam/steam/userdata/<user_id>/config/shortcuts.vdf`
- `~/.local/share/Steam/userdata/<user_id>/config/shortcuts.vdf`

**macOS:**
- `~/Library/Application Support/Steam/userdata/<user_id>/config/shortcuts.vdf`

If automatic detection fails, use the **"Browse..."** button to manually select your `shortcuts.vdf` file.

## Usage

1. **Launch the application** using one of the methods above
2. The editor will automatically locate and load your `shortcuts.vdf` file
3. **Select a shortcut** from the list to view/edit its properties
4. **Modify** any property values as needed
5. **Click "Save Changes"** to write back to the file
   - A timestamped backup is automatically created before saving
6. **Click "Delete VDF Entry"** to remove unwanted shortcuts
7. **Click "Restore from Backup..."** to restore from a previous backup
   - Browse all backups with validation status
   - See backup details (timestamp, size, shortcut count)
8. Use the **Sort** options to organize shortcuts by name or file order

## Troubleshooting

### Windows-Specific Issues

**"Python is not installed or not in PATH"**
- Install Python from [python.org](https://www.python.org/downloads/)
- During installation, check "Add Python to PATH"

**"Cannot find Steam shortcuts file"**
- Make sure Steam is installed
- Add at least one non-Steam game to create the `shortcuts.vdf` file
- Use the "Browse..." button to manually locate the file
- Check: `C:\Program Files (x86)\Steam\userdata\<your_steam_id>\config\shortcuts.vdf`

**"Access Denied" when saving**
- Close Steam before editing (Steam locks the file when running)
- Run the app as Administrator if needed
- Check file permissions in Windows Explorer

**"Cannot run PowerShell script"**
- Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Or use `run.bat` instead

**Build executable fails**
- Ensure you have enough disk space (build requires ~200MB)
- Try running `pip install --upgrade pyinstaller`
- Check antivirus isn't blocking PyInstaller

### General Issues

**Backups filling up space:**
- The app automatically keeps only the last 5 backups
- Old backups are in the same folder as `shortcuts.vdf` with `.backup_YYYYMMDD_HHMMSS` extension
- Safe to delete old `.backup_*` files manually if needed

**Changes not appearing in Steam:**
- Close and restart Steam after saving changes
- Steam only reads the file on startup

**Error loading shortcuts file:**
- The app will automatically detect corruption and offer restoration
- Click "Restore from Backup..." to manually browse and restore from backups
- Backup browser shows validation status for each backup
- Corrupted files are saved with `.corrupted_TIMESTAMP` extension before restoration

## Development

### Project Structure
```
steam-shortcuts-editor/
├── steam_shortcuts_editor.py    # Main application
├── requirements.txt              # Python dependencies
├── pyproject.toml               # Modern Python package configuration
├── run.bat                      # Windows CMD launcher
├── run.ps1                      # Windows PowerShell launcher
├── run.sh                       # Linux/macOS launcher
├── build_exe.bat                # Windows executable build script (CMD)
├── build_exe.ps1                # Windows executable build script (PowerShell)
├── steam_shortcuts_editor.spec  # PyInstaller configuration
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

### Contributing

To contribute to this project:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test on Windows, Linux, and/or macOS
5. Submit a pull request

### Building for Distribution

**Windows Executable:**
```cmd
build_exe.bat
```

The standalone `.exe` will be in `dist\SteamShortcutsEditor.exe`

**Python Package:**
```bash
pip install build
python -m build
```

## License

This project is open source and available for anyone to use and modify.

## Acknowledgments

- Original project by [DragRedSim](https://github.com/DragRedSim/steam-shortcuts-editor)
- Enhanced with [Claude Code](https://claude.ai/code)
- Uses [vdf](https://github.com/ValvePython/vdf) library for parsing Valve Data Format files
- Built with [PySide6](https://doc.qt.io/qtforpython/) (Qt for Python) for the GUI