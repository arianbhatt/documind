// Handles the document upload modal, file validation, and processing API call
document.addEventListener('DOMContentLoaded', () => {

    const uploadModal = document.getElementById('upload-modal');
    if (!uploadModal) return; // Don't run if not on chat page

    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const fileListContainer = document.getElementById('modal-file-list-container'); // Corrected ID
    const confirmUploadBtn = document.getElementById('confirm-upload-btn');
    const uploadProgress = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    let filesToUpload = [];

    // --- Event Listeners for Upload Area ---
    uploadArea.addEventListener('click', () => fileInput.click());
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        handleFiles(e.dataTransfer.files);
    });
    
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    // --- File Handling ---
    function handleFiles(files) {
        for (const file of files) {
            if (file.type === 'application/pdf') {
                if (!filesToUpload.find(f => f.name === file.name && f.size === file.size)) {
                    filesToUpload.push(file);
                }
            } else {
                showToast(`File "${file.name}" is not a PDF and was skipped.`, "error");
            }
        }
        renderFileList();
        fileInput.value = null; // Reset file input
    }

    function renderFileList() {
        fileListContainer.innerHTML = '';
        if (filesToUpload.length === 0) {
            confirmUploadBtn.disabled = true;
            return;
        }

        filesToUpload.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.innerHTML = `
                <div class="file-icon">PDF</div>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${formatFileSize(file.size)}</div>
                </div>
                <button class="file-remove-btn" data-index="${index}" title="Remove file">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            `;
            fileListContainer.appendChild(fileItem);
        });

        document.querySelectorAll('.file-remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index, 10);
                filesToUpload.splice(index, 1);
                renderFileList();
            });
        });

        confirmUploadBtn.disabled = false;
    }

    // --- Confirm Upload ---
    confirmUploadBtn.addEventListener('click', async () => {
        if (filesToUpload.length === 0) {
            showToast("No files selected for upload.", "error");
            return;
        }

        // Show progress
        uploadProgress.classList.remove('hidden');
        progressText.textContent = 'Processing documents... (this may take a moment)';
        progressFill.style.width = '50%'; // Indeterminate progress
        setLoading(true);
        
        const formData = new FormData();
        filesToUpload.forEach(file => {
            formData.append('files', file);
        });
        
        const model = document.getElementById('model-selector').value;
        formData.append('model', model);
        
        if (window.STATE.customApiKey) {
            formData.append('custom_api_key', window.STATE.customApiKey);
        }
        
        if (window.STATE.currentSessionId) {
            formData.append('session_id', window.STATE.currentSessionId);
        }

        try {
            const response = await fetch(`${API_URL}/api/process`, {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || "Processing failed");
            }
            
            // --- Success ---
            progressFill.style.width = '100%';
            progressText.textContent = result.message;
            showToast(result.message, "success");

            window.STATE.currentSessionId = result.session_id;
            window.STATE.currentUploadedFiles = result.uploaded_files;

            const chatTitleEl = document.getElementById('current-chat-title');
            if (chatTitleEl) chatTitleEl.textContent = result.title;
            
            const docCountEl = document.getElementById('document-count');
            if (docCountEl) docCountEl.textContent = `${result.uploaded_files.length} document(s)`;
            
            // --- MODIFIED: Show rename button ---
            const renameBtn = document.getElementById('rename-chat-btn');
            if (renameBtn) renameBtn.style.display = 'inline-flex';
            // --- END MODIFICATION ---
            
            const messagesContainerEl = document.getElementById('messages-container');
            if (messagesContainerEl) messagesContainerEl.innerHTML = ''; // Clear chat
            
            const emptyStateEl = document.getElementById('empty-state');
            if (emptyStateEl) emptyStateEl.classList.add('hidden');
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message assistant`;
            messageDiv.innerHTML = `
                <div class="message-avatar">AI</div>
                <div class="message-content">
                    <div class="message-bubble">
                        <div class="message-text">
                            <p>Ready to chat about: ${result.uploaded_files.join(', ')}</p>
                        </div>
                    </div>
                </div>
            `;
            if (messagesContainerEl) messagesContainerEl.appendChild(messageDiv);

            if (window.loadChatSessions) {
                await window.loadChatSessions();
            }
            if (window.updateSidebarActiveState) {
                window.updateSidebarActiveState();
            }

            setTimeout(() => {
                uploadModal.classList.add('hidden');
                resetUploadModal();
            }, 1500);

        } catch (error) {
            console.error(error);
            progressText.textContent = `Error: ${error.message}`;
            showToast(`Error: ${error.message}`, "error");
        } finally {
            setLoading(false);
        }
    });

    // --- Reset Modal State ---
    function resetUploadModal() {
        filesToUpload = [];
        fileListContainer.innerHTML = '';
        fileInput.value = null;
        confirmUploadBtn.disabled = true;
        uploadProgress.classList.add('hidden');
        progressFill.style.width = '0%';
        progressText.textContent = 'Uploading...';
    }
    
    document.querySelectorAll('[data-close-modal]').forEach(btn => {
        btn.addEventListener('click', resetUploadModal);
    });

});