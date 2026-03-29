"""File storage manager for NuniMemo.

Handles saving/loading .md files and managing assets folder.
Content is stored in filesystem, not database.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QBuffer
from PySide6.QtGui import QPixmap

from mycloudmemo.config import get_app_paths, AppPaths


class FileStorageManager:
    """Manages file-based storage for memos and assets."""

    def __init__(self, paths: AppPaths | None = None) -> None:
        self.paths = paths or get_app_paths()
        # Ensure directories exist
        self.paths.notes_dir.mkdir(parents=True, exist_ok=True)
        self.paths.assets_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def notes_dir(self) -> str:
        """Get the notes directory path as string."""
        if hasattr(self, '_notes_dir'):
            return self._notes_dir
        elif hasattr(self, 'paths'):
            return str(self.paths.notes_dir)
        else:
            raise AttributeError("Notes directory not set")

    @property
    def assets_dir(self) -> str:
        """Get the assets directory path as string."""
        if hasattr(self, '_assets_dir'):
            return self._assets_dir
        elif hasattr(self, 'paths'):
            return str(self.paths.assets_dir)
        else:
            raise AttributeError("Assets directory not set")

    def _generate_memo_filename(self, memo_id: str) -> str:
        """Generate a unique filename for a memo."""
        now = datetime.now()
        date_folder = now.strftime("%Y-%m")
        filename = f"memo_{memo_id[:8]}_{now.strftime('%H%M%S')}.md"
        return f"{date_folder}/{filename}"

    def save_memo_content(self, memo_id: str, content: str, existing_file_name: str | None = None) -> str:
        """Save memo content to .md file. Returns the file path."""

        if existing_file_name:
            file_path = self.paths.notes_dir / existing_file_name
        else:
            # Generate new filename
            file_name = self._generate_memo_filename(memo_id)
            file_path = self.paths.notes_dir / file_name
            existing_file_name = file_name

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content to file
        file_path.write_text(content, encoding='utf-8')

        return existing_file_name

    def load_memo_content(self, file_name: str) -> str:
        """Load memo content from .md file."""

        file_path = self.paths.notes_dir / file_name
        if file_path.exists():
            return file_path.read_text(encoding='utf-8')
        return ""

    def delete_memo_file(self, file_name: str) -> bool:
        """Delete a memo file."""

        file_path = self.paths.notes_dir / file_name
        if file_path.exists():
            file_path.unlink()
            # Try to remove empty parent directory
            try:
                file_path.parent.rmdir()
            except OSError:
                pass  # Directory not empty
            return True
        return False

    def save_image_from_clipboard(self, pixmap: QPixmap) -> str:
        """Save clipboard image to assets folder. Returns relative path."""

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"image_{timestamp}.png"
        file_path = self.paths.assets_dir / filename

        # Save image
        pixmap.save(str(file_path), "PNG")

        # Return relative path for markdown
        return f"assets/{filename}"

    def get_image_absolute_path(self, relative_path: str) -> Path:
        """Convert relative asset path to absolute path."""

        # Remove 'assets/' prefix if present
        if relative_path.startswith("assets/"):
            relative_path = relative_path[7:]

        return self.paths.assets_dir / relative_path

    def get_memo_absolute_path(self, file_name: str) -> Path:
        """Get absolute path for a memo file."""

        return self.paths.notes_dir / file_name

    def list_all_files(self) -> dict[str, list[Path]]:
        """List all memo and asset files for sync."""

        memos = list(self.paths.notes_dir.rglob("*.md"))
        assets = list(self.paths.assets_dir.rglob("*"))
        # Filter out directories
        assets = [f for f in assets if f.is_file()]

        return {
            "memos": memos,
            "assets": assets,
        }

    def generate_structure_json(self, folders: list, memos: list) -> dict:
        """Generate structure.json content for Google Drive sync."""

        return {
            "version": "1.0",
            "app_name": "NuniMemo",
            "last_sync": datetime.now().isoformat(),
            "folders": [
                {
                    "id": f.id,
                    "parent_id": f.parent_id,
                    "name": f.name,
                    "sort_order": f.sort_order,
                }
                for f in folders
            ],
            "memos": [
                {
                    "id": m.id,
                    "folder_id": m.folder_id,
                    "title": m.title,
                    "file_name": m.file_name,
                    "is_synced": m.is_synced,
                    "last_modified": m.last_modified,
                }
                for m in memos
            ],
        }
