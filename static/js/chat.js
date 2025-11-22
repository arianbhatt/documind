// Handles sending messages, receiving responses, and rendering chat bubbles
document.addEventListener('DOMContentLoaded', () => {
    
    const messagesContainer = document.getElementById('messages-container');
    if (!messagesContainer) return; // Don't run if not on chat page

    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const emptyState = document.getElementById('empty-state');
    const chatTitle = document.getElementById('current-chat-title');
    const docCount = document.getElementById('document-count');
    const modelSelector = document.getElementById('model-selector');
    const modelInfoDisplay = document.getElementById('model-info-display');
    const downloadChatBtn = document.getElementById('download-chat-btn');
    const renameChatBtn = document.getElementById('rename-chat-btn');

    // --- NEW: Rename Modal Elements ---
    const renameModal = document.getElementById('rename-modal');
    const renameInput = document.getElementById('rename-input');
    const confirmRenameBtn = document.getElementById('confirm-rename-btn');
    const cancelRenameBtn = document.getElementById('cancel-rename-btn');
    // --- END NEW ---

    // --- Send Message ---
    async function handleSendMessage() {
        const query = messageInput.value.trim();
        if (!query || window.STATE.isProcessing) return;

        if (!window.STATE.currentSessionId) {
            showToast("Please start a new chat and upload documents first.", "error");
            return;
        }

        // Disable input
        window.STATE.isProcessing = true;
        sendBtn.disabled = true;
        messageInput.disabled = true;
        
        appendMessage('user', query);
        messageInput.value = '';
        messageInput.style.height = 'auto'; // Reset height
        
        showTypingIndicator(true);

        try {
            const response = await fetch(`${API_URL}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: window.STATE.currentSessionId,
                    query: query,
                }),
            });

            const botMessage = await response.json();

            if (!response.ok) {
                throw new Error(botMessage.error || "Failed to get response");
            }
            
            appendMessage('assistant', botMessage.content);
            
            // Check if title changed (on first message)
            if (window.loadChatSessions) {
                await window.loadChatSessions(); // Refresh list
                const currentSession = document.querySelector(`.chat-item[data-chat-id="${window.STATE.currentSessionId}"] .chat-title`);
                if (currentSession) {
                    chatTitle.textContent = currentSession.textContent;
                }
            }

        } catch (error) {
            console.error(error);
            appendMessage('assistant', `Error: ${error.message}`);
        } finally {
            window.STATE.isProcessing = false;
            sendBtn.disabled = false;
            messageInput.disabled = false;
            showTypingIndicator(false);
            messageInput.focus();
        }
    }

    // --- Render Messages ---
    function appendMessage(role, content) {
        if (emptyState) emptyState.classList.add('hidden');
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        
        // === MODIFIED: Use SVG for User, Logo for AI ===
        if (role === 'user') {
            avatar.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`;
        } else {
            avatar.innerHTML = `<img src="/static/logo.png" alt="AI Avatar">`;
        }
        // === END OF MODIFICATION ===
        
        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'message-content';
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        const text = document.createElement('div');
        text.className = 'message-text';
        
        // === MODIFIED: Use Marked.js for Markdown and KaTeX for LaTeX ===
        text.innerHTML = marked.parse(content, {
            breaks: true, // Convert newlines to <br>
            gfm: true, // Use GitHub Flavored Markdown
        });
        
        bubble.appendChild(text);
        contentWrapper.appendChild(bubble);
        
        const meta = document.createElement('div');
        meta.className = 'message-meta';
        const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        meta.innerHTML = `<span class="message-time">${time}</span>`;
        contentWrapper.appendChild(meta);

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentWrapper);
        messagesContainer.appendChild(messageDiv);
        
        // --- ADDED: Run KaTeX renderer ---
        if (window.renderMathInElement) {
            window.renderMathInElement(text, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                    {left: '\\(', right: '\\)', display: false},
                    {left: '\\[', right: '\\]', display: true}
                ],
                throwOnError: false
            });
        }
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    // --- Typing Indicator ---
    function showTypingIndicator(show) {
        let indicator = document.getElementById('typing-indicator');
        if (show && !indicator) {
            indicator = document.createElement('div');
            indicator.id = 'typing-indicator';
            indicator.className = 'message assistant typing-indicator';
            indicator.innerHTML = `
                <div class="message-avatar">
                    <img src="/static/logo.png" alt="AI Avatar">
                </div>
                <div class="message-content">
            `;
            messagesContainer.appendChild(indicator);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } else if (!show && indicator) {
            indicator.remove();
        }
    }

    // --- Auto-resize Textarea ---
    function autoResizeTextarea() {
        if (!messageInput) return;
        messageInput.style.height = 'auto';
        messageInput.style.height = `${Math.min(messageInput.scrollHeight, 200)}px`;
    }

    // --- Input Handling ---
    if (messageInput) {
        messageInput.addEventListener('input', () => {
            autoResizeTextarea();
            if (sendBtn) sendBtn.disabled = messageInput.value.trim().length === 0;
        });

        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
            }
        });
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', handleSendMessage);
    }
    
    // --- Model Selector ---
    if (modelSelector) {
        modelSelector.addEventListener('change', () => {
            if (modelInfoDisplay) modelInfoDisplay.textContent = modelSelector.value;
            showToast(`Model set to ${modelSelector.value}. This will apply to the next new chat or document processing.`, 'info');
        });
    }

    // --- Download Chat ---
    if (downloadChatBtn) {
        downloadChatBtn.addEventListener('click', async () => {
            if (!window.STATE.currentSessionId) {
                showToast("No active chat to download.", "error");
                return;
            }
            try {
                setLoading(true);
                const response = await fetch(`${API_URL}/api/sessions/${window.STATE.currentSessionId}/download_csv`);
                if (!response.ok) throw new Error("Failed to download chat history.");
                
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `chat_history_${window.STATE.currentSessionId.substring(0,8)}.csv`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } catch (error) {
                showToast(error.message, "error");
            } finally {
                setLoading(false);
            }
        });
    }

    // --- MODIFIED: Rename Chat ---
    if (renameChatBtn) {
        renameChatBtn.addEventListener('click', () => {
            const sessionId = window.STATE.currentSessionId;
            if (!sessionId) {
                showToast("No active chat to rename.", "error");
                return;
            }
            // Populate input and show modal
            renameInput.value = chatTitle.textContent;
            renameModal.classList.remove('hidden');
            renameInput.focus();
        });
    }
    
    // --- NEW: Rename Modal Logic ---
    if (confirmRenameBtn) {
        confirmRenameBtn.addEventListener('click', async () => {
            const sessionId = window.STATE.currentSessionId;
            const newTitle = renameInput.value.trim();

            if (newTitle && newTitle !== chatTitle.textContent) {
                try {
                    setLoading(true);
                    const response = await fetch(`${API_URL}/api/sessions/${sessionId}/title`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ title: newTitle })
                    });

                    const result = await response.json();
                    if (!response.ok) {
                        throw new Error(result.error || "Failed to rename chat");
                    }

                    // Update UI
                    chatTitle.textContent = newTitle;
                    showToast("Chat renamed successfully!", "success");

                    // Refresh sidebar to show new name
                    if (window.loadChatSessions) {
                        await window.loadChatSessions();
                    }

                } catch (error) {
                    showToast(error.message, "error");
                } finally {
                    setLoading(false);
                    renameModal.classList.add('hidden');
                }
            } else {
                renameModal.classList.add('hidden');
            }
        });
    }

    if (cancelRenameBtn) {
        cancelRenameBtn.addEventListener('click', () => {
            renameModal.classList.add('hidden');
        });
    }
    // --- END NEW ---


    // --- Public API ---
    window.handleNewChat = () => {
        window.STATE.currentSessionId = null;
        window.STATE.currentUploadedFiles = [];
        messagesContainer.innerHTML = '';
        if (emptyState) emptyState.classList.remove('hidden');
        if (chatTitle) chatTitle.textContent = "New Chat";
        if (docCount) docCount.textContent = "No documents uploaded";
        if (renameChatBtn) renameChatBtn.style.display = 'none'; // <-- MODIFIED
        if (window.updateSidebarActiveState) window.updateSidebarActiveState();
    };

    window.handleLoadChat = async (sessionId) => {
        setLoading(true);
        try {
            const response = await fetch(`${API_URL}/api/sessions/${sessionId}`);
            if (!response.ok) throw new Error("Failed to load chat");
            const sessionData = await response.json();

            window.STATE.currentSessionId = sessionId;
            window.STATE.currentUploadedFiles = sessionData.uploaded_files || [];
            
            if (chatTitle) chatTitle.textContent = sessionData.title || "Chat";
            if (docCount) docCount.textContent = `${window.STATE.currentUploadedFiles.length} document(s)`;
            if (renameChatBtn) renameChatBtn.style.display = 'inline-flex'; // <-- MODIFIED
            messagesContainer.innerHTML = ''; // Clear chat

            sessionData.chat_history.forEach(msg => {
                appendMessage(msg.role, msg.content);
            });
            
            if (sessionData.chat_history.length === 0) {
                 if (emptyState) emptyState.classList.remove('hidden');
            } else {
                 if (emptyState) emptyState.classList.add('hidden');
            }

            // --- MODIFIED: Changed message, removed re-upload prompt ---
            if (sessionData.chat_history.length > 0) {
                 appendMessage('assistant', `Loaded chat: <strong>${sessionData.title}</strong>. Ready to chat!`);
                 showToast("Chat session loaded.", "success");
            } else {
                 appendMessage('assistant', `Loaded chat: <strong>${sessionData.title}</strong>. Ready to chat!`);
            }
            // --- END OF MODIFICATION ---

            if (window.updateSidebarActiveState) window.updateSidebarActiveState();
        } catch (error) { 
            console.error(error);
            showToast(`Error loading chat: ${error.message}`, "error");
        } finally { 
            setLoading(false);
        }
    };

    // --- Init ---
    if (messagesContainer) {
        window.handleNewChat();
    }
});