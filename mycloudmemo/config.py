"""Application configuration and path helpers."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

APP_NAME = "NuniMemo"
WORKSPACE_CONFIG_KEY = "workspace_path"
DEFAULT_FOLDER_CONFIG_KEY = "default_folder_id"
DEFAULT_CONFIG_FILE = "config.json"


@dataclass(frozen=True)
class AppPaths:
    """Resolved application paths under the user's selected Workspace folder."""

    base_dir: Path
    notes_dir: Path
    assets_dir: Path
    config_dir: Path
    database_path: Path
    config_file: Path


def get_default_app_data_dir() -> Path:
    """Return the default base application data directory (for config only)."""
    appdata = os.getenv("APPDATA")
    if not appdata:
        appdata = str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / APP_NAME


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load configuration from config.json."""
    if config_path is None:
        config_path = get_default_app_data_dir() / DEFAULT_CONFIG_FILE
    
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
        config_path = get_default_app_data_dir() / DEFAULT_CONFIG_FILE
    
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Config save error: {e}")
        return False


def get_workspace_path() -> Path | None:
    """Get the current workspace path from config, or None if not configured."""
    config = load_config()
    workspace_path = config.get(WORKSPACE_CONFIG_KEY)
    
    if workspace_path and Path(workspace_path).exists():
        return Path(workspace_path)
    
    # No valid workspace configured
    return None


def set_workspace_path(path: str | Path) -> bool:
    """Set the workspace path in config."""
    path = Path(path)
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Failed to create workspace directory: {e}")
            return False
    
    config = load_config()
    config[WORKSPACE_CONFIG_KEY] = str(path.resolve())
    return save_config(config)


def get_app_paths() -> AppPaths:
    """Build and return the application path collection based on workspace."""
    workspace = get_workspace_path()
    if workspace is None:
        raise RuntimeError("Workspace not configured. Please select a workspace folder.")
    
    config_dir = get_default_app_data_dir()
    
    return AppPaths(
        base_dir=workspace,
        notes_dir=workspace / "notes",
        assets_dir=workspace / "assets",
        config_dir=config_dir,
        database_path=workspace / "memo.db",
        config_file=config_dir / DEFAULT_CONFIG_FILE,
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


def change_workspace_path(new_path: str | Path, migrate: bool = True) -> bool:
    """Change workspace path and optionally migrate existing data."""
    new_path = Path(new_path)
    
    # Get current workspace path
    old_path = get_workspace_path()
    
    # Check if path is actually changing
    if old_path and old_path.resolve() == new_path.resolve():
        print("선택한 경로는 현재 저장 위치와 동일합니다.")
        return False  # Return False to indicate no change was made
    
    # Ensure new path exists
    try:
        new_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Failed to create workspace directory: {e}")
        return False
    
    # Migrate data if requested and old path exists
    if migrate and old_path.exists() and str(old_path) != "":
        if not migrate_data_to_new_location(old_path, new_path):
            return False
    
    # Update config
    return set_workspace_path(new_path)


def get_storage_path() -> Path:
    """Get current workspace path."""
    return get_workspace_path()


def get_default_folder_id() -> str | None:
    """Get the default folder ID from config, or None if not set."""
    config = load_config()
    return config.get(DEFAULT_FOLDER_CONFIG_KEY)


def set_default_folder_id(folder_id: str | None) -> bool:
    """Set the default folder ID in config."""
    config = load_config()
    if folder_id:
        config[DEFAULT_FOLDER_CONFIG_KEY] = folder_id
    else:
        config.pop(DEFAULT_FOLDER_CONFIG_KEY, None)
    return save_config(config)
