"""Background synchronization manager scaffold."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from mycloudmemo.db.database import DatabaseManager


class SyncWorker(QObject):
    """Worker object responsible for performing periodic sync operations."""

    sync_started = Signal()
    sync_finished = Signal(bool, str)

    def __init__(self, database: DatabaseManager) -> None:
        super().__init__()
        self.database = database

    def sync(self) -> None:
        """Run a sync pass.

        This scaffold emits success without cloud interaction yet. The real Google
        Drive implementation can later inspect dirty notes and upload changes.
        """

        self.sync_started.emit()
        self.sync_finished.emit(True, "Sync scaffold ready")


class SyncManager(QObject):
    """Manage a background thread and debounce-triggered sync requests."""

    sync_status_changed = Signal(str)

    def __init__(self, database: DatabaseManager, interval_ms: int = 30000) -> None:
        super().__init__()
        self.database = database
        self.thread = QThread()
        self.worker = SyncWorker(database)
        self.worker.moveToThread(self.thread)
        self.worker.sync_started.connect(lambda: self.sync_status_changed.emit("Syncing..."))
        self.worker.sync_finished.connect(self._handle_sync_finished)
        self.thread.start()

        self.timer = QTimer(self)
        self.timer.setInterval(interval_ms)
        self.timer.timeout.connect(self.request_sync)
        self.timer.start()

    def request_sync(self) -> None:
        """Request a background sync run."""

        self.worker.sync()

    def shutdown(self) -> None:
        """Stop the background thread cleanly during application shutdown."""

        self.timer.stop()
        self.thread.quit()
        self.thread.wait()

    def _handle_sync_finished(self, success: bool, message: str) -> None:
        """Update sync status when a sync run completes."""

        status = message if success else f"Sync failed: {message}"
        self.sync_status_changed.emit(status)
