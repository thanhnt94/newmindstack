// Event Listeners and Initialization

const setVh = () => {
    if (window.flashcardViewport && typeof window.flashcardViewport.refresh === 'function') {
        window.flashcardViewport.refresh();
    }
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
};

// Global Event Listeners
document.addEventListener('click', (evt) => {
    const settingsToggle = evt.target.closest('.settings-toggle-btn');
    if (settingsToggle) {
        evt.stopPropagation();
        toggleSettingsMenu(settingsToggle.closest('.toolbar-settings'));
        return;
    }

    const autoplayToggle = evt.target.closest('.audio-autoplay-toggle-btn');
    if (autoplayToggle) {
        evt.stopPropagation();
        setAudioAutoplayEnabled(!isAudioAutoplayEnabled);
        return;
    }

    const imageToggle = evt.target.closest('.image-toggle-btn');
    if (imageToggle) {
        evt.stopPropagation();
        setMediaHiddenState(!isMediaHidden);
        return;
    }

    if (!evt.target.closest('.toolbar-settings')) {
        closeAllSettingsMenus();
    }
});

// Orientation/Resize
window.addEventListener('resize', () => {
    setVh();
    if (typeof adjustCardLayout === 'function') setTimeout(adjustCardLayout, 0);
});
window.addEventListener('orientationchange', () => setTimeout(setVh, 100));

// DOM Content Loaded - Main Initialization
document.addEventListener('DOMContentLoaded', () => {
    setVh();
    document.body.classList.add('flashcard-session-active');

    // Register tab buttons
    document.querySelectorAll('.statistics-card .stats-tab-button').forEach(btn => {
        btn.addEventListener('click', handleTabClick);
    });

    // Note panel buttons
    const saveNoteBtn = document.getElementById('save-note-btn');
    const cancelNoteBtn = document.getElementById('cancel-note-btn');
    const editNoteBtn = document.getElementById('edit-note-btn');
    const closeNoteBtn = document.getElementById('close-note-btn');
    const notePanel = document.getElementById('note-panel');

    if (saveNoteBtn) saveNoteBtn.addEventListener('click', saveNote);
    if (cancelNoteBtn) cancelNoteBtn.addEventListener('click', handleCancelNote);
    if (editNoteBtn) editNoteBtn.addEventListener('click', () => setNoteMode('edit'));
    if (closeNoteBtn) closeNoteBtn.addEventListener('click', closeNotePanel);
    if (notePanel) notePanel.addEventListener('click', (e) => { if (e.target === notePanel) closeNotePanel(); });

    // End session modal
    const endSessionBtn = document.getElementById('end-session-btn');
    const confirmEndSessionBtn = document.getElementById('confirmEndSessionBtn');
    const cancelEndSessionBtn = document.getElementById('cancelEndSessionBtn');
    const endSessionModal = document.getElementById('endSessionModal');

    if (endSessionBtn) endSessionBtn.addEventListener('click', () => { if (endSessionModal) endSessionModal.style.display = 'flex'; });
    if (confirmEndSessionBtn) confirmEndSessionBtn.addEventListener('click', async () => {
        if (isAutoplaySession) cancelAutoplaySequence();
        try {
            const res = await fetch(endSessionUrl, { method: 'POST', headers: csrfHeaders });
            if (!res.ok) throw new Error('HTTP ' + res.status);
            const r = await res.json();
            window.showFlashMessage?.(r.message || 'Đã kết thúc phiên.', 'info');
            window.location.href = dashboardUrl;
        } catch (e) {
            window.showFlashMessage?.('Có lỗi xảy ra khi kết thúc phiên.', 'danger');
        } finally {
            if (endSessionModal) endSessionModal.style.display = 'none';
        }
    });
    if (cancelEndSessionBtn) cancelEndSessionBtn.addEventListener('click', () => { if (endSessionModal) endSessionModal.style.display = 'none'; });

    // Stats modal close
    const closeStatsModalBtn = document.getElementById('closeStatsModalBtn');
    if (closeStatsModalBtn) closeStatsModalBtn.addEventListener('click', () => toggleStatsModal(false));

    // Expose helpers for mobile
    window.setMediaHiddenState = setMediaHiddenState;
    window.setAudioAutoplayEnabled = setAudioAutoplayEnabled;
    window.toggleAudioAutoplay = () => setAudioAutoplayEnabled(!isAudioAutoplayEnabled);
    window.openModal = (id) => { const el = document.getElementById(id); if (el) el.style.display = 'flex'; };

    // Card state getters
    Object.defineProperty(window, 'currentFlashcardBatch', { get: () => currentFlashcardBatch, configurable: true });
    Object.defineProperty(window, 'currentFlashcardIndex', { get: () => currentFlashcardIndex, configurable: true });
    Object.defineProperty(window, 'isMediaHidden', { get: () => isMediaHidden, configurable: true });
    Object.defineProperty(window, 'isAudioAutoplayEnabled', { get: () => isAudioAutoplayEnabled, configurable: true });

    // Start fetching
    updateSessionSummary();
    getNextFlashcardBatch();
});
