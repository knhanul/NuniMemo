"""Workspace selector dialog for initial setup.

Prompts user to select a workspace folder on first startup.
"""

from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from mycloudmemo.config import set_workspace_path, get_default_app_data_dir


class WorkspaceSelectorDialog(QDialog):
    """Dialog for selecting workspace folder on first startup."""

    def __init__(self, parent: QApplication | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("누니메모 - 워크스페이스 선택")
        self.setModal(True)
        self.setFixedSize(550, 320)
        self._apply_dialog_style()
        
        self.selected_path: str | None = None
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(32, 32, 32, 32)
        
        # Title
        title_label = QLabel("워크스페이스 선택", self)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: 700;
                color: #1d1d1f;
                margin-bottom: 8px;
                font-family: "Pretendard", "Apple SD Gothic Neo", "Segoe UI", sans-serif;
            }
        """)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "누니메모가 메모와 파일을 저장할 폴더를 선택해주세요.\n"
            "이 폴더는 OneDrive, Google Drive, Dropbox 등과 동기화할 수 있습니다.",
            self
        )
        desc_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #6b7280;
                line-height: 1.5;
                font-family: "Pretendard", "Apple SD Gothic Neo", "Segoe UI", sans-serif;
            }
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Default location suggestion
        default_path = get_default_app_data_dir() / "Workspace"
        self.path_input = QLineEdit(str(default_path), self)
        self.path_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.95);
                border: 1.5px solid rgba(0, 0, 0, 0.08);
                border-radius: 12px;
                padding: 16px 20px;
                font-family: "Pretendard", "Apple SD Gothic Neo", "Segoe UI", sans-serif;
                font-size: 15px;
                color: #1d1d1f;
                font-weight: 500;
            }
            QLineEdit:focus {
                border: 2px solid rgba(0, 122, 255, 0.6);
                background: rgba(255, 255, 255, 1.0);
            }
        """)
        
        # Browse button
        browse_button = QPushButton("폴더 선택...", self)
        browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_button.setStyleSheet("""
            QPushButton {
                background: rgba(0, 122, 255, 0.9);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 16px 20px;
                font-family: "Pretendard", "Apple SD Gothic Neo", "Segoe UI", sans-serif;
                font-size: 15px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton:hover {
                background: rgba(0, 122, 255, 1.0);
            }
            QPushButton:pressed {
                background: rgba(0, 122, 255, 0.8);
            }
        """)
        browse_button.clicked.connect(self._browse_folder)
        
        # Path layout
        path_layout = QHBoxLayout()
        path_layout.setSpacing(12)
        path_layout.addWidget(self.path_input, stretch=1)
        path_layout.addWidget(browse_button)
        layout.addLayout(path_layout)
        
        # Info label
        info_label = QLabel(
            "선택한 폴더에 다음이 생성됩니다:\n"
            "• memo.db (메타데이터 데이터베이스)\n"
            "• notes/ (메모 파일들)\n"
            "• assets/ (이미지 파일들)\n"
            "• structure.json (폴더 구조 정보)",
            self
        )
        info_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #6b7280;
                padding: 12px 16px;
                background-color: rgba(243, 244, 246, 0.6);
                border-radius: 8px;
                font-family: "Pretendard", "Apple SD Gothic Neo", "Segoe UI", sans-serif;
                border: 1px solid rgba(0, 0, 0, 0.05);
                line-height: 1.6;
            }
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        
        # Style the buttons
        ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setText("시작하기")
        ok_button.setStyleSheet("""
            QPushButton {
                background: rgba(0, 122, 255, 0.9);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 14px 28px;
                font-family: "Pretendard", "Apple SD Gothic Neo", "Segoe UI", sans-serif;
                font-size: 16px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton:hover {
                background: rgba(0, 122, 255, 1.0);
            }
        """)
        
        cancel_button = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setText("종료")
        cancel_button.setStyleSheet("""
            QPushButton {
                background: rgba(142, 142, 147, 0.12);
                color: #1d1d1f;
                border: none;
                border-radius: 12px;
                padding: 14px 24px;
                font-family: "Pretendard", "Apple SD Gothic Neo", "Segoe UI", sans-serif;
                font-size: 16px;
                font-weight: 600;
                min-width: 100px;
            }
            QPushButton:hover {
                background: rgba(142, 142, 147, 0.2);
            }
        """)
        
        layout.addWidget(button_box)
    
    def _browse_folder(self) -> None:
        """Open folder browser dialog."""
        current_path = self.path_input.text()
        folder = QFileDialog.getExistingDirectory(
            self,
            "워크스페이스 폴더 선택",
            current_path if Path(current_path).exists() else str(Path.home())
        )
        if folder:
            self.path_input.setText(folder)
    
    def _on_accept(self) -> None:
        """Handle OK button click."""
        path = self.path_input.text().strip()
        if not path:
            return
        
        # Create directory if it doesn't exist
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Failed to create workspace directory: {e}")
            return
        
        # Save to config
        if set_workspace_path(path):
            self.selected_path = path
            self.accept()
    
    def _apply_dialog_style(self) -> None:
        """Apply Apple-style theme to dialog."""
        self.setStyleSheet("""
            QDialog {
                background: rgba(255, 255, 255, 0.98);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 20px;
            }
        """)
    
    def get_selected_path(self) -> str | None:
        """Return the selected workspace path."""
        return self.selected_path


def show_workspace_selector(app: QApplication) -> str | None:
    """Show workspace selector dialog and return selected path."""
    dialog = WorkspaceSelectorDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_selected_path()
    return None
