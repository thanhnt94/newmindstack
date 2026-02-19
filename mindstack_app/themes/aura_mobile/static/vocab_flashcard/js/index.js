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

        if (!evt.target.closest('.toolbar-settings')) {
            if (window.closeAllSettingsMenus) window.closeAllSettingsMenus();
        }
    });

    // 5. Start Session — Driver API or Legacy fallback
    if (window.updateSessionSummary) window.updateSessionSummary();

    const _dbSessionId = window.FlashcardConfig?.dbSessionId;
    if (_dbSessionId && _dbSessionId > 0 && window.setDriverSessionId) {
        // ── Driver Path ──────────────────────────────────────────
        console.log('🚀 [Init] Activating Driver session:', _dbSessionId);
        window.setDriverSessionId(_dbSessionId);

        // Use getNextFlashcardBatch which fetches AND displays the card
        if (window.getNextFlashcardBatch) {
            window.getNextFlashcardBatch();
        }
    } else {
        // ── Legacy Path ──────────────────────────────────────────
        console.log('[Init] Using legacy batch flow');
        if (window.getNextFlashcardBatch) window.getNextFlashcardBatch();
    }

    // 6. Mode display toggle logic (New)
    const modeBtns = document.querySelectorAll('#js-fc-mode-btn, #js-fc-mode-btn-desktop');
    const titleEls = document.querySelectorAll('.js-fc-title');

    if (modeBtns.length > 0 && titleEls.length > 0) {
        modeBtns.forEach(modeBtn => {
            modeBtn.addEventListener('click', () => {
                if (modeBtn.dataset.busy === "true") return;
                modeBtn.dataset.busy = "true";

                const originalTitles = Array.from(titleEls).map(el => el.textContent);
                const modeName = window.FlashcardConfig.modeDisplayName || 'Chế độ học';

                // Visual feedback
                modeBtn.style.opacity = "0.7";

                // Set mode name
                titleEls.forEach(el => el.textContent = modeName);

                // Revert after 2 seconds
                setTimeout(() => {
                    titleEls.forEach((el, idx) => el.textContent = originalTitles[idx]);
                    modeBtn.style.opacity = "";
                    modeBtn.dataset.busy = "false";
                }, 2000);
            });
        });
    }
});

window.addEventListener('resize', () => {
    if (window.setVh) window.setVh();
    setTimeout(() => { if (window.adjustCardLayout) window.adjustCardLayout(); }, 0);
});
