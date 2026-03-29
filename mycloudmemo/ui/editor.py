"""Milkdown Editor Component for PySide6 QWebEngineView.

Provides a WYSIWYG Markdown editor using Milkdown v7 with QWebChannel bridge.
"""

from __future__ import annotations

import json
import base64
import time
from pathlib import Path
from typing import Callable, Any

from PySide6.QtCore import (
    QObject, 
    Qt, 
    Signal, 
    Slot, 
    QTimer,
    QUrl
)
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox
)
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineSettings
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel


class EditorBridge(QObject):
    """Bridge object for QWebChannel communication between Python and JavaScript."""
    
    # Signals emitted from Python to JavaScript
    contentLoaded = Signal(str)
    imageSaved = Signal(str, str)  # relative_path, error_message
    
    def __init__(self, parent: MilkdownEditor | None = None) -> None:
        super().__init__(parent)
        self._editor: MilkdownEditor | None = parent
    
    @Slot(str)
    def onContentChanged(self, markdown: str) -> None:
        """Called when editor content changes."""
        if self._editor and self._editor.on_content_changed:
            self._editor.on_content_changed(markdown)
    
    @Slot(str, str)
    def requestImageSave(self, base64_data: str, filename: str) -> None:
        """Handle image save request from JavaScript."""
        if self._editor:
            self._editor._save_image_from_js(base64_data, filename)
    
    @Slot(str)
    def logMessage(self, message: str) -> None:
        """Log messages from JavaScript console."""
        print(f"[Milkdown] {message}")


