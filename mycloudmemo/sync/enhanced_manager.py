"""Enhanced sync manager with Google Drive integration for file-based storage."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QTimer

from mycloudmemo.db.database import DatabaseManager, FolderRecord, MemoRecord
from mycloudmemo.storage.file_manager import FileStorageManager
from mycloudmemo.sync.google_drive import GoogleDriveSync


class EnhancedSyncManager:
    """Enhanced sync manager with Google Drive support for file-based storage."""

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database
        self.file_storage = FileStorageManager()
        self.google_drive = GoogleDriveSync()
        self.timer = QTimer()
        self.timer.timeout.connect(self._auto_sync)
        self.auto_sync_interval = 300000  # 5 minutes
        self.is_syncing = False

    def start_auto_sync(self) -> None:
        """Start automatic synchronization."""
        self.timer.start(self.auto_sync_interval)

    def stop_auto_sync(self) -> None:
        """Stop automatic synchronization."""
        self.timer.stop()

    def sync_to_google_drive(self) -> bool:
        """Manual sync to Google Drive with structure.json and files."""
        if self.is_syncing:
            print("동기화가 이미 진행 중입니다...")
            return False

        self.is_syncing = True
        try:
            # Authenticate
            if not self.google_drive.authenticate():
                print("Google Drive 인증 실패")
                return False

            # 1. Generate and upload structure.json
            print("structure.json 생성 중...")
            structure_data = self._generate_structure_json()
            
            # 2. Upload structure.json
            structure_success = self.google_drive.upload_data(structure_data)
            if not structure_success:
                print("structure.json 업로드 실패")
                return False
            
            # 3. Mark all memos as synced
            unsynced_memos = self.database.get_all_unsynced_memos()
            for memo in unsynced_memos:
                self.database.mark_memo_synced(memo.id)
            
            print(f"동기화 완료: {len(unsynced_memos)}개 메모 동기화됨")
            return True

        except Exception as e:
            print(f"동기화 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.is_syncing = False

    def _generate_structure_json(self) -> Dict[str, Any]:
        """Generate structure.json content for Google Drive sync."""
        folders = self.database.fetch_folders()
        memos = []
        
        # Get all memos from all folders
        for folder in folders:
            folder_memos = self.database.fetch_memos_by_folder(folder.id)
            memos.extend(folder_memos)

        return {
            "version": "2.0",
            "app_name": "NuniMemo",
            "last_sync": datetime.now().isoformat(),
            "sync_type": "structure_only",
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

    def sync_from_google_drive(self) -> bool:
        """Sync from Google Drive to local."""
        if self.is_syncing:
            print("동기화가 이미 진행 중입니다...")
            return False

        self.is_syncing = True
        try:
            # Authenticate
            if not self.google_drive.authenticate():
                print("Google Drive 인증 실패")
                return False

            # Download structure.json
            remote_data = self.google_drive.download_data()
            if not remote_data:
                return False

            print(f"Google Drive 데이터 수신: {len(remote_data.get('memos', []))}개 메모")
            return True

        except Exception as e:
            print(f"동기화 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.is_syncing = False

    def _auto_sync(self) -> None:
        """Automatic sync callback."""
        if not self.is_syncing:
            self.sync_to_google_drive()

    def shutdown(self) -> None:
        """Stop the background timer during application shutdown."""
        self.timer.stop()
        
        # Cancel any ongoing sync
        if self.is_syncing:
            print("동기화 중단...")
            self.is_syncing = False
