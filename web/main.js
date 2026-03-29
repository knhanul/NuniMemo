/**
 * NuniMemo Web Frontend
 * PyWebView + HTML/CSS/JS + Tailwind CSS
 */

// Global state
let state = {
    folders: [],
    memos: [],
    currentFolderId: 'root',
    currentMemoId: null,
    editor: null,
    editorInstance: null,  // Milkdown editor instance
    autoSaveTimer: null,
    isLoading: false,
    tabs: [],
    activeTabId: null,
    isSwitchingTab: false,
    defaultFolderId: null,
    sortField: 'last_modified',
    sortDirection: 'desc'
};

// DOM Elements
const elements = {
    folderList: document.getElementById('folder-list'),
    memoList: document.getElementById('memo-list'),
    currentFolderLabel: document.getElementById('current-folder-label'),
    syncStatus: document.getElementById('sync-status'),
    wordCount: document.getElementById('word-count'),
    folderModal: document.getElementById('folder-modal'),
    folderNameInput: document.getElementById('folder-name-input'),
    tabBar: document.getElementById('tab-bar'),
    editor: document.getElementById('editor'),
    
    // Memo location breadcrumb
    memoLocation: document.getElementById('memo-location'),
    locationFolder: document.getElementById('location-folder'),
    locationMemo: document.getElementById('location-memo'),

    // Buttons
    btnAddFolder: document.getElementById('btn-add-folder'),
    btnDeleteFolder: document.getElementById('btn-delete-folder'),
    btnAddMemo: document.getElementById('btn-add-memo'),
    btnDeleteMemo: document.getElementById('btn-delete-memo'),
    btnSync: document.getElementById('btn-sync'),
    btnSettings: document.getElementById('btn-settings'),
    
    // Memotype modal
    memoTypeModal: document.getElementById('memo-type-modal'),
    btnCancelMemoType: document.getElementById('btn-cancel-memo-type'),
    btnConfirmMemoType: document.getElementById('btn-confirm-memo-type'),
    btnConfirmFolder: document.getElementById('btn-confirm-folder'),
    btnCancelFolder: document.getElementById('btn-cancel-folder'),
    
    // Settings modal
    settingsModal: document.getElementById('settings-modal'),
    btnCloseSettings: document.getElementById('btn-close-settings'),
    btnChangeStorage: document.getElementById('btn-change-storage'),
    currentStoragePath: document.getElementById('current-storage-path'),
    migrationProgress: document.getElementById('migration-progress'),
    migrationStatus: document.getElementById('migration-status'),
    migrationPercent: document.getElementById('migration-percent'),
    migrationBar: document.getElementById('migration-bar'),
    memoSortField: document.getElementById('memo-sort-field'),
    memoSortDirection: document.getElementById('memo-sort-direction'),
    sortIcon: document.getElementById('sort-icon')
};

// ============================================================================
// Tab Management
// ============================================================================

function createTab(memo) {
    const existingTab = state.tabs.find(tab => tab.id === `tab-${memo.id}`);
    if (existingTab) {
        switchToTab(`tab-${memo.id}`);
        return;
    }

    const tab = {
        id: `tab-${memo.id}`,
        memoId: memo.id,
        title: memo.title,
        memoType: memo.memo_type || 'rich_text', // Store memo type
        content: '',
        isDirty: false
    };

    state.tabs.push(tab);

    const tabEl = document.createElement('div');
    tabEl.className = 'tab';
    tabEl.dataset.tabId = tab.id;
    tabEl.innerHTML = `
        <span class="tab-title">${escapeHtml(memo.title)}</span>
        <button class="tab-close">
            <i data-lucide="x" class="w-3 h-3"></i>
        </button>
    `;

    tabEl.addEventListener('click', (e) => {
        if (!e.target.closest('.tab-close')) {
            switchToTab(tab.id);
        }
    });

    tabEl.querySelector('.tab-close').addEventListener('click', (e) => {
        e.stopPropagation();
        closeTab(tab.id);
    });

    const tabBarContainer = elements.tabBar.querySelector('.flex');
    tabBarContainer.appendChild(tabEl);

    loadMemoContent(memo.id, tab);
    switchToTab(tab.id);
    updateEditorState();

    lucide.createIcons();
}

function switchToTab(tabId) {
    const tab = state.tabs.find(t => t.id === tabId);
    if (!tab || !state.editorInstance) {
        return;
    }

    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });

    const tabEl = document.querySelector(`[data-tab-id="${tabId}"]`);
    if (tabEl) {
        tabEl.classList.add('active');
    }

    state.isSwitchingTab = true;
    state.activeTabId = tabId;
    state.currentMemoId = tab.memoId;
    setEditorMarkdown(tab.content || '');
    state.isSwitchingTab = false;
    updateWordCount();
    
    // Update breadcrumb location
    const memo = state.memos.find(m => m.id === tab.memoId);
    if (memo) {
        updateMemoLocation(memo);
    }
}

function closeTab(tabId) {
    console.log('Closing tab:', tabId);
    const tabIndex = state.tabs.findIndex(tab => tab.id === tabId);
    if (tabIndex === -1) {
        console.log('Tab not found:', tabId);
        return;
    }

    const tab = state.tabs[tabIndex];
    console.log('Tab to close:', tab);

    if (tab.isDirty) {
        console.log('Saving tab before closing...');
        saveTabContent(tabId);
    }

    state.tabs.splice(tabIndex, 1);
    console.log('Tabs after removal:', state.tabs);

    const tabEl = document.querySelector(`.tab[data-tab-id="${tabId}"]`);
    if (tabEl) {
        tabEl.remove();
        console.log('Tab element removed from DOM');
    }

    if (state.activeTabId === tabId) {
        console.log('Closing active tab, switching to another...');
        if (state.tabs.length > 0) {
            switchToTab(state.tabs[state.tabs.length - 1].id);
        } else {
            state.activeTabId = null;
            state.currentMemoId = null;
            setEditorMarkdown('');
            updateWordCount();
            updateEditorState();
            console.log('No more tabs, cleared editor');
        }
    }
}