class MilkdownEditor(QWidget):
    """Milkdown v7 Markdown Editor Widget for PySide6.
    
    Features:
    - WYSIWYG Markdown editing
    - Custom Enter key behavior (single \n instead of paragraph)
    - Image paste/drop with automatic saving
    - Pure Markdown I/O via QWebChannel
    """
    
    # Signals
    contentChanged = Signal(str)  # Emitted when content changes
    imageInserted = Signal(str)   # Emitted when image is inserted (relative path)
    
    def __init__(
        self, 
        parent: QWidget | None = None,
        assets_path: Path | None = None,
        on_content_changed: Callable[[str], None] | None = None
    ) -> None:
        super().__init__(parent)
        
        self.assets_path = assets_path or Path("assets")
        self.on_content_changed = on_content_changed
        self._is_loading = False
        
        # Setup UI
        self._setup_ui()
        
        # Setup WebChannel bridge
        self._setup_webchannel()
        
        # Load editor HTML
        self._load_editor()
    
    def _setup_ui(self) -> None:
        """Setup the editor UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 8, 8, 8)
        toolbar.setSpacing(4)
        
        # Format buttons
        btn_bold = QPushButton("B")
        btn_bold.setToolTip("Bold (Ctrl+B)")
        btn_bold.setFixedSize(32, 32)
        btn_bold.clicked.connect(lambda: self._exec_command("toggleBold"))
        
        btn_italic = QPushButton("I")
        btn_italic.setToolTip("Italic (Ctrl+I)")
        btn_italic.setFixedSize(32, 32)
        btn_italic.setStyleSheet("font-style: italic;")
        btn_italic.clicked.connect(lambda: self._exec_command("toggleItalic"))
        
        btn_code = QPushButton("</>")
        btn_code.setToolTip("Inline Code")
        btn_code.setFixedSize(32, 32)
        btn_code.clicked.connect(lambda: self._exec_command("toggleCode"))
        
        btn_link = QPushButton("🔗")
        btn_link.setToolTip("Insert Link")
        btn_link.setFixedSize(32, 32)
        btn_link.clicked.connect(self._insert_link)
        
        btn_image = QPushButton("🖼️")
        btn_image.setToolTip("Insert Image")
        btn_image.setFixedSize(32, 32)
        btn_image.clicked.connect(self._insert_image)
        
        toolbar.addWidget(btn_bold)
        toolbar.addWidget(btn_italic)
        toolbar.addWidget(btn_code)
        toolbar.addWidget(btn_link)
        toolbar.addWidget(btn_image)
        toolbar.addStretch()
        
        # Status label
        self.status_label = QLabel("Ready")
        toolbar.addWidget(self.status_label)
        
        layout.addLayout(toolbar)
        
        # WebEngine View
        self.web_view = QWebEngineView(self)
        self.web_view.setMinimumHeight(200)
        
        # Enable local content access
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        
        layout.addWidget(self.web_view, 1)
    
    def _setup_webchannel(self) -> None:
        """Setup QWebChannel for Python-JavaScript communication."""
        self.bridge = EditorBridge(self)
        
        self.channel = QWebChannel(self)
        self.channel.registerObject("py_bridge", self.bridge)
        
        # Inject WebChannel script
        self.web_view.page().setWebChannel(self.channel)
    
    def _load_editor(self) -> None:
        """Load the Milkdown editor HTML."""
        html_content = self._generate_html()
        self.web_view.setHtml(html_content, QUrl("qrc:/"))
    
    def _generate_html(self) -> str:
        """Generate the HTML with embedded Milkdown editor."""
        return """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Milkdown Editor</title>
    
    <!-- Milkdown v7 Editor -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@milkdown/theme-nord@7.3.0/style.css" />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@milkdown/prose@7.3.0/style.css" />
    <script type="module">
        import { Editor, rootCtx, defaultValueCtx } from 'https://cdn.jsdelivr.net/npm/@milkdown/core@7.3.0/+esm';
        import { commonmark } from 'https://cdn.jsdelivr.net/npm/@milkdown/preset-commonmark@7.3.0/+esm';
        import { gfm } from 'https://cdn.jsdelivr.net/npm/@milkdown/preset-gfm@7.3.0/+esm';
        import { nord } from 'https://cdn.jsdelivr.net/npm/@milkdown/theme-nord@7.3.0/+esm';
        import { history } from 'https://cdn.jsdelivr.net/npm/@milkdown/plugin-history@7.3.0/+esm';
        import { clipboard } from 'https://cdn.jsdelivr.net/npm/@milkdown/plugin-clipboard@7.3.0/+esm';
        import { cursor } from 'https://cdn.jsdelivr.net/npm/@milkdown/plugin-cursor@7.3.0/+esm';
        import { listener, listenerCtx } from 'https://cdn.jsdelivr.net/npm/@milkdown/plugin-listener@7.3.0/+esm';
        
        // Global editor instance
        window.milkdownEditor = null;
        window.pyBridge = null;
        
        // Wait for QWebChannel
        if (typeof qt !== 'undefined') {
            new QWebChannel(qt.webChannelTransport, function(channel) {
                window.pyBridge = channel.objects.py_bridge;
                initEditor();
            });
        } else {
            // Fallback for testing without Qt
            console.log('Qt not available, running in standalone mode');
            initEditor();
        }
        
        async function initEditor() {
            const editorEl = document.getElementById('editor');
            if (!editorEl) {
                console.error('Editor element not found');
                return;
            }
            
            // Custom Enter key plugin - maps Enter to hard break
            const customEnterKeymap = {
                Enter: {
                    run: (view) => {
                        const { state, dispatch } = view;
                        const { schema, selection } = state;
                        
                        // Insert hard break node for single line break
                        const hardBreakNode = schema.nodes.hardbreak?.create();
                        if (hardBreakNode) {
                            const tr = state.tr.insert(selection.from, hardBreakNode);
                            dispatch(tr);
                            
                            // Notify Python of content change
                            setTimeout(() => notifyContentChanged(), 0);
                            return true;
                        }
                        return false;
                    }
                }
            };
            
            window.milkdownEditor = await Editor
                .make()
                .config((ctx) => {
                    ctx.set(rootCtx, editorEl);
                    ctx.set(defaultValueCtx, '');
                    
                    // Listen for markdown changes
                    ctx.get(listenerCtx).markdownUpdated((ctx, markdown, prevMarkdown) => {
                        if (window.pyBridge) {
                            window.pyBridge.onContentChanged(markdown);
                        }
                    });
                })
                .config(nord)
                .use(commonmark)
                .use(gfm)
                .use(history)
                .use(clipboard)
                .use(cursor)
                .use(listener)
                .use(() => ({ keymap: () => customEnterKeymap }))
                .create();
            
            console.log('Milkdown initialized');
            
            // Setup image handlers
            setupImageHandlers();
        }
        
        function setupImageHandlers() {
            const editorEl = document.getElementById('editor');
            
            // Handle paste
            editorEl.addEventListener('paste', async (e) => {
                const items = e.clipboardData?.items;
                if (!items) return;
                
                for (let item of items) {
                    if (item.type.indexOf('image') !== -1) {
                        e.preventDefault();
                        const blob = item.getAsFile();
                        if (blob) {
                            await handleImageUpload(blob);
                        }
                        break;
                    }
                }
            });
            
            // Handle drop
            editorEl.addEventListener('drop', async (e) => {
                e.preventDefault();
                const files = e.dataTransfer?.files;
                if (!files) return;
                
                for (let file of files) {
                    if (file.type.indexOf('image') !== -1) {
                        await handleImageUpload(file);
                    }
                }
            });
        }
        
        async function handleImageUpload(file) {
            try {
                const base64 = await new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = (e) => resolve(e.target.result);
                    reader.onerror = reject;
                    reader.readAsDataURL(file);
                });
                
                if (window.pyBridge) {
                    window.pyBridge.requestImageSave(base64, file.name);
                } else {
                    console.log('Image upload (no bridge):', file.name);
                }
            } catch (error) {
                console.error('Image upload failed:', error);
            }
        }
        
        // Exposed functions for Python to call
        window.getMarkdown = function() {
            if (!window.milkdownEditor) return '';
            
            let markdown = '';
            window.milkdownEditor.action((ctx) => {
                const editorView = ctx.editor?.view;
                if (editorView?.state) {
                    markdown = extractMarkdownFromNode(editorView.state.doc);
                }
            });
            return markdown;
        };
        
        window.setMarkdown = function(markdown) {
            if (!window.milkdownEditor) return;
            
            window.milkdownEditor.action((ctx) => {
                const editor = ctx.editor;
                if (editor && editor.replaceAll) {
                    editor.replaceAll(markdown || '');
                }
            });
        };
        
        window.insertImage = function(relativePath, alt) {
            const markdown = `![${alt || 'image'}](${relativePath})`;
            window.milkdownEditor?.action((ctx) => {
                const view = ctx.editor?.view;
                if (view) {
                    const { state } = view;
                    const tr = state.tr.insertText(markdown, state.selection.from);
                    view.dispatch(tr);
                }
            });
        };
        
        window.execCommand = function(command) {
            // Execute formatting commands
            const commands = {
                toggleBold: () => wrapText('**', '**'),
                toggleItalic: () => wrapText('*', '*'),
                toggleCode: () => wrapText('`', '`'),
            };
            
            if (commands[command]) {
                commands[command]();
            }
        };
        
        function wrapText(before, after) {
            // Simple text wrapping - in production, use proper selection handling
            console.log('Wrap text:', before, after);
        }
        
        function notifyContentChanged() {
            const markdown = window.getMarkdown();
            if (window.pyBridge) {
                window.pyBridge.onContentChanged(markdown);
            }
        }
        
        // Markdown extraction helpers
        function extractMarkdownFromNode(node) {
            let markdown = '';
            
            node.forEach((child) => {
                if (child.type.name === 'paragraph') {
                    if (markdown) markdown += '\n\n';
                    markdown += extractTextFromNode(child);
                } else if (child.type.name === 'heading') {
                    if (markdown) markdown += '\n\n';
                    markdown += '#'.repeat(child.attrs.level) + ' ' + extractTextFromNode(child);
                } else if (child.type.name === 'hardbreak') {
                    markdown += '\n';
                } else if (child.type.name === 'code_block') {
                    if (markdown) markdown += '\n\n';
                    markdown += '```\n' + child.textContent + '\n```';
                } else if (child.type.name === 'bullet_list' || child.type.name === 'ordered_list') {
                    if (markdown) markdown += '\n\n';
                    markdown += extractListFromNode(child, child.type.name === 'ordered_list');
                } else if (child.type.name === 'blockquote') {
                    if (markdown) markdown += '\n\n';
                    markdown += '> ' + extractTextFromNode(child).replace(/\n/g, '\n> ');
                }
            });
            
            return markdown;
        }
        
        function extractTextFromNode(node) {
            let text = '';
            
            node.forEach((child) => {
                if (child.isText) {
                    text += child.text;
                } else if (child.type.name === 'hardbreak') {
                    text += '\n';
                } else if (child.type.name === 'image') {
                    text += `![${child.attrs.alt || ''}](${child.attrs.src || ''})`;
                } else if (child.type.name === 'link') {
                    text += `[${extractTextFromNode(child)}](${child.attrs.href || ''})`;
                } else if (child.type.name === 'strong') {
                    text += `**${extractTextFromNode(child)}**`;
                } else if (child.type.name === 'em') {
                    text += `*${extractTextFromNode(child)}*`;
                } else if (child.type.name === 'code') {
                    text += `\`${extractTextFromNode(child)}\``;
                } else {
                    text += extractTextFromNode(child);
                }
            });
            
            return text;
        }
        
        function extractListFromNode(node, ordered) {
            let text = '';
            let index = 1;
            
            node.forEach((child) => {
                if (child.type.name === 'list_item') {
                    const prefix = ordered ? `${index}. ` : '- ';
                    text += prefix + extractTextFromNode(child) + '\n';
                    index++;
                }
            });
            
            return text.trim();
        }
    </script>
    
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #ffffff;
        }
        
        #editor {
            height: 100vh;
            overflow-y: auto;
        }
        
        .milkdown {
            height: 100%;
        }
        
        .milkdown .editor {
            padding: 1rem 2rem;
            min-height: 100%;
        }
        
        /* Ensure proper spacing for hard breaks */
        .milkdown br {
            display: block;
            content: "";
            margin-top: 0.5em;
        }
    </style>
