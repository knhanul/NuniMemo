"""API class for PyWebView JavaScript bridge.

This class provides the interface between the web frontend and Python backend,
exposing methods that can be called from JavaScript via pywebview.
"""

import json
import os
from pathlib import Path
from typing import Any

from mycloudmemo.db.database import DatabaseManager
from mycloudmemo.storage.file_manager import FileStorageManager


class WebMemoAPI:
    """API class exposed to JavaScript via PyWebView bridge."""

    def __init__(
        self,
        database: DatabaseManager,
        file_storage: FileStorageManager,
        sync_manager: Any = None
    ) -> None:
        """Initialize API with backend services."""
        self.database = database
        self.file_storage = file_storage
        self.sync_manager = sync_manager

    # ==========================================================================
    # Folder Operations
    # ==========================================================================

    def get_folders(self) -> str:
        """Get all folders as JSON string.
        
        Returns:
            JSON string containing list of folders with id, parent_id, name.
        """
        try:
            folders = self.database.fetch_folders()
            result = [
                {
                    "id": f.id,
                    "parent_id": f.parent_id,
                    "name": f.name,
                    "sort_order": f.sort_order
                }
                for f in folders
            ]
            return json.dumps({"success": True, "data": result})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def create_folder(self, parent_id: str, name: str) -> str:
        """Create a new folder.
        
        Args:
            parent_id: Parent folder ID (null for root)
            name: Folder name
            
        Returns:
            JSON string with created folder info or error.
        """
        try:
            # Database expects (name, parent_id)
            folder_id = self.database.create_folder(name, parent_id)
            return json.dumps({
                "success": True,
                "data": {"id": folder_id, "parent_id": parent_id, "name": name}
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def delete_folder(self, folder_id: str) -> str:
        """Delete a folder.
        
        Args:
            folder_id: Folder ID to delete
            
        Returns:
            JSON string with success status or error.
        """
        try:
            # Check for subfolders
            subfolder_count = self.database.count_subfolders(folder_id)
            if subfolder_count > 0:
                return json.dumps({
                    "success": False,
                    "error": f"Cannot delete folder with {subfolder_count} subfolders"
                })
            
            # Check for memos
            memo_count = self.database.count_memos_in_folder(folder_id)
            if memo_count > 0:
                return json.dumps({
                    "success": False,
                    "error": f"Cannot delete folder with {memo_count} memos"
                })
            
            self.database.delete_folder(folder_id)
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def move_folder(self, folder_id: str, new_parent_id: str, sort_order: int) -> str:
        """Move a folder to new parent.
        
        Args:
            folder_id: Folder to move
            new_parent_id: New parent folder ID
            sort_order: New sort order
            
        Returns:
            JSON string with success status.
        """
        try:
            success = self.database.move_folder(folder_id, new_parent_id, sort_order)
            return json.dumps({"success": success})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    # ==========================================================================
    # Memo Operations
    # ==========================================================================

    def get_memos(self, folder_id: str) -> str:
        """Get all memos in a folder.
        
        Args:
            folder_id: Folder ID to get memos from (root for all memos)
            
        Returns:
            JSON string containing list of memos.
        """
        try:
            # If root folder, get all memos from all folders
            if folder_id == "root":
                memos = self.database.fetch_all_memos()
            else:
                memos = self.database.fetch_memos_by_folder(folder_id)
            
            # Get folder names for hub view
            folders = self.database.fetch_folders()
            folder_map = {f.id: f.name for f in folders}
            
            result = [
                {
                    "id": m.id,
                    "folder_id": m.folder_id,
                    "folder_name": folder_map.get(m.folder_id, ""),
                    "title": m.title,
                    "file_name": m.file_name,
                    "is_synced": m.is_synced,
                    "created_at": m.created_at,
                    "last_modified": m.last_modified,
                    "updated_at": m.updated_at
                }
                for m in memos
            ]
            return json.dumps({"success": True, "data": result})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _get_file_url(self, relative_path: str) -> str:
        """Convert relative asset path to file:// URL for PyWebView preview."""
        # Get assets directory
        if hasattr(self, '_assets_path') and self._assets_path:
            assets_dir = Path(self._assets_path)
        elif hasattr(self, '_storage_path') and self._storage_path:
            assets_dir = Path(self._storage_path) / "assets"
        else:
            assets_dir = Path.home() / "NuniMemo" / "assets"
        
        # Convert relative path to absolute
        if relative_path.startswith('assets/'):
            relative_path = relative_path[7:]  # Remove 'assets/' prefix
        
        image_path = assets_dir / relative_path
        if image_path.exists():
            absolute_path = str(image_path).replace('\\', '/')
            return f"file:///{absolute_path}"
        return relative_path  # Return original if file doesn't exist

    def _convert_relative_to_base64(self, content: str) -> str:
        """Convert relative asset paths to base64 data URLs for preview."""
        import re
        import base64
        from pathlib import Path
        
        # Get assets directory
        if hasattr(self, '_assets_path') and self._assets_path:
            assets_dir = Path(self._assets_path)
        elif hasattr(self, '_storage_path') and self._storage_path:
            assets_dir = Path(self._storage_path) / "assets"
        else:
            assets_dir = Path.home() / "NuniMemo" / "assets"
        
        # Pattern to match relative asset paths in markdown
        pattern = r'!\[([^\]]*)\]\((assets/[^)]+)\)'
        
        def replace_path(match):
            alt_text = match.group(1)
            relative_path = match.group(2)
            
            # Convert to absolute path
            filename = relative_path.replace('assets/', '')
            image_path = assets_dir / filename
            
            if image_path.exists():
                try:
                    # Read file and convert to base64
                    with open(image_path, 'rb') as f:
                        image_bytes = f.read()
                    
                    # Determine mime type from extension
                    ext = image_path.suffix.lower()
                    mime_types = {
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.gif': 'image/gif',
                        '.webp': 'image/webp'
                    }
                    mime_type = mime_types.get(ext, 'image/png')
                    
                    # Convert to base64
                    base64_data = base64.b64encode(image_bytes).decode('utf-8')
                    data_url = f"data:{mime_type};base64,{base64_data}"
                    
                    return f'![{alt_text}]({data_url})'
                except Exception as e:
                    print(f"Failed to convert image to base64: {e}")
            
            return match.group(0)  # Return original if conversion fails
        
        return re.sub(pattern, replace_path, content)

    def get_memo_content(self, memo_id: str) -> str:
        """Get memo content by ID."""
        try:
            memo = self.database.get_memo_by_id(memo_id)
            if not memo:
                return json.dumps({"success": False, "error": "Memo not found"})
            
            # Load content from file
            load_method = getattr(self, '_load_memo_content', None)
            if load_method and self.file_storage is None:
                content = load_method(memo.file_name)
            elif self.file_storage:
                content = self.file_storage.load_memo_content(memo.file_name)
            else:
                content = ""
            
            # Convert relative paths to base64 for immediate preview
            content = self._convert_relative_to_base64(content)
            
            return json.dumps({
                "success": True,
                "data": {
                    "id": memo.id,
                    "title": memo.title,
                    "content": content,
                    "folder_id": memo.folder_id
                }
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def create_memo(self, folder_id: str, title: str, memo_type: str = "rich_text") -> str:
        """Create a new memo.
        
        Args:
            folder_id: Folder ID to create memo in
            title: Memo title
            memo_type: Memo type (rich_text, markdown, image)
            
        Returns:
            JSON string with created memo info.
        """
        try:
            # Generate filename using stored method or fall back
            gen_method = getattr(self, '_generate_memo_filename', None)
            if gen_method and self.file_storage is None:
                file_name = gen_method("temp")
            elif self.file_storage:
                file_name = self.file_storage._generate_memo_filename("temp")
            else:
                return json.dumps({"success": False, "error": "File storage not available"})
            
            # Create empty file using stored method
            save_method = getattr(self, '_save_memo_content', None)
            if save_method and self.file_storage is None:
                save_method("temp", "", file_name)
            elif self.file_storage:
                self.file_storage.save_memo_content("temp", "", file_name)
            else:
                return json.dumps({"success": False, "error": "File storage not available"})
            
            # Create database record with memo_type
            memo_id = self.database.create_memo(folder_id, title, file_name, memo_type)
            
            return json.dumps({
                "success": True,
                "data": {
                    "id": memo_id,
                    "folder_id": folder_id,
                    "title": title,
                    "file_name": file_name,
                    "memo_type": memo_type
                }
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def save_memo(self, memo_id: str, content: str, title: str | None = None) -> str:
        """Save memo content.
        
        Args:
            memo_id: Memo ID to save
            content: Memo HTML content
            title: Optional new title
            
        Returns:
            JSON string with success status.
        """
        try:
            memo = self.database.get_memo_by_id(memo_id)
            if not memo:
                return json.dumps({"success": False, "error": "Memo not found"})
            
            # Use stored method or fall back to file_storage
            save_method = getattr(self, '_save_memo_content', None)
            if save_method and self.file_storage is None:
                save_method(memo_id, content, memo.file_name)
            elif self.file_storage:
                self.file_storage.save_memo_content(memo_id, content, memo.file_name)
            else:
                return json.dumps({"success": False, "error": "File storage not available"})
            
            # Update title if provided
            if title:
                self.database.update_memo(memo_id, title=title)
            
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def update_memo_title(self, memo_id: str, title: str) -> str:
        """Update memo title only.
        
        Args:
            memo_id: Memo ID
            title: New title
            
        Returns:
            JSON string with success status.
        """
        try:
            # Update title in database
            self.database.update_memo(memo_id, title=title)
            
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _convert_base64_to_relative(self, content: str) -> str:
        """Convert base64 data URLs to relative paths for saving."""
        import re
        import base64
        from pathlib import Path
        from datetime import datetime

        # Get assets directory
        if hasattr(self, '_assets_path') and self._assets_path:
            assets_dir = Path(self._assets_path)
        elif hasattr(self, '_storage_path') and self._storage_path:
            assets_dir = Path(self._storage_path) / "assets"
        else:
            assets_dir = Path.home() / "NuniMemo" / "assets"

        assets_dir.mkdir(parents=True, exist_ok=True)

        # Pattern to match base64 data URLs in markdown
        pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)'

        def replace_base64(match):
            alt_text = match.group(1)
            mime_type = match.group(2)
            base64_data = match.group(3)

            # Determine extension from mime type
            ext_to_ext = {
                'png': '.png',
                'jpeg': '.jpg',
                'jpg': '.jpg',
                'gif': '.gif',
                'webp': '.webp'
            }
            ext = ext_to_ext.get(mime_type.lower(), '.png')

            # Generate unique filename with timestamp (similar to save_image)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:17]
            safe_name = f"img_{timestamp}{ext}"

            # Full path for saving
            image_path = assets_dir / safe_name

            try:
                # Decode and save
                image_bytes = base64.b64decode(base64_data)
                with open(image_path, 'wb') as f:
                    f.write(image_bytes)
                    f.flush()
                    os.fsync(f.fileno())

                return f'![{alt_text}](assets/{safe_name})'
            except Exception as e:
                print(f"Failed to save base64 image: {e}")
                return match.group(0)  # Return original if saving fails

        # Replace base64 URLs with relative paths
        content = re.sub(pattern, replace_base64, content)

        # Also convert any remaining file:// URLs
        file_pattern = r'!\[([^\]]*)\]\(file:///[^)]+\)'

        def replace_file_url(match):
            alt_text = match.group(1)
            # For file:// URLs, we can't easily recover the file, so just return a placeholder
            # Or extract filename from the URL if possible
            return f'![{alt_text}](assets/{alt_text})'

        return re.sub(file_pattern, replace_file_url, content)

    def save_memo_content(self, memo_id: str, content: str) -> str:
        """Save memo content."""
        try:
            memo = self.database.get_memo_by_id(memo_id)
            if not memo:
                return json.dumps({"success": False, "error": "Memo not found"})
            
            # Convert base64 URLs back to relative paths
            content = self._convert_base64_to_relative(content)
            
            # Save content to file
            save_method = getattr(self, '_save_memo_content', None)
            if save_method and self.file_storage is None:
                save_method(memo_id, content, memo.file_name)
            elif self.file_storage:
                self.file_storage.save_memo_content(memo_id, content, memo.file_name)
            else:
                return json.dumps({"success": False, "error": "File storage not available"})
            
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def delete_memo(self, memo_id: str) -> str:
        """Delete a memo.
        
        Args:
            memo_id: Memo ID to delete
            
        Returns:
            JSON string with success status.
        """
        try:
            memo = self.database.get_memo_by_id(memo_id)
            if not memo:
                return json.dumps({"success": False, "error": "Memo not found"})
            
            # Delete file using stored method
            del_method = getattr(self, '_delete_memo_file', None)
            if del_method and self.file_storage is None:
                del_method(memo.file_name)
            elif self.file_storage:
                self.file_storage.delete_memo_file(memo.file_name)
            
            # Delete from database
            self.database.delete_memo(memo_id)
            
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    # ==========================================================================
    # Sync Operations
    # ==========================================================================

    def sync_to_drive(self) -> str:
        """Trigger sync to Google Drive.
        
        Returns:
            JSON string with sync status.
        """
        try:
            if not self.sync_manager:
                return json.dumps({"success": False, "error": "Sync manager not available"})
            
            success = self.sync_manager.sync_to_drive()
            return json.dumps({"success": success})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def get_sync_status(self) -> str:
        """Get current sync status.
        
        Returns:
            JSON string with sync status info.
        """
        try:
            if not self.sync_manager:
                return json.dumps({"success": True, "data": {"enabled": False}})
            
            status = self.sync_manager.get_status()
            return json.dumps({"success": True, "data": status})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    # ==========================================================================
    # Storage Management
    # ==========================================================================

    def get_storage_path(self) -> str:
        """Get current storage path.
        
        Returns:
            JSON string with storage path.
        """
        try:
            # Use stored path if available, otherwise fall back to file_storage or default
            if hasattr(self, '_storage_path') and self._storage_path:
                path = self._storage_path
            elif self.file_storage:
                path = str(self.file_storage.base_path)
            else:
                path = str(Path.home() / "NuniMemo")
            return json.dumps({"success": True, "data": {"path": path}})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def select_folder_dialog(self) -> str:
        """Open folder picker dialog.
        
        Returns:
            JSON string with selected path or empty if cancelled.
        """
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            # Create hidden root window
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            # Open folder dialog
            folder_path = filedialog.askdirectory(
                title="메모 보관 폴더 선택",
                mustexist=True
            )
            
            root.destroy()
            
            if folder_path:
                return json.dumps({"success": True, "data": {"path": folder_path}})
            else:
                return json.dumps({"success": True, "data": {"path": None}})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def migrate_storage(self, new_path: str, overwrite: bool = False) -> str:
        """Migrate all memo data to new storage location.
        
        Args:
            new_path: New storage folder path
            overwrite: If True, allow overwriting existing data
            
        Returns:
            JSON string with success status.
        """
        try:
            new_base = Path(new_path)
            
            # Validate new path
            if not new_base.exists():
                return json.dumps({"success": False, "error": "Selected folder does not exist"})
            
            if not new_base.is_dir():
                return json.dumps({"success": False, "error": "Selected path is not a directory"})
            
            # Check if new path is writable
            try:
                test_file = new_base / ".write_test"
                test_file.touch()
                test_file.unlink()
            except Exception:
                return json.dumps({"success": False, "error": "Selected folder is not writable"})
            
            # Get current storage path
            if hasattr(self, '_storage_path') and self._storage_path:
                old_base = Path(self._storage_path)
            elif self.file_storage:
                old_base = self.file_storage.base_path
            else:
                old_base = Path.home() / "NuniMemo"
            
            old_base = Path(old_base)
            
            # Don't migrate if same path
            print(f"Debug: old_base = {old_base.resolve()}")
            print(f"Debug: new_base = {new_base.resolve()}")
            print(f"Debug: are they equal? {old_base.resolve() == new_base.resolve()}")
            if old_base.resolve() == new_base.resolve():
                return json.dumps({"success": False, "error": "선택한 경로는 현재 저장 위치와 동일합니다."})
            
            # Create new storage structure
            new_notes_dir = new_base / "notes"
            new_db_path = new_base / "memo.db"
            
            # Check if target already has data and warn user
            if new_db_path.exists() or new_notes_dir.exists():
                # Count existing items to show user what will be affected
                existing_memos = 0
                if new_db_path.exists():
                    try:
                        import sqlite3
                        conn = sqlite3.connect(new_db_path)
                        cursor = conn.execute("SELECT COUNT(*) FROM memos")
                        existing_memos = cursor.fetchone()[0]
                        conn.close()
                    except:
                        existing_memos = "?"
                
                if not overwrite:
                    # Ask user if they want to merge/overwrite existing data
                    return json.dumps({
                        "success": False, 
                        "error": f"Target folder already contains {existing_memos} existing memos. This will merge/overwrite existing data. Please backup the target folder first if needed."
                    })
            
            # Copy database file
            if old_base.exists():
                old_db_path = old_base / "memo.db"
                if old_db_path.exists():
                    import shutil
                    new_db_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(old_db_path, new_db_path)
                
                # Copy notes directory
                old_notes_dir = old_base / "notes"
                if old_notes_dir.exists():
                    shutil.copytree(old_notes_dir, new_notes_dir, dirs_exist_ok=True)
                
                # Copy assets directory if exists
                old_assets_dir = old_base / "assets"
                if old_assets_dir.exists():
                    new_assets_dir = new_base / "assets"
                    shutil.copytree(old_assets_dir, new_assets_dir, dirs_exist_ok=True)
            
            # Save configuration for next startup
            config_path = Path.home() / ".nunimemo" / "config.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            import json as json_lib
            config = {"storage_path": str(new_base)}
            with open(config_path, 'w', encoding='utf-8') as f:
                json_lib.dump(config, f, indent=2)
            
            # Update runtime storage paths to new location
            self._storage_path = str(new_base)
            self._assets_path = str(new_base / "assets")
            
            return json.dumps({
                "success": True, 
                "data": {
                    "message": "Storage migrated successfully. Please restart the app for full effect.",
                    "new_path": str(new_base)
                }
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def save_image(self, base64_data: str, filename: str) -> str:
        """Save base64-encoded image to assets directory and return relative path.

        Args:
            base64_data: Base64-encoded image data (data:image/...;base64,...)
            filename: Original filename

        Returns:
            JSON string with saved image path.
        """
        try:
            import base64
            import re
            from pathlib import Path
            from datetime import datetime

            # Parse base64 data
            if ',' in base64_data:
                header, data = base64_data.split(',', 1)
            else:
                data = base64_data
                header = ""

            # Determine file extension from header or original filename
            ext = Path(filename).suffix.lower()
            mime_type = "image/png"
            if not ext:
                # Try to extract from header
                if 'image/png' in header:
                    ext = '.png'
                    mime_type = 'image/png'
                elif 'image/jpeg' in header or 'image/jpg' in header:
                    ext = '.jpg'
                    mime_type = 'image/jpeg'
                elif 'image/gif' in header:
                    ext = '.gif'
                    mime_type = 'image/gif'
                elif 'image/webp' in header:
                    ext = '.webp'
                    mime_type = 'image/webp'
                else:
                    ext = '.png'  # Default
                    mime_type = 'image/png'
            else:
                ext_to_mime = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp'
                }
                mime_type = ext_to_mime.get(ext, 'image/png')

            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:17]
            safe_name = f"img_{timestamp}{ext}"

            # Determine assets directory path
            if hasattr(self, '_storage_path') and self._storage_path:
                assets_dir = Path(self._storage_path) / "assets"
            elif self.file_storage:
                assets_dir = Path(self.file_storage.base_path) / "assets"
            else:
                assets_dir = Path.home() / "NuniMemo" / "assets"

            # Ensure assets directory exists
            assets_dir.mkdir(parents=True, exist_ok=True)

            # Full path for saving
            image_path = assets_dir / safe_name

            # Decode and save
            image_bytes = base64.b64decode(data)
            with open(image_path, 'wb') as f:
                f.write(image_bytes)
                f.flush()
                os.fsync(f.fileno())

            data_uri = f"data:{mime_type};base64,{data}"
            print(f"DEBUG: Returning data_uri: {data_uri[:50]}...")
            print(f"DEBUG: Returning path: assets/{safe_name}")

            return json.dumps({
                "success": True,
                "data": {
                    "data_uri": data_uri,
                    "path": f"assets/{safe_name}",
                    "relative_path": f"assets/{safe_name}",
                    "filename": safe_name
                }
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def get_default_folder(self) -> str:
        """Get the default folder ID from config.

        Returns:
            JSON string with default folder ID or None.
        """
        try:
            from mycloudmemo.config import get_default_folder_id
            folder_id = get_default_folder_id()
            return json.dumps({"success": True, "data": {"folder_id": folder_id}})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def set_default_folder(self, folder_id: str | None) -> str:
        """Set the default folder ID in config.

        Args:
            folder_id: Folder ID to set as default, or None to clear.

        Returns:
            JSON string with success status.
        """
        try:
            from mycloudmemo.config import set_default_folder_id
            success = set_default_folder_id(folder_id)
            return json.dumps({"success": success})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def move_memo(self, memo_id: str, folder_id: str, sort_order: int) -> str:
        """Move a memo to a different folder and/or change its sort order.
        
        Args:
            memo_id: Memo ID to move
            folder_id: Target folder ID
            sort_order: New sort order position
            
        Returns:
            JSON string with success status.
        """
        try:
            self.database.move_memo(memo_id, folder_id, sort_order)
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
