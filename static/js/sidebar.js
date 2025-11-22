// Handles sidebar collapse, chat list loading, search, and delete
document.addEventListener('DOMContentLoaded', () => {
    
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return; // Don't run this script if sidebar isn't on the page

    const chatList = document.getElementById('chat-list');
    const newChatBtn = document.getElementById('new-chat-btn');
    const chatSearch = document.getElementById('chat-search');
    const mobileToggle = document.getElementById('sidebar-toggle-mobile');
    let chatSessions = {}; // Cache for sessions

    // --- NEW: Delete Modal Elements ---
    const deleteModal = document.getElementById('confirm-delete-modal');
    const deleteModalText = document.getElementById('delete-modal-text');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
    // --- END NEW ---

    // --- Mobile Sidebar Toggle ---
    let mobileOverlay = null;
    if (mobileToggle) {
        mobileToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.add('open');
            if (!mobileOverlay) {
                mobileOverlay = document.createElement('div');
                mobileOverlay.className = 'mobile-overlay';
                mobileOverlay.addEventListener('click', closeMobileSidebar);
                if (sidebar.nextSibling) {
                    sidebar.parentNode.insertBefore(mobileOverlay, sidebar.nextSibling);
                } else {
                    sidebar.parentNode.appendChild(mobileOverlay);
                }
            }
            mobileOverlay.classList.add('open');
        });
    }

    function closeMobileSidebar() {
        sidebar.classList.remove('open');
        if (mobileOverlay) {
            mobileOverlay.classList.remove('open');
        }
    }

    // --- Load Chat Sessions ---
    async function loadChatSessions() {
        try {
            const response = await fetch(`${API_URL}/api/sessions`);
            if (!response.ok) {
                showToast("Failed to load chat sessions.", "error");
                return;
            }
            chatSessions = await response.json();
            renderChatList(chatSessions);
        } catch (error) {
            console.error("Error loading sessions:", error);
            showToast("Error loading chat sessions.", "error");
        }
    }

    // --- Render Chat List ---
    function renderChatList(sessions, filter = '') {
        if (!chatList) return;
        chatList.innerHTML = '';
        const sessionEntries = Object.entries(sessions);

        if (sessionEntries.length === 0) {
            chatList.innerHTML = `<p style="padding: 0 16px; color: var(--text-tertiary); font-size: 0.875rem;">No chat sessions found.</p>`;
            return;
        }
        
        const filteredEntries = sessionEntries.filter(([id, data]) => 
            data.title.toLowerCase().includes(filter.toLowerCase())
        );

        const section = document.createElement('div');
        section.className = 'chat-list-section';

        filteredEntries.forEach(([id, data]) => {
            const item = document.createElement('div');
            item.className = 'chat-item';
            item.dataset.chatId = id;
            if (id === window.STATE.currentSessionId) {
                item.classList.add('active');
            }
            
            const lastUpdated = new Date(data.last_updated).toLocaleString('en-US', {
                month: 'short', 
                day: 'numeric',
                hour: '2-digit', 
                minute: '2-digit'
            });

            item.innerHTML = `
                <svg class="chat-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <div class="chat-item-content">
                    <span class="chat-title">${data.title}</span>
                    <span class="chat-preview">${lastUpdated}</span>
                </div>
                <button class="chat-menu-btn icon-btn" data-chat-id="${id}" title="More options">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/>
                    </svg>
                </button>
            `;
            
            // Click on item to load chat
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.chat-menu-btn')) {
                    if (window.handleLoadChat) window.handleLoadChat(id);
                    closeMobileSidebar();
                }
            });

            // Click on menu button
            item.querySelector('.chat-menu-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                // --- MODIFIED: Pass title to context menu ---
                showChatContextMenu(e.currentTarget, id, data.title);
            });

            section.appendChild(item);
        });
        
        chatList.appendChild(section);
    }

    // --- Chat Search ---
    if (chatSearch) {
        chatSearch.addEventListener('input', (e) => {
            renderChatList(chatSessions, e.target.value);
        });
    }

    // --- New Chat Button ---
    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => {
            if (window.handleNewChat) window.handleNewChat();
            closeMobileSidebar();
        });
    }

    // --- Context Menu ---
    function showChatContextMenu(button, sessionId, sessionTitle) { // <-- MODIFIED
        document.querySelectorAll('.chat-item-menu').forEach(menu => menu.remove());

        const menu = document.createElement('div');
        menu.className = 'chat-item-menu';
        menu.innerHTML = `
            <button class="chat-menu-delete-btn" data-session-id="${sessionId}" data-session-title="${sessionTitle}">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    <line x1="10" y1="11" x2="10" y2="17"></line>
                    <line x1="14" y1="11" x2="14" y2="17"></line>
                </svg>
                <span>Delete</span>
            </button>
        `;

        const rect = button.getBoundingClientRect();
        document.body.appendChild(menu);
        
        const menuWidth = menu.offsetWidth;
        const menuHeight = menu.offsetHeight;
        
        let top = rect.bottom;
        let left = rect.left - menuWidth + rect.width;

        if (left < 0) left = rect.left;
        if (top + menuHeight > window.innerHeight) top = rect.top - menuHeight;

        menu.style.top = `${top}px`;
        menu.style.left = `${left}px`;

        // --- MODIFIED: Show delete modal instead of confirm() ---
        menu.querySelector('.chat-menu-delete-btn').addEventListener('click', (e) => {
            const btn = e.currentTarget;
            const title = btn.dataset.sessionTitle;
            const id = btn.dataset.sessionId;

            deleteModalText.innerHTML = `Are you sure you want to delete <strong>"${title}"</strong>? This action cannot be undone.`;
            // Store the ID on the confirm button to be read later
            confirmDeleteBtn.dataset.sessionId = id; 
            deleteModal.classList.remove('hidden');
            menu.remove();
        });
    }

    // --- MODIFIED: Delete Chat Logic ---
    async function performDeleteChat(sessionId) {
        try {
            setLoading(true);
            const response = await fetch(`${API_URL}/api/sessions/${sessionId}`, {
                method: 'DELETE'
            });
            if (!response.ok) {
                throw new Error("Failed to delete session.");
            }
            showToast("Chat deleted.", "success");
            
            if (window.STATE.currentSessionId === sessionId) {
                if (window.handleNewChat) window.handleNewChat();
            }
            
            await loadChatSessions(); // Refresh list

        } catch (error) {
            console.error("Error deleting chat:", error);
            showToast(error.message, "error");
        } finally {
            setLoading(false);
            deleteModal.classList.add('hidden');
        }
    }
    
    // --- NEW: Listeners for Delete Modal ---
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', () => {
            const sessionId = confirmDeleteBtn.dataset.sessionId;
            if (sessionId) {
                performDeleteChat(sessionId);
            }
        });
    }

    if (cancelDeleteBtn) {
        cancelDeleteBtn.addEventListener('click', () => {
            deleteModal.classList.add('hidden');
        });
    }
    // --- END NEW ---

    // --- Public API for other scripts ---
    window.loadChatSessions = loadChatSessions;
    window.updateSidebarActiveState = () => {
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.toggle('active', item.dataset.chatId === window.STATE.currentSessionId);
        });
    };

    // --- Settings Button ---
    const settingsBtn = document.getElementById('settings-btn');
    if (settingsBtn) {
        settingsBtn.addEventListener('click', () => {
            const rightPanel = document.getElementById('right-panel');
            if (rightPanel) {
                rightPanel.classList.remove('hidden');
            } else {
                showToast("Error: Settings panel element not found.", "error");
            }
        });
    }

    // Initial load
    loadChatSessions();
});