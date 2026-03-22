"""Application configuration and path helpers."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

APP_NAME = "MyCloudMemo"
DRIVE_ROOT_FOLDER_NAME = "MyCloudMemo"
DEFAULT_CONFIG_FILE = "config.json"


@dataclass(frozen=True)
class AppPaths:
    """Resolved application paths under the user's AppData directory."""

    base_dir: Path
    notes_dir: Path
    assets_dir: Path
    config_dir: Path
    database_path: Path
    token_path: Path
    credentials_path: Path
    config_file: Path


def get_default_app_data_dir() -> Path:
    """Return the default base application data directory."""
    appdata = os.getenv("APPDATA")
    if not appdata:
        appdata = str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / APP_NAME


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load configuration from config.json."""
    if config_path is None:
        config_path = get_default_app_data_dir() / "config" / DEFAULT_CONFIG_FILE
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Config load error: {e}")
    
    return {}


def save_config(config: dict[str, Any], config_path: Path | None = None) -> bool:
    """Save configuration to config.json."""
    if config_path is None:
        config_path = get_default_app_data_dir() / "config" / DEFAULT_CONFIG_FILE
    
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Config save error: {e}")
        return False


def get_storage_path_from_config() -> Path:
    """Get storage path from config or use default."""
    config = load_config()
    custom_path = config.get("storage_path")
    
    if custom_path and Path(custom_path).exists():
        return Path(custom_path)
    
    return get_default_app_data_dir()


def get_app_paths() -> AppPaths:
    """Build and return the application path collection."""

    base_dir = get_storage_path_from_config()
    default_dir = get_default_app_data_dir()
    
    return AppPaths(
        base_dir=base_dir,
        notes_dir=base_dir / "notes",
        assets_dir=base_dir / "assets",
        config_dir=default_dir / "config",
        database_path=base_dir / "memo.db",
        token_path=default_dir / "config" / "token.json",
        credentials_path=default_dir / "config" / "client_secret.json",
        config_file=default_dir / "config" / DEFAULT_CONFIG_FILE,
    )


def ensure_app_directories(paths: AppPaths | None = None) -> AppPaths:
    """Create the application directory structure if it does not exist."""

    resolved_paths = paths or get_app_paths()
    for directory in (
        resolved_paths.base_dir,
        resolved_paths.notes_dir,
        resolved_paths.assets_dir,
        resolved_paths.config_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return resolved_paths


def migrate_data_to_new_location(old_base: Path, new_base: Path) -> bool:
    """Migrate all data from old location to new location."""
    try:
        if not old_base.exists():
            print(f"Old location does not exist: {old_base}")
            return True  # Nothing to migrate
        
        # Ensure new location exists
        new_base.mkdir(parents=True, exist_ok=True)
        
        # Migrate notes
        old_notes = old_base / "notes"
        new_notes = new_base / "notes"
        if old_notes.exists():
            print(f"Migrating notes from {old_notes} to {new_notes}")
            if new_notes.exists():
                # Merge directories
                for item in old_notes.iterdir():
                    dest = new_notes / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)
            else:
                shutil.copytree(old_notes, new_notes)
        
        # Migrate assets
        old_assets = old_base / "assets"
        new_assets = new_base / "assets"
        if old_assets.exists():
            print(f"Migrating assets from {old_assets} to {new_assets}")
            if new_assets.exists():
                for item in old_assets.iterdir():
                    dest = new_assets / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)
            else:
                shutil.copytree(old_assets, new_assets)
        
        # Migrate database
        old_db = old_base / "memo.db"
        new_db = new_base / "memo.db"
        if old_db.exists():
            print(f"Migrating database from {old_db} to {new_db}")
            shutil.copy2(old_db, new_db)
        
        print("Data migration completed successfully")
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def change_storage_path(new_path: str | Path, migrate: bool = True) -> bool:
    """Change storage path and optionally migrate existing data."""
    new_path = Path(new_path)
    
    # Get current path
    current_config = load_config()
    old_path_str = current_config.get("storage_path")
    old_path = Path(old_path_str) if old_path_str else get_default_app_data_dir()
    
    # Check if path is actually changing
    if old_path.resolve() == new_path.resolve():
        print("New path is same as current path, no change needed")
        return True
    
    # Ensure new path exists
    new_path.mkdir(parents=True, exist_ok=True)
    
    # Migrate data if requested
    if migrate and old_path.exists():
        if not migrate_data_to_new_location(old_path, new_path):
            return False
    
    # Update config
    current_config["storage_path"] = str(new_path.resolve())
    if save_config(current_config):
        print(f"Storage path changed to: {new_path}")
        return True
    
    return False


def get_storage_path() -> Path:
    """Get current storage path."""
    return get_storage_path_from_config()