function saveTabContent(tabId) {
    const tab = state.tabs.find(t => t.id === tabId);
    if (!tab || !tab.memoId) {
        console.log('Cannot save: tab or memoId not found');
        return;
    }

    // Get Markdown content from Vditor
    const markdown = getEditorMarkdown();
    
    // Extract title from first line of Markdown
    const text = markdown.trim();
    const firstLine = text.split('\n')[0] || '';
    // Remove Markdown heading markers for title
    const title = firstLine.replace(/^#+\s*/, '').substring(0, 30) || '제목 없음';
    
    // Update title in tab state and UI
    tab.title = title;
    const tabEl = document.querySelector(`[data-tab-id="${tabId}"] .tab-title`);
    if (tabEl) {
        tabEl.textContent = title;
    }
    
    // Save Markdown content to backend
    callApi('save_memo_content', tab.memoId, markdown).then(response => {
        if (response.success) {
            tab.isDirty = false;
            console.log('Memo saved successfully with title:', title);
        } else {
            console.error('Failed to save memo:', response.error);
            showError('메모 저장에 실패했습니다.');
        }
    });
}

function updateTabTitle(tabId) {
    console.log('Updating tab title for:', tabId);
    const tab = state.tabs.find(t => t.id === tabId);
    
    console.log('Tab found:', tab);
    console.log('Editor instance exists:', !!state.editorInstance);
    console.log('Active tab ID:', state.activeTabId);

    if (tab && state.editorInstance && state.activeTabId === tabId) {
        // Get Markdown text and extract first line
        const markdown = getEditorMarkdown();
        const firstLine = markdown.split('\n')[0] || '';
        // Remove Markdown heading markers for title
        const title = firstLine.replace(/^#+\s*/, '').substring(0, 30) || '제목 없음';
        console.log('Markdown content:', markdown.substring(0, 100));
        console.log('First line:', firstLine);
        console.log('New title:', title);
        
        // Update tab state
        tab.title = title;
        
        // Update DOM element - try multiple selectors
        const tabEl = document.querySelector(`[data-tab-id="${tabId}"]`);
        console.log('Tab element found:', tabEl);
        
        if (tabEl) {
            const titleEl = tabEl.querySelector('.tab-title');
            console.log('Title element found:', titleEl);
            
            if (titleEl) {
                // Force update with innerHTML to ensure it changes
                titleEl.innerHTML = escapeHtml(title);
                console.log('Title updated in DOM with innerHTML:', title);
                
                // Double-check by reading it back
                const updatedTitle = titleEl.textContent;
                console.log('Verification - DOM title now shows:', updatedTitle);
                
                // Also update the memo list item title
                const memoEl = document.querySelector(`[data-memo-id="${tab.memoId}"]`);
                if (memoEl) {
                    const memoTitleEl = memoEl.querySelector('.text-sm.font-medium');
                    if (memoTitleEl) {
                        // Update memo list title (preserve folder prefix if exists)
                        const currentText = memoTitleEl.textContent;
                        const folderPrefix = currentText.includes('📁') ? currentText.split('|')[0] + '| ' : '';
                        memoTitleEl.textContent = folderPrefix + title;
                        console.log('Memo list title updated:', folderPrefix + title);
                        
                        // Update the memo in state to persist the title change
                        const memo = state.memos.find(m => m.id === tab.memoId);
                        if (memo) {
                            memo.title = title;
                            console.log('Memo title updated in state:', memo);
                            
                            // Also save the title to database
                            callApi('update_memo_title', tab.memoId, title).then(response => {
                                if (!response.success) {
                                    console.error('Failed to update memo title:', response.error);
                                }
                            });
                        }
                    }
                }
            } else {
                // If .tab-title not found, update the whole tab content
                const closeButton = tabEl.querySelector('.tab-close');
                if (closeButton) {
                    const titleSpan = document.createElement('span');
                    titleSpan.className = 'tab-title';
                    titleSpan.textContent = title;
                    tabEl.insertBefore(titleSpan, closeButton);
                    console.log('Title element created and added:', title);
                }
            }
        }
    }
}

function loadMemoContent(memoId, tab) {
    callApi('get_memo_content', memoId).then(response => {
        if (response.success) {
            // Store the Markdown content directly
            tab.content = response.data.content;
            tab.isDirty = false;
            
            // Use window.toastEditor for setting content
            if (window.toastEditor) {
                state.isSwitchingTab = true;
                window.toastEditor.setMarkdown(tab.content || '', false);
                state.isSwitchingTab = false;
                updateWordCount();
            } else {
                console.error('TOAST UI Editor not initialized - cannot load content');
            }
        }
    });
}

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    elements.memoSortField.addEventListener('change', (e) => {
        state.sortField = e.target.value;
        sortMemos();
        renderMemos();
    });
    
    elements.memoSortDirection.addEventListener('click', () => {
        state.sortDirection = state.sortDirection === 'desc' ? 'asc' : 'desc';
        elements.sortIcon.setAttribute('data-lucide', state.sortDirection === 'desc' ? 'arrow-down' : 'arrow-up');
        lucide.createIcons();
        sortMemos();
        renderMemos();
    });
    
    // Initialize Lucide icons
    lucide.createIcons();
    initEditor();
    
    // Setup event listeners
    setupEventListeners();
    
    // Wait for pywebview to be ready
    if (window.pywebview && window.pywebview.api) {
        console.log('PyWebView API is ready');
        await initializeApp();
    } else {
        console.log('Waiting for PyWebView API...');
        // Wait for pywebviewready event
        window.addEventListener('pywebviewready', async () => {
            console.log('PyWebView API is now ready');
            await initializeApp();
        });
    }
});

async function initializeApp() {
    // Load initial data
    await loadFolders();
    
    // Try to load and select default folder
    await loadDefaultFolder();
    
    // If no default folder or it doesn't exist, fall back to root
    if (!state.defaultFolderId || !state.folders.some(f => f.id === state.defaultFolderId)) {
        await loadMemos('root');
        selectFolder('root');
    }
    
    // Update editor state to show empty state UI if no tabs open
    updateEditorState();
}

function initEditor() {
    if (!elements.editor) {
        console.error('Editor element not found in DOM');
        return;
    }
    
    // Initialize TOAST UI Editor when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initToastEditor);
    } else {
        initToastEditor();
    }
}

function initToastEditor() {
    try {
        console.log('Initializing TOAST UI Editor...');
        
        // Check if toastui is available
        if (typeof toastui === 'undefined' || !toastui.Editor) {
            console.error('TOAST UI Editor library not loaded');
            return;
        }
        
        // Create TOAST UI Editor instance
        window.toastEditor = new toastui.Editor({
            el: document.querySelector('#editor'),
            height: '100%',
            initialEditType: 'wysiwyg',
            previewStyle: 'vertical',
            hideModeSwitch: true,
            placeholder: '여기에 메모를 작성하세요...',
            toolbarItems: [
                ['heading', 'bold', 'italic', 'strike'],
                ['hr', 'quote'],
                ['ul', 'ol', 'task', 'indent', 'outdent'],
                ['table', 'image', 'link'],
                ['code', 'codeblock']
            ],
            hooks: {
                addImageBlobHook: (blob, callback) => {
                    const reader = new FileReader();
                    reader.onload = () => {
                        const base64String = reader.result;
                        const filename = blob.name || 'image_' + new Date().getTime() + '.png';

                        window.pywebview.api.save_image(base64String, filename)
                            .then(res => {
                                console.log('Raw response from save_image:', res);
                                
                                // PyWebView might return a string or an object
                                let response = typeof res === 'string' ? JSON.parse(res) : res;
                                console.log('Parsed response:', response);

                                if (response && response.success && response.data) {
                                    console.log('Image save successful:', response.data);
                                    console.log('Available fields:', Object.keys(response.data));
                                    console.log('data_uri:', response.data.data_uri);
                                    console.log('path:', response.data.path);
                                    
                                    // Use base64 data URI for immediate preview
                                    const imageUrl = response.data.data_uri || response.data.path;
                                    console.log('Using imageUrl:', imageUrl);
                                    callback(imageUrl, blob.name || 'image');
                                } else {
                                    console.error("Image save failed:", response);
                                }
                            })
                            .catch(err => {
                                console.error("Error calling save_image:", err);
                            });
                    };
                    reader.readAsDataURL(blob);
                }
            },
            events: {
                change: () => {
                    handleEditorChange();
                }
            }
        });
        
        // Also keep reference in state for consistency
        state.editorInstance = window.toastEditor;
        
        console.log('TOAST UI Editor initialized successfully');
        
        // Fix toolbar icon sizes after initialization
        scheduleToolbarFixes();
        
        // Add table resize functionality
        addTableResizeFunctionality();
        
        // Set initial opacity
        elements.editor.style.opacity = '1';
        
        updateWordCount();
        
    } catch (error) {
        console.error('Failed to initialize TOAST UI Editor:', error);
        elements.editor.innerHTML = `
            <div style="padding: 20px; color: #dc2626; text-align: center;">
                <p><strong>에디터 초기화 실패</strong></p>
                <p style="font-size: 12px; color: #64748b;">${error.message}</p>
            </div>
        `;
    }
}

