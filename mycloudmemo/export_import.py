"""
Data export and import functionality for NuniMemo
"""

import json
import sqlite3
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class NuniMemoExporter:
    """Handle data export operations"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = Path(workspace_path)
        self.db_path = self.workspace_path / "memo.db"
        self.notes_dir = self.workspace_path / "notes"
        self.assets_dir = self.workspace_path / "assets"
    
    def export_to_zip(self, export_path: Path, include_assets: bool = True) -> Dict[str, Any]:
        """Export all data to a ZIP file"""
        try:
            print(f"Debug: Starting export to {export_path}")
            print(f"Debug: Include assets: {include_assets}")
            
            export_data = {
                "version": "1.0",
                "export_date": datetime.now().isoformat(),
                "workspace_name": self.workspace_path.name,
                "folders": [],
                "memos": [],
                "assets_included": include_assets
            }
            
            # Export database data
            if self.db_path.exists():
                print(f"Debug: Exporting folders...")
                export_data["folders"] = self._export_folders()
                print(f"Debug: Found {len(export_data['folders'])} folders")
                
                print(f"Debug: Exporting memos...")
                export_data["memos"] = self._export_memos()
                print(f"Debug: Found {len(export_data['memos'])} memos in export_data")
            else:
                print(f"Debug: Database file not found at {self.db_path}")
            
            # Create ZIP file
            print(f"Debug: Creating ZIP file...")
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add metadata
                metadata_json = json.dumps(export_data, indent=2, ensure_ascii=False)
                zipf.writestr("metadata.json", metadata_json)
                print(f"Debug: Added metadata.json")
                
                # Add database
                if self.db_path.exists():
                    zipf.write(self.db_path, "memo.db")
                    print(f"Debug: Added database file")
                
                # Add notes files
                if self.notes_dir.exists():
                    note_files_added = 0
                    for note_file in self.notes_dir.rglob("*"):
                        if note_file.is_file():
                            zipf.write(note_file, note_file.relative_to(self.notes_dir))
                            note_files_added += 1
                    print(f"Debug: Added {note_files_added} note files")
                
                # Add assets if requested
                if include_assets and self.assets_dir.exists():
                    asset_files_added = 0
                    for asset_file in self.assets_dir.rglob("*"):
                        if asset_file.is_file():
                            zipf.write(asset_file, asset_file.relative_to(self.assets_dir))
                            asset_files_added += 1
                    print(f"Debug: Added {asset_files_added} asset files")
            
            print(f"Debug: Export completed successfully")
            return {
                "success": True,
                "export_path": str(export_path),
                "stats": {
                    "folders": len(export_data["folders"]),
                    "memos": len(export_data["memos"]),
                    "assets": include_assets and self.assets_dir.exists(),
                    "assets_included": include_assets
                }
            }
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return {
                "success": False,
                "error": f"내보내기 실패: {str(e)}"
            }
    
    def _export_folders(self) -> List[Dict[str, Any]]:
        """Export folders from database"""
        folders = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, parent_id, name, created_at, modified_at 
                    FROM folders 
                    ORDER BY parent_id, name
                """)
                
                for row in cursor.fetchall():
                    folders.append({
                        "id": row[0],
                        "parent_id": row[1],
                        "name": row[2],
                        "created_at": row[3],
                        "updated_at": row[4]
                    })
        except Exception as e:
            logger.error(f"Failed to export folders: {e}")
        
        return folders
    
    def _export_memos(self) -> List[Dict[str, Any]]:
        """Export memos from database"""
        memos = []
        try:
            print(f"Debug: Exporting from workspace: {self.workspace_path}")
            print(f"Debug: Database path: {self.db_path}")
            print(f"Debug: Notes directory: {self.notes_dir}")
            print(f"Debug: Database exists: {self.db_path.exists()}")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, folder_id, title, file_name, memo_type, is_synced, last_modified, created_at, updated_at
                    FROM memos 
                    ORDER BY folder_id, created_at
                """)
                
                all_rows = cursor.fetchall()
                print(f"Debug: Found {len(all_rows)} memos in database")
                
                for i, row in enumerate(all_rows):
                    print(f"Debug: Processing memo {i+1}/{len(all_rows)}: {row[0]}")
                    print(f"Debug:   title={row[2]}, file_name={row[3]}")
                    
                    memo_data = {
                        "id": row[0],
                        "folder_id": row[1],
                        "title": row[2],
                        "file_name": row[3],
                        "memo_type": row[4],
                        "is_synced": bool(row[5]),
                        "last_modified": row[6],
                        "created_at": row[7],
                        "updated_at": row[8]
                    }
                    
                    # Add content from notes file
                    note_file = self.workspace_path / row[3]
                    print(f"Debug: Looking for file at {note_file}")
                    print(f"Debug: File exists: {note_file.exists()}")
                    
                    if note_file.exists():
                        print(f"Debug: Reading file content")
                        with open(note_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            memo_data["content"] = content
                            print(f"Debug: Content length: {len(content)} chars")
                    else:
                        print(f"Debug: File not found!")
                        memo_data["content"] = ""
                    
                    memos.append(memo_data)
                    print(f"Debug: Memo added to export list (total: {len(memos)})")
                    
        except Exception as e:
            logger.error(f"Failed to export memos: {e}")
            print(f"Debug: Exception in _export_memos: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"Debug: Final export list contains {len(memos)} memos")
        return memos


class NuniMemoImporter:
    """Handle data import operations"""
    
    def __init__(self, target_workspace: Path):
        self.target_workspace = Path(target_workspace)
        self.db_path = self.target_workspace / "memo.db"
        self.notes_dir = self.target_workspace / "notes"
        self.assets_dir = self.target_workspace / "assets"
    
    def import_from_zip(self, zip_path: Path, merge_mode: bool = False) -> Dict[str, Any]:
        """Import data from ZIP file"""
        try:
            # Create backup if not merging
            if not merge_mode and self.db_path.exists():
                backup_path = self._create_backup()
                logger.info(f"Created backup: {backup_path}")
            
            # Extract and validate ZIP
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                # Read metadata
                if "metadata.json" not in zipf.namelist():
                    return {"success": False, "error": "잘못된 내보내기 파일입니다"}
                
                metadata = json.loads(zipf.read("metadata.json").decode('utf-8'))
                
                # Extract to temp directory
                temp_dir = self.target_workspace / "temp_import"
                temp_dir.mkdir(exist_ok=True)
                zipf.extractall(temp_dir)
            
            # Import data
            stats = self._import_data(temp_dir, metadata, merge_mode)
            
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return {
                "success": True,
                "message": f"데이터가 성공적으로 가져왔습니다. (병합 모드: {'ON' if merge_mode else 'OFF'})",
                "stats": stats,
                "source_version": metadata.get("version", "unknown"),
                "source_date": metadata.get("export_date", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return {
                "success": False,
                "error": f"가져오기 실패: {str(e)}"
            }
    
    def _create_backup(self) -> Path:
        """Create backup of current data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.target_workspace.parent / f"{self.target_workspace.name}_backup_{timestamp}"
        shutil.copytree(self.target_workspace, backup_path)
        return backup_path
    
    def _import_data(self, temp_dir: Path, metadata: Dict[str, Any], merge_mode: bool) -> Dict[str, Any]:
        """Import data from extracted directory"""
        stats = {"folders": 0, "memos": 0, "assets": 0}
        
        # Ensure directories exist
        self.notes_dir.mkdir(exist_ok=True)
        self.assets_dir.mkdir(exist_ok=True)
        
        # Copy database
        temp_db = temp_dir / "memo.db"
        if temp_db.exists():
            if merge_mode:
                self._merge_database(temp_db, stats)
            else:
                shutil.copy2(temp_db, self.db_path)
                # Count imported items
                with sqlite3.connect(self.db_path) as conn:
                    stats["folders"] = conn.execute("SELECT COUNT(*) FROM folders").fetchone()[0]
                    stats["memos"] = conn.execute("SELECT COUNT(*) FROM memos").fetchone()[0]
        
        # Copy notes
        temp_notes = temp_dir / "notes"
        if temp_notes.exists():
            for note_file in temp_notes.rglob("*.md"):
                dest_file = self.notes_dir / note_file.relative_to(temp_notes)
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(note_file, dest_file)
                if not merge_mode:
                    stats["memos"] += 1
        
        # Copy assets if included
        if metadata.get("assets_included", False):
            temp_assets = temp_dir / "assets"
            if temp_assets.exists():
                for asset_file in temp_assets.rglob("*"):
                    if asset_file.is_file():
                        dest_file = self.assets_dir / asset_file.relative_to(temp_assets)
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(asset_file, dest_file)
                        stats["assets"] += 1
        
        return stats
    
    def _merge_database(self, temp_db_path: Path, stats: Dict[str, Any]) -> None:
        """Merge database contents"""
        # This is a simplified merge - in production, you'd want more sophisticated conflict resolution
        with sqlite3.connect(self.db_path) as target_conn:
            with sqlite3.connect(temp_db_path) as source_conn:
                
                # Merge folders
                source_folders = source_conn.execute("SELECT * FROM folders").fetchall()
                for folder in source_folders:
                    try:
                        target_conn.execute("""
                            INSERT OR IGNORE INTO folders 
                            (id, parent_id, name, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, folder)
                        if target_conn.rowcount > 0:
                            stats["folders"] += 1
                    except sqlite3.IntegrityError:
                        pass  # Folder already exists
                
                # Merge memos
                source_memos = source_conn.execute("SELECT * FROM memos").fetchall()
                for memo in source_memos:
                    try:
                        target_conn.execute("""
                            INSERT OR IGNORE INTO memos 
                            (id, folder_id, title, memo_type, created_at, updated_at, last_modified, is_synced)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, memo)
                        if target_conn.rowcount > 0:
                            stats["memos"] += 1
                    except sqlite3.IntegrityError:
                        pass  # Memo already exists


