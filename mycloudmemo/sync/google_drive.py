"""Google Drive integration for MyCloudMemo."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from mycloudmemo.config import get_app_paths


class GoogleDriveSync:
    """Handle Google Drive synchronization for memos."""

    SCOPES = ["https://www.googleapis.com/auth/drive.file"]
    APP_NAME = "MyCloudMemo"
    SYNC_FILE_NAME = "nuni_memo_data.json"

    def __init__(self) -> None:
        self.paths = get_app_paths()
        # Try bundled credentials first, then user config
        bundled_path = Path(__file__).parent / "credentials.json"
        if bundled_path.exists():
            self.credentials_path = bundled_path
        else:
            self.credentials_path = self.paths.credentials_path
        self.token_path = self.paths.token_path
        self.service = None
        self.sync_file_id = None

    def authenticate(self) -> bool:
        """Authenticate with Google Drive."""
        try:
            creds = None
            if self.token_path.exists():
                creds = Credentials.from_authorized_user_file(str(self.token_path), self.SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not self.credentials_path.exists():
                        print("Google Drive 인증 파일을 찾을 수 없습니다.")
                        print("개발자에게 연락하여 Google Drive 동기화 설정을 요청해주세요.")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                with self.token_path.open("w") as token:
                    token.write(creds.to_json())

            self.service = build("drive", "v3", credentials=creds)
            return True

        except Exception as e:
            print(f"Google Drive 인증 실패: {e}")
            return False

    def find_or_create_sync_file(self) -> Optional[str]:
        """Find existing sync file or create new one."""
        try:
            # Search for existing file
            results = (
                self.service.files()
                .list(
                    q=f"name='{self.SYNC_FILE_NAME}' and trashed=false",
                    spaces="drive",
                    fields="files(id, name, modifiedTime)",
                )
                .execute()
            )
            
            files = results.get("files", [])
            if files:
                self.sync_file_id = files[0]["id"]
                print(f"기존 동기화 파일 찾음: {files[0]['name']}")
                return files[0]["id"]

            # Create new file
            file_metadata = {
                "name": self.SYNC_FILE_NAME,
                "parents": [],  # Root folder
            }
            
            # Create empty file
            file = (
                self.service.files()
                .create(body=file_metadata, fields="id")
                .execute()
            )
            
            self.sync_file_id = file.get("id")
            print(f"새 동기화 파일 생성: {self.sync_file_id}")
            return self.sync_file_id

        except HttpError as e:
            print(f"동기화 파일 찾기/생성 실패: {e}")
            return None

    def upload_data(self, data: Dict[str, Any]) -> bool:
        """Upload memo data to Google Drive."""
        try:
            if not self.service:
                if not self.authenticate():
                    return False

            if not self.sync_file_id:
                if not self.find_or_create_sync_file():
                    return False

            # Prepare data with timestamp
            upload_data = {
                "version": "1.0",
                "app_name": self.APP_NAME,
                "last_sync": datetime.now().isoformat(),
                "data": data,
            }

            # Convert to JSON bytes
            json_data = json.dumps(upload_data, ensure_ascii=False, indent=2)
            media = MediaIoBaseUpload(
                io.BytesIO(json_data.encode('utf-8')), mimetype="application/json", resumable=True
            )

            # Upload file
            self.service.files().update(
                fileId=self.sync_file_id,
                media_body=media,
                fields="id, modifiedTime",
            ).execute()

            print("Google Drive 업로드 성공")
            return True

        except Exception as e:
            print(f"Google Drive 업로드 실패: {e}")
            return False

    def download_data(self) -> Optional[Dict[str, Any]]:
        """Download memo data from Google Drive."""
        try:
            if not self.service:
                if not self.authenticate():
                    return None

            if not self.sync_file_id:
                if not self.find_or_create_sync_file():
                    return None

            # Download file
            request = self.service.files().get_media(fileId=self.sync_file_id)
            file_io = io.BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"다운로드 진행: {int(status.progress() * 100)}%")

            # Parse JSON
            file_io.seek(0)
            content = file_io.read().decode("utf-8")
            data = json.loads(content)

            print("Google Drive 다운로드 성공")
            return data

        except Exception as e:
            print(f"Google Drive 다운로드 실패: {e}")
            return None

    def get_last_sync_time(self) -> Optional[datetime]:
        """Get last sync time from Google Drive."""
        try:
            if not self.service or not self.sync_file_id:
                return None

            file = (
                self.service.files()
                .get(fileId=self.sync_file_id, fields="modifiedTime")
                .execute()
            )
            
            modified_time = file.get("modifiedTime")
            if modified_time:
                return datetime.fromisoformat(modified_time.replace("Z", "+00:00"))
            
            return None

        except Exception as e:
            print(f"동기화 시간 확인 실패: {e}")
            return None


# Import io for MediaIoBaseUpload
import io