function fixToolbarIcons() {
    // Inject custom CSS if not already present
    if (!document.getElementById('toolbar-fix-style')) {
        const style = document.createElement('style');
        style.id = 'toolbar-fix-style';
        style.textContent = `
            /* Button sizing */
            .toastui-editor-toolbar button,
            .toastui-editor-defaultUI-toolbar button,
            .toastui-editor-toolbar .tui-toolbar-btn {
                width: 24px !important;
                height: 24px !important;
                padding: 0 !important;
                margin: 0 1px !important;
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            /* Icon sizing - target the actual icon elements */
            .toastui-editor-toolbar-icons,
            .toastui-editor-toolbar button svg,
            .toastui-editor-toolbar button i {
                width: 14px !important;
                height: 14px !important;
                opacity: 1 !important;
                visibility: visible !important;
            }
            /* Force icon visibility on ALL states */
            .toastui-editor-toolbar button:hover,
            .toastui-editor-toolbar button:focus,
            .toastui-editor-toolbar button:active {
                background-color: #e2e8f0 !important;
            }
            .toastui-editor-toolbar button:hover .toastui-editor-toolbar-icons,
            .toastui-editor-toolbar button:focus .toastui-editor-toolbar-icons,
            .toastui-editor-toolbar button:active .toastui-editor-toolbar-icons,
            .toastui-editor-toolbar button:hover svg,
            .toastui-editor-toolbar button:focus svg,
            .toastui-editor-toolbar button:active svg {
                opacity: 1 !important;
                visibility: visible !important;
                display: inline-block !important;
            }
            /* Tooltip positioning */
            .toastui-editor-toolbar-tooltip {
                position: absolute !important;
                z-index: 99999 !important;
                pointer-events: none !important;
                background: #1e293b !important;
                color: white !important;
                padding: 4px 8px !important;
                border-radius: 4px !important;
                font-size: 11px !important;
                white-space: nowrap !important;
                top: 100% !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                margin-top: 4px !important;
            }
        `;
        document.head.appendChild(style);
    }
    
    // Direct style application to all toolbar buttons
    const allToolbarElements = document.querySelectorAll('.toastui-editor-toolbar, .toastui-editor-defaultUI-toolbar');
    allToolbarElements.forEach(toolbar => {
        const buttons = toolbar.querySelectorAll('button, .tui-toolbar-btn');
        buttons.forEach(btn => {
            btn.style.cssText += ';width:24px!important;height:24px!important;padding:0!important;display:inline-flex!important;align-items:center!important;justify-content:center!important;overflow:visible!important;';
            
            // Find and resize icons
            const icons = btn.querySelectorAll('.toastui-editor-toolbar-icons, svg, i, span[class*="icon"]');
            icons.forEach(icon => {
                icon.style.cssText += ';width:14px!important;height:14px!important;min-width:14px!important;min-height:14px!important;opacity:1!important;visibility:visible!important;display:inline-block!important;';
            });
        });
    });
}

// Schedule multiple fixes and set up observer
function scheduleToolbarFixes() {
    // Run immediately and multiple times
    [0, 100, 300, 600, 1000, 2000].forEach(delay => {
        setTimeout(fixToolbarIcons, delay);
    });
    
    // Set up observer to continuously fix any new toolbar elements
    const observer = new MutationObserver((mutations) => {
        let shouldFix = false;
        mutations.forEach(mutation => {
            if (mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1) { // Element node
                        if (node.classList && (
                            node.classList.contains('toastui-editor-toolbar') ||
                            node.classList.contains('toastui-editor-defaultUI-toolbar') ||
                            node.querySelector('.toastui-editor-toolbar')
                        )) {
                            shouldFix = true;
                        }
                    }
                });
            }
        });
        if (shouldFix) {
            fixToolbarIcons();
        }
    });
    
    // Observe the entire document for toolbar changes
    setTimeout(() => {
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }, 500);
}

// Add table resize functionality
function addTableResizeFunctionality() {
    // Add custom CSS for better table resize
    if (!document.getElementById('table-resize-style')) {
        const style = document.createElement('style');
        style.id = 'table-resize-style';
        style.textContent = `
            .toastui-editor-contents table {
                position: relative !important;
                resize: both !important;
                overflow: auto !important;
                min-width: 200px !important;
                min-height: 100px !important;
                max-width: 100% !important;
                border: 1px solid #e2e8f0 !important;
            }
            
            .toastui-editor-contents table:hover {
                outline: 2px solid #3b82f6 !important;
                outline-offset: 2px !important;
            }
            
            .toastui-editor-contents table.resize-handle {
                position: relative !important;
            }
            
            .toastui-editor-contents table.resize-handle::after {
                content: '';
                position: absolute !important;
                bottom: 0 !important;
                right: 0 !important;
                width: 20px !important;
                height: 20px !important;
                background: linear-gradient(135deg, transparent 50%, #3b82f6 50%) !important;
                cursor: nwse-resize !important;
                z-index: 10 !important;
            }
        `;
        document.head.appendChild(style);
    }
    
    // Monitor editor content for tables and add resize functionality
    const editorContent = document.querySelector('.toastui-editor-contents');
    if (editorContent) {
        const tableObserver = new MutationObserver((mutations) => {
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1) {
                        // Check if this is a table or contains tables
                        if (node.tagName === 'TABLE' || node.querySelector('table')) {
                            const tables = node.tagName === 'TABLE' ? [node] : node.querySelectorAll('table');
                            tables.forEach(table => addResizeHandle(table));
                        }
                    }
                });
            });
        });
        
        tableObserver.observe(editorContent, {
            childList: true,
            subtree: true
        });
        
        // Add resize handles to existing tables
        const existingTables = editorContent.querySelectorAll('table');
        existingTables.forEach(table => addResizeHandle(table));
    }
}

