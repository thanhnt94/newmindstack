/**
 * Index.js - Entry point for Flashcard Session
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Init Base State
    if (window.currentUserTotalScoreInit !== undefined) {
        window.currentUserTotalScore = window.currentUserTotalScoreInit;
    }

    // 2. Settings init
    if (window.FlashcardConfig) {
        window.userButtonCount = window.FlashcardConfig.userButtonCount;
        window.isAutoplaySession = window.FlashcardConfig.isAutoplaySession;
    }
    if (window.initAudioSettings) window.initAudioSettings();
    if (window.initUiSettings) window.initUiSettings();

    // 3. Layout init
    if (window.setVh) window.setVh();
    document.body.classList.add('flashcard-session-active');

    // 4. Bind Global Event Listeners

    // Tab switching in stats card
    function handleTabClick(event) {
        const button = event.currentTarget || event.target.closest('.stats-tab-button');
        if (!button) return;

        const targetPaneId = button.dataset.target;
        if (!targetPaneId) return;

        const parentContainer = button.closest('.statistics-card');
        if (!parentContainer) return;

        parentContainer.querySelectorAll('.stats-tab-button').forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        parentContainer.querySelectorAll('.stats-tab-pane').forEach(pane => {
            pane.classList.toggle('active', pane.id === targetPaneId);
        });
    }
    document.querySelectorAll('.statistics-card .stats-tab-button').forEach(btn => btn.addEventListener('click', handleTabClick));

    // End Session Modals
    const endSessionBtn = document.getElementById('end-session-btn');
    const endSessionModal = document.getElementById('endSessionModal');
    const confirmEndSessionBtn = document.getElementById('confirmEndSessionBtn');
    const cancelEndSessionBtn = document.getElementById('cancelEndSessionBtn');

    if (endSessionBtn) endSessionBtn.addEventListener('click', () => endSessionModal.style.display = 'flex');

    if (confirmEndSessionBtn) confirmEndSessionBtn.addEventListener('click', async () => {
        if (window.FlashcardConfig.isAutoplaySession) {
            window.cancelAutoplaySequence();
        }
        try {
            const res = await fetch(window.FlashcardConfig.endSessionUrl, { method: 'POST', headers: window.FlashcardConfig.csrfHeaders });
            if (!res.ok) throw new Error('HTTP ' + res.status);
            const r = await res.json();
            if (window.showFlashMessage) window.showFlashMessage(r.message || 'Đã kết thúc phiên.', 'info');
            window.location.href = window.FlashcardConfig.vocabDashboardUrl;
        } catch (e) {
            if (window.showFlashMessage) window.showFlashMessage('Có lỗi xảy ra khi kết thúc phiên.', 'danger');
        } finally {
            if (endSessionModal) endSessionModal.style.display = 'none';
        }
    });

    if (cancelEndSessionBtn) cancelEndSessionBtn.addEventListener('click', () => endSessionModal.style.display = 'none');

    // Note Panel Events
    const saveNoteBtn = document.getElementById('save-note-btn');
    const cancelNoteBtn = document.getElementById('cancel-note-btn');
    const editNoteBtn = document.getElementById('edit-note-btn');
    const closeNoteBtn = document.getElementById('close-note-btn');
    const notePanel = document.getElementById('note-panel');

    if (saveNoteBtn) saveNoteBtn.addEventListener('click', window.saveNote);
    if (cancelNoteBtn) cancelNoteBtn.addEventListener('click', window.handleCancelNote);
    if (editNoteBtn) editNoteBtn.addEventListener('click', () => window.setNoteMode('edit'));
    if (closeNoteBtn) closeNoteBtn.addEventListener('click', window.closeNotePanel);
    if (notePanel) notePanel.addEventListener('click', (event) => {
        if (event.target === notePanel) {
            window.closeNotePanel();
        }
    });

    // Stats Mobile Close
    const closeStatsModalBtn = document.getElementById('closeStatsModalBtn');
    if (closeStatsModalBtn) closeStatsModalBtn.addEventListener('click', () => window.toggleStatsModal(false));

    // Settings Listeners
    document.addEventListener('click', (evt) => {
        const settingsToggle = evt.target.closest('.settings-toggle-btn');

        if (settingsToggle) {
            evt.stopPropagation();
            if (window.toggleSettingsMenu) window.toggleSettingsMenu(settingsToggle.closest('.toolbar-settings'));
            return;
        }

        const autoplayToggle = evt.target.closest('.audio-autoplay-toggle-btn');
        if (autoplayToggle) {
            evt.stopPropagation();
            if (window.setAudioAutoplayEnabled) window.setAudioAutoplayEnabled(!window.isAudioAutoplayEnabled);
            return;
        }

        if (!evt.target.closest('.toolbar-settings')) {
            if (window.closeAllSettingsMenus) window.closeAllSettingsMenus();
        }
    });

    // 5. Start Session
    if (window.updateSessionSummary) window.updateSessionSummary();
    if (window.getNextFlashcardBatch) window.getNextFlashcardBatch();
});

window.addEventListener('resize', () => {
    if (window.setVh) window.setVh();
    setTimeout(() => { if (window.adjustCardLayout) window.adjustCardLayout(); }, 0);
});
