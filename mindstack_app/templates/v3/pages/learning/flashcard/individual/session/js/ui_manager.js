/**
 * UI Manager for Flashcard Session
 * Handles global event delegation, keyboard shortcuts, and view interactions.
 */
window.UIManager = (function () {

    // --- Initialization ---

    function init() {
        setupGlobalEventListeners();
        setupKeyboardShortcuts();
        setupMobileSpecifics();

        // Start Session
        if (window.SessionEngine) {
            window.SessionEngine.init();
        }
    }

    // --- Event Delegation ---

    function setupGlobalEventListeners() {
        document.body.addEventListener('click', async (e) => {
            const target = e.target;
            const card = window.SessionEngine ? window.SessionEngine.getCurrentCard() : null;

            // 1. Flip Card
            if (target.closest('.js-flip-card-btn') || target.closest('.flashcard-card')) {
                // Prevent flip if clicking on interactive elements
                if (target.closest('button') && !target.closest('.js-flip-card-btn')) return;

                const cardEl = target.closest('.flashcard-card-container')?.querySelector('.flashcard-card');
                if (cardEl && !cardEl.classList.contains('flipped')) {
                    cardEl.classList.add('flipped');
                    if (window.SessionEngine) window.SessionEngine.handleCardFlip();
                }
            }

            // 2. Rating Buttons (Answer)
            const ratingBtn = target.closest('.js-rating-btn');
            if (ratingBtn && window.SessionEngine) {
                const itemId = ratingBtn.dataset.itemId;
                const answer = ratingBtn.dataset.rating;
                // Calculate duration... simplified for now
                const duration = 0;

                // UI feedback (loading state)
                const actionsDiv = ratingBtn.closest('.actions');
                if (actionsDiv) {
                    const originalContent = actionsDiv.innerHTML;
                    actionsDiv.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="sr-only">Loading...</span></div>';

                    const result = await window.SessionEngine.submitAnswer(itemId, answer, duration);
                    if (result && result.success) {
                        // Update stats logic in SessionEngine will be triggered by nextCard
                        window.SessionEngine.nextCard();
                    } else {
                        // Error handling
                        actionsDiv.innerHTML = originalContent;
                        alert('Có lỗi xảy ra khi nộp câu trả lời.');
                    }
                }
            }

            // 3. Audio Buttons
            const audioBtn = target.closest('.play-audio-btn');
            if (audioBtn && window.FlashcardAudioController) {
                e.preventDefault();
                e.stopPropagation();

                const selector = audioBtn.dataset.audioTarget;
                const audioEl = document.querySelector(selector);

                if (audioEl) {
                    if (audioEl.error || !audioEl.src) {
                        // Try TTS generation
                        actionIconSpin(audioBtn, true);
                        await window.FlashcardAudioController.generateAndPlayAudio(audioBtn, audioEl);
                        actionIconSpin(audioBtn, false);
                    } else {
                        window.FlashcardAudioController.playAudioAfterLoad(audioEl);
                    }
                }
            }

            // 4. Settings Toggles (Image, AutoPlay)
            const imgToggle = target.closest('.image-toggle-btn');
            if (imgToggle) {
                e.stopPropagation();
                const isHidden = localStorage.getItem('flashcardHideImages') === 'true';
                localStorage.setItem('flashcardHideImages', !isHidden);
                if (window.SessionEngine) {
                    window.SessionEngine.syncSettingsToServer({ show_image: isHidden }); // Toggle logic inverted: isHidden=true means show=false
                    // Re-render current card to apply
                    window.SessionEngine.renderCurrentCard();
                    // Or just toggle CSS class? Re-render is safer for consistency
                }
            }

            const autoPlayToggle = target.closest('.audio-autoplay-toggle-btn');
            if (autoPlayToggle) {
                e.stopPropagation();
                const isAuto = localStorage.getItem('flashcardAutoplayAudio') === 'true';
                localStorage.setItem('flashcardAutoplayAudio', !isAuto);
                if (window.SessionEngine) {
                    window.SessionEngine.syncSettingsToServer({ autoplay: !isAuto });
                    window.SessionEngine.renderCurrentCard();
                }
            }

            // 5. Modals (Feedback, AI, Notes) - assuming global modal functions exist or we extract them too
            if (target.closest('.open-feedback-modal-btn')) {
                const btn = target.closest('.open-feedback-modal-btn');
                if (window.openFeedbackModal) window.openFeedbackModal(btn.dataset.itemId);
            }
        });
    }

    function setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ignore if input focused
            if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

            // Space: Flip
            if (e.code === 'Space') {
                e.preventDefault();
                const cardEl = document.querySelector('.flashcard-card-container .flashcard-card');
                if (cardEl && !cardEl.classList.contains('flipped')) {
                    cardEl.classList.add('flipped');
                    if (window.SessionEngine) window.SessionEngine.handleCardFlip();
                }
                return;
            }

            // Numbers 1-4: Rating
            if (['Digit1', 'Digit2', 'Digit3', 'Digit4'].includes(e.code)) {
                const cardEl = document.querySelector('.flashcard-card-container .flashcard-card');
                if (cardEl && cardEl.classList.contains('flipped')) {
                    const rating = e.key;
                    const btn = document.querySelector(`.js-rating-btn[data-shortcut="${rating}"]`);
                    if (btn) btn.click();
                }
            }
        });
    }

    function setupMobileSpecifics() {
        // Mobile header toggles (Stats, etc)
        const statsToggle = document.querySelector('.js-fc-stats-toggle');
        if (statsToggle) {
            statsToggle.addEventListener('click', () => {
                const row = document.querySelector('.fc-stats-row');
                if (row) {
                    const isHidden = row.style.display === 'none';
                    row.style.display = isHidden ? 'flex' : 'none';
                    // Update icon/text
                }
            });
        }
    }

    // --- Helpers ---
    function actionIconSpin(btn, spin) {
        const icon = btn.querySelector('i');
        if (!icon) return;
        if (spin) {
            btn.dataset.originalIcon = icon.className;
            icon.className = 'fas fa-spinner fa-spin';
        } else {
            icon.className = btn.dataset.originalIcon || 'fas fa-volume-up';
        }
    }

    function showLoading(show) {
        const container = document.getElementById('flashcard-viewport-container');
        if (container) {
            if (show) container.classList.add('is-loading'); // CSS should handle this
            else container.classList.remove('is-loading');
        }
    }

    function showFinishedScreen() {
        const container = document.getElementById('flashcard-viewport-container');
        if (container) {
            container.innerHTML = `
                <div class="session-finished-state">
                    <i class="fas fa-check-circle text-6xl text-emerald-500 mb-4"></i>
                    <h2 class="text-2xl font-bold mb-2">Đã hoàn thành!</h2>
                    <p class="mb-4">Bạn đã hoàn thành phiên học này.</p>
                    <a href="/learning/dashboard" class="btn btn-primary">Về trang chủ</a>
                </div>
            `;
        }
    }

    function showError(msg) {
        alert(msg);
    }

    return {
        init,
        showLoading,
        showFinishedScreen,
        showError
    };
})();

// Start when ready
document.addEventListener('DOMContentLoaded', () => {
    // Check if dependencies loaded
    if (window.SessionEngine && window.RenderEngine && window.FlashcardAudioController) {
        UIManager.init();
    } else {
        console.error('Core modules failed to load.');
    }
});