def export_workspace(workspace_path: str, export_path: str, include_assets: bool = True) -> str:
    """Export workspace data"""
    print(f"Debug: export_workspace called with workspace_path={workspace_path}")
    print(f"Debug: export_workspace called with export_path={export_path}")
    print(f"Debug: export_workspace called with include_assets={include_assets}")
    
    workspace = Path(workspace_path)
    export_file = Path(export_path)
    
    print(f"Debug: workspace exists: {workspace.exists()}")
    
    if not workspace.exists():
        return json.dumps({"success": False, "error": "워크스페이스가 존재하지 않습니다"})
    
    print(f"Debug: Creating NuniMemoExporter with workspace: {workspace}")
    exporter = NuniMemoExporter(workspace)
    result = exporter.export_to_zip(export_file, include_assets)
    print(f"Debug: exporter returned result: {result}")
    return json.dumps(result, ensure_ascii=False)


def import_workspace(zip_path: str, target_workspace: str, merge_mode: bool = False) -> str:
    """Import workspace data"""
    import_file = Path(zip_path)
    target = Path(target_workspace)
    
    if not import_file.exists():
        return json.dumps({"success": False, "error": "가져올 파일이 존재하지 않습니다"})
    
    if not import_file.suffix.lower() == '.zip':
        return json.dumps({"success": False, "error": "ZIP 파일만 지원됩니다"})
    
    # Create target workspace if it doesn't exist
    target.mkdir(parents=True, exist_ok=True)
    
    importer = NuniMemoImporter(target)
    result = importer.import_from_zip(import_file, merge_mode)
    return json.dumps(result, ensure_ascii=False)