// Add resize handle to a table
function addResizeHandle(table) {
    if (table.classList.contains('resize-handle')) return;
    
    table.classList.add('resize-handle');
    
    // Make table resizable
    table.style.resize = 'both';
    table.style.overflow = 'auto';
    table.style.minWidth = '200px';
    table.style.minHeight = '100px';
    table.style.maxWidth = '100%';
    
    // Add resize event listener
    let isResizing = false;
    let startX, startY, startWidth, startHeight;
    
    const resizeHandle = document.createElement('div');
    resizeHandle.style.cssText = `
        position: absolute;
        bottom: 0;
        right: 0;
        width: 20px;
        height: 20px;
        background: linear-gradient(135deg, transparent 50%, #3b82f6 50%);
        cursor: nwse-resize;
        z-index: 10;
    `;
    
    table.style.position = 'relative';
    table.appendChild(resizeHandle);
    
    resizeHandle.addEventListener('mousedown', (e) => {
        isResizing = true;
        startX = e.clientX;
        startY = e.clientY;
        startWidth = parseInt(document.defaultView.getComputedStyle(table).width, 10);
        startHeight = parseInt(document.defaultView.getComputedStyle(table).height, 10);
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        
        const width = startWidth + e.clientX - startX;
        const height = startHeight + e.clientY - startY;
        
        table.style.width = Math.max(200, width) + 'px';
        table.style.height = Math.max(100, height) + 'px';
    });
    
    document.addEventListener('mouseup', () => {
        isResizing = false;
    });
}

function handleEditorChange() {
    updateWordCount();
    
    if (state.isSwitchingTab || !state.activeTabId) {
        return;
    }
    
    const activeTab = state.tabs.find(tab => tab.id === state.activeTabId);
    if (!activeTab) {
        return;
    }
    
    const content = getEditorMarkdown();
    activeTab.content = content;
    activeTab.isDirty = true;
    updateTabTitle(activeTab.id);
    scheduleAutoSave(activeTab.id);
}

function getEditorMarkdown() {
    if (window.toastEditor) {
        return window.toastEditor.getMarkdown() || '';
    }
    if (state.editorInstance) {
        return state.editorInstance.getMarkdown() || '';
    }
    return '';
}

function setEditorMarkdown(markdown) {
    if (window.toastEditor) {
        window.toastEditor.setMarkdown(markdown || '', false);
    } else if (state.editorInstance) {
        state.editorInstance.setMarkdown(markdown || '', false);
    }
}

function updateWordCount() {
    const markdown = getEditorMarkdown() || '';
    const plainText = markdown
        .replace(/[#*_`\[\](){}]/g, '')
        .replace(/!\[.*?\]\(.*?\)/g, '[이미지]')
        .replace(/\[.*?\]\(.*?\)/g, '[링크]')
        .trim();
    const count = plainText ? plainText.split(/\s+/).filter(w => w.length > 0).length : 0;
    elements.wordCount.textContent = `${count} 단어`;
}

function updateEditorState() {
    const hasOpenFile = state.tabs.length > 0;
    const editorContainer = document.getElementById('editor-container');
    
    if (!editorContainer) return;
    
    let placeholder = document.getElementById('editor-placeholder');
    
    if (!hasOpenFile) {
        // Hide the entire editor container
        editorContainer.style.display = 'none';
        
        if (!placeholder) {
            placeholder = document.createElement('div');
            placeholder.id = 'editor-placeholder';
            placeholder.className = 'flex flex-col items-center justify-center flex-1 text-slate-400 bg-slate-50';
            placeholder.innerHTML = `
                <i data-lucide="file-plus" class="w-16 h-16 mb-4 text-slate-300"></i>
                <p class="text-lg font-medium text-slate-500 mb-2">메모를 선택하거나 새로 만들어주세요</p>
                <p class="text-sm text-slate-400">왼쪽 메모 목록에서 메모를 클릭하거나<br>"새 메모" 버튼을 눌러 시작하세요</p>
                <button onclick="createMemo()" class="mt-6 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition flex items-center gap-2">
                    <i data-lucide="plus" class="w-4 h-4"></i>
                    새 메모 만들기
                </button>
            `;
            // Insert placeholder as sibling after editor-container
            editorContainer.parentNode.insertBefore(placeholder, editorContainer.nextSibling);
            lucide.createIcons();
        }
        placeholder.style.display = 'flex';
    } else {
        // Show editor container, hide placeholder
        editorContainer.style.display = 'flex';
        if (placeholder) {
            placeholder.style.display = 'none';
        }
        
        // Refresh TOAST UI Editor after showing
        setTimeout(() => {
            if (window.toastEditor) {
                window.toastEditor.refresh();
            }
        }, 50);
    }
}

function setupEventListeners() {
    // Folder buttons
    elements.btnAddFolder.addEventListener('click', showFolderModal);
    elements.btnDeleteFolder.addEventListener('click', deleteSelectedFolder);
    elements.btnConfirmFolder.addEventListener('click', createFolder);
    elements.btnCancelFolder.addEventListener('click', hideFolderModal);
    
    // Memo buttons
    elements.btnAddMemo.addEventListener('click', createMemo);
    elements.btnDeleteMemo.addEventListener('click', deleteSelectedMemo);
    
    // (Memo type modal removed - now creates markdown directly)
    
    // Other buttons
    elements.btnSync.addEventListener('click', syncToDrive);
    elements.btnSettings.addEventListener('click', showSettingsModal);
    
    // Settings modal
    elements.btnCloseSettings.addEventListener('click', hideSettingsModal);
    elements.btnChangeStorage.addEventListener('click', changeStorageFolder);
    
    // Close settings modal on backdrop click
    elements.settingsModal.addEventListener('click', (e) => {
        if (e.target === elements.settingsModal) hideSettingsModal();
    });
    
    // Modal enter key
    elements.folderNameInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') createFolder();
    });
    
    // Close modal on backdrop click
    elements.folderModal.addEventListener('click', (e) => {
        if (e.target === elements.folderModal) hideFolderModal();
    });
}

// ============================================================================
// API Calls
// ============================================================================

async function callApi(method, ...args) {
    if (!window.pywebview || !window.pywebview.api) {
        console.error('PyWebView API not available');
        return { success: false, error: 'API not available' };
    }
    
    try {
        console.log(`Calling API: ${method} with args:`, args);
        const result = await window.pywebview.api[method](...args);
        console.log(`API response:`, result);
        return JSON.parse(result);
    } catch (error) {
        console.error(`API call failed: ${method}`, error);
        return { success: false, error: error.message || error.toString() };
    }
}

// ============================================================================
// Folder Operations
// ============================================================================

