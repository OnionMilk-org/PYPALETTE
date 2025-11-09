"""
Settings Manager for PyPalette
Handles loading and saving application settings using JSON
"""

import os
import sys
import json


class SettingsManager:
    """Manages application settings storage and retrieval"""
    
    def __init__(self, max_recent_files=10):
        self.max_recent_files = max_recent_files
        self.recent_files = []
        self._settings_file = None
        
        # Last used directories for different operations
        self.last_directories = {
            'open_image': '',
            'save_image': '',
            'export_palette': '',
            'import_palette': '',
            'export_pmap': '',
            'import_pmap': ''
        }
    
    def get_settings_file_path(self):
        """Get the path to the settings.json file - always next to the application script"""
        if self._settings_file:
            return self._settings_file
            
        # Get the directory where the main script is located
        if hasattr(sys, '_MEIPASS'):
            # Running as PyInstaller executable
            script_dir = os.path.dirname(sys.executable)
        else:
            # Running as Python script - look for main script in call stack
            import inspect
            # Get the main module file path
            main_module = sys.modules['__main__']
            if hasattr(main_module, '__file__') and main_module.__file__:
                script_dir = os.path.dirname(os.path.abspath(main_module.__file__))
            else:
                # Fallback to current directory
                script_dir = os.getcwd()
        
        settings_path = os.path.join(script_dir, 'settings.json')
        
        # Ensure the directory exists (should always exist since script is there)
        os.makedirs(script_dir, exist_ok=True)
        
        self._settings_file = settings_path
        return settings_path
    
    def _get_application_directory(self):
        """Get the application directory (same as settings file location)"""
        settings_path = self.get_settings_file_path()
        return os.path.dirname(settings_path)
    
    def load_settings(self):
        """Load all settings from settings.json - always searches next to application script"""
        try:
            settings_file = self.get_settings_file_path()
            
            print(f"Searching for settings file at: {settings_file}")
            
            if os.path.exists(settings_file):
                print(f"Settings file found, loading settings...")
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings_data = json.load(f)
                    self.recent_files = settings_data.get('recent_files', [])
                    self.last_directories.update(settings_data.get('last_directories', {}))
                    print(f"Loaded {len(self.recent_files)} recent files and directory settings")
            else:
                print("Settings file not found, initializing empty settings")
                self.recent_files = []
            
            # Ensure we don't exceed max recent files
            self.recent_files = self.recent_files[:self.max_recent_files]
            return self.recent_files
            
        except Exception as e:
            print(f"Error loading recent files: {e}")
            self.recent_files = []
            return []
    
    def save_settings(self):
        """Save all settings to settings.json - always saves next to application script"""
        try:
            settings_file = self.get_settings_file_path()
            
            print(f"Saving settings to: {settings_file}")
            
            # Load existing settings or create new ones
            settings_data = {}
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        settings_data = json.load(f)
                    print("Loaded existing settings file")
                except:
                    print("Existing settings file corrupted, creating new one")
                    settings_data = {}
            else:
                print("Creating new settings file")
            
            # Update settings
            settings_data['recent_files'] = self.recent_files
            settings_data['last_directories'] = self.last_directories
            
            # Save to file
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully saved {len(self.recent_files)} recent files and directory settings")
                
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def save_recent_files(self):
        """Backward compatibility method - calls save_settings"""
        self.save_settings()
    
    def load_recent_files(self):
        """Backward compatibility method - calls load_settings"""
        return self.load_settings()
    
    def add_recent_file(self, filepath):
        """Add a file to the recent files list"""
        # Remove if already exists
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        
        # Add to front
        self.recent_files.insert(0, filepath)
        
        # Limit size
        self.recent_files = self.recent_files[:self.max_recent_files]
        
        # Also remember the directory
        directory = os.path.dirname(filepath)
        self.set_last_directory('open_image', directory)
        
        # Save immediately
        self.save_settings()
    
    def get_recent_files(self):
        """Get the list of recent files"""
        return self.recent_files.copy()
    
    def remove_recent_file(self, filepath):
        """Remove a specific file from the recent files list"""
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
            self.save_settings()
    
    def clear_recent_files(self):
        """Clear all recent files"""
        self.recent_files = []
        self.save_settings()
    
    def set_last_directory(self, operation, directory):
        """Set the last used directory for a specific operation"""
        if operation in self.last_directories:
            self.last_directories[operation] = directory
            print(f"Updated last directory for {operation}: {directory}")
    
    def get_last_directory(self, operation):
        """Get the last used directory for a specific operation"""
        directory = self.last_directories.get(operation, '')
        
        # If no directory is saved or it doesn't exist, use application directory
        if not directory or not os.path.exists(directory):
            directory = self._get_application_directory()
        
        print(f"Using directory for {operation}: {directory}")
        return directory
    
    def save_last_directory(self, operation, filepath):
        """Save the directory of a file for future use"""
        directory = os.path.dirname(filepath)
        self.set_last_directory(operation, directory)
        self.save_settings()