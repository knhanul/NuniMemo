"""PyWebView application bootstrap for NuniMemo.

Modern web-based UI using PyWebView + HTML/CSS/JS (Tailwind CSS).
"""

from __future__ import annotations

import json
import signal
import sys
from pathlib import Path
from typing import Any

import webview
from bottle import Bottle, static_file

from mycloudmemo.config import ensure_app_directories, get_app_paths, get_workspace_path, get_default_app_data_dir, DEFAULT_CONFIG_FILE
from mycloudmemo.ui.workspace_dialog import show_workspace_selector
from mycloudmemo.db.database import DatabaseManager
from mycloudmemo.storage.file_manager import FileStorageManager
from mycloudmemo.api import WebMemoAPI

# Global reference to API for route handlers
_api_instance = None


def get_html_path() -> str:
    """Get the path to the HTML frontend file."""
    # Check for development path first
    dev_path = Path(__file__).parent.parent / "web" / "index.html"
    if dev_path.exists():
        return str(dev_path)
    
    # Fall back to installed package path
    pkg_path = Path(__file__).parent / "web" / "index.html"
    if pkg_path.exists():
        return str(pkg_path)
    
    raise FileNotFoundError("Frontend HTML file not found. Please ensure web/index.html exists.")


def create_api() -> WebMemoAPI:
    """Create and configure API with all backend services."""
    
    # Check for custom storage path in config
    config_path = Path.home() / ".nunimemo" / "config.json"
    custom_storage_path = None
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                custom_storage_path = config.get('storage_path')
        except Exception:
            pass  # Use default if config reading fails
    
    # Check if workspace is configured
    if get_workspace_path() is None:
        # For webview, we need to handle workspace selection differently
        # For now, use default workspace
        from mycloudmemo.config import set_workspace_path
        default_workspace = get_default_app_data_dir() / "Workspace"
        set_workspace_path(default_workspace)
    
    paths = ensure_app_directories(get_app_paths())
    
    # Use custom storage path if configured
    if custom_storage_path:
        custom_path = Path(custom_storage_path)
        if custom_path.exists():
            # Override paths with custom storage location
            from mycloudmemo.config import AppPaths
            paths = AppPaths(
                base_dir=custom_path,
                notes_dir=custom_path / "notes",
                assets_dir=custom_path / "assets",
                config_dir=get_default_app_data_dir(),
                database_path=custom_path / "memo.db",
                config_file=get_default_app_data_dir() / DEFAULT_CONFIG_FILE
            )
            paths.notes_dir.mkdir(parents=True, exist_ok=True)
            paths.assets_dir.mkdir(parents=True, exist_ok=True)
    
    database = DatabaseManager(paths.database_path)
    database.initialize()
    
    file_storage = FileStorageManager(paths)
    sync_manager = None  # No sync manager for local workspace mode
    
    # Create API
    api = WebMemoAPI(database, file_storage, sync_manager)
    
    # Store the actual storage path and assets path for later use
    api._storage_path = str(paths.base_dir)
    api._assets_path = str(paths.assets_dir)
    
    # Remove database path objects that cause serialization issues
    if hasattr(database, 'database_path'):
        # Convert to string to avoid Path serialization issues
        database.database_path = str(database.database_path)
    
    # Store file_storage methods directly on api to avoid exposing Path objects
    api._save_memo_content = file_storage.save_memo_content
    api._load_memo_content = file_storage.load_memo_content
    api._delete_memo_file = file_storage.delete_memo_file
    api._generate_memo_filename = file_storage._generate_memo_filename
    
    # Replace file_storage reference with None to prevent JS exposure
    api.file_storage = None
    
    return api


def serve_assets(filepath):
    """Serve image assets from the storage directory."""
    global _api_instance
    if _api_instance and hasattr(_api_instance, '_assets_path'):
        assets_path = Path(_api_instance._assets_path)
        return static_file(filepath, root=str(assets_path))
    return None


def main() -> int:
    """Run the web-based desktop application."""
    
    # Handle Ctrl+C gracefully
    def signal_handler(signum, frame):
        print("\n앱을 종료합니다...")
        # Don't call sys.exit() here, let webview handle cleanup
        # This prevents the SystemExit exception in atexit callbacks
        import os
        os._exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create API instance
        api = create_api()
        
        # Store global reference for route handlers
        global _api_instance
        _api_instance = api
        
        # Get HTML file path
        html_path = get_html_path()
        
        # Create webview window
        window = webview.create_window(
            title="NuniMemo",
            url=html_path,
            js_api=api,
            width=1200,
            height=800,
            min_size=(800, 600),
            frameless=False,  # Set to True for custom title bar (requires additional JS/CSS)
            easy_drag=True,
            background_color="#f8fafc",  # Match Tailwind bg-slate-50
            text_select=True,
        )
        
        # Start webview with default server
        webview.start(
            debug=True,  # Enable for development
            http_server=True,
        )
        
        return 0
        
    except Exception as e:
        print(f"Error starting application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
