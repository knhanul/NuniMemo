"""Main application window for NuniMemo.

Unified WYSIWYG editor with file-based storage.
"""

from __future__ import annotations
import os
import re
from pathlib import Path
from PySide6.QtCore import Qt, QMimeData, QTimer, QBuffer, Signal, QRect, QPoint, QSize
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QPixmap, QDrag, QClipboard, QPainter, QPen, QColor, QCursor, QTextCursor, QBrush, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QSpinBox,
    QStatusBar,
    QSystemTrayIcon,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QMenu,
    QLineEdit,
    QDialog,
    QDialogButtonBox,
    QStyle,
    QCheckBox,
    QFileDialog,
    QGraphicsDropShadowEffect,
)

from mycloudmemo.ui.ui_mainwindow import Ui_MainWindow

from mycloudmemo.db.database import DatabaseManager, FolderRecord, MemoRecord
from mycloudmemo.storage.file_manager import FileStorageManager
from mycloudmemo.sync.enhanced_manager import EnhancedSyncManager
from mycloudmemo.config import get_storage_path, change_workspace_path, get_app_paths


class ImageResizeDialog(QDialog):
    """Dialog for resizing images in the editor."""
    
    def __init__(self, parent=None, current_width=None, current_height=None):
        super().__init__(parent)
        self.setWindowTitle("이미지 크기 조정")
        self.setModal(True)
        self.resize(400, 200)
        
        layout = QVBoxLayout(self)
        
        # Size inputs
        size_layout = QHBoxLayout()
        
        # Width
        width_layout = QVBoxLayout()
        width_layout.addWidget(QLabel("너비 (px):"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 2000)
        self.width_spin.setValue(current_width or 400)
        self.width_spin.setSuffix(" px")
        width_layout.addWidget(self.width_spin)
        size_layout.addLayout(width_layout)
        
        # Height
        height_layout = QVBoxLayout()
        height_layout.addWidget(QLabel("높이 (px):"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 2000)
        self.height_spin.setValue(current_height or 300)
        self.height_spin.setSuffix(" px")
        height_layout.addWidget(self.height_spin)
        size_layout.addLayout(height_layout)
        
        # Maintain aspect ratio
        self.maintain_aspect = QCheckBox("가로세로 비율 유지")
        self.maintain_aspect.setChecked(True)
        size_layout.addWidget(self.maintain_aspect)
        
        layout.addLayout(size_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Connect aspect ratio maintenance
        self.width_spin.valueChanged.connect(self._on_width_changed)
        self.height_spin.valueChanged.connect(self._on_height_changed)
        
        # Store original aspect ratio
        if current_width and current_height:
            self.aspect_ratio = current_width / current_height
        else:
            self.aspect_ratio = 4 / 3  # Default ratio
    
    def _on_width_changed(self, value):
        """Maintain aspect ratio when width changes."""
        if self.maintain_aspect.isChecked():
            new_height = int(value / self.aspect_ratio)
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(new_height)
            self.height_spin.blockSignals(False)
    
    def _on_height_changed(self, value):
        """Maintain aspect ratio when height changes."""
        if self.maintain_aspect.isChecked():
            new_width = int(value * self.aspect_ratio)
            self.width_spin.blockSignals(True)
            self.width_spin.setValue(new_width)
            self.width_spin.blockSignals(False)
    
    def get_size(self):
        """Return the selected size as (width, height)."""
        return self.width_spin.value(), self.height_spin.value()


class WysiwygTextEdit(QTextEdit):
    """Custom QTextEdit with image resize functionality."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        
        # Resize functionality
        self._resizing = False
        self._resize_cursor = None  # 'nw', 'ne', 'sw', 'se'
        self._resize_start_pos = QPoint()
        self._resize_start_rect = QRect()
        self._resize_image_cursor = None
        self._hover_image_rect = QRect()
        self._handle_size = 8
        self._aspect_ratio_locked = True
        
        # Set up mouse tracking
        self.setMouseTracking(True)
        
        # Timer for updating hover state
        self._hover_timer = QTimer()
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._update_hover_state)
    
    def mousePressEvent(self, event) -> None:  # noqa: N802
        """Handle mouse press for resize handles."""
        if event.button() == Qt.MouseButton.LeftButton:
            cursor = self._image_cursor_at(event.pos())
            image_rect = self._get_image_rect(cursor)
            
            if image_rect.isValid():
                resize_cursor = self._get_resize_cursor(event.pos(), image_rect)
                if resize_cursor:
                    self._resizing = True
                    self._resize_cursor = resize_cursor
                    self._resize_start_pos = event.pos()
                    self._resize_start_rect = image_rect
                    self._resize_image_cursor = cursor
                    event.accept()
                    return
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        """Handle mouse move for resize cursors and dragging."""
        if self._resizing and self._resize_image_cursor:
            self._perform_resize(event.pos())
            event.accept()
            return
        
        cursor = self._image_cursor_at(event.pos())
        image_rect = self._get_image_rect(cursor)
        
        if image_rect.isValid():
            resize_cursor = self._get_resize_cursor(event.pos(), image_rect)
            if resize_cursor:
                # Set appropriate cursor for all 8 directions
                if resize_cursor in ['nw', 'se']:
                    self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
                elif resize_cursor in ['ne', 'sw']:
                    self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
                elif resize_cursor in ['n', 's']:
                    self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
                else:  # 'e', 'w'
                    self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
                
                self._hover_image_rect = image_rect
                self._hover_timer.start(50)  # Delay for hover update
            else:
                # Still hovering over image but not on handle
                self.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
                self._hover_image_rect = image_rect
                self._hover_timer.start(50)
        else:
            self.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
            self._hover_image_rect = QRect()
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        """Handle mouse release to finish resizing."""
        if self._resizing and event.button() == Qt.MouseButton.LeftButton:
            self._finish_resize()
            self._resizing = False
            self._resize_cursor = None
            self._resize_image_cursor = None
            self.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
            event.accept()
            return
        
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        """Handle double-click events for image resizing."""
        cursor = self._image_cursor_at(event.pos())
        
        if cursor is not None:
            image_format = cursor.charFormat().toImageFormat()
            if image_format:
                current_width = image_format.width()
                current_height = image_format.height()

                # Ensure we have valid dimensions
                if current_width <= 0:
                    current_width = 400
                if current_height <= 0:
                    current_height = 300

                dialog = ImageResizeDialog(self, current_width, current_height)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    new_width, new_height = dialog.get_size()
                    self._apply_image_size(cursor, new_width, new_height)

                event.accept()
                return
        
        # Handle normal double-click
        super().mouseDoubleClickEvent(event)
    
    def paintEvent(self, event) -> None:  # noqa: N802
        """Paint resize handles on hover."""
        super().paintEvent(event)
        
        if self._hover_image_rect.isValid() and not self._resizing:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            
            try:
                # Draw a border around the image
                painter.setPen(QPen(QColor(64, 158, 255), 2))
                painter.setBrush(QBrush())  # Empty brush for border only
                painter.drawRect(self._hover_image_rect)
                
                # Draw all 8 handles (corners + edges)
                handle_size = self._handle_size
                
                # Corner handles
                corners = [
                    self._hover_image_rect.topLeft(),
                    self._hover_image_rect.topRight(),
                    self._hover_image_rect.bottomLeft(),
                    self._hover_image_rect.bottomRight()
                ]
                
                # Edge handles
                edges = [
                    QPoint(self._hover_image_rect.left() + self._hover_image_rect.width() // 2, self._hover_image_rect.top()),  # Top
                    QPoint(self._hover_image_rect.right(), self._hover_image_rect.top() + self._hover_image_rect.height() // 2),  # Right
                    QPoint(self._hover_image_rect.left() + self._hover_image_rect.width() // 2, self._hover_image_rect.bottom()),  # Bottom
                    QPoint(self._hover_image_rect.left(), self._hover_image_rect.top() + self._hover_image_rect.height() // 2),  # Left
                ]
                
                painter.setPen(QPen(QColor(64, 158, 255), 1))
                painter.setBrush(QColor(64, 158, 255, 200))
                
                # Draw corner handles
                for corner in corners:
                    handle_rect = QRect(
                        corner.x() - handle_size // 2,
                        corner.y() - handle_size // 2,
                        handle_size,
                        handle_size
                    )
                    painter.drawRect(handle_rect)
                    painter.fillRect(handle_rect, QColor(64, 158, 255, 200))
                
                # Draw edge handles (slightly smaller)
                painter.setBrush(QColor(64, 158, 255, 150))
                for edge in edges:
                    handle_rect = QRect(
                        edge.x() - handle_size // 2,
                        edge.y() - handle_size // 2,
                        handle_size,
                        handle_size
                    )
                    painter.drawRect(handle_rect)
                    painter.fillRect(handle_rect, QColor(64, 158, 255, 180))
                    
            finally:
                painter.end()
    
    def _get_image_rect(self, cursor) -> QRect:
        """Get the rectangle of the image at cursor position."""
        if cursor is None or not cursor.charFormat().isImageFormat():
            return QRect()
        
        image_format = cursor.charFormat().toImageFormat()
        if not image_format:
            return QRect()

        # Get image dimensions
        image_width = image_format.width()
        image_height = image_format.height()
        
        # In QTextEdit, the cursor for an inline image often resolves to the
        # position immediately after the image. Shift back by the image width
        # so the overlay aligns with the actual rendered image bounds.
        cursor_rect = self.cursorRect(cursor)

        x = cursor_rect.left() - int(image_width)
        if x < 0:
            x = cursor_rect.left()
        y = cursor_rect.top()
        
        return QRect(x, y, image_width, image_height)

    def _image_cursor_at(self, pos) -> QTextCursor | None:
        """Return a cursor selecting the image object at a viewport position."""

        base_cursor = self.cursorForPosition(pos)
        candidate_positions = [base_cursor.position(), max(0, base_cursor.position() - 1)]

        for candidate_position in candidate_positions:
            candidate_cursor = self.textCursor()
            candidate_cursor.setPosition(candidate_position)
            candidate_cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
            if candidate_cursor.charFormat().isImageFormat():
                return candidate_cursor

        return None

    def _apply_image_size(self, cursor: QTextCursor, width: int, height: int) -> None:
        """Replace the selected image object with updated size information."""

        image_format = cursor.charFormat().toImageFormat()
        if not image_format:
            return

        image_format.setWidth(width)
        image_format.setHeight(height)

        cursor.beginEditBlock()
        cursor.insertImage(image_format)
        cursor.endEditBlock()

        self.setTextCursor(cursor)
        self._hover_image_rect = self._get_image_rect(cursor)
        self.viewport().update()

        if self.main_window and self.main_window.current_memo:
            self.main_window.is_modified = True
            self.main_window.auto_save_timer.start(self.main_window.auto_save_delay)
    
    def _get_resize_cursor(self, pos, image_rect) -> str | None:
        """Get resize cursor type based on position."""
        handle_margin = self._handle_size // 2
        
        # Check corners
        corners = [
            (image_rect.topLeft(), 'nw'),
            (image_rect.topRight(), 'ne'),
            (image_rect.bottomLeft(), 'sw'),
            (image_rect.bottomRight(), 'se'),
        ]
        
        for corner_pos, cursor_type in corners:
            handle_rect = QRect(corner_pos.x() - handle_margin,
                               corner_pos.y() - handle_margin,
                               self._handle_size, self._handle_size)
            if handle_rect.contains(pos):
                return cursor_type
        
        # Check edges
        edges = [
            (QRect(image_rect.left(), image_rect.top() - handle_margin, 
                   image_rect.width(), self._handle_size), 'n'),
            (QRect(image_rect.right() - handle_margin, image_rect.top(), 
                   self._handle_size, image_rect.height()), 'e'),
            (QRect(image_rect.left(), image_rect.bottom(), 
                   image_rect.width(), self._handle_size), 's'),
            (QRect(image_rect.left() - handle_margin, image_rect.top(), 
                   self._handle_size, image_rect.height()), 'w'),
        ]
        
        for edge_rect, cursor_type in edges:
            if edge_rect.contains(pos):
                return cursor_type
        
        return None
    
    def _perform_resize(self, current_pos) -> None:
        """Perform the resize operation."""
        if not self._resize_image_cursor or not self._resize_start_rect.isValid():
            return
        
        # Calculate size change
        delta = current_pos - self._resize_start_pos
        new_rect = QRect(self._resize_start_rect)
        
        # Resize based on cursor type (all 8 directions)
        if self._resize_cursor in ['nw']:
            new_rect.setTopLeft(self._resize_start_rect.topLeft() + delta)
        elif self._resize_cursor in ['ne']:
            new_rect.setTopRight(self._resize_start_rect.topRight() + QPoint(delta.x(), delta.y()))
        elif self._resize_cursor in ['sw']:
            new_rect.setBottomLeft(self._resize_start_rect.bottomLeft() + QPoint(delta.x(), delta.y()))
        elif self._resize_cursor in ['se']:
            new_rect.setBottomRight(self._resize_start_rect.bottomRight() + delta)
        elif self._resize_cursor in ['n']:
            new_rect.setTop(self._resize_start_rect.top() + delta.y())
        elif self._resize_cursor in ['s']:
            new_rect.setBottom(self._resize_start_rect.bottom() + delta.y())
        elif self._resize_cursor in ['e']:
            new_rect.setRight(self._resize_start_rect.right() + delta.x())
        elif self._resize_cursor in ['w']:
            new_rect.setLeft(self._resize_start_rect.left() + delta.x())
        
        # Ensure minimum size
        if new_rect.width() < 20:
            if self._resize_cursor in ['nw', 'sw']:
                new_rect.setLeft(new_rect.right() - 20)
            elif self._resize_cursor in ['ne', 'se']:
                new_rect.setRight(new_rect.left() + 20)
            elif self._resize_cursor in ['w']:
                new_rect.setLeft(new_rect.right() - 20)
            elif self._resize_cursor in ['e']:
                new_rect.setRight(new_rect.left() + 20)
        
        if new_rect.height() < 20:
            if self._resize_cursor in ['nw', 'ne']:
                new_rect.setTop(new_rect.bottom() - 20)
            elif self._resize_cursor in ['sw', 'se']:
                new_rect.setBottom(new_rect.top() + 20)
            elif self._resize_cursor in ['n']:
                new_rect.setTop(new_rect.bottom() - 20)
            elif self._resize_cursor in ['s']:
                new_rect.setBottom(new_rect.top() + 20)
        
        # Maintain aspect ratio if locked (only for corners)
        if self._aspect_ratio_locked and self._resize_cursor in ['nw', 'ne', 'sw', 'se']:
            original_ratio = self._resize_start_rect.width() / self._resize_start_rect.height()
            new_ratio = new_rect.width() / new_rect.height()
            
            if abs(new_ratio - original_ratio) > 0.1:
                # Adjust to maintain ratio
                if self._resize_cursor in ['nw', 'sw']:
                    new_rect.setHeight(int(new_rect.width() / original_ratio))
                else:  # 'ne', 'se'
                    new_rect.setWidth(int(new_rect.height() * original_ratio))
        
        if new_rect.width() > 0 and new_rect.height() > 0:
            self._apply_image_size(self._resize_image_cursor, new_rect.width(), new_rect.height())
            self._resize_image_cursor = self._image_cursor_at(current_pos)
            self._hover_image_rect = new_rect
    
    def _finish_resize(self) -> None:
        """Finish the resize operation and mark as modified."""
        self.viewport().update()
    
    def _update_hover_state(self) -> None:
        """Update hover state and trigger repaint."""
        self.viewport().update()


class FolderTreeWidget(QTreeWidget):
    folder_drop_completed = Signal()

    def supportedDropActions(self) -> Qt.DropAction:  # noqa: N802
        return Qt.DropAction.MoveAction

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        event.setDropAction(Qt.DropAction.MoveAction)
        super().dropEvent(event)
        if event.isAccepted():
            self.folder_drop_completed.emit()


class FolderNameDialog(QDialog):
    """Dialog for entering folder name."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("새 폴더")
        self.setModal(True)
        self.setFixedSize(400, 200)

        # Apply modern theme
        self._apply_dialog_style()

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(32, 32, 32, 32)

        label = QLabel("폴더 이름", self)
        label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: #1d1d1f;
                margin-bottom: 8px;
                font-family: "Pretendard", "Apple SD Gothic Neo", "Segoe UI", sans-serif;
            }
        """)

        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("폴더 이름을 입력하세요...")
        self.name_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.95);
                border: 1.5px solid rgba(0, 0, 0, 0.08);
                border-radius: 12px;
                padding: 16px 20px;
                font-family: "Pretendard", "Apple SD Gothic Neo", "Segoe UI", sans-serif;
                font-size: 16px;
                color: #1d1d1f;
                font-weight: 500;
                transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
            }
            QLineEdit:focus {
                border: 2px solid rgba(0, 122, 255, 0.6);
                background: rgba(255, 255, 255, 1.0);
                box-shadow: 0 0 0 4px rgba(0, 122, 255, 0.1);
                outline: none;
            }
            QLineEdit:hover:not(:focus) {
                border: 1.5px solid rgba(0, 0, 0, 0.15);
                background: rgba(255, 255, 255, 1.0);
            }
        """)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        cancel_button = QPushButton("취소", self)
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
                transition: all 0.2s cubic-bezier(0.4, 0.0, 0.2, 1);
            }
            QPushButton:hover {
                background: rgba(142, 142, 147, 0.2);
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background: rgba(142, 142, 147, 0.3);
                transform: translateY(0px);
            }
        """)
        cancel_button.clicked.connect(self.reject)
        
        ok_button = QPushButton("확인", self)
        ok_button.setStyleSheet("""
            QPushButton {
                background: rgba(0, 122, 255, 0.9);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 14px 24px;
                font-family: "Pretendard", "Apple SD Gothic Neo", "Segoe UI", sans-serif;
                font-size: 16px;
                font-weight: 600;
                min-width: 100px;
                transition: all 0.2s cubic-bezier(0.4, 0.0, 0.2, 1);
            }
            QPushButton:hover {
                background: rgba(0, 122, 255, 1.0);
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3);
            }
            QPushButton:pressed {
                background: rgba(0, 122, 255, 0.8);
                transform: translateY(0px);
            }
        """)
        ok_button.clicked.connect(self.accept)

        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)

        layout.addWidget(label)
        layout.addWidget(self.name_input)
        layout.addLayout(button_layout)

        self.name_input.setFocus()
        self.name_input.returnPressed.connect(self.accept)

    def _apply_dialog_style(self) -> None:
        """Apply Apple-style theme to dialog."""
        self.setStyleSheet("""
            QDialog {
                background: rgba(255, 255, 255, 0.98);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 20px;
                backdrop-filter: blur(20px);
            }
        """)

    def get_folder_name(self) -> str:
        """Return the entered folder name."""
        return self.name_input.text().strip()

    def accept(self) -> None:
        """Validate input before accepting."""
        name = self.get_folder_name()
        if not name:
            QMessageBox.warning(self, "오류", "폴더 이름을 입력하세요.")
            return
        super().accept()


class StorageSettingsDialog(QDialog):
    """Dialog for configuring storage path."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("저장 위치 설정")
        self.setModal(True)
        self.setFixedSize(600, 280)

        # Apply modern theme
        self._apply_dialog_style()

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(32, 32, 32, 32)

        # Current path label
        current_label = QLabel("현재 저장 위치", self)
        current_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: #1d1d1f;
                margin-bottom: 8px;
                font-family: "Pretendard", "Apple SD Gothic Neo", "Segoe UI", sans-serif;
            }
        """)
        layout.addWidget(current_label)

        self.current_path_label = QLabel(self)
        self.current_path_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #6b7280;
                padding: 12px 16px;
                background-color: rgba(243, 244, 246, 0.8);
                border-radius: 8px;
                font-family: "Pretendard", "Apple SD Gothic Neo", "Segoe UI", sans-serif;
                border: 1px solid rgba(0, 0, 0, 0.05);
            }
        """)
        self.current_path_label.setWordWrap(True)
        layout.addWidget(self.current_path_label)

        # New path selection
        path_layout = QHBoxLayout()
        path_layout.setSpacing(12)
        
        self.path_input = QLineEdit(self)
        self.path_input.setPlaceholderText("새 저장 위치를 선택하세요...")
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
                transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
            }
            QLineEdit:focus {
                border: 2px solid rgba(0, 122, 255, 0.6);
                background: rgba(255, 255, 255, 1.0);
                box-shadow: 0 0 0 4px rgba(0, 122, 255, 0.1);
                outline: none;
            }
            QLineEdit:hover:not(:focus) {
                border: 1.5px solid rgba(0, 0, 0, 0.15);
                background: rgba(255, 255, 255, 1.0);
            }
        """)
        
        browse_button = QPushButton("폴더 선택", self)
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
                min-width: 100px;
                transition: all 0.2s cubic-bezier(0.4, 0.0, 0.2, 1);
            }
            QPushButton:hover {
                background: rgba(0, 122, 255, 1.0);
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3);
            }
            QPushButton:pressed {
                background: rgba(0, 122, 255, 0.8);
                transform: translateY(0px);
            }
        """)
        browse_button.clicked.connect(self._browse_folder)
        
        path_layout.addWidget(self.path_input, stretch=1)
        path_layout.addWidget(browse_button)
        layout.addLayout(path_layout)

        # Migrate checkbox
        self.migrate_checkbox = QCheckBox("기존 데이터를 새 위치로 이동", self)
        self.migrate_checkbox.setChecked(True)
        self.migrate_checkbox.setStyleSheet("""
            QCheckBox {
                color: #1d1d1f;
                spacing: 12px;
                font-family: "Pretendard", "Apple SD Gothic Neo", "Segoe UI", sans-serif;
                font-size: 15px;
                font-weight: 500;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 5px;
                border: 2px solid rgba(0, 0, 0, 0.2);
                background: rgba(255, 255, 255, 0.8);
                transition: all 0.2s ease;
            }
            QCheckBox::indicator:hover {
                border: 2px solid rgba(0, 122, 255, 0.5);
                background: rgba(0, 122, 255, 0.1);
            }
            QCheckBox::indicator:checked {
                background: rgba(0, 122, 255, 0.9);
                border: 2px solid rgba(0, 122, 255, 0.9);
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTQiIGhlaWdodD0iMTEiIHZpZXdCb3g9IjAgMCAxNCAxMSIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEzIDAuNUw0LjUgOUwxIDUuNSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
            }
        """)
        layout.addWidget(self.migrate_checkbox)

        # Info label
        info_label = QLabel("저장 위치를 변경하면 앱이 새 위치를 사용합니다.\n기존 데이터를 이동하지 않으면 새 위치에서 비어있는 상태로 시작합니다.", self)
        info_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #6b7280;
                padding: 12px 16px;
                background-color: rgba(243, 244, 246, 0.6);
                border-radius: 8px;
                font-family: "Pretendard", "Apple SD Gothic Neo", "Segoe UI", sans-serif;
                border: 1px solid rgba(0, 0, 0, 0.05);
                line-height: 1.4;
            }
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        cancel_button = QPushButton("취소", self)
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
                transition: all 0.2s cubic-bezier(0.4, 0.0, 0.2, 1);
            }
            QPushButton:hover {
                background: rgba(142, 142, 147, 0.2);
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background: rgba(142, 142, 147, 0.3);
                transform: translateY(0px);
            }
        """)
        cancel_button.clicked.connect(self.reject)
        
        ok_button = QPushButton("적용", self)
        ok_button.setStyleSheet("""
            QPushButton {
                background: rgba(0, 122, 255, 0.9);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 14px 24px;
                font-family: "Pretendard", "Apple SD Gothic Neo", "Segoe UI", sans-serif;
                font-size: 16px;
                font-weight: 600;
                min-width: 100px;
                transition: all 0.2s cubic-bezier(0.4, 0.0, 0.2, 1);
            }
            QPushButton:hover {
                background: rgba(0, 122, 255, 1.0);
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3);
            }
            QPushButton:pressed {
                background: rgba(0, 122, 255, 0.8);
                transform: translateY(0px);
            }
        """)
        ok_button.clicked.connect(self.accept)

        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)

        # Load current path
        self._load_current_path()

    def _apply_dialog_style(self) -> None:
        """Apply Apple-style theme to dialog."""
        self.setStyleSheet("""
            QDialog {
                background: rgba(255, 255, 255, 0.98);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 20px;
                backdrop-filter: blur(20px);
            }
        """)

    def _load_current_path(self) -> None:
        """Load and display current storage path."""
        from mycloudmemo.config import get_storage_path
        current_path = get_storage_path()
        self.current_path_label.setText(str(current_path))

    def _browse_folder(self) -> None:
        """Open folder browser dialog."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "저장 위치 선택",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.path_input.setText(folder)

    def get_selected_path(self) -> str:
        """Return the selected path."""
        return self.path_input.text().strip()

    def should_migrate(self) -> bool:
        """Return whether to migrate existing data."""
        return self.migrate_checkbox.isChecked()