async function loadFolders() {
    const response = await callApi('get_folders');
    if (response.success) {
        state.folders = response.data;
        renderFolders();
    } else {
        showError('폴더를 불러오는데 실패했습니다.');
    }
}

function renderFolders() {
    console.log('Rendering folders...');
    console.log('Current folders state:', state.folders);
    
    elements.folderList.innerHTML = '';
    
    // Find and add root folder first
    const rootFolder = state.folders.find(f => f.id === 'root');
    console.log('Root folder found:', rootFolder);
    if (rootFolder) {
        const rootEl = createFolderElement(rootFolder, 0);
        elements.folderList.appendChild(rootEl);
        console.log('Root folder added to DOM');
    }
    
    // Build folder tree for non-root folders
    const topLevelFolders = state.folders.filter(f => f.parent_id === null && f.id !== 'root');
    console.log('Top level folders:', topLevelFolders);
    
    topLevelFolders.forEach(folder => {
        const folderEl = createFolderElement(folder, 0);
        elements.folderList.appendChild(folderEl);
        
        // Add subfolders recursively
        const subfolders = getSubfolders(folder.id, 0);
        subfolders.forEach(subEl => {
            elements.folderList.appendChild(subEl);
        });
    });
    
    console.log('Folder list HTML after render:', elements.folderList.innerHTML);
    
    // Re-initialize icons for new elements
    lucide.createIcons();
}

function getSubfolders(parentId, depth) {
    const subfolders = state.folders.filter(f => f.parent_id === parentId);
    const elements = [];
    
    subfolders.forEach(folder => {
        const folderEl = createFolderElement(folder, depth + 1);
        elements.push(folderEl);
        
        // Recursively add nested subfolders
        const nestedSubfolders = getSubfolders(folder.id, depth + 1);
        elements.push(...nestedSubfolders);
    });
    
    return elements;
}

function createFolderElement(folder, depth) {
    const div = document.createElement('div');
    const isActive = folder.id === state.currentFolderId;
    const hasChildren = state.folders.some(f => f.parent_id === folder.id);
    const isDefault = folder.id === state.defaultFolderId;
    
    // Selected folder uses folder-open icon, others use folder (closed) icon
    // Default folder gets yellow color
    let iconName = isActive ? 'folder-open' : 'folder';
    let iconColor = isDefault ? 'text-yellow-500' : (isActive ? 'text-blue-500' : 'text-slate-400');
    
    div.className = `list-item flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer ${
        isActive ? 'active' : ''
    } ${isDefault ? 'default-folder' : ''}`;
    div.style.paddingLeft = `${12 + depth * 16}px`;
    div.dataset.folderId = folder.id;
    
    div.innerHTML = `
        <i data-lucide="${iconName}" class="w-4 h-4 ${iconColor}"></i>
        <span class="text-sm truncate flex-1 ${isActive ? 'font-medium' : 'text-slate-700'}">${escapeHtml(folder.name)}</span>
        ${isDefault ? '<i data-lucide="star" class="w-3 h-3 text-yellow-500"></i>' : ''}
    `;
    
    div.addEventListener('click', () => selectFolder(folder.id));
    
    // Context menu for folder
    div.addEventListener('contextmenu', (e) => showFolderContextMenu(e, folder));
    
    // Drag and drop
    div.draggable = true;
    div.addEventListener('dragstart', (e) => onFolderDragStart(e, folder));
    div.addEventListener('dragover', (e) => onFolderDragOver(e, folder));
    div.addEventListener('dragleave', onFolderDragLeave);
    div.addEventListener('drop', (e) => onFolderDrop(e, folder));
    div.addEventListener('dragend', onFolderDragEnd);
    
    return div;
}

function selectFolder(folderId) {
    state.currentFolderId = folderId;
    
    // Re-render folders to update icons (selected = folder-open, others = folder)
    renderFolders();
    
    // Update folder label
    const folder = state.folders.find(f => f.id === folderId);
    elements.currentFolderLabel.textContent = folder ? folder.name : 'Notes';
    
    // Load memos
    loadMemos(folderId);
}

function showFolderModal() {
    elements.folderModal.classList.remove('hidden');
    elements.folderModal.classList.add('flex');
    elements.folderNameInput.focus();
}

function hideFolderModal() {
    elements.folderModal.classList.add('hidden');
    elements.folderModal.classList.remove('flex');
    elements.folderNameInput.value = '';
}

async function createFolder() {
    const name = elements.folderNameInput.value.trim();
    if (!name) return;
    
    // If current folder is root, create top-level folder (parent_id = null)
    // Otherwise create subfolder under current folder
    const parentId = state.currentFolderId === 'root' ? null : state.currentFolderId;
    
    const response = await callApi('create_folder', parentId, name);
    if (response.success) {
        hideFolderModal();
        await loadFolders();
        selectFolder(response.data.id);
    } else {
        showError(response.error || '폴더 생성에 실패했습니다.');
    }
}

async function deleteSelectedFolder() {
    if (state.currentFolderId === 'root') {
        showError('루트 폴더는 삭제할 수 없습니다.');
        return;
    }
    
    const folder = state.folders.find(f => f.id === state.currentFolderId);
    if (!folder) return;
    
    if (!confirm(`'${folder.name}' 폴더를 삭제하시겠습니까?`)) return;
    
    const response = await callApi('delete_folder', state.currentFolderId);
    if (response.success) {
        await loadFolders();
        selectFolder('root');
    } else {
        showError(response.error || '폴더 삭제에 실패했습니다.');
    }
}

// ============================================================================
// Memo Operations
// ============================================================================

async function loadMemos(folderId) {
    const response = await callApi('get_memos', folderId);
    if (response.success) {
        state.memos = response.data;
        sortMemos(); // Apply current sort settings
        renderMemos();
    } else {
        showError('메모를 불러오는데 실패했습니다.');
    }
}

function renderMemos() {
    console.log('Rendering memos...');
    console.log('Current memos state:', state.memos);
    
    elements.memoList.innerHTML = '';
    
    if (state.memos.length === 0) {
        console.log('No memos to display');
        elements.memoList.innerHTML = `
            <div class="flex flex-col items-center justify-center h-32 text-slate-400">
                <i data-lucide="file-x" class="w-8 h-8 mb-2"></i>
                <span class="text-xs">메모가 없습니다</span>
            </div>
        `;
        lucide.createIcons();
        return;
    }
    
    console.log(`Rendering ${state.memos.length} memos`);
    state.memos.forEach((memo, index) => {
        console.log(`Rendering memo ${index}:`, memo);
        const memoEl = createMemoElement(memo);
        elements.memoList.appendChild(memoEl);
    });
    
    console.log('Memo list HTML after render:', elements.memoList.innerHTML);
    
    lucide.createIcons();
}

