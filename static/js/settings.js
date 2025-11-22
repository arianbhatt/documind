document.addEventListener('DOMContentLoaded', () => {
    const rightPanel = document.getElementById('right-panel');
    if (!rightPanel) return;

    const closeBtn = document.getElementById('close-settings-panel');
    const saveBtn = document.getElementById('save-settings-btn');
    const apiKeyInput = document.getElementById('custom-api-key-input');
    const storageKey = 'documind_custom_api_key';

    // --- Load saved key on page load ---
    function loadSavedKey() {
        const savedKey = localStorage.getItem(storageKey);
        if (savedKey) {
            window.STATE.customApiKey = savedKey;
            apiKeyInput.value = savedKey;
            showToast("Loaded custom API key from storage.", "info");
        }
    }

    // --- Save key to state and local storage ---
    function saveKey() {
        const newKey = apiKeyInput.value.trim();
        if (newKey) {
            window.STATE.customApiKey = newKey;
            localStorage.setItem(storageKey, newKey);
            showToast("Custom API key saved.", "success");
        } else {
            // If user clears the field, remove the key
            window.STATE.customApiKey = null;
            localStorage.removeItem(storageKey);
            showToast("Custom API key cleared.", "info");
        }
        rightPanel.classList.add('hidden');
    }

    // --- Close panel ---
    function closePanel() {
        rightPanel.classList.add('hidden');
    }

    // --- Event Listeners ---
    saveBtn.addEventListener('click', saveKey);
    closeBtn.addEventListener('click', closePanel);

    // --- Initial Load ---
    loadSavedKey();
});