class MainWindow(QMainWindow):
    """Primary desktop shell with unified WYSIWYG editor and file-based storage."""

    def __init__(self, database: DatabaseManager, sync_manager: EnhancedSyncManager) -> None:
        super().__init__()
        self.database = database
        self.sync_manager = sync_manager
        self.file_storage = FileStorageManager()
        self.current_folder_id = "root"
        self.current_memo: MemoRecord | None = None
        self._is_reloading_memos = False
        
        # Auto-save functionality
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self._auto_save)
        self.auto_save_delay = 2000  # 2 seconds
        self.is_modified = False

        # Load custom font and set as global default
        self._setup_custom_font()

        # Apply modern Apple-style theme
        self._apply_modern_theme()

        # Load Qt Designer UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Connect UI elements to variables for backward compatibility
        self.folder_tree = self.ui.folderTree
        
        # Replace QTreeWidget with FolderTreeWidget for drag-drop support
        if isinstance(self.folder_tree, QTreeWidget):
            parent = self.folder_tree.parent()
            layout = parent.layout()
            
            # Create new FolderTreeWidget with same properties
            new_tree = FolderTreeWidget(parent)
            new_tree.setObjectName(self.folder_tree.objectName())
            new_tree.setStyleSheet(self.folder_tree.styleSheet())
            new_tree.setHeaderHidden(self.folder_tree.isHeaderHidden())
            new_tree.setIndentation(self.folder_tree.indentation())
            new_tree.setContextMenuPolicy(self.folder_tree.contextMenuPolicy())
            new_tree.setDragEnabled(True)
            new_tree.setAcceptDrops(True)
            new_tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
            new_tree.setDefaultDropAction(Qt.DropAction.MoveAction)
            
            # Replace in layout
            index = layout.indexOf(self.folder_tree)
            layout.removeWidget(self.folder_tree)
            layout.insertWidget(index, new_tree)
            self.folder_tree.deleteLater()
            self.folder_tree = new_tree
            self.ui.folderTree = new_tree
        
        self.note_list = self.ui.memoList
        self.editor = self.ui.editor
        self.folder_label = self.ui.currentFolderLabel
        self.sync_label = self.ui.syncStatusLabel
        self.add_folder_button = self.ui.addFolderButton
        self.folder_delete_button = self.ui.folderDeleteButton
        self.add_note_button = self.ui.addMemoButton
        self.memo_delete_button = self.ui.memoDeleteButton
        self.settings_button = self.ui.settingsButton
        
        # Setup custom widgets
        self._setup_editor()
        self._setup_card_shadow()
        self._setup_button_icons()
        self._create_actions()
        self._create_toolbar()
        self._create_tray_icon()
        self._connect_signals()
        self._load_folders()
        self._load_memos(self.current_folder_id)

    def _setup_custom_font(self) -> None:
        """Load Pretendard font and set as global default."""
        try:
            # Get font file path
            font_path = Path(__file__).parent.parent.parent / "Pretendard-Regular.ttf"
            
            if font_path.exists():
                # Load font into QFontDatabase
                font_db = QFontDatabase()
                font_id = font_db.addApplicationFont(str(font_path))
                
                if font_id != -1:
                    font_families = font_db.applicationFontFamilies(font_id)
                    if font_families:
                        font_family = font_families[0]
                        
                        # Set as global default font
                        app_font = QApplication.font()
                        app_font.setFamily(font_family)
                        app_font.setPointSize(14)
                        QApplication.setFont(app_font)
                        
                        print(f"Successfully loaded and set Pretendard font: {font_family}")
                    else:
                        print("No font families found for Pretendard")
                else:
                    print("Failed to load Pretendard font")
            else:
                print(f"Pretendard font file not found at: {font_path}")
                # Fallback to system fonts
                app_font = QApplication.font()
                app_font.setFamily("Apple SD Gothic Neo")
                app_font.setPointSize(14)
                QApplication.setFont(app_font)
                
        except Exception as e:
            print(f"Error setting up custom font: {e}")
            # Fallback to system fonts
            app_font = QApplication.font()
            app_font.setFamily("Apple SD Gothic Neo")
            app_font.setPointSize(14)
            QApplication.setFont(app_font)

    def _setup_card_shadow(self) -> None:
        """Apply iOS-style card shadow effect to editorCard widget."""
        try:
            # Create drop shadow effect
            shadow = QGraphicsDropShadowEffect()
            
            # iOS-style shadow settings
            shadow.setBlurRadius(25.0)  # Wide blur radius for soft shadow
            shadow.setXOffset(0.0)      # No horizontal offset for centered shadow
            shadow.setYOffset(2.0)      # Slight vertical offset for depth
            shadow.setColor(QColor(0, 0, 0, 60))  # Subtle shadow with transparency
            
            # Apply shadow to editorCard widget
            self.ui.editorCard.setGraphicsEffect(shadow)
            
            print("Applied iOS-style card shadow effect to editorCard")
            
        except Exception as e:
            print(f"Error applying card shadow: {e}")

    def _apply_modern_theme(self) -> None:
        """Apply modern Apple-style theme to the application."""
        try:
            # Get the path to the QSS file
            qss_path = Path(__file__).parent.parent / "assets" / "modern_style.qss"
            
            # Read and apply the stylesheet
            with open(qss_path, 'r', encoding='utf-8') as f:
                qss_content = f.read()
            
            self.setStyleSheet(qss_content)
            print(f"Applied modern theme from: {qss_path}")
            
        except Exception as e:
            print(f"Failed to apply modern theme: {e}")
            # Fallback to basic styling if theme file not found
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f5f5f7;
                }
                QScrollBar:vertical {
                    background: transparent;
                    width: 8px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background: rgba(0, 0, 0, 0.2);
                    border-radius: 4px;
                }
                QTreeWidget::item:selected, QListWidget::item:selected {
                    background: rgba(0, 122, 255, 0.15);
                    border-radius: 12px;
                    color: #1d1d1f;
                }
            """)

    def _setup_button_icons(self) -> None:
        """Set icon images for toolbar buttons."""
        # Get assets directory path
        assets_path = Path(__file__).parent.parent / "assets"
        
        # Add Folder button - use folder-plus icon
        folder_plus_icon = QIcon(str(assets_path / "folder-plus.svg"))
        self.add_folder_button.setIcon(folder_plus_icon)
        self.add_folder_button.setText("")
        self.add_folder_button.setIconSize(QSize(16, 16))
        
        # Delete Folder button - use folder-x icon
        folder_x_icon = QIcon(str(assets_path / "folder-x.svg"))
        self.folder_delete_button.setIcon(folder_x_icon)
        self.folder_delete_button.setText("")
        self.folder_delete_button.setIconSize(QSize(16, 16))
        
        # Add Memo button - use file-plus icon
        file_plus_icon = QIcon(str(assets_path / "file-plus.svg"))
        self.add_note_button.setIcon(file_plus_icon)
        self.add_note_button.setText("")
        self.add_note_button.setIconSize(QSize(16, 16))
        
        # Delete Memo button - use file-x icon
        file_x_icon = QIcon(str(assets_path / "file-x.svg"))
        self.memo_delete_button.setIcon(file_x_icon)
        self.memo_delete_button.setText("")
        self.memo_delete_button.setIconSize(QSize(16, 16))
        
        # Settings button - use computer/settings icon (fallback to standard icon)
        settings_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.settings_button.setIcon(settings_icon)
        self.settings_button.setText("")
        self.settings_button.setIconSize(QSize(16, 16))

    def _setup_editor(self) -> None:
        """Setup the editor with custom configuration."""
        # Configure editor for WYSIWYG editing
        self.editor.setPlaceholderText("여기에 메모를 작성하세요...\n\n팁: Ctrl+V로 클립보드 이미지를 바로 붙여넣을 수 있습니다.\n팁: 이미지를 더블클릭하면 크기를 조정할 수 있습니다.")
        self.editor.setAcceptRichText(True)
        self.editor.main_window = self
        
        # Override key press and focus out events
        self.editor.keyPressEvent = self._editor_key_press_event
        self.editor.focusOutEvent = self._editor_focus_out_event
        
        # Setup context menu
        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self._show_editor_context_menu)
        
        # Setup folder tree
        self.folder_tree.setHeaderLabel("워크스페이스")
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setIndentation(14)
        self.folder_tree.setRootIsDecorated(True)
        self.folder_tree.setUniformRowHeights(True)
        self.folder_tree.setAnimated(True)
        self.folder_tree.setExpandsOnDoubleClick(True)
        self.folder_tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.folder_tree.setDragEnabled(True)
        self.folder_tree.setAcceptDrops(True)
        self.folder_tree.setDropIndicatorShown(True)
        self.folder_tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.folder_tree.setDragDropOverwriteMode(False)
        self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_tree.customContextMenuRequested.connect(self._show_folder_context_menu)
        
        # Setup status bar labels
        self.ui.statusbar.showMessage("준비됨")
        self.sync_status_label = QLabel("동기화 상태: 최신 상태", self)
        self.word_count_label = QLabel("단어 수: 0", self)
        self.ui.statusbar.addWidget(self.sync_status_label)
        self.ui.statusbar.addPermanentWidget(self.word_count_label)
        self._update_word_count()

    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Folder tree
        self.folder_tree.itemSelectionChanged.connect(self._on_folder_selection_changed)
        self.folder_tree.customContextMenuRequested.connect(self._show_folder_context_menu)
        self.folder_tree.folder_drop_completed.connect(self._on_folder_drop_completed)
        
        # Memo list
        self.note_list.itemSelectionChanged.connect(self._on_memo_selection_changed)
        
        # Editor
        self.editor.textChanged.connect(self._on_text_changed)
        
        # Buttons
        self.add_folder_button.clicked.connect(self._create_new_folder)
        self.folder_delete_button.clicked.connect(self._delete_selected_folder)
        self.add_note_button.clicked.connect(self._create_new_memo)
        self.memo_delete_button.clicked.connect(self._delete_selected_memo)
        self.settings_button.clicked.connect(self._open_settings)

    def _serialize_editor_content(self) -> str:
        """Serialize editor contents for storage while preserving inline images."""

        html = self.editor.toHtml()
        html = re.sub(r'src="file:///[^"]*/assets/([^"]+)"', r'src="assets/\1"', html)
        html = re.sub(r'src="[^"]*[\\/]assets/([^"]+)"', r'src="assets/\1"', html)
        return html

    def _set_editor_content(self, content: str) -> None:
        """Load stored content into the integrated editor."""

        self.editor.blockSignals(True)
        if not content.strip():
            self.editor.clear()
        else:
            def resolve_asset_path(match):
                asset_relative_path = f"assets/{match.group(1)}"
                return f'src="{self.file_storage.get_image_absolute_path(asset_relative_path).as_uri()}"'

            resolved_content = re.sub(
                r'src="assets/([^"]+)"',
                resolve_asset_path,
                content,
            )
            if "<html" in content.lower() or "<p" in content.lower() or "<img" in content.lower():
                self.editor.setHtml(resolved_content)
            else:
                self.editor.setPlainText(content)
        self.editor.blockSignals(False)

    def _load_folders(self) -> None:
        """Populate the folder tree from the database."""

        folders = self.database.fetch_folders()
        self.folder_tree.clear()
        
        # Get assets directory path
        assets_path = Path(__file__).parent.parent / "assets"
        folder_closed_icon = QIcon(str(assets_path / "folder-closed.svg"))
        folder_open_icon = QIcon(str(assets_path / "folder-open.svg"))

        # Find and handle root folder separately
        root_folder = None
        regular_folders = []
        
        for folder in folders:
            if folder.id == "root":
                root_folder = folder
            else:
                regular_folders.append(folder)

        # Build children hierarchy for regular folders only
        children_by_parent: dict[str | None, list[FolderRecord]] = {}
        for folder in regular_folders:
            children_by_parent.setdefault(folder.parent_id, []).append(folder)

        def build_item(folder: FolderRecord) -> QTreeWidgetItem:
            # Count subfolders
            subfolder_count = self.database.count_subfolders(folder.id)
            
            # Build display name with subfolder indicator
            display_name = folder.name
            if subfolder_count > 0:
                display_name += f" ({subfolder_count})"
            
            # Use SVG folder icons
            item = QTreeWidgetItem([display_name])
            item.setIcon(0, folder_closed_icon)
            item.setData(0, Qt.ItemDataRole.UserRole, folder.id)
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsDragEnabled
                | Qt.ItemFlag.ItemIsDropEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
            )
            
            # Add children
            for child_folder in children_by_parent.get(folder.id, []):
                item.addChild(build_item(child_folder))
            
            return item

        # Add root folder as first top-level item with special styling
        if root_folder:
            root_item = QTreeWidgetItem([root_folder.name])
            root_item.setIcon(0, QIcon(str(assets_path / "folder-closed.svg")))
            root_item.setData(0, Qt.ItemDataRole.UserRole, "root")
            root_item.setFlags(
                root_item.flags()
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
            )
            # Remove drag/drop for root folder
            root_item.setFlags(root_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled & ~Qt.ItemFlag.ItemIsDropEnabled)
            self.folder_tree.addTopLevelItem(root_item)

        # Add regular folders
        for top_level_folder in children_by_parent.get(None, []):
            self.folder_tree.addTopLevelItem(build_item(top_level_folder))

        # Only expand root folder initially, let users control subfolders
        if self.folder_tree.topLevelItemCount() > 0:
            # Expand root folder (first item)
            self.folder_tree.expandItem(self.folder_tree.topLevelItem(0))
            # Select root folder by default
            self.folder_tree.setCurrentItem(self.folder_tree.topLevelItem(0))

    def _create_actions(self) -> None:
        """Create reusable window actions."""

        self.show_action = QAction("누니메모 열기", self)
        self.show_action.triggered.connect(self._restore_from_tray)

        self.quit_action = QAction("종료", self)
        self.quit_action.triggered.connect(self._quit_application)

        self.settings_action = QAction("⚙️ 설정", self)
        self.settings_action.triggered.connect(self._open_settings)

    def _create_toolbar(self) -> None:
        """Create the top toolbar for common actions."""

        toolbar = QToolBar("메인 툴바", self)
        toolbar.setMovable(False)
        toolbar.setHidden(True)  # Hide toolbar completely
        self.addToolBar(toolbar)

    def _create_tray_icon(self) -> None:
        """Configure minimize-to-tray behavior."""

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("누니메모")
        self.tray_icon.setIcon(QIcon(str(Path(__file__).parent.parent / "assets" / "nuni_ico.ico")))
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        tray_menu = QMenu(self)
        tray_menu.addAction(self.show_action)
        tray_menu.addAction(self.quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def _load_memos(self, folder_id: str) -> None:
        """Populate the memo list for the selected folder.
        
        If root folder is selected, show all memos from all folders (hub view).
        """

        previous_selection_id = self.current_memo.id if self.current_memo else None
        self._is_reloading_memos = True
        self.note_list.blockSignals(True)
        self.note_list.clear()
        
        # Get all folders for lookup
        folders = self.database.fetch_folders()
        folder_map = {f.id: f for f in folders}
        
        # If root folder, show all memos (hub view)
        if folder_id == "root":
            memos = self.database.fetch_all_memos()
        else:
            memos = self.database.fetch_memos_by_folder(folder_id)
        
        # Get assets directory path
        assets_path = Path(__file__).parent.parent / "assets"
        file_icon = QIcon(str(assets_path / "file.svg"))
        
        from datetime import datetime
        
        for memo in memos:
            # Format dates for display
            try:
                created_dt = datetime.fromisoformat(memo.created_at.replace('Z', '+00:00'))
                updated_dt = datetime.fromisoformat(memo.updated_at.replace('Z', '+00:00'))
                
                # Format: "YYYY-MM-DD HH:mm" for Korean locale
                created_str = created_dt.strftime("%Y-%m-%d %H:%M")
                updated_str = updated_dt.strftime("%Y-%m-%d %H:%M")
                
                # Get folder name for hub view
                folder_name = ""
                if folder_id == "root" and memo.folder_id in folder_map:
                    folder_name = f"📁 {folder_map[memo.folder_id].name} | "
                
                # Display title with dates
                if created_dt.date() == updated_dt.date():
                    # Same day - show one date
                    display_text = f"{folder_name}{memo.title}\n📝 {updated_str}"
                else:
                    # Different days - show both
                    display_text = f"{folder_name}{memo.title}\n📅 {created_str} → 🔄 {updated_str}"
            except:
                # Fallback if date parsing fails
                folder_name = ""
                if folder_id == "root" and memo.folder_id in folder_map:
                    folder_name = f"📁 {folder_map[memo.folder_id].name} | "
                display_text = f"{folder_name}{memo.title}"
            
            item = QListWidgetItem(display_text)
            item.setIcon(file_icon)
            item.setData(Qt.ItemDataRole.UserRole, memo)
            self.note_list.addItem(item)
            
        if self.note_list.count() == 0:
            self.current_memo = None
            self._set_editor_content("")
            self._update_word_count()
        elif previous_selection_id:
            for index in range(self.note_list.count()):
                item = self.note_list.item(index)
                memo = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(memo, MemoRecord) and memo.id == previous_selection_id:
                    self.note_list.setCurrentItem(item)
                    break
        self.note_list.blockSignals(False)
        self._is_reloading_memos = False

    def _on_folder_drop_completed(self) -> None:
        """Handle folder drop completion by refreshing the folder tree."""
        print("Debug: Folder drop completed, refreshing folder tree")
        # Save current folder selection
        current_folder_id = self.current_folder_id
        
        # Refresh folder tree
        self._load_folders()
        
        # Restore folder selection
        if current_folder_id:
            self._select_folder_by_id(current_folder_id)

    def _on_folder_selection_changed(self) -> None:
        """Handle folder tree selection changes."""

        if self.is_modified and self.current_memo:
            self._auto_save()

        current_item = self.folder_tree.currentItem()
        if current_item is None:
            return
        folder_id = current_item.data(0, Qt.ItemDataRole.UserRole)
        self.current_folder_id = folder_id
        
        # Update label with hub indicator for root folder
        if folder_id == "root":
            self.folder_label.setText(f"📂 {current_item.text(0)} (전체 메모)")
        else:
            self.folder_label.setText(f"📁 {current_item.text(0)}")
        
        self._load_memos(folder_id)

    def _on_memo_selection_changed(self) -> None:
        """Display the selected memo in the editor."""

        if self._is_reloading_memos:
            return

        if self.is_modified and self.current_memo:
            self._auto_save()

        current_item = self.note_list.currentItem()
        if current_item is None:
            return
        memo = current_item.data(Qt.ItemDataRole.UserRole)
        if isinstance(memo, MemoRecord):
            self.current_memo = memo
            self.is_modified = False
            self.auto_save_timer.stop()
            
            # Load content from file
            content = self.file_storage.load_memo_content(memo.file_name)

            self._set_editor_content(content)
            self._update_word_count()

    def _select_memo_by_id(self, memo_id: str) -> None:
        """Select a memo in the memo list by its ID."""

        for i in range(self.note_list.count()):
            item = self.note_list.item(i)
            memo = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(memo, MemoRecord) and memo.id == memo_id:
                self.note_list.setCurrentItem(item)
                return

    def _on_text_changed(self) -> None:
        """Handle text changes in the editor."""

        if self.current_memo:
            self.is_modified = True
            self.auto_save_timer.start(self.auto_save_delay)
            print(f"Text changed, auto-save scheduled in {self.auto_save_delay}ms")
        else:
            # No current memo - create one automatically
            content = self.editor.toPlainText().strip()
            if content:
                self._create_memo_from_editor()
        
        self._update_word_count()

    def _create_memo_from_editor(self) -> None:
        """Create a memo from the current editor content."""

        if self.current_folder_id == "root":
            QMessageBox.warning(self, "오류", "먼저 폴더를 선택해주세요.")
            self._set_editor_content("")
            return

        initial_title = self.editor.toPlainText().split('\n')[0].strip() or "새 메모"
        initial_content = self._serialize_editor_content()
        
        try:
            # Generate file path
            file_name = self.file_storage._generate_memo_filename("temp")
            
            # Create database record first
            memo_id = self.database.create_memo(
                self.current_folder_id,
                title=initial_title,
                file_name=file_name
            )
            print(f"Auto-created memo: {memo_id}")
            
            # Save content to file
            self.file_storage.save_memo_content(memo_id, initial_content, file_name)
            
            # Get the created memo record
            created_memo = self.database.get_memo_by_id(memo_id)
            if created_memo is not None:
                self.current_memo = created_memo
                self.is_modified = False  # Just saved
            
            # Reload memos list
            self._load_memos(self.current_folder_id)
            
            # Select the new memo
            self._select_memo_by_id(memo_id)
            
            # Update UI
            self._update_sync_status("메모 생성됨")
            
        except Exception as e:
            QMessageBox.warning(self, "오류", f"메모를 생성할 수 없습니다: {str(e)}")
            print(f"Auto-create memo failed: {e}")
            self._set_editor_content("")

    def _editor_focus_out_event(self, event) -> None:
        """Save when editor loses focus."""
        if self.is_modified and self.current_memo:
            print("Editor lost focus, triggering auto-save")
            self._auto_save()
        QTextEdit.focusOutEvent(self.editor, event)

    def _auto_save(self) -> None:
        """Auto-save the current memo to file."""

        print(f"Auto-save triggered: current_memo={bool(self.current_memo)}, is_modified={self.is_modified}")
        
        if not self.current_memo or not self.is_modified:
            print("Auto-save skipped: no memo or not modified")
            return
        
        try:
            print(f"Saving memo {self.current_memo.id}")
            
            # Get current content
            current_content = self._serialize_editor_content()
            plain_text_content = self.editor.toPlainText()
            
            # Save to file
            file_name = self.file_storage.save_memo_content(
                self.current_memo.id, 
                current_content, 
                self.current_memo.file_name
            )
            
            # Update database metadata
            first_line = plain_text_content.split('\n')[0].strip() or "새 메모"
            self.database.update_memo_metadata(
                self.current_memo.id, 
                title=first_line,
                is_synced=False
            )
            
            # Update current_memo reference
            self.current_memo = MemoRecord(
                id=self.current_memo.id,
                folder_id=self.current_memo.folder_id,
                title=first_line,
                file_name=file_name,
                is_synced=False,
                last_modified=self.current_memo.last_modified
            )
            
            self.is_modified = False
            self._update_sync_status("자동 저장됨")
            print("Auto-save completed successfully")

            current_memo_id = self.current_memo.id
            self._load_memos(self.current_folder_id)
            self._select_memo_by_id(current_memo_id)
                
        except Exception as e:
            self._update_sync_status(f"저장 실패: {str(e)}")
            print(f"Auto-save failed: {e}")

    def _delete_selected_folder(self) -> None:
        """Delete selected folder with validation."""
        selected_folder_item = self.folder_tree.currentItem()
        if not selected_folder_item:
            QMessageBox.warning(self, "폴더 삭제", "삭제할 폴더를 선택해주세요.")
            return
        
        self._delete_folder(selected_folder_item)

    def _delete_selected_memo(self) -> None:
        """Delete selected memo."""
        selected_memo_item = self.note_list.currentItem()
        if not selected_memo_item:
            QMessageBox.warning(self, "메모 삭제", "삭제할 메모를 선택해주세요.")
            return
        
        self._delete_memo(selected_memo_item)

    def _delete_folder(self, folder_item: QTreeWidgetItem) -> None:
        """Delete folder with validation for subfolders and memos."""
        folder_id = folder_item.data(0, Qt.ItemDataRole.UserRole)
        folder_name = folder_item.text(0)
        
        # Debug: Show actual subfolder count
        subfolder_count = self.database.count_subfolders(folder_id)
        print(f"Debug: Folder '{folder_name}' ({folder_id}) has {subfolder_count} subfolders")
        
        # Check if folder has subfolders
        if subfolder_count > 0:
            QMessageBox.warning(
                self, 
                "삭제 불가", 
                f"하위 폴더가 {subfolder_count}개 있어 삭제할 수 없습니다.\n먼저 하위 폴더를 모두 삭제해주세요."
            )
            return
        
        # Debug: Show actual memo count
        memo_count = self.database.count_memos_in_folder(folder_id)
        print(f"Debug: Folder '{folder_name}' ({folder_id}) has {memo_count} memos")
        
        # Check if folder has memos
        if memo_count > 0:
            QMessageBox.warning(
                self, 
                "삭제 불가", 
                f"메모가 {memo_count}개 있어 삭제할 수 없습니다.\n먼저 모든 메모를 삭제해주세요."
            )
            return
        
        # Confirm deletion
        folder_name = folder_item.text(0)
        reply = QMessageBox.question(
            self,
            "폴더 삭제",
            f"'{folder_name}' 폴더를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Delete from database
                self.database.delete_folder(folder_id)
                
                # Reload folder tree
                self._load_folders()
                
                # If current folder was deleted, switch to root
                if self.current_folder_id == folder_id:
                    self.current_folder_id = "root"
                    self._load_memos(self.current_folder_id)
                
                QMessageBox.information(self, "삭제 완료", "폴더가 삭제되었습니다.")
                
            except Exception as e:
                QMessageBox.critical(self, "삭제 오류", f"폴더 삭제 중 오류가 발생했습니다: {str(e)}")

    def _delete_memo(self, memo_item: QListWidgetItem) -> None:
        """Delete selected memo."""
        memo = memo_item.data(Qt.ItemDataRole.UserRole)
        if not memo:
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "메모 삭제",
            f"'{memo.title}' 메모를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Delete file
                self.file_storage.delete_memo_file(memo.file_name)
                
                # Delete from database
                self.database.delete_memo(memo.id)
                
                # Clear editor if deleted memo was current
                if self.current_memo and self.current_memo.id == memo.id:
                    self.current_memo = None
                    self._set_editor_content("")
                    self._update_word_count()
                
                # Reload memo list
                self._load_memos(self.current_folder_id)
                
                QMessageBox.information(self, "삭제 완료", "메모가 삭제되었습니다.")
                
            except Exception as e:
                QMessageBox.critical(self, "삭제 오류", f"메모 삭제 중 오류가 발생했습니다: {str(e)}")

    def _create_new_memo(self) -> None:
        """Create a new memo in the current folder."""

        # Allow creating memos in any folder including root
        if not self.current_folder_id:
            QMessageBox.warning(self, "오류", "먼저 폴더를 선택해주세요.")
            return
        
        try:
            # Generate file path
            file_name = self.file_storage._generate_memo_filename("temp")
            
            # Create empty file
            self.file_storage.save_memo_content("temp", "", file_name)
            
            # Create database record
            memo_id = self.database.create_memo(
                self.current_folder_id,
                title="새 메모",
                file_name=file_name
            )
            print(f"Created new memo: {memo_id}")
            
            # Reload memos list
            self._load_memos(self.current_folder_id)

            # Explicitly establish current memo state
            created_memo = self.database.get_memo_by_id(memo_id)
            if created_memo is not None:
                self.current_memo = created_memo

            # Find and select the new memo
            self._select_memo_by_id(memo_id)
            
            # Focus on editor
            self.editor.setFocus()
            
        except Exception as e:
            QMessageBox.warning(self, "오류", f"메모를 생성할 수 없습니다: {str(e)}")
            print(f"Create memo failed: {e}")

    def _editor_key_press_event(self, event) -> None:
        """Handle key press events in the editor for image paste."""
        
        if event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            
            if mime_data.hasImage():
                self._paste_image_from_clipboard()
                event.accept()
                return
            
            QTextEdit.keyPressEvent(self.editor, event)
            return
        
        QTextEdit.keyPressEvent(self.editor, event)

    def _paste_image_from_clipboard(self) -> None:
        """Paste image from clipboard to assets folder."""
        
        try:
            clipboard = QApplication.clipboard()
            image = clipboard.pixmap()
            
            if image.isNull():
                return
            
            # Save to assets folder
            relative_path = self.file_storage.save_image_from_clipboard(image)
            absolute_path = self.file_storage.get_image_absolute_path(relative_path)

            cursor = self.editor.textCursor()
            
            # Get image dimensions and set reasonable default size
            img_width = image.width()
            img_height = image.height()
            
            # Set reasonable default size (max 600px width, maintain aspect ratio)
            max_width = 600
            if img_width > max_width:
                ratio = max_width / img_width
                img_width = max_width
                img_height = int(img_height * ratio)
            
            # Create image format with proper size
            from PySide6.QtGui import QTextImageFormat
            image_format = QTextImageFormat()
            image_format.setName(str(absolute_path))
            image_format.setWidth(img_width)
            image_format.setHeight(img_height)
            
            cursor.insertImage(image_format)
            cursor.insertBlock()
            cursor.insertBlock()
            
            print(f"Image saved and inserted: {relative_path}")
            
        except Exception as e:
            print(f"이미지 붙여넣기 실패: {e}")
            QMessageBox.warning(self, "오류", "이미지 붙여넣기에 실패했습니다.")

    def _show_editor_context_menu(self, position) -> None:
        """Show context menu with image resize option."""
        cursor = self.editor._image_cursor_at(position)
        
        if cursor is not None and cursor.charFormat().isImageFormat():
            menu = QMenu(self)
            resize_action = menu.addAction("이미지 크기 조정...")
            
            action = menu.exec(self.editor.mapToGlobal(position))
            if action == resize_action:
                self._resize_image_at_cursor(cursor)

    def _resize_image_at_cursor(self, cursor) -> None:
        """Resize image at the given cursor position."""
        image_format = cursor.charFormat().toImageFormat()
        if not image_format:
            return
        
        # Get current image size
        current_width = image_format.width()
        current_height = image_format.height()
        
        print(f"Context menu image size: {current_width}x{current_height}")
        
        # Ensure we have valid dimensions
        if current_width <= 0:
            current_width = 400
        if current_height <= 0:
            current_height = 300
        
        # Show resize dialog
        dialog = ImageResizeDialog(self, current_width, current_height)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_width, new_height = dialog.get_size()
            self.editor._apply_image_size(cursor, new_width, new_height)

    def _update_sync_status(self, message: str) -> None:
        """Reflect save status in the header and status bar."""

        self.sync_label.setText(f"●  {message}")
        self.sync_status_label.setText(f"상태: {message}")

    def _update_word_count(self) -> None:
        """Refresh the footer word count based on editor content."""

        text = self.editor.toPlainText().strip()
        count = len(text.split()) if text else 0
        self.word_count_label.setText(f"단어 수: {count}")

    def _create_new_folder(self) -> None:
        """Create a new folder with user input."""

        # If current folder is "모든 메모", create top-level folder
        if self.current_folder_id == "root":
            self._create_new_folder_at_position(None, "top_level")
            return

        dialog = FolderNameDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_folder_name().strip()
            if name:
                parent_id = self.current_folder_id
                folder_id = self.database.create_folder(name, parent_id)
                self._load_folders()
                self._select_folder_by_id(folder_id)

    def _select_folder_by_id(self, folder_id: str) -> None:
        """Select a folder in the tree by its ID."""

        def find_item(tree_widget: QTreeWidget, target_id: str) -> QTreeWidgetItem | None:
            for i in range(tree_widget.topLevelItemCount()):
                item = tree_widget.topLevelItem(i)
                if item.data(0, Qt.ItemDataRole.UserRole) == target_id:
                    return item
                child = self._find_child_item(item, target_id)
                if child:
                    return child
            return None

        item = find_item(self.folder_tree, folder_id)
        if item:
            self.folder_tree.setCurrentItem(item)

    def _find_child_item(self, parent: QTreeWidgetItem, target_id: str) -> QTreeWidgetItem | None:
        """Recursively find child item by ID."""

        for i in range(parent.childCount()):
            item = parent.child(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == target_id:
                return item
            child = self._find_child_item(item, target_id)
            if child:
                return child
        return None

    def _show_folder_context_menu(self, position) -> None:
        """Show context menu for folder operations."""

        print(f"Debug: Context menu requested at position {position}")
        item = self.folder_tree.itemAt(position)
        menu = QMenu(self)
        
        if item:
            folder_id = item.data(0, Qt.ItemDataRole.UserRole)
            folder_name = item.text(0)
            print(f"Debug: Right-clicked on folder '{folder_name}' (ID: {folder_id})")
            
            # "모든 메모" 폴더는 최상위 폴더 추가만 가능
            if folder_id == "root":
                print("Debug: Adding '최상위 폴더 추가' for root folder")
                add_top_level_action = menu.addAction("최상위 폴더 추가")
                add_top_level_action.triggered.connect(lambda: self._create_new_folder_at_position(None, "top_level"))
            else:
                add_submenu = QMenu("폴더 추가", self)
                
                add_subfolder_action = add_submenu.addAction(f"'{folder_name}' 하위에 폴더")
                add_subfolder_action.triggered.connect(lambda: self._create_new_folder_at_position(folder_id, "subfolder"))
                
                parent_id = self._get_parent_folder_id(folder_id)
                add_same_level_action = add_submenu.addAction("같은 레벨에 폴더")
                add_same_level_action.triggered.connect(lambda: self._create_new_folder_at_position(parent_id, "same_level"))
                
                menu.addMenu(add_submenu)
                menu.addSeparator()
                
                delete_action = menu.addAction("폴더 삭제")
                # Find the tree widget item for this folder
                item = None
                for i in range(self.folder_tree.topLevelItemCount()):
                    item = self._find_folder_item(self.folder_tree.topLevelItem(i), folder_id)
                    if item:
                        break
                if item:
                    delete_action.triggered.connect(lambda: self._delete_folder(item))
        else:
            print("Debug: Right-clicked on empty space, adding '최상위 폴더 추가'")
            add_top_level_action = menu.addAction("최상위 폴더 추가")
            add_top_level_action.triggered.connect(lambda: self._create_new_folder_at_position(None, "top_level"))
        
        if not menu.isEmpty():
            print("Debug: Executing context menu")
            menu.exec(self.folder_tree.mapToGlobal(position))
        else:
            print("Debug: Menu is empty, not showing")

    def _find_folder_item(self, parent_item: QTreeWidgetItem, folder_id: str) -> QTreeWidgetItem | None:
        """Find tree widget item by folder ID."""
        if parent_item.data(0, Qt.ItemDataRole.UserRole) == folder_id:
            return parent_item
        
        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            if child_item.data(0, Qt.ItemDataRole.UserRole) == folder_id:
                return child_item
            
            # Recursively search in child items
            found = self._find_folder_item(child_item, folder_id)
            if found:
                return found
        
        return None

    def _get_parent_folder_id(self, folder_id: str) -> str | None:
        """Get the parent folder ID for a given folder."""

        folders = self.database.fetch_folders()
        for folder in folders:
            if folder.id == folder_id:
                return folder.parent_id
        return None

    def _create_new_folder_at_position(self, parent_id: str | None, position_type: str) -> None:
        """Create a new folder at the specified position."""

        print(f"Debug: Creating folder - parent_id={parent_id}, position_type={position_type}")

        dialog = FolderNameDialog(self)
        if position_type == "top_level":
            dialog.setWindowTitle("최상위 폴더 추가")
        elif position_type == "same_level":
            dialog.setWindowTitle("같은 레벨에 폴더 추가")
        elif position_type == "subfolder":
            dialog.setWindowTitle("하위 폴더 추가")
            parent_name = self._get_folder_name_by_id(parent_id)
            if parent_name:
                dialog.name_input.setPlaceholderText(f"'{parent_name}' 하위에 폴더...")
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_folder_name().strip()
            print(f"Debug: User entered folder name: '{name}'")
            if name:
                try:
                    folder_id = self.database.create_folder(name, parent_id)
                    print(f"Debug: Created folder with ID: {folder_id}")
                    self._load_folders()
                    self._select_folder_by_id(folder_id)
                except Exception as e:
                    print(f"Debug: Error creating folder: {e}")
                    QMessageBox.warning(self, "폴더 생성 오류", f"폴더 생성 중 오류가 발생했습니다: {str(e)}")
        else:
            print("Debug: User cancelled folder creation")

    def _get_folder_name_by_id(self, folder_id: str) -> str | None:
        """Get folder name by ID."""

        folders = self.database.fetch_folders()
        for folder in folders:
            if folder.id == folder_id:
                return folder.name
        return None

    def _persist_folder_tree_structure(self) -> None:
        """Persist the current folder tree structure immediately after drag and drop."""

        folder_updates: list[tuple[str, str | None, int]] = []

        def walk_item(item: QTreeWidgetItem, parent_id: str | None, position: int) -> None:
            folder_id = item.data(0, Qt.ItemDataRole.UserRole)
            if folder_id == "root":
                return
            folder_updates.append((folder_id, parent_id, position * 10))
            for index in range(item.childCount()):
                walk_item(item.child(index), folder_id, index)

        for top_level_index in range(self.folder_tree.topLevelItemCount()):
            walk_item(self.folder_tree.topLevelItem(top_level_index), None, top_level_index)

        for folder_id, parent_id, sort_order in folder_updates:
            if self.database._is_descendant_of(parent_id, folder_id):
                self._load_folders()
                QMessageBox.warning(self, "이동 불가", "폴더를 자신의 하위 폴더로 이동할 수 없습니다.")
                return

        for folder_id, parent_id, sort_order in folder_updates:
            self.database.move_folder(folder_id, parent_id, sort_order)

        current_item = self.folder_tree.currentItem()
        current_folder_id = current_item.data(0, Qt.ItemDataRole.UserRole) if current_item else None
        self._load_folders()
        if current_folder_id:
            self._select_folder_by_id(current_folder_id)

    def _calculate_sort_order(self, parent_id: str | None, position: int) -> int:
        """Calculate the sort order for a folder at a specific position."""

        folders = self.database.fetch_folders()
        sibling_folders = [f for f in folders if f.parent_id == parent_id]
        sibling_folders.sort(key=lambda f: f.sort_order)
        
        if position >= len(sibling_folders):
            return (sibling_folders[-1].sort_order if sibling_folders else 0) + 1
        else:
            target_folder = sibling_folders[position]
            return target_folder.sort_order

    def _update_sibling_sort_orders(self, parent_id: str | None) -> None:
        """Update sort orders for all folders in the same parent."""

        folders = self.database.fetch_folders()
        sibling_folders = [f for f in folders if f.parent_id == parent_id]
        sibling_folders.sort(key=lambda f: f.sort_order)
        
        folder_orders = [(folder.id, i * 10) for i, folder in enumerate(sibling_folders)]
        self.database.reorder_folders(parent_id, folder_orders)

    def _restore_from_tray(self) -> None:
        """Restore the window from the system tray."""

        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _on_tray_icon_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Restore the application when the tray icon is activated."""

        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._restore_from_tray()

    def _open_settings(self) -> None:
        """Open settings dialog for storage path configuration."""
        
        dialog = StorageSettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_path = dialog.get_selected_path()
            if new_path:
                migrate = dialog.should_migrate()
                
                reply = QMessageBox.question(
                    self,
                    "저장 위치 변경 확인",
                    f"저장 위치를 다음으로 변경하시겠습니까?\n\n{new_path}\n\n" +
                    ("기존 데이터가 새 위치로 이동됩니다." if migrate else "기존 데이터는 이동되지 않습니다."),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    if change_workspace_path(new_path, migrate=migrate):
                        QMessageBox.information(
                            self,
                            "저장 위치 변경 완료",
                            f"저장 위치가 변경되었습니다.\n\n새 위치: {new_path}\n\n" +
                            "앱을 다시 시작하면 새 위치가 적용됩니다."
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            "변경 실패",
                            "저장 위치 변경 중 오류가 발생했습니다."
                        )

    def _quit_application(self) -> None:
        """Terminate the application explicitly from the tray or toolbar."""

        try:
            self.sync_manager.shutdown()
        except Exception as e:
            print(f"Sync shutdown error: {e}")
        
        try:
            self.tray_icon.hide()
            self.tray_icon.setVisible(False)
        except Exception as e:
            print(f"Tray icon hide error: {e}")
        
        # Force quit
        QApplication.quit()
        
        # Fallback force exit
        import sys
        QTimer.singleShot(500, lambda: sys.exit(0))

    def closeEvent(self, event: QCloseEvent) -> None:
        """Minimize to tray instead of exiting when the window is closed."""

        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "누니메모",
                "앱이 시스템 트레이에서 계속 실행 중입니다.",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
            event.ignore()
            return
        super().closeEvent(event)


# Add custom styles for icon buttons
def apply_icon_button_style(button: QPushButton) -> None:
    """Apply consistent styling to icon buttons."""
    button.setStyleSheet("""
        QPushButton[iconButton="true"] {
            background-color: transparent;
            border: 1px solid #d9e2ec;
            border-radius: 6px;
            color: #64748b;
            font-size: 14px;
            font-weight: 600;
            min-width: 24px;
            min-height: 24px;
            max-width: 24px;
            max-height: 24px;
        }
        QPushButton[iconButton="true"]:hover {
            background-color: #f1f5f9;
            border-color: #94a3b8;
            color: #475569;
        }
        QPushButton[iconButton="true"]:pressed {
            background-color: #e2e8f0;
            border-color: #64748b;
        }
    """)
