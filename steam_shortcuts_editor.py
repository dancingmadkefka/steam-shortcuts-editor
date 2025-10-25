import vdf
import sys
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QListView, QFrame, QScrollArea, QPushButton,
    QLineEdit, QTextEdit, QMessageBox, QGridLayout, QSplitter,
    QFileDialog, QRadioButton, QAbstractItemView, QButtonGroup
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QItemSelectionModel, QItemSelection
import ctypes
import platform

# Import winreg for Windows registry access
try:
    import winreg
except ImportError:
    winreg = None  # Not available on non-Windows platforms

class SteamShortcutsEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Default path (will be set properly in find_shortcuts_path)
        self.shortcuts_path = None
        
        # Set up the UI
        self.setWindowTitle("Steam Shortcuts Editor")
        self.setMinimumSize(900, 600)
        
        # Try to automatically find the shortcuts.vdf path
        self.enable_save = self.find_shortcuts_path()

        # Load the data if path exists
        if self.shortcuts_path:
            self.load_data()
        
        # Create the UI
        self.setup_ui()
    
    def get_steam_path_from_registry(self):
        """Get Steam installation path from Windows Registry"""
        if platform.system() != 'Windows' or winreg is None:
            return None

        try:
            # Try to get Steam path from registry
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
            steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
            winreg.CloseKey(key)
            return Path(steam_path)
        except (FileNotFoundError, OSError):
            pass

        # Try alternative registry location
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
            install_path, _ = winreg.QueryValueEx(key, "InstallPath")
            winreg.CloseKey(key)
            return Path(install_path)
        except (FileNotFoundError, OSError):
            pass

        return None

    def get_steam_library_folders(self, steam_path):
        """Get all Steam library folders including additional library locations"""
        library_folders = [steam_path]

        # Check for libraryfolders.vdf which lists additional Steam library locations
        library_vdf = steam_path / "steamapps" / "libraryfolders.vdf"
        if library_vdf.exists():
            try:
                with open(library_vdf, 'r', encoding='utf-8') as f:
                    library_data = vdf.load(f)
                    if 'libraryfolders' in library_data:
                        for folder_info in library_data['libraryfolders'].values():
                            if isinstance(folder_info, dict) and 'path' in folder_info:
                                library_folders.append(Path(folder_info['path']))
            except Exception:
                pass  # If we can't parse it, just use the main Steam path

        return library_folders

    def find_shortcuts_path(self):
        """Try to automatically locate the shortcuts.vdf file"""
        possible_locations = []

        # For Windows, try registry first
        if platform.system() == 'Windows':
            steam_path = self.get_steam_path_from_registry()
            if steam_path:
                # Add the main Steam path and any library folders
                for library_path in self.get_steam_library_folders(steam_path):
                    possible_locations.append(library_path / "userdata")

            # Fallback to common Windows locations
            possible_locations.extend([
                Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Steam/userdata",
                Path("C:/Program Files/Steam/userdata"),
            ])

        # Common locations for all platforms
        possible_locations.extend([
            Path.home() / ".steam/steam/userdata",  # Linux
            Path.home() / ".local/share/Steam/userdata",  # Alternative Linux
            Path.home() / "Library/Application Support/Steam/userdata"  # macOS
        ])

        # Search through all possible locations
        for location in possible_locations:
            if location.exists() and location.is_dir():
                # Look for userdata directories
                try:
                    for user_dir in location.iterdir():
                        if user_dir.is_dir() and user_dir.name.isdigit():
                            # Check for shortcuts.vdf
                            shortcuts_file = user_dir / "config" / "shortcuts.vdf"
                            if shortcuts_file.exists():
                                self.shortcuts_path = str(shortcuts_file)
                                return True
                except PermissionError:
                    continue  # Skip directories we don't have permission to read

        return False
    
    def load_data(self):
        """Load data from shortcuts.vdf file with corruption detection"""
        if not self.shortcuts_path:
            self.data = {"shortcuts": {}}
            self.original_data = self.data.copy()
            self.enable_save = False
            return

        # Check if file exists
        if not os.path.exists(self.shortcuts_path):
            self.data = {"shortcuts": {}}
            self.original_data = self.data.copy()
            self.enable_save = False
            return

        # Check file size for obvious corruption
        file_size = os.path.getsize(self.shortcuts_path)

        # File is suspiciously small (less than 100 bytes)
        if file_size < 100:
            self.offer_restoration(f"File is too small ({file_size} bytes). It may be corrupted or empty.")
            self.data = {"shortcuts": {}}
            self.original_data = self.data.copy()
            self.enable_save = False
            try:
                self.save_button.setEnabled(self.enable_save)
            except AttributeError:
                pass
            return

        # Compare with backup sizes if available
        backups = self.find_available_backups()
        valid_backups = [b for b in backups if b['is_valid']]

        if valid_backups and len(valid_backups) >= 2:
            # Calculate median backup size
            backup_sizes = [b['size'] for b in valid_backups]
            median_size = sorted(backup_sizes)[len(backup_sizes) // 2]

            # If current file is less than 50% of median backup size, likely corrupted
            if file_size < median_size * 0.5:
                self.offer_restoration(
                    f"File size ({file_size:,} bytes) is significantly smaller than expected "
                    f"(median backup: {median_size:,} bytes). The file may be corrupted."
                )
                self.data = {"shortcuts": {}}
                self.original_data = self.data.copy()
                self.enable_save = False
                try:
                    self.save_button.setEnabled(self.enable_save)
                except AttributeError:
                    pass
                return

        # Try to load the file
        try:
            with open(self.shortcuts_path, 'rb') as f:
                self.data = vdf.binary_load(f)

            # Validate data structure
            if not isinstance(self.data, dict):
                raise ValueError("Invalid data structure: expected dictionary")

            if 'shortcuts' not in self.data:
                raise ValueError("Invalid data structure: missing 'shortcuts' key")

            if not isinstance(self.data['shortcuts'], dict):
                raise ValueError("Invalid data structure: 'shortcuts' should be a dictionary")

            # Successfully loaded
            self.original_data = self.data.copy()  # Keep a copy for comparison
            self.enable_save = True

        except Exception as e:
            # Failed to load - offer restoration
            error_msg = str(e)
            if "parse" in error_msg.lower() or "decode" in error_msg.lower():
                error_msg = f"VDF parsing error: {error_msg}"
            elif "invalid" in error_msg.lower():
                error_msg = f"Data validation error: {error_msg}"
            else:
                error_msg = f"Failed to load file: {error_msg}"

            self.offer_restoration(error_msg)
            self.data = {"shortcuts": {}}
            self.original_data = self.data.copy()
            self.enable_save = False

        # Update save button state if it exists
        try:
            self.save_button.setEnabled(self.enable_save)
        except AttributeError:
            pass  # save_button doesn't exist yet during initialization
    
    def setup_ui(self):
        """Set up the main UI components"""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create path selection widget
        path_widget = QWidget()
        path_layout = QHBoxLayout(path_widget)
        path_layout.setContentsMargins(0, 0, 0, 0)
        
        path_layout.addWidget(QLabel("Shortcuts File:"))
        self.path_edit = QLineEdit()
        if self.shortcuts_path:
            self.path_edit.setText(self.shortcuts_path)
        self.path_edit.setReadOnly(True)
        path_layout.addWidget(self.path_edit, 1)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_shortcuts_file)
        path_layout.addWidget(browse_button)
        
        main_layout.addWidget(path_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)
        
        # Create sort options
        self.sort_type = QButtonGroup(exclusive=True)
        sort_id = QRadioButton("File order")
        sort_id.setChecked(True)
        sort_name = QRadioButton("Shortcut Name")
        self.sort_type.addButton(sort_id, 1) # id numbers are used to map against the shortcut list model
        self.sort_type.addButton(sort_name, 0)
        self.sort_type.idToggled.connect(self.sort_shortcuts)
        self.sort_order = 1

        # Create left panel for shortcut list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_header_panel = QWidget()
        left_header_layout = QHBoxLayout(left_header_panel)
        left_header_layout.addWidget(QLabel("Shortcuts:"))
        left_header_layout.addStretch()
        left_header_layout.addWidget(QLabel("Sort by:"))
        left_header_layout.addWidget(sort_id)
        left_header_layout.addWidget(sort_name)

        left_layout.addWidget(left_header_panel)
        
        # Create shortcut list
        self.shortcut_list = QStandardItemModel()
        self.shortcut_list_widget = QListView()
        self.shortcut_list_widget.setModel(self.shortcut_list)
        self.shortcut_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.shortcut_list_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.shortcut_list_widget.selectionModel().selectionChanged.connect(self.on_shortcut_select)

        left_layout.addWidget(self.shortcut_list_widget)
        
        # Add shortcuts to list if data is loaded
        if hasattr(self, 'data'):
            self.refresh_shortcut_list()
        
        # Create right panel for properties
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Create selection actions panel
        self.selection_panel = QWidget()
        self.selection_panel.setVisible(False)  # Hidden by default
        selection_panel_layout = QVBoxLayout(self.selection_panel)
        selection_panel_layout.setContentsMargins(5, 5, 5, 5)

        # Add frame for better visibility
        selection_frame = QFrame()
        selection_frame.setFrameShape(QFrame.Shape.StyledPanel)
        selection_frame.setFrameShadow(QFrame.Shadow.Raised)
        selection_frame_layout = QVBoxLayout(selection_frame)

        # Selection info label
        self.selection_info_label = QLabel("No games selected")
        self.selection_info_label.setWordWrap(True)
        selection_frame_layout.addWidget(self.selection_info_label)

        # Buttons layout
        selection_buttons_layout = QHBoxLayout()
        self.update_location_button = QPushButton("Update Game Location")
        self.update_location_button.clicked.connect(self.update_game_locations)
        self.update_location_button.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; }")
        self.clear_selection_button = QPushButton("Clear Selection")
        self.clear_selection_button.clicked.connect(self.clear_selection)

        selection_buttons_layout.addWidget(self.update_location_button)
        selection_buttons_layout.addWidget(self.clear_selection_button)
        selection_frame_layout.addLayout(selection_buttons_layout)

        selection_panel_layout.addWidget(selection_frame)
        right_layout.addWidget(self.selection_panel)

        # Create scroll area for properties
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.properties_widget = QWidget()
        self.properties_layout = QGridLayout(self.properties_widget)
        scroll_area.setWidget(self.properties_widget)
        right_layout.addWidget(QLabel("Properties:"))
        right_layout.addWidget(scroll_area)
        
        # Create buttons
        buttons_layout = QHBoxLayout()
        self.delete_button = QPushButton("Delete VDF Entry")
        self.delete_button.clicked.connect(self.delete_entry)
        self.delete_button.setDisabled(True)
        self.restore_backup_button = QPushButton("Restore from Backup...")
        self.restore_backup_button.clicked.connect(self.show_backup_browser)
        self.restore_backup_button.setToolTip("Restore shortcuts.vdf from a previous backup")
        self.save_button = QPushButton("Save Changes")
        self.save_button.clicked.connect(self.save_changes)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.restore_backup_button)
        buttons_layout.addWidget(self.refresh_button)
        buttons_layout.addWidget(self.save_button)
        right_layout.addLayout(buttons_layout)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 700])  # Initial sizes
    
    def browse_shortcuts_file(self):
        """Let the user browse for the shortcuts.vdf file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select shortcuts.vdf file",
            str(Path.home()),
            "VDF Files (*.vdf);;All Files (*)"
        )
        
        if file_path:
            self.shortcuts_path = file_path
            self.path_edit.setText(file_path)
            self.load_data()
            self.refresh_shortcut_list()

    def sort_shortcuts(self, column, checked):
        if checked:
            self.shortcut_list.sort(column)
            self.sort_order = column
    
    def refresh_shortcut_list(self):
        """Refresh the shortcut list in the UI"""
        self.shortcut_list.clear()
        self.shortcut_list.setHorizontalHeaderLabels(["Name", "File Order"])
        if hasattr(self, 'data') and 'shortcuts' in self.data:
            for shortcut_id in self.data['shortcuts']:
                shortcut = self.data['shortcuts'][shortcut_id]
                app_name = dict((k.lower(), v) for k, v in shortcut.items()).get('appname', f"Shortcut {shortcut_id}")
                self.shortcut_list.appendRow([QStandardItem(app_name), QStandardItem(shortcut_id)])
    
    def on_shortcut_select(self, selection):
        """Handle selection of a shortcut from the list"""
        # Get selected items
        selected_indexes = self.shortcut_list_widget.selectionModel().selectedIndexes()
        # Filter to only get one index per row (we have 2 columns)
        selected_rows = list(set([index.row() for index in selected_indexes]))

        # Update selection panel
        if len(selected_rows) > 1:
            # Multiple selection - show selection panel, hide properties
            self.selection_panel.setVisible(True)
            selected_games = [self.shortcut_list.item(row, 0).text() for row in selected_rows]
            self.selection_info_label.setText(
                f"<b>{len(selected_rows)} games selected:</b><br>" +
                "<br>".join([f"• {game}" for game in selected_games[:10]]) +
                (f"<br>... and {len(selected_games) - 10} more" if len(selected_games) > 10 else "")
            )
            # Clear properties view
            while self.properties_layout.count():
                item = self.properties_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.delete_button.setDisabled(True)
            self.current_shortcut_id = None
            return
        elif len(selected_rows) == 1:
            # Single selection - hide selection panel, show properties
            self.selection_panel.setVisible(False)
            shortcut_item_row = selected_rows[0]
        else:
            # No selection - hide both
            self.selection_panel.setVisible(False)
            while self.properties_layout.count():
                item = self.properties_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.delete_button.setDisabled(True)
            self.current_shortcut_id = None
            return

        # Clear current properties
        while self.properties_layout.count():
            item = self.properties_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.delete_button.setDisabled(True)

        if not hasattr(self, 'data') or 'shortcuts' not in self.data:
            return

        # Get shortcut data
        shortcut_id = self.shortcut_list.item(shortcut_item_row, 1).text()
        shortcut = self.data['shortcuts'][shortcut_id]

        # Save reference to current shortcut
        self.current_shortcut_name = self.shortcut_list.item(shortcut_item_row, 0).text()
        self.current_shortcut_id = shortcut_id
        self.entry_widgets = {}

        # Add entry for each property
        row = 0
        for key, value in shortcut.items():
            # Add label
            self.properties_layout.addWidget(QLabel(f"{key}:"), row, 0)

            # Different handling based on value type
            if isinstance(value, dict):
                text_value = json.dumps(value, indent=2)
                entry = QTextEdit()
                entry.setPlainText(text_value)
                entry.setMinimumHeight(100)
            else:
                # Convert to string for display
                if isinstance(value, bytes):
                    text_value = value.decode('utf-8', errors='replace')
                elif isinstance(value, int):
                    #coerce value stored as unsigned in vdf but parsed as signed back into uint
                    #This is useful because SteamRomManager saves its icon files with this uint value, and writes them into the icon field
                    text_value = str(ctypes.c_uint32(value).value)
                else:
                    text_value = str(value)

                entry = QLineEdit()
                entry.setText(text_value)

            # Add browse button for exe and icon fields
            if key.lower() in ['exe', 'icon', 'startdir', 'launchoptions'] and isinstance(entry, QLineEdit):
                browse_button = QPushButton("Browse...")
                browse_button.setMaximumWidth(80)
                if key.lower() == 'exe':
                    browse_button.clicked.connect(lambda checked=False, k=key: self.browse_for_exe(k))
                elif key.lower() == 'icon':
                    browse_button.clicked.connect(lambda checked=False, k=key: self.browse_for_icon(k))
                elif key.lower() == 'startdir':
                    browse_button.clicked.connect(lambda checked=False, k=key: self.browse_for_directory(k))
                self.properties_layout.addWidget(entry, row, 1)
                self.properties_layout.addWidget(browse_button, row, 2)
            else:
                self.properties_layout.addWidget(entry, row, 1)

            self.entry_widgets[key] = entry
            row += 1

        self.delete_button.setDisabled(False)

    def clear_selection(self):
        """Clear the current selection"""
        self.shortcut_list_widget.clearSelection()

    def auto_update_start_dir(self, exe_path, shortcut_id):
        """Automatically update StartDir based on exe path"""
        if not exe_path:
            return

        # Get the directory containing the exe
        start_dir = str(Path(exe_path).parent)

        # Update the data
        if shortcut_id in self.data['shortcuts']:
            # Find the StartDir key (case-insensitive)
            shortcut = self.data['shortcuts'][shortcut_id]
            start_dir_key = None
            for key in shortcut.keys():
                if key.lower() == 'startdir':
                    start_dir_key = key
                    break

            if start_dir_key:
                self.data['shortcuts'][shortcut_id][start_dir_key] = start_dir
            else:
                # Add StartDir if it doesn't exist
                self.data['shortcuts'][shortcut_id]['StartDir'] = start_dir

    def browse_for_exe(self, key):
        """Browse for an exe file for a single property"""
        if not hasattr(self, 'current_shortcut_id') or self.current_shortcut_id is None:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select executable for {self.current_shortcut_name}",
            str(Path.home()),
            "Executable Files (*.exe);;All Files (*)"
        )

        if file_path and key in self.entry_widgets:
            self.entry_widgets[key].setText(file_path)
            # Auto-update StartDir
            self.auto_update_start_dir(file_path, self.current_shortcut_id)
            # Update the StartDir widget if it exists
            for widget_key in self.entry_widgets:
                if widget_key.lower() == 'startdir':
                    self.entry_widgets[widget_key].setText(str(Path(file_path).parent))
                    break

    def browse_for_icon(self, key):
        """Browse for an icon file"""
        if not hasattr(self, 'current_shortcut_id') or self.current_shortcut_id is None:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select icon for {self.current_shortcut_name}",
            str(Path.home()),
            "Image Files (*.png *.jpg *.jpeg *.ico);;All Files (*)"
        )

        if file_path and key in self.entry_widgets:
            self.entry_widgets[key].setText(file_path)

    def browse_for_directory(self, key):
        """Browse for a directory"""
        if not hasattr(self, 'current_shortcut_id') or self.current_shortcut_id is None:
            return

        dir_path = QFileDialog.getExistingDirectory(
            self,
            f"Select directory for {self.current_shortcut_name}",
            str(Path.home())
        )

        if dir_path and key in self.entry_widgets:
            self.entry_widgets[key].setText(dir_path)

    def scan_folder_for_exes(self, folder_path):
        """Recursively scan a folder for exe files and return a dict mapping lowercase filename to full path"""
        exe_map = {}
        folder = Path(folder_path)

        # Recursively find all .exe files
        for exe_file in folder.rglob('*.exe'):
            # Use lowercase filename (without path) as key for case-insensitive matching
            filename = exe_file.name.lower()
            # If duplicate filenames exist, prefer shorter paths (likely the main game exe)
            if filename not in exe_map or len(str(exe_file)) < len(str(exe_map[filename])):
                exe_map[filename] = str(exe_file)

        return exe_map

    def auto_match_games_in_folder(self, selected_games, folder_path):
        """Automatically match and update games based on exe files in a folder"""
        # Scan the folder for all exe files
        exe_map = self.scan_folder_for_exes(folder_path)

        if not exe_map:
            QMessageBox.warning(
                self,
                "No Executables Found",
                f"No .exe files were found in:\n{folder_path}\n\nPlease select a different folder."
            )
            return 0

        matched = []
        unmatched = []

        for game_name, shortcut_id in selected_games:
            # Get the current exe path to extract the filename
            shortcut = self.data['shortcuts'][shortcut_id]
            exe_key = None
            current_exe = None

            for key in shortcut.keys():
                if key.lower() == 'exe':
                    exe_key = key
                    current_exe = shortcut[key]
                    break

            if not exe_key or not current_exe:
                unmatched.append((game_name, "No Exe field found"))
                continue

            # Extract just the filename from the current exe path
            current_filename = Path(current_exe).name.lower()

            # Try to find a match in the scanned folder
            if current_filename in exe_map:
                new_exe_path = exe_map[current_filename]
                self.data['shortcuts'][shortcut_id][exe_key] = new_exe_path
                self.auto_update_start_dir(new_exe_path, shortcut_id)
                matched.append((game_name, new_exe_path))
            else:
                unmatched.append((game_name, f"No match for '{current_filename}'"))

        # Show detailed summary
        summary = f"<b>Auto-Match Results:</b><br><br>"

        if matched:
            summary += f"<b style='color: green;'>✓ Successfully matched {len(matched)} game(s):</b><br>"
            for game_name, new_path in matched[:10]:  # Show first 10
                summary += f"• {game_name}<br>  → {new_path}<br>"
            if len(matched) > 10:
                summary += f"<i>... and {len(matched) - 10} more</i><br>"
            summary += "<br>"

        if unmatched:
            summary += f"<b style='color: orange;'>⚠ Could not match {len(unmatched)} game(s):</b><br>"
            for game_name, reason in unmatched[:10]:  # Show first 10
                summary += f"• {game_name}: {reason}<br>"
            if len(unmatched) > 10:
                summary += f"<i>... and {len(unmatched) - 10} more</i><br>"
            summary += "<br>"

        summary += "<br><b>Don't forget to save changes!</b>"

        # Create a custom message box with rich text
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Auto-Match Complete")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(summary)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()

        return len(matched)

    def update_game_locations(self):
        """Update game locations for selected games"""
        selected_indexes = self.shortcut_list_widget.selectionModel().selectedIndexes()
        selected_rows = list(set([index.row() for index in selected_indexes]))

        if not selected_rows:
            QMessageBox.warning(self, "Warning", "No games selected.")
            return

        # Get the shortcut IDs and names for selected games
        selected_games = []
        for row in selected_rows:
            game_name = self.shortcut_list.item(row, 0).text()
            shortcut_id = self.shortcut_list.item(row, 1).text()
            selected_games.append((game_name, shortcut_id))

        if len(selected_games) == 1:
            # Single game - simple file picker
            game_name, shortcut_id = selected_games[0]

            # Get current exe location to use as starting directory
            current_exe = None
            shortcut = self.data['shortcuts'][shortcut_id]
            for key in shortcut.keys():
                if key.lower() == 'exe':
                    current_exe = shortcut[key]
                    break

            start_dir = str(Path(current_exe).parent) if current_exe and Path(current_exe).exists() else str(Path.home())

            file_path, _ = QFileDialog.getOpenFileName(
                self,
                f"Select new executable location for {game_name}",
                start_dir,
                "Executable Files (*.exe);;All Files (*)"
            )

            if file_path:
                # Find the Exe key (case-insensitive)
                exe_key = None
                for key in shortcut.keys():
                    if key.lower() == 'exe':
                        exe_key = key
                        break

                if exe_key:
                    self.data['shortcuts'][shortcut_id][exe_key] = file_path
                    self.auto_update_start_dir(file_path, shortcut_id)
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Updated location for {game_name}\n\nExe: {file_path}\nStartDir: {Path(file_path).parent}\n\nDon't forget to save changes!"
                    )
                    # Refresh the properties view if this game is still selected
                    self.on_shortcut_select(None)
                else:
                    QMessageBox.warning(self, "Warning", f"Could not find Exe field for {game_name}")
        else:
            # Multiple games - ask how to proceed with better options
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Update Multiple Games")
            msg_box.setText(f"You have {len(selected_games)} games selected.\n\nHow would you like to update them?")
            msg_box.setIcon(QMessageBox.Icon.Question)

            auto_button = msg_box.addButton("Auto-Detect in Folder", QMessageBox.ButtonRole.AcceptRole)
            manual_button = msg_box.addButton("Select Each Manually", QMessageBox.ButtonRole.ActionRole)
            msg_box.addButton(QMessageBox.StandardButton.Cancel)

            msg_box.setDetailedText(
                "Auto-Detect: Select a folder and automatically match games by exe filename.\n"
                "This works great when you've moved games to a new location but kept the same exe names.\n\n"
                "Select Each Manually: Pick the exe for each game one by one.\n"
                "The file picker will remember your last location to make navigation easier."
            )

            msg_box.exec()

            clicked_button = msg_box.clickedButton()

            if clicked_button == auto_button:
                # Auto-detect mode
                folder_path = QFileDialog.getExistingDirectory(
                    self,
                    "Select folder containing your moved games",
                    str(Path.home())
                )

                if folder_path:
                    matched_count = self.auto_match_games_in_folder(selected_games, folder_path)
                    if matched_count > 0:
                        # Refresh the view
                        self.on_shortcut_select(None)

            elif clicked_button == manual_button:
                # Manual selection mode with directory memory
                updated_count = 0
                last_directory = str(Path.home())

                for game_name, shortcut_id in selected_games:
                    file_path, _ = QFileDialog.getOpenFileName(
                        self,
                        f"Select new executable location for {game_name} ({updated_count + 1}/{len(selected_games)})",
                        last_directory,
                        "Executable Files (*.exe);;All Files (*)"
                    )

                    if file_path:
                        # Remember this directory for the next game
                        last_directory = str(Path(file_path).parent)

                        # Find the Exe key (case-insensitive)
                        shortcut = self.data['shortcuts'][shortcut_id]
                        exe_key = None
                        for key in shortcut.keys():
                            if key.lower() == 'exe':
                                exe_key = key
                                break

                        if exe_key:
                            self.data['shortcuts'][shortcut_id][exe_key] = file_path
                            self.auto_update_start_dir(file_path, shortcut_id)
                            updated_count += 1
                    else:
                        # User cancelled - ask if they want to continue with remaining games
                        if updated_count < len(selected_games) - 1:
                            continue_reply = QMessageBox.question(
                                self,
                                "Continue?",
                                f"Updated {updated_count} games so far. Continue with remaining games?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                            )
                            if continue_reply == QMessageBox.StandardButton.No:
                                break

                if updated_count > 0:
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Updated {updated_count} out of {len(selected_games)} games.\n\nDon't forget to save changes!"
                    )
                    # Refresh the view
                    self.on_shortcut_select(None)

    def delete_entry(self):
        """Delete the currently selected VDF entry"""
        if not hasattr(self, 'current_shortcut_id') or self.current_shortcut_id is None:
            QMessageBox.warning(self, "Warning", "No entry selected.")
            return

        try:
            entry = self.current_shortcut_name
            if (QMessageBox.question(self, "Warning", f"Are you sure you want to delete the entry {entry}?", defaultButton=QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes):
                self.data['shortcuts'].pop(self.current_shortcut_id)
                current_row = self.shortcut_list.findItems(self.current_shortcut_id, column=1)[0].row()
                self.shortcut_list.removeRow(current_row)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed: {e}")
    
    def create_backup(self):
        """Create a backup of the shortcuts.vdf file"""
        if not self.shortcuts_path or not os.path.exists(self.shortcuts_path):
            return False

        try:
            # Create backup with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.shortcuts_path}.backup_{timestamp}"

            shutil.copy2(self.shortcuts_path, backup_path)

            # Keep only the last 5 backups to avoid clutter
            backup_dir = Path(self.shortcuts_path).parent
            backup_pattern = Path(self.shortcuts_path).name + ".backup_*"
            backups = sorted(backup_dir.glob(backup_pattern), key=lambda p: p.stat().st_mtime, reverse=True)

            # Delete older backups beyond the first 5
            for old_backup in backups[5:]:
                try:
                    old_backup.unlink()
                except Exception:
                    pass  # Ignore errors when deleting old backups

            return True
        except Exception as e:
            QMessageBox.warning(self, "Backup Warning", f"Could not create backup: {e}\n\nDo you want to continue saving?")
            return False

    def find_available_backups(self):
        """Find all available backup files for the current shortcuts.vdf file"""
        if not self.shortcuts_path or not os.path.exists(self.shortcuts_path):
            return []

        backup_dir = Path(self.shortcuts_path).parent
        backup_pattern = Path(self.shortcuts_path).name + ".backup_*"
        backups = sorted(backup_dir.glob(backup_pattern), key=lambda p: p.stat().st_mtime, reverse=True)

        backup_info = []
        for backup in backups:
            try:
                stats = backup.stat()
                # Parse timestamp from filename
                timestamp_str = backup.name.split(".backup_")[1]
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                # Validate backup
                is_valid, shortcut_count = self.validate_backup_file(str(backup))

                backup_info.append({
                    'path': str(backup),
                    'size': stats.st_size,
                    'timestamp': timestamp,
                    'timestamp_str': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    'is_valid': is_valid,
                    'shortcut_count': shortcut_count
                })
            except Exception:
                # Skip malformed backup files
                continue

        return backup_info

    def validate_backup_file(self, backup_path):
        """Validate if a backup file can be loaded successfully
        Returns (is_valid, shortcut_count)
        """
        try:
            with open(backup_path, 'rb') as f:
                data = vdf.binary_load(f)

            # Check if data has expected structure
            if not isinstance(data, dict):
                return False, 0

            if 'shortcuts' not in data:
                return False, 0

            if not isinstance(data['shortcuts'], dict):
                return False, 0

            # Count shortcuts
            shortcut_count = len(data['shortcuts'])

            return True, shortcut_count
        except Exception:
            return False, 0

    def restore_from_backup(self, backup_path):
        """Restore the shortcuts.vdf file from a backup
        Returns True if successful, False otherwise
        """
        if not self.shortcuts_path:
            return False

        try:
            # First validate the backup
            is_valid, _ = self.validate_backup_file(backup_path)
            if not is_valid:
                QMessageBox.critical(
                    self,
                    "Invalid Backup",
                    f"The selected backup file is corrupted or invalid:\n{backup_path}"
                )
                return False

            # Create a backup of current file before restoring (if it exists)
            if os.path.exists(self.shortcuts_path):
                corrupted_backup = f"{self.shortcuts_path}.corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                try:
                    shutil.copy2(self.shortcuts_path, corrupted_backup)
                except Exception:
                    pass  # Don't fail if we can't backup the corrupted file

            # Restore the backup
            shutil.copy2(backup_path, self.shortcuts_path)

            # Reload the data
            self.load_data()
            self.refresh_shortcut_list()

            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Restoration Failed",
                f"Failed to restore from backup:\n{e}"
            )
            return False

    def offer_restoration(self, error_message):
        """Show dialog offering to restore from backup when corruption is detected"""
        backups = self.find_available_backups()

        if not backups:
            # No backups available
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("File Corrupted - No Backups Available")
            msg.setText(f"Failed to load shortcuts file:\n{error_message}")
            msg.setInformativeText("No backup files were found. You can try:\n• Browse for a different shortcuts.vdf file\n• Manually locate a backup file")
            browse_button = msg.addButton("Browse for File", QMessageBox.ButtonRole.AcceptRole)
            msg.addButton(QMessageBox.StandardButton.Cancel)
            msg.exec()

            if msg.clickedButton() == browse_button:
                self.browse_shortcuts_file()
            return

        # Find the most recent valid backup
        valid_backups = [b for b in backups if b['is_valid']]

        if not valid_backups:
            # Have backups but none are valid
            QMessageBox.critical(
                self,
                "File Corrupted - No Valid Backups",
                f"Failed to load shortcuts file:\n{error_message}\n\n"
                f"Found {len(backups)} backup(s) but all appear to be corrupted.\n\n"
                "You may need to manually locate a valid backup or shortcuts file."
            )
            return

        most_recent = valid_backups[0]

        # Show restoration dialog
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("File Corruption Detected")
        msg.setText(f"Failed to load shortcuts file:\n{error_message}")
        msg.setInformativeText(
            f"A valid backup was found:\n\n"
            f"Backup Date: {most_recent['timestamp_str']}\n"
            f"File Size: {most_recent['size']:,} bytes\n"
            f"Shortcuts: {most_recent['shortcut_count']}\n\n"
            "Would you like to restore from this backup?"
        )

        restore_button = msg.addButton("Restore from Backup", QMessageBox.ButtonRole.AcceptRole)
        browse_backups_button = msg.addButton("Browse All Backups", QMessageBox.ButtonRole.ActionRole)
        browse_file_button = msg.addButton("Browse for File", QMessageBox.ButtonRole.ActionRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)

        msg.exec()
        clicked = msg.clickedButton()

        if clicked == restore_button:
            if self.restore_from_backup(most_recent['path']):
                QMessageBox.information(
                    self,
                    "Restoration Successful",
                    f"Successfully restored from backup:\n{most_recent['timestamp_str']}\n\n"
                    f"Loaded {most_recent['shortcut_count']} shortcut(s)."
                )
        elif clicked == browse_backups_button:
            self.show_backup_browser()
        elif clicked == browse_file_button:
            self.browse_shortcuts_file()

    def show_backup_browser(self):
        """Show a dialog to browse and select from available backups"""
        backups = self.find_available_backups()

        if not backups:
            QMessageBox.information(
                self,
                "No Backups Found",
                "No backup files were found for the current shortcuts.vdf file."
            )
            return

        # Create dialog
        from PySide6.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QDialogButtonBox, QHeaderView

        dialog = QDialog(self)
        dialog.setWindowTitle("Restore from Backup")
        dialog.setMinimumSize(700, 400)

        layout = QVBoxLayout(dialog)

        # Add info label
        info_label = QLabel(f"Found {len(backups)} backup file(s). Select a backup to restore:")
        layout.addWidget(info_label)

        # Create table
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Timestamp", "Size (bytes)", "Shortcuts", "Status", "File"])
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Populate table
        table.setRowCount(len(backups))
        for i, backup in enumerate(backups):
            # Timestamp
            table.setItem(i, 0, QTableWidgetItem(backup['timestamp_str']))

            # Size
            size_item = QTableWidgetItem(f"{backup['size']:,}")
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(i, 1, size_item)

            # Shortcut count
            count_item = QTableWidgetItem(str(backup['shortcut_count']) if backup['is_valid'] else "N/A")
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, 2, count_item)

            # Status
            status = "Valid" if backup['is_valid'] else "Corrupted"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(Qt.GlobalColor.green if backup['is_valid'] else Qt.GlobalColor.red)
            table.setItem(i, 3, status_item)

            # File path
            table.setItem(i, 4, QTableWidgetItem(backup['path']))

        # Resize columns
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(table)

        # Add buttons
        button_box = QDialogButtonBox()
        restore_button = button_box.addButton("Restore Selected", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_button = button_box.addButton(QDialogButtonBox.StandardButton.Cancel)

        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        layout.addWidget(button_box)

        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get selected row
            selected_rows = table.selectedIndexes()
            if selected_rows:
                row = selected_rows[0].row()
                selected_backup = backups[row]

                if not selected_backup['is_valid']:
                    QMessageBox.warning(
                        self,
                        "Invalid Backup",
                        "The selected backup file appears to be corrupted. Please select a different backup."
                    )
                    return

                # Confirm restoration
                confirm = QMessageBox.question(
                    self,
                    "Confirm Restoration",
                    f"Restore from backup:\n\n"
                    f"Date: {selected_backup['timestamp_str']}\n"
                    f"Shortcuts: {selected_backup['shortcut_count']}\n\n"
                    "This will replace your current shortcuts.vdf file.\n"
                    "The current file will be saved with a .corrupted timestamp.\n\n"
                    "Are you sure?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if confirm == QMessageBox.StandardButton.Yes:
                    if self.restore_from_backup(selected_backup['path']):
                        QMessageBox.information(
                            self,
                            "Restoration Successful",
                            f"Successfully restored from backup:\n{selected_backup['timestamp_str']}\n\n"
                            f"Loaded {selected_backup['shortcut_count']} shortcut(s)."
                        )

    def save_changes(self):
        """Save changes to the shortcuts.vdf file"""
        if not self.shortcuts_path:
            QMessageBox.warning(self, "Warning", "No shortcuts file selected.")
            return

        # Create backup before saving
        if not self.create_backup():
            # Ask user if they want to proceed without backup
            reply = QMessageBox.question(
                self,
                "Continue Without Backup?",
                "Failed to create backup. Do you want to save anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Save current editing if any
        if hasattr(self, 'current_shortcut_id') and self.current_shortcut_id is not None:
            for key, entry in self.entry_widgets.items():
                if isinstance(entry, QTextEdit):
                    try:
                        # Try to parse as json for dict values
                        value = json.loads(entry.toPlainText())
                    except:
                        value = entry.toPlainText().strip()
                else:
                    value = entry.text()
                    # Try to convert to original type if possible
                    original_value = self.original_data['shortcuts'][self.current_shortcut_id].get(key)
                    if isinstance(original_value, int):
                        try:
                            value = int(value)
                        except ValueError:
                            pass

                self.data['shortcuts'][self.current_shortcut_id][key] = value

        # Save to file
        try:
            with open(self.shortcuts_path, 'wb') as f:
                vdf.binary_dump(self.data, f)
            QMessageBox.information(self, "Success", "Shortcuts saved successfully!\n\nA backup was created in the same directory.")
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save shortcuts: {e}")
    
    def refresh_data(self):
        """Reload data from file and refresh UI"""
        if self.shortcuts_path:
            self.load_data()
            self.refresh_shortcut_list()
        else:
            QMessageBox.warning(self, "Warning", "No shortcuts file selected.")

def main():
    app = QApplication(sys.argv)
    window = SteamShortcutsEditor()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 