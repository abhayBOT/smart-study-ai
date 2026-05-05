#!/usr/bin/env python3
"""
Streamlit Storage Manager
Handles data persistence for Streamlit Cloud hosting
"""

import os
import json
import pickle
import gzip
from pathlib import Path
import tempfile

class StreamlitStorage:
    """Storage manager optimized for Streamlit Cloud"""
    
    def __init__(self):
        # Streamlit Cloud paths
        self.persistent_dir = "/mount/data"
        self.backup_dir = "/mount/backups"
        
        # Create directories if they don't exist
        try:
            os.makedirs(self.persistent_dir, exist_ok=True)
            os.makedirs(self.backup_dir, exist_ok=True)
        except PermissionError:
            # Fallback to current directory
            self.persistent_dir = "data"
            self.backup_dir = "backups"
            os.makedirs(self.persistent_dir, exist_ok=True)
            os.makedirs(self.backup_dir, exist_ok=True)
        
        # Local fallback paths
        self.local_data_dir = "data"
        self.local_backup_dir = "backups"
    
    def save_json(self, filename, data, compress=True):
        """Save JSON data with optional compression"""
        try:
            filepath = os.path.join(self.persistent_dir, filename)
            
            if compress:
                # Save with gzip compression
                with gzip.open(f"{filepath}.gz", 'wt', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                # Save normally
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving {filename}: {e}")
            return False
    
    def load_json(self, filename, default=None, compress=True):
        """Load JSON data with optional compression"""
        try:
            filepath = os.path.join(self.persistent_dir, filename)
            
            if compress:
                # Try compressed version first
                compressed_path = f"{filepath}.gz"
                if os.path.exists(compressed_path):
                    with gzip.open(compressed_path, 'rt', encoding='utf-8') as f:
                        return json.load(f)
            
            # Fallback to uncompressed
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return default
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return default
    
    def save_pickle(self, filename, data, compress=True):
        """Save pickle data with optional compression"""
        try:
            filepath = os.path.join(self.persistent_dir, filename)
            
            if compress:
                with gzip.open(f"{filepath}.gz", 'wb') as f:
                    pickle.dump(data, f)
            else:
                with open(filepath, 'wb') as f:
                    pickle.dump(data, f)
            
            return True
        except Exception as e:
            print(f"Error saving pickle {filename}: {e}")
            return False
    
    def load_pickle(self, filename, default=None, compress=True):
        """Load pickle data with optional compression"""
        try:
            filepath = os.path.join(self.persistent_dir, filename)
            
            if compress:
                compressed_path = f"{filepath}.gz"
                if os.path.exists(compressed_path):
                    with gzip.open(compressed_path, 'rb') as f:
                        return pickle.load(f)
            
            # Fallback to uncompressed
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    return pickle.load(f)
            
            return default
        except Exception as e:
            print(f"Error loading pickle {filename}: {e}")
            return default
    
    def backup_file(self, filename):
        """Create backup of a file"""
        try:
            source_path = os.path.join(self.persistent_dir, filename)
            backup_path = os.path.join(self.backup_dir, f"{filename}.backup")
            
            if os.path.exists(source_path):
                import shutil
                shutil.copy2(source_path, backup_path)
                return True
            return False
        except Exception as e:
            print(f"Error backing up {filename}: {e}")
            return False
    
    def cleanup_old_backups(self, max_backups=5):
        """Clean up old backup files"""
        try:
            backup_files = []
            for file in os.listdir(self.backup_dir):
                if file.endswith('.backup'):
                    backup_files.append(os.path.join(self.backup_dir, file))
            
            # Sort by modification time and keep only the newest
            backup_files.sort(key=os.path.getmtime, reverse=True)
            
            for old_backup in backup_files[max_backups:]:
                os.remove(old_backup)
            
            return True
        except Exception as e:
            print(f"Error cleaning backups: {e}")
            return False
    
    def get_storage_info(self):
        """Get information about storage usage"""
        try:
            info = {
                "persistent_dir": self.persistent_dir,
                "backup_dir": self.backup_dir,
                "data_files": [],
                "backup_files": []
            }
            
            if os.path.exists(self.persistent_dir):
                info["data_files"] = os.listdir(self.persistent_dir)
            
            if os.path.exists(self.backup_dir):
                info["backup_files"] = os.listdir(self.backup_dir)
            
            return info
        except Exception as e:
            print(f"Error getting storage info: {e}")
            return {"error": str(e)}

# Global storage instance
storage = StreamlitStorage()

# Convenience functions for main app
def safe_save_json(filename, data):
    """Save JSON data safely"""
    return storage.save_json(filename, data)

def safe_load_json(filename, default=None):
    """Load JSON data safely"""
    return storage.load_json(filename, default)

def safe_save_pickle(filename, data):
    """Save pickle data safely"""
    return storage.save_pickle(filename, data)

def safe_load_pickle(filename, default=None):
    """Load pickle data safely"""
    return storage.load_pickle(filename, default)

def backup_data(filename):
    """Backup a data file"""
    return storage.backup_file(filename)

def cleanup_backups():
    """Clean up old backups"""
    return storage.cleanup_old_backups()

def get_storage_info():
    """Get storage information"""
    return storage.get_storage_info()
