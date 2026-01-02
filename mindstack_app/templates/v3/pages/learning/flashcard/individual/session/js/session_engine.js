/**
 * Session Engine for Flashcard Session
 * "Controller" role: Handles API calls, Session state, and orchestrates Render & Audio engines.
 */
window.SessionEngine = (function () {
    // --- State ---
    let currentFlashcardBatch = [];
    let currentFlashcardIndex = 0;
    let sessionStats = {
        total_reviewed: 0,
        session_start: Date.now(),
        correct_count: 0,
        incorrect_count: 0
    };
    let sessionAnswerHistory = []; // { front, answer, scoreChange, timestamp }
    let isReviewFinished = false;

    // --- References to Config ---
    const getConfig = () => window.FlashcardConfig || {};

    // --- API Interactions ---

    async function syncSettingsToServer(settings) {
        const url = getConfig().updateVisualSettingsUrl;
        const csrfToken = getConfig().csrfToken;
        if (!url) return;

        try {
            await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(settings)
            });
        } catch (err) {
            console.warn('[SessionEngine] Failed to sync settings:', err);
        }
    }

    async function fetchNextBatch() {
        const url = getConfig().getFlashcardBatchUrl;
        if (!url) {
            console.error('[SessionEngine] Missing getFlashcardBatchUrl');
            return null;
        }

        try {
            const response = await fetch(url);
            const data = await response.json();
            if (data.status === 'success') {
                return data.batch;
            } else if (data.status === 'finished') {
                return 'finished';
            } else {
                console.error('[SessionEngine] Batch fetch failed:', data.message);
                return null;
            }
        } catch (err) {
            console.error('[SessionEngine] Batch fetch error:', err);
            return null;
        }
    }

    async function submitAnswer(itemId, answer, duration) {
        const url = getConfig().submitAnswerUrl;
        const csrfToken = getConfig().csrfToken;
        if (!url) {
            console.error('[SessionEngine] Missing submitAnswerUrl');
            return null;
        }

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    item_id: itemId,
                    answer: answer,
                    duration: duration
                })
            });
            return await response.json();
        } catch (err) {
            console.error('[SessionEngine] Answer submission error:', err);
            return null;
        }
    }

    // --- Logic ---

    function getCardContent(card) {
        if (!card) return {};
        // Use server-provided content if available (pre-rendered or structured)
        // Fallback to raw text
        return {
            front: card.content?.front || card.front_text || '',
            back: card.content?.back || card.back_text || ''
        };
    }

    function getCurrentCard() {
        if (!currentFlashcardBatch || currentFlashcardIndex >= currentFlashcardBatch.length) return null;
        return currentFlashcardBatch[currentFlashcardIndex];
    }

    async function nextCard() {
        currentFlashcardIndex++;

        if (currentFlashcardIndex >= currentFlashcardBatch.length) {
            // Fetch next batch
            if (window.UIManager) window.UIManager.showLoading(true);
            const result = await fetchNextBatch();
            if (window.UIManager) window.UIManager.showLoading(false);

            if (result === 'finished') {
                isReviewFinished = true;
                if (window.UIManager) window.UIManager.showFinishedScreen();
                return;
            }

            if (Array.isArray(result) && result.length > 0) {
                currentFlashcardBatch = result;
                currentFlashcardIndex = 0;
            } else {
                // Fallback or error state
                console.warn('[SessionEngine] Received empty batch or error.');
                return;
            }
        }

        renderCurrentCard();
    }

    function renderCurrentCard() {
        if (isReviewFinished) return;
        const card = getCurrentCard();
        if (!card) return;

        // Render Card UI
        if (window.RenderEngine) {
            const isMobile = window.innerWidth <= 768; // Simple check, or use config
            const isMediaHidden = localStorage.getItem('flashcardHideImages') === 'true';
            const isAudioAutoplayEnabled = localStorage.getItem('flashcardAutoplayAudio') === 'true';
            const canEdit = getConfig().userIsAdmin || false;

            // Stats
            const stats = card.stats_data || {};
            const scoreChange = 0; // Initial render of card has no score change yet

            // Desktop Render
            const desktopHtml = window.RenderEngine.renderDesktopCardHtml(null, {
                itemId: card.item_id,
                fTxt: window.RenderEngine.formatTextForHtml(getCardContent(card).front),
                bTxt: window.RenderEngine.formatTextForHtml(getCardContent(card).back),
                frontImg: card.content?.front_image || null,
                backImg: card.content?.back_image || null,
                frontAudioUrl: card.audio_url_front,
                backAudioUrl: card.audio_url_back,
                hasFrontAudio: !!card.audio_url_front,
                hasBackAudio: !!card.audio_url_back,
                frontAudioContent: card.content?.front_audio_content || getCardContent(card).front,
                backAudioContent: card.content?.back_audio_content || getCardContent(card).back,
                buttonsHtml: generateRatingButtonsHtml(card.item_id), // Define helper
                canEditCurrentCard: canEdit,
                editUrl: getConfig().editUrlTemplate ? getConfig().editUrlTemplate.replace('/0', '/' + card.container_id).replace('/0', '/' + card.item_id) + '?is_modal=true' : '#',
                isMediaHidden: isMediaHidden,
                isAudioAutoplayEnabled: isAudioAutoplayEnabled,
                cardCategory: card.category || 'default',
                buttonCount: 4
            });

            // Mobile Render
            const mobileHtml = window.RenderEngine.renderMobileCardHtml(null, {
                itemId: card.item_id,
                fTxt: window.RenderEngine.formatTextForHtml(getCardContent(card).front),
                bTxt: window.RenderEngine.formatTextForHtml(getCardContent(card).back),
                frontImg: card.content?.front_image || null,
                backImg: card.content?.back_image || null,
                frontAudioUrl: card.audio_url_front,
                backAudioUrl: card.audio_url_back,
                hasFrontAudio: !!card.audio_url_front,
                hasBackAudio: !!card.audio_url_back,
                frontAudioContent: card.content?.front_audio_content || getCardContent(card).front,
                backAudioContent: card.content?.back_audio_content || getCardContent(card).back,
                buttonsHtml: generateRatingButtonsHtml(card.item_id),
                canEditCurrentCard: canEdit,
                editUrl: getConfig().editUrlTemplate ? getConfig().editUrlTemplate.replace('/0', '/' + card.container_id).replace('/0', '/' + card.item_id) + '?is_modal=true' : '#',
                isMediaHidden: isMediaHidden,
                isAudioAutoplayEnabled: isAudioAutoplayEnabled,
                cardCategory: card.category || 'default',
                buttonCount: 4
            });

            // Update DOM
            const container = document.getElementById('flashcard-viewport-container');
            if (container) {
                // Determine if we are updating desktop or mobile view parts
                // Ideally, we replace the content of '.flashcard-desktop-view' and '.flashcard-mobile-view'
                const desktopView = document.querySelector('.flashcard-desktop-view');
                if (desktopView) desktopView.innerHTML = desktopHtml;

                const mobileView = document.querySelector('.flashcard-mobile-view');
                if (mobileView) mobileView.innerHTML = mobileHtml;
            }

            // Stats Update
            updateStatsView(stats, scoreChange, getCardContent(card), true);

            // Post-Render Layout Adjust
            window.RenderEngine.adjustCardLayout();

            // Re-bind UI events? 
            // Better: use Event Delegation in ui_manager.js so we don't need to rebind.

            // Audio Autoplay logic
            handleAutoplay(card);
        }
    }

    function generateRatingButtonsHtml(itemId) {
        // Return HTML string for rating buttons (Again, Hard, Good, Easy)
        // Standardized for both views or customizable
        return `
            <button class="action-btn is-again js-rating-btn" data-rating="1" data-item-id="${itemId}" data-label="Again" data-shortcut="1">
                <span class="label">Quên</span><span class="sub-label">< 1m</span>
            </button>
            <button class="action-btn is-hard js-rating-btn" data-rating="2" data-item-id="${itemId}" data-label="Hard" data-shortcut="2">
                <span class="label">Khó</span><span class="sub-label">2d</span>
            </button>
            <button class="action-btn is-good js-rating-btn" data-rating="3" data-item-id="${itemId}" data-label="Good" data-shortcut="3">
                <span class="label">Được</span><span class="sub-label">4d</span>
            </button>
            <button class="action-btn is-easy js-rating-btn" data-rating="4" data-item-id="${itemId}" data-label="Easy" data-shortcut="4">
                <span class="label">Dễ</span><span class="sub-label">7d</span>
            </button>
        `;
    }

    function updateStatsView(stats, scoreChange, cardContent, isInitial) {
        if (!window.RenderEngine) return;

        // Desktop Stats
        const desktopStatsContainer = document.getElementById('stats-content-desktop');
        if (desktopStatsContainer) {
            desktopStatsContainer.innerHTML = window.RenderEngine.renderCardStatsHtml(stats, scoreChange, cardContent, isInitial);
        }

        // Mobile Stats
        const mobileStatsContainer = document.getElementById('stats-content-mobile');
        if (mobileStatsContainer) {
            mobileStatsContainer.innerHTML = window.RenderEngine.renderMobileCardStatsHtml(stats, scoreChange, cardContent, isInitial);
        }

        // Mobile History (if function exists in UI manager or Render Engine)
        // Trigger event for UI manager to update history
        const event = new CustomEvent('flashcardStatsUpdated', {
            detail: { stats, scoreChange, cardContent }
        });
        document.dispatchEvent(event);
    }

    function handleAutoplay(card) {
        if (!window.FlashcardAudioController) return;

        const isAutoplay = localStorage.getItem('flashcardAutoplayAudio') === 'true';
        if (!isAutoplay) {
            window.FlashcardAudioController.stopAllAudio();
            return;
        }

        window.FlashcardAudioController.cancelAutoplay();
        const token = window.FlashcardAudioController.getCurrentToken();

        // Autoplay sequence: Front Audio -> Wait -> (User flips) -> Back Audio
        // Actually, usually just Front Audio on load. Back audio plays on flip.

        // Find visible audio element
        const isMobile = window.getComputedStyle(document.querySelector('.flashcard-mobile-view')).display !== 'none';
        const audioSelector = isMobile ? '#front-audio-mobile' : '#front-audio-desktop';
        const audioEl = document.querySelector(audioSelector);

        if (audioEl && audioEl.src) {
            window.FlashcardAudioController.playAudioAfterLoad(audioEl);
        } else if (card.content?.front_audio_content) {
            // TTS fallback if needed?
        }
    }

    // Initialize
    async function init() {
        if (window.UIManager) window.UIManager.showLoading(true);
        const batch = await fetchNextBatch();
        if (batch === 'finished') {
            isReviewFinished = true;
            if (window.UIManager) window.UIManager.showFinishedScreen();
        } else if (batch && batch.length > 0) {
            currentFlashcardBatch = batch;
            currentFlashcardIndex = -1; // Will step to 0
            if (window.UIManager) window.UIManager.showLoading(false);
            nextCard();
        } else {
            if (window.UIManager) window.UIManager.showError('Không thể tải thẻ. Vui lòng tải lại trang.');
        }
    }

    return {
        init,
        nextCard,
        submitAnswer,
        getCurrentCard,
        get sessionStats() { return sessionStats; },
        get sessionAnswerHistory() { return sessionAnswerHistory; },
        syncSettingsToServer,
        // Expose for UI interactions
        handleCardFlip: () => {
            // Play back audio if autoplay enabled
            const isAutoplay = localStorage.getItem('flashcardAutoplayAudio') === 'true';
            if (isAutoplay && window.FlashcardAudioController) {
                const isMobile = window.getComputedStyle(document.querySelector('.flashcard-mobile-view')).display !== 'none';
                const audioSelector = isMobile ? '#back-audio-mobile' : '#back-audio-desktop';
                const audioEl = document.querySelector(audioSelector);
                if (audioEl) window.FlashcardAudioController.playAudioAfterLoad(audioEl);
            }
        }
    };
})();