function sortMemos() {
    const field = state.sortField;
    const direction = state.sortDirection;
    
    state.memos.sort((a, b) => {
        let aVal, bVal;
        
        if (field === 'title') {
            aVal = (a.title || '').toLowerCase();
            bVal = (b.title || '').toLowerCase();
        } else if (field === 'created_at') {
            aVal = new Date(a.created_at || 0).getTime();
            bVal = new Date(b.created_at || 0).getTime();
        } else if (field === 'last_modified') {
            aVal = new Date(a.last_modified || 0).getTime();
            bVal = new Date(b.last_modified || 0).getTime();
        } else {
            return 0;
        }
        
        if (aVal < bVal) return direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return direction === 'asc' ? 1 : -1;
        return 0;
    });
}

function createMemoElement(memo) {
    const div = document.createElement('div');
    const isActive = memo.id === state.currentMemoId;
    
    div.className = `list-item flex flex-col px-4 py-3 border-b border-slate-50 cursor-pointer ${
        isActive ? 'active' : ''
    }`;
    div.dataset.memoId = memo.id;
    div.draggable = true;
    
    // Format dates
    const createdDate = new Date(memo.created_at).toLocaleDateString('ko-KR', {
        month: 'short',
        day: 'numeric'
    });
    const modifiedDate = new Date(memo.last_modified).toLocaleDateString('ko-KR', {
        month: 'short',
        day: 'numeric'
    });
    const createdTime = new Date(memo.created_at).toLocaleTimeString('ko-KR', {
        hour: '2-digit',
        minute: '2-digit'
    });
    const modifiedTime = new Date(memo.last_modified).toLocaleTimeString('ko-KR', {
        hour: '2-digit',
        minute: '2-digit'
    });
    
    // Show folder name if in root folder (hub view)
    const folderPrefix = state.currentFolderId === 'root' && memo.folder_name ? 
        `<span class="text-xs text-slate-400 mr-1">📁 ${escapeHtml(memo.folder_name)}</span>` : '';
    
    // Get icon based on memo type
    const typeIcons = {
        'rich_text': 'file-text',
        'markdown': 'code',
        'image': 'image'
    };
    const iconName = typeIcons[memo.memo_type] || 'file-text';
    
    div.innerHTML = `
        <div class="flex items-center gap-2">
            <i data-lucide="${iconName}" class="w-4 h-4 ${isActive ? 'text-blue-500' : 'text-slate-400'} flex-shrink-0"></i>
            <div class="flex-1 min-w-0">
                <div class="text-sm font-medium truncate ${isActive ? 'text-blue-600' : 'text-slate-700'}">${folderPrefix}${escapeHtml(memo.title)}</div>
            </div>
        </div>
        <div class="flex items-center gap-3 mt-1 ml-6 text-xs">
            <span class="text-slate-400" title="생성: ${createdDate} ${createdTime}">생성 ${createdDate}</span>
            <span class="text-slate-300">|</span>
            <span class="text-slate-500" title="수정: ${modifiedDate} ${modifiedTime}">수정 ${modifiedDate}</span>
        </div>
    `;
    
    div.addEventListener('click', () => selectMemo(memo.id));
    
    // Drag and drop for memos
    div.addEventListener('dragstart', (e) => onMemoDragStart(e, memo));
    div.addEventListener('dragover', (e) => onMemoDragOver(e, memo));
    div.addEventListener('dragleave', onMemoDragLeave);
    div.addEventListener('drop', (e) => onMemoDrop(e, memo));
    div.addEventListener('dragend', onMemoDragEnd);
    
    return div;
}

async function selectMemo(memoId) {
    console.log('Selecting memo:', memoId);
    // Find memo data
    const memo = state.memos.find(m => m.id === memoId);
    if (!memo) {
        console.error('Memo not found:', memoId);
        return;
    }
    
    console.log('Memo found:', memo);
    
    // Update current memo ID and re-render to update highlight
    state.currentMemoId = memoId;
    renderMemos(); // Re-render to update active highlight
    
    // Update breadcrumb with memo location
    updateMemoLocation(memo);
    
    // Create or switch to tab
    createTab(memo);
}

function updateMemoLocation(memo) {
    // Show the breadcrumb container
    if (elements.memoLocation) {
        elements.memoLocation.classList.remove('hidden');
        
        // Update folder name
        const folder = state.folders.find(f => f.id === memo.folder_id);
        if (elements.locationFolder) {
            elements.locationFolder.textContent = folder ? folder.name : (memo.folder_name || '모든 메모');
        }
        
        // Update memo title
        if (elements.locationMemo) {
            elements.locationMemo.textContent = memo.title;
        }
        
        // Re-initialize icons for chevrons
        lucide.createIcons();
    }
}

async function createMemo() {
    // Directly create markdown memo without type selection
    const response = await callApi('create_memo', state.currentFolderId, '새 메모', 'markdown');
    if (response.success) {
        await loadMemos(state.currentFolderId);
        // Set the new memo as current and select it
        state.currentMemoId = response.data.id;
        renderMemos(); // Re-render to show correct highlight
        selectMemo(response.data.id);
        updateEditorState();
    } else {
        showError('메모 생성에 실패했습니다.');
    }
}

function showMemoTypeModal() {
    elements.memoTypeModal.classList.remove('hidden');
    elements.memoTypeModal.classList.add('flex');
    // Reset to default selection
    const defaultRadio = elements.memoTypeModal.querySelector('input[value="rich_text"]');
    if (defaultRadio) defaultRadio.checked = true;
}

function hideMemoTypeModal() {
    elements.memoTypeModal.classList.add('hidden');
    elements.memoTypeModal.classList.remove('flex');
}

async function createMemoWithType() {
    const selectedType = elements.memoTypeModal.querySelector('input[name="memo-type"]:checked')?.value || 'rich_text';
    hideMemoTypeModal();
    
    const typeLabels = {
        'rich_text': '새 메모',
        'markdown': '새 Markdown',
        'image': '새 이미지'
    };
    
    const response = await callApi('create_memo', state.currentFolderId, typeLabels[selectedType], selectedType);
    if (response.success) {
        await loadMemos(state.currentFolderId);
        selectMemo(response.data.id);
        // Ensure editor is shown after creating new memo
        updateEditorState();
    } else {
        showError('메모 생성에 실패했습니다.');
    }
}

async function deleteSelectedMemo() {
    if (!state.currentMemoId) {
        showError('삭제할 메모를 선택해주세요.');
        return;
    }
    
    const memo = state.memos.find(m => m.id === state.currentMemoId);
    if (!memo) return;
    
    if (!confirm(`'${memo.title}' 메모를 삭제하시겠습니까?`)) return;
    
    const response = await callApi('delete_memo', state.currentMemoId);
    if (response.success) {
        const closingTabId = state.activeTabId || `tab-${state.currentMemoId}`;
        if (closingTabId) {
            closeTab(closingTabId);
        }
        await loadMemos(state.currentFolderId);
    } else {
        showError('메모 삭제에 실패했습니다.');
    }
}

// ============================================================================
// Editor & Auto-save
// ============================================================================

