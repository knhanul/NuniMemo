"""Qt application bootstrap for NuniMemo."""

from __future__ import annotations

import signal
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from mycloudmemo.config import ensure_app_directories, get_app_paths, get_workspace_path
from mycloudmemo.db.database import DatabaseManager
from mycloudmemo.sync.enhanced_manager import EnhancedSyncManager
from mycloudmemo.ui.main_window import MainWindow
from mycloudmemo.ui.workspace_dialog import show_workspace_selector

try:
    from qt_material import apply_stylesheet
except ImportError:  # pragma: no cover - optional dependency fallback
    apply_stylesheet = None


APP_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #f4f8fc;
    color: #1d232f;
    font-family: "Malgun Gothic", "Segoe UI", sans-serif;
    font-size: 13px;
}
#navigationPanel {
    background-color: #f7f9fc;
    border-right: 1px solid #dde5ef;
}
QSplitter::handle {
    background-color: #d8e3f0;
    width: 1px;
}
QLineEdit, QTextEdit, QTextBrowser {
    background-color: #ffffff;
    border: 1px solid #d9e2ec;
    border-radius: 8px;
    padding: 8px 16px;
    font-family: "Malgun Gothic", "Segoe UI", "Nanum Gothic", sans-serif;
    font-size: 13px;
    selection-background-color: #cfe7ff;
    text-indent: 0px;
}
QTreeWidget, QListWidget {
    background: transparent;
    border: none;
    outline: none;
    padding: 0px;
}
QTreeWidget {
    show-decoration-selected: 1;
}
QTreeView::branch {
    background: transparent;
}
QTreeView::branch:has-children:closed {
    image: none;
}
QTreeView::branch:has-children:open {
    image: none;
}
QTreeWidget::item, QListWidget::item {
    border-radius: 6px;
    padding: 7px 8px;
    margin: 1px 0px;
}
QListWidget::item {
    padding-left: 10px;
}
QTreeWidget::item:hover, QListWidget::item:hover {
    background-color: #eef4fb;
}
QTreeWidget::item:selected, QListWidget::item:selected {
    background-color: #dcecff;
    color: #122033;
}
QTextEdit, QTextBrowser {
    background-color: #ffffff;
    border: none;
    padding: 12px 16px;
    font-family: "Malgun Gothic", "Segoe UI", sans-serif;
    selection-background-color: #cfe7ff;
}
QPushButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1890f2, stop:1 #6fd3ff);
    border: none;
    border-radius: 22px;
    padding: 12px 28px;
    color: white;
    font-family: "Malgun Gothic", "Segoe UI", sans-serif;
    font-size: 14px;
    font-weight: 600;
    text-align: center;
    min-width: 80px;
}
QPushButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1185e6, stop:1 #5fc8f5);
}
QPushButton[navAction="true"] {
    background: #ffffff;
    border: 1px solid #d8e2ee;
    border-radius: 6px;
    padding: 6px 10px;
    color: #35506f;
    font-size: 12px;
    font-weight: 600;
    min-width: 0px;
}
QPushButton[navAction="true"]:hover {
    background: #eef5ff;
    border: 1px solid #c5daf7;
    color: #1d64c3;
}
QStatusBar {
    background-color: #eef4fa;
    border-top: 1px solid #d9e2ec;
}
QLabel[sectionTitle="true"] {
    font-family: "Malgun Gothic", "Segoe UI", sans-serif;
    font-size: 12px;
    font-weight: 700;
    color: #5b6878;
    padding: 8px 4px 6px 4px;
    letter-spacing: 0.4px;
}
QLabel[muted="true"] {
    color: #5f6b7a;
}
"""


def configure_application() -> tuple[QApplication, DatabaseManager, EnhancedSyncManager] | None:
    """Create and configure core application services."""

    app = QApplication(sys.argv)
    app.setApplicationName("NuniMemo")
    app.setQuitOnLastWindowClosed(False)

    if apply_stylesheet is not None:
        apply_stylesheet(app, theme="light_blue.xml")
    app.setStyleSheet(APP_STYLESHEET)

    # Check if workspace is configured
    if get_workspace_path() is None:
        # Show workspace selector dialog
        workspace_path = show_workspace_selector(app)
        if workspace_path is None:
            # User cancelled - exit application
            return None

    paths = ensure_app_directories(get_app_paths())
    database = DatabaseManager(paths.database_path)
    database.initialize()
    sync_manager = EnhancedSyncManager(database)
    return app, database, sync_manager


def main() -> int:
    """Run the desktop application."""

    # Handle Ctrl+C gracefully
    def signal_handler(signum, frame):
        print("\n앱을 종료합니다...")
        QApplication.quit()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    result = configure_application()
    if result is None:
        # User cancelled workspace selection
        return 0
    
    app, database, sync_manager = result
    
    # Create main window
    window = MainWindow(database=database, sync_manager=sync_manager)
    window.show()
    
    # Connect application quit signal to cleanup
    app.aboutToQuit.connect(lambda: cleanup(app, sync_manager))
    
    # Run the application
    return app.exec()


def cleanup(app: QApplication, sync_manager: EnhancedSyncManager) -> None:
    """Clean up resources before application exit."""
    try:
        print("리소스 정리 중...")
        sync_manager.shutdown()
        print("동기화 관리자 종료됨")
    except Exception as e:
        print(f"정리 중 오류 발생: {e}")
    
    # Force quit if hanging
    QTimer.singleShot(1000, app.quit)
