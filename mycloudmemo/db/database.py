"""SQLite database access layer for NuniMemo.

This module handles metadata storage only. Actual content is stored in filesystem.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

from mycloudmemo.db.schema import SCHEMA_SQL


@dataclass(frozen=True)
class FolderRecord:
    """Folder row representation."""

    id: str
    parent_id: str | None
    name: str
    sort_order: int


@dataclass(frozen=True)
class MemoRecord:
    """Memo metadata row representation.
    
    Actual content is stored in .md files, not in database.
    """

    id: str
    folder_id: str
    title: str
    file_name: str  # Relative path like "notes/2024-03/memo_12345.md"
    is_synced: bool
    last_modified: str  # ISO format timestamp


class DatabaseManager:
    """Manage SQLite connections and common application queries."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        """Return a configured SQLite connection."""

        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        return connection

    def initialize(self) -> None:
        """Initialize the schema and seed required default records."""

        with self.connect() as connection:
            try:
                connection.executescript(SCHEMA_SQL)
                connection.commit()
            except sqlite3.OperationalError as e:
                if "no such column: sort_order" in str(e):
                    # Handle migration for existing databases
                    self._migrate_add_sort_order()
                else:
                    raise

    def _migrate_add_sort_order(self) -> None:
        """Add sort_order column to existing folders table."""

        with self.connect() as connection:
            # Add sort_order column
            connection.execute("ALTER TABLE folders ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
            
            # Create index
            connection.execute("CREATE INDEX IF NOT EXISTS idx_folders_parent_order ON folders(parent_id, sort_order)")
            
            # Update existing folders with sort order based on name
            folders = connection.execute("SELECT id, parent_id FROM folders").fetchall()
            for folder_id, parent_id in folders:
                # Get the count of siblings with lower names
                count = connection.execute(
                    "SELECT COUNT(*) FROM folders WHERE parent_id = ? AND name < (SELECT name FROM folders WHERE id = ?)",
                    (parent_id, folder_id)
                ).fetchone()[0]
                connection.execute(
                    "UPDATE folders SET sort_order = ? WHERE id = ?",
                    (count * 10, folder_id)
                )
            
            connection.commit()

    def fetch_folders(self) -> list[FolderRecord]:
        """Return folders ordered by sort_order within each parent."""

        query = """
            SELECT id, parent_id, name, sort_order
            FROM folders
            ORDER BY CASE WHEN parent_id IS NULL THEN 0 ELSE 1 END, 
                     parent_id, sort_order, name COLLATE NOCASE
        """
        with self.connect() as connection:
            rows = connection.execute(query).fetchall()
        return [
            FolderRecord(
                id=row["id"], 
                parent_id=row["parent_id"], 
                name=row["name"],
                sort_order=row["sort_order"]
            )
            for row in rows
        ]

    def fetch_memos_by_folder(self, folder_id: str) -> list[MemoRecord]:
        """Return memos for a folder ordered by last modification time."""

        query = """
            SELECT id, folder_id, title, file_name, is_synced, last_modified
            FROM memos
            WHERE folder_id = ?
            ORDER BY last_modified DESC, title COLLATE NOCASE
        """
        with self.connect() as connection:
            rows = connection.execute(query, (folder_id,)).fetchall()
        return [
            MemoRecord(
                id=row["id"],
                folder_id=row["folder_id"],
                title=row["title"],
                file_name=row["file_name"],
                is_synced=bool(row["is_synced"]),
                last_modified=row["last_modified"],
            )
            for row in rows
        ]

    def get_memo_by_id(self, memo_id: str) -> Optional[MemoRecord]:
        """Get single memo by ID."""

        query = """
            SELECT id, folder_id, title, file_name, is_synced, last_modified
            FROM memos WHERE id = ?
        """
        with self.connect() as connection:
            row = connection.execute(query, (memo_id,)).fetchone()
        if row:
            return MemoRecord(
                id=row["id"],
                folder_id=row["folder_id"],
                title=row["title"],
                file_name=row["file_name"],
                is_synced=bool(row["is_synced"]),
                last_modified=row["last_modified"],
            )
        return None

    def create_memo(self, folder_id: str, title: str, file_name: str) -> str:
        """Create a new memo record and return its ID."""

        memo_id = str(uuid.uuid4())
        
        query = """
            INSERT INTO memos (id, folder_id, title, file_name, is_synced, last_modified)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        with self.connect() as connection:
            connection.execute(query, (
                memo_id, folder_id, title, file_name, False,
                datetime.now().isoformat()
            ))
            connection.commit()
        return memo_id

    def update_memo_metadata(self, memo_id: str, title: str, is_synced: bool = False) -> bool:
        """Update memo metadata (not content)."""

        query = """
            UPDATE memos 
            SET title = ?, is_synced = ?, last_modified = ?
            WHERE id = ?
        """
        with self.connect() as connection:
            cursor = connection.execute(query, (
                title, is_synced, datetime.now().isoformat(), memo_id
            ))
            connection.commit()
        return cursor.rowcount > 0

    def delete_memo(self, memo_id: str) -> bool:
        """Delete a memo record."""

        with self.connect() as connection:
            cursor = connection.execute("DELETE FROM memos WHERE id = ?", (memo_id,))
            connection.commit()
        return cursor.rowcount > 0

    def mark_memo_synced(self, memo_id: str) -> bool:
        """Mark memo as synced."""

        query = "UPDATE memos SET is_synced = 1 WHERE id = ?"
        with self.connect() as connection:
            cursor = connection.execute(query, (memo_id,))
            connection.commit()
        return cursor.rowcount > 0

    def get_all_unsynced_memos(self) -> list[MemoRecord]:
        """Get all memos that need to be synced."""

        query = """
            SELECT id, folder_id, title, file_name, is_synced, last_modified
            FROM memos WHERE is_synced = 0
            ORDER BY last_modified DESC
        """
        with self.connect() as connection:
            rows = connection.execute(query).fetchall()
        return [
            MemoRecord(
                id=row["id"],
                folder_id=row["folder_id"],
                title=row["title"],
                file_name=row["file_name"],
                is_synced=bool(row["is_synced"]),
                last_modified=row["last_modified"]
            )
            for row in rows
        ]

    def execute(self, query: str, parameters: tuple[Any, ...] = ()) -> None:
        """Execute a write query within a managed transaction."""

        with self.connect() as connection:
            connection.execute(query, parameters)
            connection.commit()

    def create_folder(self, name: str, parent_id: str | None = None) -> str:
        """Create a new folder and return its ID."""

        folder_id = str(uuid.uuid4())
        # Get the next sort order for this parent
        sort_order = self._get_next_sort_order(parent_id)
        query = "INSERT INTO folders (id, parent_id, name, sort_order) VALUES (?, ?, ?, ?)"
        with self.connect() as connection:
            connection.execute(query, (folder_id, parent_id, name, sort_order))
            connection.commit()
        return folder_id

    def _get_next_sort_order(self, parent_id: str | None) -> int:
        """Get the next sort order for a given parent."""

        query = "SELECT MAX(sort_order) FROM folders WHERE parent_id IS ?"
        with self.connect() as connection:
            result = connection.execute(query, (parent_id,)).fetchone()
            return (result[0] or 0) + 1

    def move_folder(self, folder_id: str, new_parent_id: str | None, new_sort_order: int) -> bool:
        """Move a folder to a new parent and position."""

        if folder_id == "root":
            return False  # Cannot move root folder
        
        # Prevent moving a folder into its own descendant
        if self._is_descendant_of(new_parent_id, folder_id):
            return False
        
        query = "UPDATE folders SET parent_id = ?, sort_order = ?, modified_at = CURRENT_TIMESTAMP WHERE id = ?"
        with self.connect() as connection:
            cursor = connection.execute(query, (new_parent_id, new_sort_order, folder_id))
            connection.commit()
        return cursor.rowcount > 0

    def _is_descendant_of(self, potential_parent_id: str | None, folder_id: str) -> bool:
        """Check if potential_parent_id is a descendant of folder_id."""

        if potential_parent_id is None:
            return False
        
        folders = self.fetch_folders()
        folder_map = {f.id: f for f in folders}
        
        current_id = potential_parent_id
        while current_id and current_id in folder_map:
            if current_id == folder_id:
                return True
            current_id = folder_map[current_id].parent_id
        return False

    def reorder_folders(self, parent_id: str | None, folder_orders: list[tuple[str, int]]) -> bool:
        """Update sort orders for multiple folders in the same parent."""

        query = "UPDATE folders SET sort_order = ?, modified_at = CURRENT_TIMESTAMP WHERE id = ?"
        with self.connect() as connection:
            for folder_id, sort_order in folder_orders:
                connection.execute(query, (sort_order, folder_id))
            connection.commit()
        return True

    def delete_folder(self, folder_id: str) -> bool:
        """Delete a folder, all subfolders, and all memos. Returns True if deleted."""

        if folder_id == "root":
            return False  # Cannot delete root folder

        with self.connect() as connection:
            # Get all memo file names in this folder and subfolders before deletion
            memo_files = []
            
            # Collect memos from this folder
            cursor = connection.execute("SELECT file_name FROM memos WHERE folder_id = ?", (folder_id,))
            memo_files.extend([row[0] for row in cursor.fetchall()])
            
            # Collect memos from all subfolders recursively
            subfolder_ids = self._get_all_subfolder_ids(folder_id)
            for sub_id in subfolder_ids:
                cursor = connection.execute("SELECT file_name FROM memos WHERE folder_id = ?", (sub_id,))
                memo_files.extend([row[0] for row in cursor.fetchall()])
            
            # Delete memos from this folder and all subfolders
            all_folder_ids = [folder_id] + subfolder_ids
            for fid in all_folder_ids:
                connection.execute("DELETE FROM memos WHERE folder_id = ?", (fid,))
            
            # Delete all subfolders
            for sub_id in subfolder_ids:
                connection.execute("DELETE FROM folders WHERE id = ?", (sub_id,))
            
            # Delete the folder itself
            cursor = connection.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
            connection.commit()
            
        return cursor.rowcount > 0, memo_files

    def _get_all_subfolder_ids(self, folder_id: str) -> list[str]:
        """Recursively get all subfolder IDs for a given folder."""
        
        subfolder_ids = []
        
        def collect_subfolders(parent_id: str):
            with self.connect() as connection:
                cursor = connection.execute("SELECT id FROM folders WHERE parent_id = ?", (parent_id,))
                for row in cursor.fetchall():
                    sub_id = row[0]
                    subfolder_ids.append(sub_id)
                    collect_subfolders(sub_id)
        
        collect_subfolders(folder_id)
        return subfolder_ids
