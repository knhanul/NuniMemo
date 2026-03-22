"""Google OAuth2 helpers for desktop login and token refresh."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from mycloudmemo.config import DRIVE_ROOT_FOLDER_NAME, ensure_app_directories, get_app_paths

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GoogleAuthError(RuntimeError):
    """Raised when Google authentication cannot be completed."""


@dataclass
class AuthSession:
    """Result of a Google authentication request."""

    credentials: Credentials
    drive_root_folder_name: str = DRIVE_ROOT_FOLDER_NAME


class GoogleAuthManager:
    """Handle OAuth credential loading, login flow, and token persistence."""

    def __init__(self, credentials_path: Path | None = None, token_path: Path | None = None) -> None:
        paths = ensure_app_directories(get_app_paths())
        self.credentials_path = Path(credentials_path or paths.credentials_path)
        self.token_path = Path(token_path or paths.token_path)

    def load_credentials(self) -> Credentials | None:
        """Load persisted credentials from disk if available."""

        if not self.token_path.exists():
            return None
        credentials = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        return credentials

    def get_valid_credentials(self) -> Credentials | None:
        """Return valid credentials, refreshing an expired token when possible."""

        credentials = self.load_credentials()
        if not credentials:
            return None
        if credentials.valid:
            return credentials
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            self.save_credentials(credentials)
            return credentials
        return None

    def authenticate(self) -> AuthSession:
        """Perform desktop OAuth flow and persist the resulting credentials."""

        credentials = self.get_valid_credentials()
        if credentials is None:
            if not self.credentials_path.exists():
                raise GoogleAuthError(
                    "Missing Google OAuth client configuration. "
                    f"Expected client secret at: {self.credentials_path}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path),
                SCOPES,
            )
            credentials = flow.run_local_server(port=0)
            self.save_credentials(credentials)
        return AuthSession(credentials=credentials)

    def save_credentials(self, credentials: Credentials) -> None:
        """Persist authorized user credentials to disk."""

        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(credentials.to_json(), encoding="utf-8")
