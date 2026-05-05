#!/usr/bin/env python3
"""
Replit Storage Workarounds for Free Hosting
Handles data persistence and backup strategies for Replit's limited storage
"""

import os
import json
import pickle
import gzip
import requests
from pathlib import Path
import shutil

class ReplitStorage:
    """Storage manager optimized for Replit free hosting"""
    
    def __init__(self):
        # Replit persistent storage paths
        self.persistent_dir = "/home/runner/project/data"
        self.backup_dir = "/home/runner/project/backups"
        
        # Create directories if they don't exist
        os.makedirs(self.persistent_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Local fallback paths
        self.local_data_dir = "data"
        self.local_backup_dir = "backups"
        
        # Use Replit paths if available, fallback to local
        self.data_dir = self.persistent_dir if os.path.exists("/home/runner") else self.local_data_dir
        self.backup_dir_path = self.backup_dir if os.path.exists("/home/runner") else self.local_backup_dir
        
        print(f"📁 Using storage directory: {self.data_dir}")
    
    def save_json(self, filename, data, compress=True):
        """Save JSON data with optional compression"""
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            if compress:
                # Save compressed version
                with gzip.open(f"{filepath}.gz", "wt", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            
            # Always save uncompressed version as fallback
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            print(f"💾 Saved {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving {filename}: {e}")
            return False
    
    def load_json(self, filename, try_compressed=True):
        """Load JSON data with fallback to compressed version"""
        filepath = os.path.join(self.data_dir, filename)
        
        # Try compressed version first
        if try_compressed and os.path.exists(f"{filepath}.gz"):
            try:
                with gzip.open(f"{filepath}.gz", "rt", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Compressed file failed, trying uncompressed: {e}")
        
        # Try uncompressed version
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ Error loading {filename}: {e}")
        
        return None
    
    def backup_to_gist(self, data, filename, gist_token=None):
        """Backup data to GitHub Gist (optional)"""
        if not gist_token:
            return False
        
        try:
            gist_url = "https://api.github.com/gists"
            headers = {
                "Authorization": f"token {gist_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            payload = {
                "description": f"Backup of {filename} from Smart Study AI",
                "public": False,
                "files": {
                    filename: {
                        "content": json.dumps(data, indent=2)
                    }
                }
            }
            
            response = requests.post(gist_url, headers=headers, json=payload)
            if response.status_code == 201:
                print(f"✅ Backed up {filename} to GitHub Gist")
                return True
            else:
                print(f"❌ Gist backup failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Gist backup error: {e}")
            return False
    
    def create_local_backup(self, source_file, backup_name=None):
        """Create local backup of important files"""
        if not os.path.exists(source_file):
            return False
        
        if not backup_name:
            backup_name = os.path.basename(source_file)
        
        backup_path = os.path.join(self.backup_dir_path, backup_name)
        
        try:
            shutil.copy2(source_file, backup_path)
            print(f"📦 Created backup: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False
    
    def cleanup_old_files(self, max_files=10):
        """Clean up old backup files to save space"""
        try:
            backup_files = []
            if os.path.exists(self.backup_dir_path):
                backup_files = os.listdir(self.backup_dir_path)
            
            # Keep only the most recent files
            if len(backup_files) > max_files:
                backup_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.backup_dir_path, x)))
                
                for old_file in backup_files[:-max_files]:
                    old_path = os.path.join(self.backup_dir_path, old_file)
                    os.remove(old_path)
                    print(f"🗑️  Removed old backup: {old_file}")
                    
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
    
    def get_storage_info(self):
        """Get storage usage information"""
        info = {
            "data_dir": self.data_dir,
            "backup_dir": self.backup_dir_path
        }
        
        try:
            if os.path.exists(self.data_dir):
                data_files = list(Path(self.data_dir).rglob("*"))
                info["data_files"] = len(data_files)
                info["data_size"] = sum(f.stat().st_size for f in data_files if f.is_file())
            
            if os.path.exists(self.backup_dir_path):
                backup_files = list(Path(self.backup_dir_path).rglob("*"))
                info["backup_files"] = len(backup_files)
                info["backup_size"] = sum(f.stat().st_size for f in backup_files if f.is_file())
                
        except Exception as e:
            print(f"❌ Storage info error: {e}")
        
        return info

# Global storage instance
storage = ReplitStorage()

# Convenience functions for the main app
def safe_save_json(filename, data):
    """Safely save JSON data using Replit storage"""
    return storage.save_json(filename, data)

def safe_load_json(filename, default=None):
    """Safely load JSON data using Replit storage"""
    result = storage.load_json(filename)
    return result if result is not None else default

def backup_important_files():
    """Backup important application files"""
    important_files = [
        "users.json",
        "notes.json", 
        "assignments.json",
        "vector_db/index_compressed.faiss",
        "vector_db/metadata_compressed.pkl"
    ]
    
    for file_path in important_files:
        if os.path.exists(file_path):
            storage.create_local_backup(file_path)
    
    storage.cleanup_old_files()

if __name__ == "__main__":
    print("🧪 Testing Replit storage...")
    
    # Test saving and loading
    test_data = {"test": "data", "timestamp": "2026-05-05"}
    
    if storage.save_json("test.json", test_data):
        loaded_data = storage.load_json("test.json")
        if loaded_data == test_data:
            print("✅ Storage test passed!")
        else:
            print("❌ Storage test failed!")
    
    # Show storage info
    info = storage.get_storage_info()
    print(f"📊 Storage info: {info}")
