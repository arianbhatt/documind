// This script will be loaded on all pages (via base.html)
// It handles global state and components like theme and modals.

// Global state
window.STATE = {
    currentSessionId: null,
    isProcessing: false,
    uploadedFiles: [],
};

// API base URL (relative)
const API_URL = ""; 

document.addEventListener('DOMContentLoaded', () => {
    
    // --- Theme Toggle ---
    const themeToggleBtn = document.getElementById('theme-toggle');
    const body = document.body;

    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'theme-dark';
    body.className = savedTheme;

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            if (body.classList.contains('theme-dark')) {
                body.className = 'theme-light';
                localStorage.setItem('theme', 'theme-light');
            } else {
                body.className = 'theme-dark';
                localStorage.setItem('theme', 'theme-dark');
            }
        });
    }

    // --- Modal Handling ---
    const uploadModal = document.getElementById('upload-modal');
    const openModalBtns = [
        document.getElementById('upload-btn'),
        document.getElementById('attach-btn'),
        document.getElementById('upload-docs-btn-main'),
    ];

    const closeModalBtns = document.querySelectorAll('[data-close-modal]');

    const openModal = () => {
        if (uploadModal) uploadModal.classList.remove('hidden');
    }
    const closeModal = () => {
        if (uploadModal) uploadModal.classList.add('hidden');
    }

    openModalBtns.forEach(btn => {
        if(btn) btn.addEventListener('click', openModal);
    });

    closeModalBtns.forEach(btn => {
        if(btn) btn.addEventListener('click', closeModal);
    });

    // --- Global Click Listeners ---
    document.addEventListener('click', (e) => {
        // Close sidebar context menus if clicking outside
        if (!e.target.closest('.chat-menu-btn') && !e.target.closest('.chat-item-menu')) {
            document.querySelectorAll('.chat-item-menu').forEach(menu => {
                menu.classList.add('hidden');
            });
        }
    });
});