function scheduleAutoSave(tabId) {
    const tab = state.tabs.find(t => t.id === tabId);
    if (!tab) return;
    
    if (tab.autoSaveTimer) {
        clearTimeout(tab.autoSaveTimer);
    }
    
    tab.autoSaveTimer = setTimeout(() => {
        saveTabContent(tabId);
    }, 2000);
}

// ============================================================================
// Keyboard Shortcuts
// ============================================================================

document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + S: Save current tab
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (state.activeTabId) {
            saveTabContent(state.activeTabId);
        }
    }
    
    // Ctrl/Cmd + N: New memo
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        createMemo();
    }
    
    // Ctrl/Cmd + W: Close current tab
    if ((e.ctrlKey || e.metaKey) && e.key === 'w') {
        e.preventDefault();
        if (state.activeTabId) {
            closeTab(state.activeTabId);
        }
    }
    
    // Ctrl/Cmd + Tab: Switch to next tab
    if ((e.ctrlKey || e.metaKey) && e.key === 'Tab') {
        e.preventDefault();
        switchToNextTab();
    }
});

function switchToNextTab() {
    if (state.tabs.length === 0) return;
    
    const currentIndex = state.tabs.findIndex(tab => tab.id === state.activeTabId);
    const nextIndex = (currentIndex + 1) % state.tabs.length;
    switchToTab(state.tabs[nextIndex].id);
}

// ============================================================================
// Drag & Drop
// ============================================================================

function onFolderDragStart(e, folder) {
    console.log('Drag start:', folder.id, folder.name);
    e.dataTransfer.setData('folderId', folder.id);
    e.dataTransfer.effectAllowed = 'move';
    e.target.classList.add('dragging');
}

function onFolderDragOver(e, folder) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    const draggedId = e.dataTransfer.getData('folderId');
    if (draggedId && draggedId !== folder.id) {
        e.currentTarget.classList.add('drag-over');
    }
}

function onFolderDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

async function onFolderDrop(e, targetFolder) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove('drag-over');
    
    const draggedId = e.dataTransfer.getData('folderId');
    console.log('Drop:', draggedId, 'onto', targetFolder.id, targetFolder.name);
    
    if (!draggedId) {
        console.error('No draggedId found');
        return;
    }
    
    if (draggedId === targetFolder.id) {
        console.log('Same folder, ignoring');
        return;
    }
    
    // Prevent circular reference
    const isDescendant = checkIsDescendant(draggedId, targetFolder.id);
    console.log('Is descendant check:', draggedId, 'under', targetFolder.id, ':', isDescendant);
    if (isDescendant) {
        showError('하위 폴더로 이동할 수 없습니다.');
        return;
    }
    
    // If dropped on 'root' folder, set parent_id to null (top-level)
    // Otherwise use the target folder's ID as parent
    const newParentId = targetFolder.id === 'root' ? null : targetFolder.id;
    console.log('Moving folder', draggedId, 'to parent', newParentId);
    
    const response = await callApi('move_folder', draggedId, newParentId, 0);
    console.log('Move folder response:', response);
    
    if (response.success) {
        await loadFolders();
    } else {
        showError('폴더 이동에 실패했습니다: ' + (response.error || 'Unknown error'));
    }
}

function onFolderDragEnd(e) {
    e.target.classList.remove('dragging');
    document.querySelectorAll('.drag-over').forEach(el => {
        el.classList.remove('drag-over');
    });
}

// ============================================================================
// Memo Drag & Drop
// ============================================================================

function onMemoDragStart(e, memo) {
    console.log('Memo drag start:', memo.id, memo.title);
    e.dataTransfer.setData('memoId', memo.id);
    e.dataTransfer.effectAllowed = 'move';
    e.target.classList.add('dragging');
}

function onMemoDragOver(e, memo) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    const draggedId = e.dataTransfer.getData('memoId');
    if (draggedId && draggedId !== memo.id) {
        e.currentTarget.classList.add('drag-over');
    }
}

function onMemoDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

async function onMemoDrop(e, targetMemo) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove('drag-over');
    
    const draggedId = e.dataTransfer.getData('memoId');
    console.log('Memo drop:', draggedId, 'onto', targetMemo.id);
    
    if (!draggedId || draggedId === targetMemo.id) {
        return;
    }
    
    // Reorder memos
    const draggedIndex = state.memos.findIndex(m => m.id === draggedId);
    const targetIndex = state.memos.findIndex(m => m.id === targetMemo.id);
    
    if (draggedIndex === -1 || targetIndex === -1) {
        return;
    }
    
    // Move memo in array
    const [draggedMemo] = state.memos.splice(draggedIndex, 1);
    state.memos.splice(targetIndex, 0, draggedMemo);
    
    // Update sort order via API
    const newSortOrder = targetIndex;
    const response = await callApi('move_memo', draggedId, targetMemo.folder_id, newSortOrder);
    
    if (response.success) {
        renderMemos();
    } else {
        showError('메모 이동에 실패했습니다.');
        // Revert on failure
        await loadMemos(state.currentFolderId);
    }
}

function onMemoDragEnd(e) {
    e.target.classList.remove('dragging');
    document.querySelectorAll('.drag-over').forEach(el => {
        el.classList.remove('drag-over');
    });
}

function checkIsDescendant(parentId, childId) {
    const children = state.folders.filter(f => f.parent_id === parentId);
    if (children.length === 0) return false;
    
    for (const child of children) {
        if (child.id === childId) return true;
        if (checkIsDescendant(child.id, childId)) return true;
    }
    return false;
}