</head>
<body>
    <div id="editor"></div>
</body>
</html>"""
    
    def _exec_command(self, command: str) -> None:
        """Execute a formatting command in the editor."""
        self.web_view.page().runJavaScript(f"window.execCommand('{command}');")
    
    def _insert_link(self) -> None:
        """Insert a link at cursor position."""
        # In production, show a dialog for URL input
        self.web_view.page().runJavaScript(
            "window.milkdownEditor?.action((ctx) => { "
            "const view = ctx.editor?.view; "
            "if (view) { "
            "const { state } = view; "
            "const tr = state.tr.insertText('[link](url)', state.selection.from); "
            "view.dispatch(tr); "
            "} "
            "});"
        )
    
    def _insert_image(self) -> None:
        """Open file dialog to insert an image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        
        if file_path:
            # Copy to assets folder and insert
            self._copy_and_insert_image(Path(file_path))
    
    def _copy_and_insert_image(self, source_path: Path) -> None:
        """Copy image to assets folder and insert into editor."""
        try:
            # Ensure assets directory exists
            self.assets_path.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename
            timestamp = int(time.time() * 1000)
            ext = source_path.suffix
            dest_name = f"img_{timestamp}{ext}"
            dest_path = self.assets_path / dest_name
            
            # Copy file
            import shutil
            shutil.copy2(source_path, dest_path)
            
            # Get relative path
            relative_path = f"assets/{dest_name}"
            
            # Insert into editor
            self.insert_image(relative_path, source_path.name)
            
            self.imageInserted.emit(relative_path)
            self.status_label.setText(f"Image inserted: {dest_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to insert image: {e}")
    
    def _save_image_from_js(self, base64_data: str, filename: str) -> None:
        """Save image from JavaScript (paste/drop) and insert into editor."""
        try:
            # Ensure assets directory exists
            self.assets_path.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename
            timestamp = int(time.time() * 1000)
            ext = Path(filename).suffix or '.png'
            dest_name = f"img_{timestamp}{ext}"
            dest_path = self.assets_path / dest_name
            
            # Decode base64 and save
            # Remove data:image/...;base64, prefix if present
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            
            image_bytes = base64.b64decode(base64_data)
            dest_path.write_bytes(image_bytes)
            
            # Get relative path
            relative_path = f"assets/{dest_name}"
            
            # Insert into editor via JavaScript
            self.insert_image(relative_path, filename)
            
            self.imageInserted.emit(relative_path)
            self.bridge.imageSaved.emit(relative_path, "")
            
        except Exception as e:
            error_msg = str(e)
            self.bridge.imageSaved.emit("", error_msg)
            print(f"Error saving image: {e}")
    
    # Public API
    def get_markdown(self) -> str:
        """Get the current Markdown content from the editor."""
        # Use a callback to get the value asynchronously
        result = [""]
        
        def callback(value):
            result[0] = value
        
        self.web_view.page().runJavaScript("window.getMarkdown();", callback)
        
        # Wait for result (in production, use proper async handling)
        import time
        timeout = 0
        while not result[0] and timeout < 50:
            time.sleep(0.01)
            timeout += 1
        
        return result[0]
    
    def set_markdown(self, markdown: str) -> None:
        """Set the Markdown content in the editor."""
        # Escape special characters for JavaScript string
        escaped = json.dumps(markdown)
        self.web_view.page().runJavaScript(f"window.setMarkdown({escaped});")
        self._is_loading = True
        QTimer.singleShot(100, lambda: setattr(self, '_is_loading', False))
    
    def insert_image(self, relative_path: str, alt: str = "") -> None:
        """Insert an image at the current cursor position."""
        escaped_path = json.dumps(relative_path)
        escaped_alt = json.dumps(alt)
        self.web_view.page().runJavaScript(
            f"window.insertImage({escaped_path}, {escaped_alt});"
        )
    
    def clear(self) -> None:
        """Clear the editor content."""
        self.set_markdown("")
    
    def focus(self) -> None:
        """Set focus to the editor."""
        self.web_view.setFocus()
    
    def set_assets_path(self, path: Path) -> None:
        """Set the assets directory path for image storage."""
        self.assets_path = path