function updateWordCount() {
    if (!state.editor) {
        elements.wordCount.textContent = '0 단어';
        return;
    }
    
    // Get Markdown text from Vditor
    const markdown = state.editor.getValue() || '';
    // Remove Markdown syntax for word count
    const plainText = markdown
        .replace(/[#*_`\[\](){}]/g, '')  // Remove common Markdown syntax
        .replace(/!\[.*?\]\(.*?\)/g, '[이미지]')  // Replace images
        .replace(/\[.*?\]\(.*?\)/g, '[링크]')  // Replace links
        .trim();
    const count = plainText ? plainText.split(/\s+/).filter(w => w.length > 0).length : 0;
    elements.wordCount.textContent = `${count} 단어`;
}

// ============================================================================
// Utilities
// ============================================================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    alert(message); // Simple alert for now, can be replaced with toast notification
}

// ============================================================================
// Sync
// ============================================================================

async function syncToDrive() {
    updateSyncStatus('동기화 중...');
    elements.btnSync.classList.add('animate-spin');
    
    const response = await callApi('sync_to_drive');
    
    elements.btnSync.classList.remove('animate-spin');
    
    if (response.success) {
        updateSyncStatus('동기화됨');
        alert('동기화가 완료되었습니다.');
    } else {
        updateSyncStatus('동기화 실패');
        showError(response.error || '동기화에 실패했습니다.');
    }
}

// ============================================================================
// Settings
// ============================================================================

async function showSettingsModal() {
    elements.settingsModal.classList.remove('hidden');
    elements.settingsModal.classList.add('flex');
    
    // Load current storage path
    const response = await callApi('get_storage_path');
    if (response.success) {
        elements.currentStoragePath.textContent = response.data.path;
    } else {
        elements.currentStoragePath.textContent = '경로를 불러올 수 없습니다';
    }
    
    // Hide migration progress
    elements.migrationProgress.classList.add('hidden');
    
    lucide.createIcons();
}

function hideSettingsModal() {
    elements.settingsModal.classList.add('hidden');
    elements.settingsModal.classList.remove('flex');
}

async function changeStorageFolder() {
    // Open folder picker dialog via backend
    const response = await callApi('select_folder_dialog');
    if (!response.success || !response.data.path) {
        return; // User cancelled or error
    }
    
    const newPath = response.data.path;
    const currentPath = elements.currentStoragePath.textContent;
    
    if (newPath === currentPath) {
        alert('동일한 폴더가 선택되었습니다.');
        return;
    }
    
    // Check if target has existing data and ask about overwrite
    const checkResponse = await callApi('migrate_storage', newPath, false);
    if (!checkResponse.success && checkResponse.error.includes('already contains')) {
        const overwrite = confirm(
            `대상 폴더에 이미 메모 데이터가 있습니다.\n\n${checkResponse.error}\n\n기존 데이터를 덮어쓰시겠습니까?\n(백업 후 진행을 권장합니다.)`
        );
        
        if (!overwrite) {
            return;
        }
        
        // Proceed with overwrite
        const migrateResponse = await callApi('migrate_storage', newPath, true);
        handleMigrationResult(migrateResponse, newPath);
        return;
    }
    
    // No existing data, proceed normally
    const migrateResponse = await callApi('migrate_storage', newPath, false);
    handleMigrationResult(migrateResponse, newPath);
}

function handleMigrationResult(response, newPath) {
    // Hide progress UI
    elements.migrationProgress.classList.add('hidden');
    elements.btnChangeStorage.disabled = false;
    
    if (response.success) {
        elements.currentStoragePath.textContent = newPath;
        alert('저장 폴더가 성공적으로 변경되었습니다.\n앱을 다시 시작해야 변경사항이 완전히 적용됩니다.');
        hideSettingsModal();
    } else {
        showError('저장 폴더 변경에 실패했습니다: ' + (response.error || 'Unknown error'));
    }
}

function updateSyncStatus(status) {
    if (elements.syncStatus) {
        elements.syncStatus.textContent = status;
    }
}

// ============================================================================
// Default Folder & Context Menu
// ============================================================================

async function loadDefaultFolder() {
    const response = await callApi('get_default_folder');
    if (response.success && response.data.folder_id) {
        state.defaultFolderId = response.data.folder_id;
        // Select default folder if it exists in the folder list
        const folderExists = state.folders.some(f => f.id === state.defaultFolderId);
        if (folderExists) {
            selectFolder(state.defaultFolderId);
        }
    }
}

async function setDefaultFolder(folderId) {
    const response = await callApi('set_default_folder', folderId);
    if (response.success) {
        state.defaultFolderId = folderId;
        await loadFolders();
    } else {
        showError('기본 폴더 설정에 실패했습니다.');
    }
}

function showFolderContextMenu(e, folder) {
    e.preventDefault();
    
    // Remove existing context menu
    const existingMenu = document.querySelector('.folder-context-menu');
    if (existingMenu) {
        existingMenu.remove();
    }
    
    // Create context menu
    const menu = document.createElement('div');
    menu.className = 'folder-context-menu absolute bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-50 min-w-[150px]';
    menu.style.left = `${e.pageX}px`;
    menu.style.top = `${e.pageY}px`;
    
    // Set as default option
    const isDefault = folder.id === state.defaultFolderId;
    const defaultOption = document.createElement('div');
    defaultOption.className = 'px-4 py-2 hover:bg-slate-100 cursor-pointer text-sm flex items-center gap-2';
    defaultOption.innerHTML = `<i data-lucide="${isDefault ? 'star-off' : 'star'}" class="w-4 h-4"></i> ${isDefault ? '기본 폴더 해제' : '기본 폴더로 설정'}`;
    defaultOption.addEventListener('click', async () => {
        if (isDefault) {
            await setDefaultFolder(null);
        } else {
            await setDefaultFolder(folder.id);
        }
        menu.remove();
    });
    
    menu.appendChild(defaultOption);
    
    document.body.appendChild(menu);
    lucide.createIcons();
    
    // Close menu when clicking outside
    const closeMenu = (e) => {
        if (!menu.contains(e.target)) {
            menu.remove();
            document.removeEventListener('click', closeMenu);
        }
    };
    setTimeout(() => {
        document.addEventListener('click', closeMenu);
    }, 0);
}

// ============================================================================
// Default Folder & Context Menu
// ============================================================================

async function setDefaultFolder(folderId) {
    const response = await callApi('set_default_folder', folderId);
    if (response.success) {
        state.defaultFolderId = folderId;
        await loadFolders();
    } else {
        showError('기본 폴더 설정에 실패했습니다.');
    }
}

function showFolderContextMenu(e, folder) {
    e.preventDefault();
    
    // Remove existing context menu
    const existingMenu = document.querySelector('.folder-context-menu');
    if (existingMenu) {
        existingMenu.remove();
    }
    
    // Create context menu
    const menu = document.createElement('div');
    menu.className = 'folder-context-menu absolute bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-50 min-w-[150px]';
    menu.style.left = `${e.pageX}px`;
    menu.style.top = `${e.pageY}px`;
    
    // Set as default option
    const isDefault = folder.id === state.defaultFolderId;
    const defaultOption = document.createElement('div');
    defaultOption.className = 'px-4 py-2 hover:bg-slate-100 cursor-pointer text-sm flex items-center gap-2';
    defaultOption.innerHTML = `<i data-lucide="${isDefault ? 'star-off' : 'star'}" class="w-4 h-4"></i> ${isDefault ? '기본 폴더 해제' : '기본 폴더로 설정'}`;
    defaultOption.addEventListener('click', async () => {
        if (isDefault) {
            await setDefaultFolder(null);
        } else {
            await setDefaultFolder(folder.id);
        }
        menu.remove();
    });
    
    menu.appendChild(defaultOption);
    
    document.body.appendChild(menu);
    lucide.createIcons();
    
    // Close menu when clicking outside
    const closeMenu = (e) => {
        if (!menu.contains(e.target)) {
            menu.remove();
            document.removeEventListener('click', closeMenu);
        }
    };
    setTimeout(() => {
        document.addEventListener('click', closeMenu);
    }, 0);
}

async function loadDefaultFolder() {
    const response = await callApi('get_default_folder');
    if (response.success && response.data.folder_id) {
        state.defaultFolderId = response.data.folder_id;
        // Select default folder if it exists in the folder list
        const folderExists = state.folders.some(f => f.id === state.defaultFolderId);
        if (folderExists) {
            selectFolder(state.defaultFolderId);
        }
    }
}
