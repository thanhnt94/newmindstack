/**
 * Session Manager for Flashcard Session
 * [v2] SessionDriverClient integration
 */

// Global State
let currentFlashcardBatch = [];
let currentFlashcardIndex = 0;
let previousCardStats = null;
let sessionScore = 0;
let currentUserTotalScore = window.currentUserTotalScoreInit || 0;
let sessionAnswerHistory = [];
let currentStreak = 0;
let currentCardStartTime = 0;
let isSubmitting = false; // [LOCK] Prevent double submissions
let isFetchingBatch = false; // [LOCK] Prevent multiple background fetches
let activeFetchPromise = null; // [PROMISE] Track the current batch fetch
let isSessionEnding = false; // [STATE] Track if we reached the end

// ── Driver API State ────────────────────────────────────────────────
let _driverSessionId = null;

/**
 * Quality map: rating string → numeric quality (1-4).
 */
const _QUALITY_MAP = {
    'again': 1, 'quên': 1,
    'hard': 2, 'mơ_hồ': 2,
    'good': 3, 'nhớ': 3,
    'easy': 4, 'very_easy': 4,
};

/**
 * Map Driver /next response → legacy card format for renderCard().
 *
 * Driver returns: { item_id, interaction_type, data: { type, item_id, container_id, front, back, content }, progress, is_last }
 * renderCard expects: { item_id, container_id, content: { front, back, front_img, ... }, initial_stats, can_edit, container_title }
 */
function _mapDriverItemToLegacy(driverPayload) {
    const d = driverPayload.data || {};
    return {
        item_id: driverPayload.item_id || d.item_id,
        container_id: d.container_id,
        content: d.content || { front: d.front || '', back: d.back || '' },
        initial_stats: d.initial_stats || {},
        can_edit: d.can_edit || false,
        container_title: d.container_title || '',
        // Backend pre-rendered HTML
        html_front: d.html_front,
        html_back: d.html_back,
        html_full: d.html_full,
        // progress metadata from driver
        _progress: driverPayload.progress || {},
        _is_last: driverPayload.is_last || false,
    };
}



// Local stats
let sessionStatsLocal = {
    processed: (window.FlashcardConfig && window.FlashcardConfig.initialProcessedCount) ? window.FlashcardConfig.initialProcessedCount : 0,
    total: 0,
    correct: (window.FlashcardConfig && window.FlashcardConfig.initialCorrectCount) ? window.FlashcardConfig.initialCorrectCount : 0,
    incorrect: (window.FlashcardConfig && window.FlashcardConfig.initialIncorrectCount) ? window.FlashcardConfig.initialIncorrectCount : 0,
    vague: (window.FlashcardConfig && window.FlashcardConfig.initialVagueCount) ? window.FlashcardConfig.initialVagueCount : 0
};

// --- Settings Sync ---

function syncSettingsToServer() {
    const saveSettingsUrl = window.FlashcardConfig.saveSettingsUrl;
    if (!saveSettingsUrl) return;

    // Audio autoplay is NO LONGER synced to server — it's localStorage-only.
    const isMediaHidden = window.isMediaHidden;
    const showStats = window.showStats;

    const payload = {
        visual_settings: {
            show_image: !isMediaHidden,
            show_stats: showStats
        }
    };

    console.log('[SYNC SETTINGS] Sending to server:', payload);

    fetch(saveSettingsUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...window.FlashcardConfig.csrfHeaders },
        body: JSON.stringify(payload)
    })
        .then(r => r.json())
        .then(data => console.log('[SYNC SETTINGS] Server response:', data))
        .catch(err => console.warn('[SYNC SETTINGS] Failed:', err));
}

// Mobile helpers
window.updateVisualSettings = function (newSettings) {
    if (newSettings.show_image !== undefined) {
        window.setMediaHiddenState(!newSettings.show_image); // This calls sync inside it
    }
    if (newSettings.autoplay !== undefined) {
        window.setAudioAutoplayEnabled(newSettings.autoplay); // This calls sync inside it
    }
    if (newSettings.show_stats !== undefined) {
        window.showStats = newSettings.show_stats;
        syncSettingsToServer(); // Manually sync if we just updated variable

        // Re-apply visibility
        if (!window.showStats) {
            const currentCardStatsContainer = document.getElementById('current-card-stats');
            const previousCardStatsContainer = document.getElementById('previous-card-stats');
            if (currentCardStatsContainer) currentCardStatsContainer.style.display = 'none';
            if (previousCardStatsContainer) previousCardStatsContainer.style.display = 'none';
            const mobileStats = document.getElementById('current-card-stats-mobile');
            if (mobileStats) mobileStats.style.display = 'none';
        } else {
            const currentCardStatsContainer = document.getElementById('current-card-stats');
            const previousCardStatsContainer = document.getElementById('previous-card-stats');
            if (currentCardStatsContainer) currentCardStatsContainer.style.display = '';
            if (previousCardStatsContainer) previousCardStatsContainer.style.display = '';
            const mobileStats = document.getElementById('current-card-stats-mobile');
            if (mobileStats) mobileStats.style.display = '';
        }
    }
};

// Update card state badge (NEW/LEARNED/HARD/MASTER)
window.updateStateBadge = function (customState) {
    const badge = document.querySelector('.js-fc-state-badge');
    const textEl = document.querySelector('.js-fc-state-text');
    if (!badge || !textEl) return;

    // Remove all state classes
    badge.classList.remove('state-new', 'state-learned', 'state-hard', 'state-master', 'hidden');

    // Map state to Vietnamese labels and CSS class (Spec v8: 5 states)
    const stateConfig = {
        'new': { label: 'MỚI', cssClass: 'state-new', icon: 'fa-seedling' },
        'learning': { label: 'ĐANG HỌC', cssClass: 'state-new', icon: 'fa-book-open' },
        'review': { label: 'ÔN TẬP', cssClass: 'state-learned', icon: 'fa-check-circle' },
        'learned': { label: 'ĐÃ HỌC', cssClass: 'state-learned', icon: 'fa-check-circle' },
        'hard': { label: 'KHÓ', cssClass: 'state-hard', icon: 'fa-fire' },
        'master': { label: 'THÀNH THẠO', cssClass: 'state-master', icon: 'fa-crown' }
    };

    const config = stateConfig[customState] || stateConfig['new'];
    badge.classList.add(config.cssClass);
    textEl.textContent = config.label;

    // Update icon
    const iconEl = badge.querySelector('i');
    if (iconEl) {
        iconEl.className = 'fa-solid ' + config.icon;
    }

    console.log('[StateBadge] Updated to:', customState, '->', config.label);
};

// --- Batch Management ---

// --- Smart Batch Management (Prefetching) ---

async function ensureFlashcardBuffer(immediate = false) {
    if (isSessionEnding) return null;
    if (activeFetchPromise) {
        console.log('[Batch] Already fetching, returning existing promise');
        return activeFetchPromise;
    }

    // [SRS-DYNAMIC] Fetch smaller batches (3) more frequently to ensure 
    // we always get the MOST DUE cards from the database at the current moment.
    const remaining = currentFlashcardBatch.length - (currentFlashcardIndex + 1);
    if (!immediate && remaining > 1) return null;

    console.log('[Batch] Refilling buffer... (immediate:', immediate, 'remaining:', remaining, ')');

    // [SSR] Check for initial batched data injected from server
    if (window.initialFlashcardBatch && window.initialFlashcardBatch.length > 0) {
        console.log('[Batch] Using Server-Side Initial Batch (SSR)', window.initialFlashcardBatch.length, 'items');
        const initialItems = window.initialFlashcardBatch;
        window.initialFlashcardBatch = null; // Clear it

        // Process initial items similar to fetch result
        currentFlashcardBatch.push(...initialItems);

        // Update total if passed in config or derived
        if (window.FlashcardConfig && window.FlashcardConfig.totalItems) {
            sessionStatsLocal.total = window.FlashcardConfig.totalItems;
        }

        // Trigger audio prefetch
        if (window.prefetchAudioForUpcomingCards) {
            window.prefetchAudioForUpcomingCards(1);
        }

        return Promise.resolve(initialItems);
    }

    isFetchingBatch = true;

    activeFetchPromise = (async () => {
        try {
            const config = window.FlashcardConfig;

            // ── [v2] Use Driver API if session is active ────────────
            if (_driverSessionId) {
                const nextUrl = `/session/api/${_driverSessionId}/next`;
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 8000);

                console.log('[Batch/Driver] Fetching next from:', nextUrl);
                const res = await fetch(nextUrl, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    signal: controller.signal
                });
                clearTimeout(timeoutId);

                if (!res.ok) {
                    throw new Error('HTTP ' + res.status);
                }

                const payload = await res.json();

                // Session finished?
                if (payload.finished) {
                    isSessionEnding = true;
                    if (immediate && remaining <= 0) {
                        handleSessionEnd(payload.summary?.message || 'Hoàn thành phiên học!');
                    }
                    return;
                }

                // Map to legacy format & push
                const legacyItem = _mapDriverItemToLegacy(payload);

                // Deduplicate
                const existingIds = new Set(currentFlashcardBatch.map(i => i.item_id));
                if (!existingIds.has(legacyItem.item_id)) {
                    currentFlashcardBatch.push(legacyItem);
                    console.log('[Batch/Driver] Added item', legacyItem.item_id, 'Buffer size:', currentFlashcardBatch.length);
                }

                // Update stats from progress
                if (legacyItem._progress) {
                    sessionStatsLocal.total = legacyItem._progress.total_items || sessionStatsLocal.total;
                }

                if (legacyItem._is_last) {
                    console.log('[Batch/Driver] This is the last item in queue.');
                }

                // Audio prefetch
                if (window.prefetchAudioForUpcomingCards) {
                    window.prefetchAudioForUpcomingCards(1);
                }

                return;
            }

            // ── Legacy fallback (old batch API) ─────────────────────
            if (!config || !config.getFlashcardBatchUrl) {
                console.error('[Batch] FlashcardConfig.getFlashcardBatchUrl is missing.');
                return null;
            }
            const getFlashcardBatchUrl = config.getFlashcardBatchUrl;

            const excludedIds = currentFlashcardBatch.map(item => item.item_id).join(',');
            let urlWithBatch = `${getFlashcardBatchUrl}${getFlashcardBatchUrl.includes('?') ? '&' : '?'}batch_size=1`;
            if (excludedIds) {
                urlWithBatch += `&exclude_items=${excludedIds}`;
            }

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 8000);

            console.log('[Batch] Fetching from:', urlWithBatch);
            const res = await fetch(urlWithBatch, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            console.log('[Batch] Fetch status:', res.status);

            if (!res.ok) {
                if (res.status === 404) {
                    isSessionEnding = true;
                    let endMessage = "Hết thẻ.";
                    try {
                        const end = await res.json();
                        endMessage = end.message || endMessage;
                    } catch (e) { }

                    console.log('[Batch] No more cards available.');
                    if (immediate && remaining <= 0) {
                        handleSessionEnd(endMessage);
                    }
                    return;
                }
                throw new Error('HTTP ' + res.status);
            }

            const batch = await res.json();
            console.log('[Batch] Data received items count:', batch.items ? batch.items.length : 0);
            const newItems = batch.items || [];

            if (newItems.length === 0) {
                isSessionEnding = true;
                if (immediate && remaining <= 0) {
                    handleSessionEnd("Hết thẻ trong phiên này!");
                }
                return;
            }

            sessionStatsLocal.total = batch.total_items_in_session || sessionStatsLocal.total;
            if (batch.session_points !== undefined) sessionScore = batch.session_points;

            const existingIds = new Set(currentFlashcardBatch.map(i => i.item_id));
            const uniqueNewItems = newItems.filter(i => !existingIds.has(i.item_id));

            if (uniqueNewItems.length > 0) {
                currentFlashcardBatch.push(...uniqueNewItems);
                console.log('[Batch] Buffer updated. Added:', uniqueNewItems.length, 'New size:', currentFlashcardBatch.length);
            } else {
                console.log('[Batch] No new unique items received (all duplicates).');
            }

            if (batch.container_name && batch.container_name !== 'Bộ thẻ') {
                document.querySelectorAll('.js-fc-title').forEach(el => {
                    el.textContent = batch.container_name;
                    el.title = batch.container_name;
                });
            }

            if (window.prefetchAudioForUpcomingCards) {
                console.log('[Batch] Triggering audio pre-generation for the new batch');
                window.prefetchAudioForUpcomingCards(1);
            }

        } catch (e) {
            console.error('[Batch] Failed to fetch batch:', e);
            if (immediate && remaining <= 0) {
                window.setFlashcardContent(`<p class='text-red-500 text-center'>Không thể tải thẻ. Vui lòng thử lại.</p>`);
            }
        } finally {
            isFetchingBatch = false;
            activeFetchPromise = null;
        }
    })();

    return activeFetchPromise;
}

function handleSessionEnd(message) {
    if (window.FlashcardConfig.isAutoplaySession) {
        window.cancelAutoplaySequence();
    }
    const dashboardUrl = window.FlashcardConfig.vocabDashboardUrl || '/';
    window.setFlashcardContent(`
        <div class="text-center py-12 text-gray-600">
            <i class="fas fa-check-circle text-5xl text-green-500 mb-4"></i>
            <h3 class="text-xl font-semibold text-gray-700 mb-2">Hoàn thành phiên học!</h3>
            <p class="text-gray-500">${window.formatTextForHtml(message)}</p>
            <button id="return-to-dashboard-btn" class="mt-6 px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 shadow-sm">
                <i class="fas fa-home mr-2"></i> Quay lại Dashboard
            </button>
        </div>
    `);

    document.getElementById('return-to-dashboard-btn')?.addEventListener('click', () => {
        window.location.href = dashboardUrl;
    });
}

/**
 * Loads and displays the next card in the buffer.
 * If buffer is empty, it waits for a fetch.
 */
async function getNextFlashcardBatch() {
    // If the card at current index is already in buffer, just show it
    // Note: index might have been incremented by submitFlashcardAnswer
    if (currentFlashcardIndex < currentFlashcardBatch.length) {
        displayCurrentCard();
        // Background check for refill
        ensureFlashcardBuffer();
        return;
    }

    // Buffer empty or at the end
    if (isSessionEnding) {
        handleSessionEnd("Bạn đã hoàn thành tất cả các thẻ!");
        return;
    }

    // Must fetch immediate
    window.isSubmitLock = false;
    window.stopAllFlashcardAudio();
    window.setFlashcardContent(`<div class="flex flex-col items-center justify-center h-full text-blue-500 min-h-[300px]"><i class="fas fa-spinner fa-spin text-4xl mb-3"></i><p>Đang tải thẻ...</p></div>`);

    await ensureFlashcardBuffer(true);

    if (currentFlashcardBatch.length > currentFlashcardIndex) {
        displayCurrentCard();
    } else {
        console.warn('[Session] No cards in buffer after fetch attempt.');
        if (!isSessionEnding) {
            window.setFlashcardContent(`<p class='text-red-500 text-center py-12'>Không thể tải thêm thẻ. Hãy thử tải lại trang.</p>`);
        }
    }
}

async function displayCurrentCard(force = false) {
    console.log(`[Display] Attempting to display card at index: ${currentFlashcardIndex}, Buffer size: ${currentFlashcardBatch.length} (Force: ${force})`);

    // [UX-DEFER] If a notification is active, wait until it finishes
    // UNLESS force is true (e.g. calling from submitFlashcardAnswer with smart timing)
    if (window.isNotificationActive && !force) {
        console.warn('[Display] Deferring: Notification is currently ACTIVE');
        window.pendingCardDisplay = true;
        return;
    }

    const currentCardData = currentFlashcardBatch[currentFlashcardIndex];
    if (!currentCardData) {
        console.error('[Display] FAILED: No card data found at index', currentFlashcardIndex);
        return;
    }

    console.log('[Display] Rendering card ID:', currentCardData.item_id);

    window.isSubmitLock = false;
    window.stopAllFlashcardAudio();

    // [ANIMATION] Start Exit Transition
    const cardSurface = document.querySelector('.card-surface');
    if (cardSurface) {
        cardSurface.classList.add('card-transition-exit');
        await new Promise(resolve => setTimeout(resolve, 100)); // Match CSS 0.1s
    }

    // Stats Rendering
    const currentCardStatsContainer = document.getElementById('current-card-stats');
    if (window.renderCardStatsHtml && currentCardStatsContainer) {
        const html = window.renderCardStatsHtml(currentCardData.initial_stats, 0, currentCardData.content, true);
        window.displayCardStats(currentCardStatsContainer, html);
    }

    const mobileCurrent = document.getElementById('current-card-stats-mobile');
    if (mobileCurrent && window.renderMobileCardStatsHtml) {
        const html = window.renderMobileCardStatsHtml(currentCardData.initial_stats, 0, currentCardData.content, true);
        mobileCurrent.innerHTML = html;
    }

    // [UX-RESET] Info Bar stats
    if (window.updateFlashcardStats && currentCardData.initial_stats) {
        const statsForReset = {
            statistics: {
                repetitions: currentCardData.initial_stats.repetitions,
                easiness_factor: currentCardData.initial_stats.easiness_factor,
                difficulty: currentCardData.initial_stats.difficulty,
                stability: currentCardData.initial_stats.stability,
                retrievability: currentCardData.initial_stats.retrievability,
                times_reviewed: currentCardData.initial_stats.times_reviewed
            },
            srs_data: {
                next_review: currentCardData.initial_stats.next_review || null
            },
            new_progress_status: currentCardData.initial_stats.status || currentCardData.initial_stats.custom_state || 'new'
        };
        window.updateFlashcardStats(statsForReset);
    }

    window.renderCard(currentCardData);

    // [ANIMATION] Enter Transition
    if (cardSurface) {
        cardSurface.classList.remove('card-transition-exit');
        cardSurface.classList.add('card-transition-enter');
        void cardSurface.offsetHeight; // Force reflow
        cardSurface.classList.add('card-transition-enter-active');

        setTimeout(() => {
            cardSurface.classList.remove('card-transition-enter', 'card-transition-enter-active');
        }, 200); // Match CSS 0.15s + buffer
    }

    // Card state badge
    const customState = currentCardData.initial_stats?.custom_state || 'new';
    window.updateStateBadge(customState);

    // Mobile UI
    const mobileBottomBar = document.querySelector('.fc-bottom-bar');
    if (mobileBottomBar) mobileBottomBar.style.display = '';

    currentCardStartTime = Date.now();
    window.updateSessionSummary();

    // Trigger audio prefetch for upcoming cards to stay ahead
    if (window.prefetchAudioForUpcomingCards) {
        // Prefetch more aggressively (2 cards ahead) to avoid gaps
        window.prefetchAudioForUpcomingCards(2);
    }

    // Session Stats Update
    const historyCount = (window.sessionAnswerHistory ? window.sessionAnswerHistory.length : 0);
    const initialCount = (window.FlashcardConfig && window.FlashcardConfig.initialProcessedCount) ? window.FlashcardConfig.initialProcessedCount : 0;
    sessionStatsLocal.processed = initialCount + historyCount + 1;
    // sessionStatsLocal.total is updated from batch fetch

    window.flashcardSessionStats = {
        progress: sessionStatsLocal.processed,
        processed: sessionStatsLocal.processed,
        total: sessionStatsLocal.total,
        correct: sessionStatsLocal.correct,
        incorrect: sessionStatsLocal.incorrect,
        vague: sessionStatsLocal.vague,
        session_score: sessionScore,

        // [FIX] Add FSRS stats to prevent overwrite with 0s
        difficulty: currentCardData.initial_stats ? currentCardData.initial_stats.difficulty : 0,
        stability: currentCardData.initial_stats ? currentCardData.initial_stats.stability : 0,
        retrievability: currentCardData.initial_stats ? currentCardData.initial_stats.retrievability : 0,
        repetitions: currentCardData.initial_stats ? (currentCardData.initial_stats.repetitions || 0) : 0,
        times_reviewed: currentCardData.initial_stats ? (currentCardData.initial_stats.times_reviewed || 0) : 0,
        status: currentCardData.initial_stats ? (currentCardData.initial_stats.status || 'new') : 'new'
    };
    document.dispatchEvent(new CustomEvent('flashcardStatsUpdated', { detail: window.flashcardSessionStats }));
}



// ... (inside renderNewBatchItems or wherever card is shown)
// Finding render rendering point is key. It's window.renderCard(currentCardData) at line 152.

async function submitFlashcardAnswer(itemId, answer) {
    if (window.hidePreviewTooltip) window.hidePreviewTooltip(true); // Force immediate hide
    if (isSubmitting) return; // Prevent double clicks

    isSubmitting = true;
    window.isSubmitLock = true; // [LOCK] Prevent tooltips from showing during transition

    // [SMART TRANSITION] 1. Immediate Action
    if (window.hideRatingButtons) window.hideRatingButtons();

    window.stopAllFlashcardAudio();

    // [NEW] Calculate duration
    const durationMs = currentCardStartTime > 0 ? (Date.now() - currentCardStartTime) : 0;
    try {
        let data;

        // ── [v2] Use Driver API if session is active ────────────
        if (_driverSessionId) {
            const submitUrl = `/session/api/${_driverSessionId}/submit`;
            const quality = _QUALITY_MAP[String(answer).toLowerCase()] || 3;

            const res = await fetch(submitUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...window.FlashcardConfig.csrfHeaders },
                body: JSON.stringify({ item_id: itemId, quality: quality, duration_ms: durationMs })
            });

            if (!res.ok) {
                const errorText = await res.text();
                throw new Error(`HTTP error! status: ${res.status}, body: ${errorText}`);
            }

            const driverResult = await res.json();

            // Map Driver result → legacy response shape
            data = {
                success: true,
                score_change: driverResult.score_change || 0,
                updated_total_score: currentUserTotalScore + (driverResult.score_change || 0),
                is_correct: driverResult.is_correct,
                new_progress_status: driverResult.feedback?.rated_quality >= 2 ? 'review' : 'learning',
                statistics: driverResult.srs_update || {},
                srs_data: driverResult.srs_update || {},
                answer_result: answer,
                gamification: driverResult.gamification || null
            };
        } else {
            // ── Legacy fallback ─────────────────────────────────
            const submitAnswerUrl = window.FlashcardConfig.submitAnswerUrl;
            const res = await fetch(submitAnswerUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...window.FlashcardConfig.csrfHeaders },
                body: JSON.stringify({ item_id: itemId, user_answer: answer, duration_ms: durationMs })
            });

            if (!res.ok) {
                const errorText = await res.text();
                throw new Error(`HTTP error! status: ${res.status}, body: ${errorText}`);
            }
            data = await res.json();
            // Legacy might not have gamification, defaults to null
        }

        sessionScore += data.score_change;
        currentUserTotalScore = data.updated_total_score;

        // [UX-IMMEDIATE] 3. Update Current Card Stats Immediately
        if (window.updateFlashcardStats) {
            window.updateFlashcardStats(data);
        }

        // [SMART TRANSITION] 2. Notification & Dynamic Wait
        let notificationPromise = Promise.resolve();

        if (data.score_change > 0 && window.showScoreToast) {
            // ONLY dispatch start if we are actually showing a toast
            document.dispatchEvent(new CustomEvent('notificationStart'));
            // Pass full gamification object if available, otherwise just number
            const toastInput = data.gamification || data.score_change;
            console.log('[ScoreToast] Triggering with:', toastInput);
            notificationPromise = window.showScoreToast(toastInput);
        }

        // Memory Power Notification (if distinct from Score)
        // If both exist, maybe chain them or show combined? 
        // For now, let's prioritize Score Toast as the main blocker.

        const previousCardContent = currentFlashcardBatch[currentFlashcardIndex].content;
        previousCardStats = {
            stats: data.statistics,
            scoreChange: data.score_change,
            cardContent: previousCardContent
        };

        // Push to session history for full stats display
        sessionAnswerHistory.push({
            front: previousCardContent.front,
            back: previousCardContent.back,
            answer: answer,
            scoreChange: data.score_change,
            stats: data.statistics,
            timestamp: Date.now()
        });

        const previousCardStatsContainer = document.getElementById('previous-card-stats');
        if (window.renderCardStatsHtml && previousCardStatsContainer) {
            const html = window.renderCardStatsHtml(data.statistics, data.score_change, previousCardContent, false);
            window.displayCardStats(previousCardStatsContainer, html);
        }

        const mobilePrev = document.getElementById('previous-card-stats-mobile');
        if (mobilePrev && window.renderMobileCardStatsHtml) {
            const mobileHtml = window.renderMobileCardStatsHtml(data.statistics, data.score_change, previousCardContent, false);
            mobilePrev.innerHTML = mobileHtml;
        }

        const prevTabButton = document.querySelector('.stats-tab-button[data-target="previous-card-stats-pane"]');
        if (prevTabButton) {
            prevTabButton.click();
        }

        // Update local stats based on answer
        const answerResult = String(data.answer_result || answer).toLowerCase();
        // Any SRS "pass" (quality >= 2) is considered correct in the HUD summary
        if (['good', 'easy', 'very_easy', 'nhớ', 'medium', 'hard', 'mơ_hồ'].includes(answerResult)) {
            sessionStatsLocal.correct++;
        } else if (['fail', 'again', 'quên'].includes(answerResult)) {
            sessionStatsLocal.incorrect++;
        } else {
            sessionStatsLocal.vague++;
        }    // Vague answers typically break streak or keep it? Let's keep it but not increment?
        // Or treat as break? Let's reset for now to be strict, or keep. 
        // Let's reset if it's not "correct".
        sessionStatsLocal.processed++;

        // Calculate Accuracy
        const totalAnswered = sessionStatsLocal.correct + sessionStatsLocal.incorrect + sessionStatsLocal.vague;
        const accuracy = totalAnswered > 0 ? Math.round((sessionStatsLocal.correct / totalAnswered) * 100) : 100;

        // Update window stats and dispatch event immediately
        window.flashcardSessionStats = {
            progress: sessionStatsLocal.processed,
            processed: sessionStatsLocal.processed,
            total: sessionStatsLocal.total,
            correct: sessionStatsLocal.correct,
            incorrect: sessionStatsLocal.incorrect,
            vague: sessionStatsLocal.vague,
            accuracy: accuracy,
            session_score: sessionScore,
            // Include card-specific stats (Box B)
            current_card_history_right: data.statistics ? data.statistics.correct_count : 0,
            current_card_history_wrong: data.statistics ? (data.statistics.incorrect_count + data.statistics.vague_count) : 0,
            // FSRS metrics (Required for HUD)
            difficulty: data.statistics ? data.statistics.difficulty : 0,
            stability: data.statistics ? data.statistics.stability : 0,
            retrievability: data.statistics ? data.statistics.retrievability : 0,
            status: data.new_progress_status || data.statistics?.status || 'new',
            repetitions: data.statistics ? (data.statistics.repetitions || 0) : 0,
            rating_counts: data.statistics?.rating_counts || { 1: 0, 2: 0, 3: 0, 4: 0 }
        };

        // Update HUD immediately for the card we just answered
        if (window.updateCardHudStats) {
            window.updateCardHudStats(data.statistics);
        }

        document.dispatchEvent(new CustomEvent('flashcardStatsUpdated', { detail: window.flashcardSessionStats }));

        // [SMART TRANSITION] 3. Wait for Notification to Finish (Dynamic Wait)
        // We increment the index and THEN wait for the notification to trigger displayCurrentCard
        currentFlashcardIndex++;

        // [OPTIMIZATION] Trigger background fetch if buffer needs refill
        // checking > because we just incremented. if index == length, we are out.
        const needsRefill = (currentFlashcardIndex >= currentFlashcardBatch.length);
        let backgroundFetchPromise = Promise.resolve();

        if (needsRefill && !isSessionEnding) {
            console.log('[Optimization] Buffer empty. Starting background fetch parallel with notification.');
            backgroundFetchPromise = ensureFlashcardBuffer(true);
        }

        // [UX-TUNING] Increase delay to keep old card visible specifically for 1.8s
        const smoothDelayPromise = new Promise(resolve => setTimeout(resolve, 1800));

        // Wait for BOTH (Fetch to complete) AND (Smooth Delay)
        await Promise.all([backgroundFetchPromise, smoothDelayPromise]);

        // Validate buffer state
        if (currentFlashcardIndex < currentFlashcardBatch.length) {
            // Ready to show - FORCE display over notification
            displayCurrentCard(true);
            // Trigger next refill immediately for the card AFTER this one
            ensureFlashcardBuffer();
        } else {
            // Still empty? (Network error or slow?) Fallback to standard flow
            await notificationPromise;

            if (!isSessionEnding) {
                await getNextFlashcardBatch();
            }
        }



        if (window.showRatingButtons) window.showRatingButtons();

        isSubmitting = false;
    } catch (e) {
        window.isSubmitLock = false; // [UNLOCK] on error
        console.error('Lỗi khi gửi đáp án:', e);
        if (window.showCustomAlert) window.showCustomAlert('Có lỗi khi gửi đáp án. Vui lòng thử lại.');
        if (window.showRatingButtons) window.showRatingButtons();
        isSubmitting = false;
    } finally {
        isSubmitting = false;
    }
}


async function updateFlashcardCard(itemId, setId) {
    const numericItemId = Number(itemId);
    const numericSetId = Number(setId);

    if (!Number.isInteger(numericItemId) || numericItemId <= 0) {
        const message = 'Không thể xác định thẻ cần cập nhật.';
        if (window.showFlashMessage) {
            window.showFlashMessage(message, 'warning');
        }
        throw new Error(message);
    }

    const flashcardItemApiUrlTemplate = window.FlashcardConfig.flashcardItemApiUrlTemplate;
    const apiUrl = flashcardItemApiUrlTemplate.replace('/0', `/${numericItemId}`);

    try {
        const response = await fetch(apiUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        let payload = null;

        try {
            payload = await response.json();
        } catch (parseError) {
            payload = null;
        }

        if (!response.ok || !payload || !payload.success || !payload.item) {
            const errorMessage = (payload && payload.message) ? payload.message : 'Không thể tải lại thẻ sau khi chỉnh sửa.';
            throw new Error(errorMessage);
        }

        const updatedItem = payload.item;

        if (Number.isInteger(numericSetId) && updatedItem.container_id !== numericSetId) {
            const message = 'Thẻ vừa chỉnh sửa không thuộc bộ hiện tại.';
            if (window.showFlashMessage) {
                window.showFlashMessage(message, 'warning');
            }
            return updatedItem;
        }

        const targetIndex = currentFlashcardBatch.findIndex(card => Number(card.item_id) === Number(updatedItem.item_id));

        if (targetIndex === -1) {
            const message = 'Không tìm thấy thẻ đang hiển thị trong phiên để cập nhật.';
            if (window.showFlashMessage) {
                window.showFlashMessage(message, 'info');
            }
            return updatedItem;
        }

        currentFlashcardBatch[targetIndex] = updatedItem;

        if (targetIndex === currentFlashcardIndex) {
            window.stopAllFlashcardAudio();
            window.renderCard(updatedItem);

            // Re-render stats
            const currentCardStatsContainer = document.getElementById('current-card-stats');
            if (window.renderCardStatsHtml && currentCardStatsContainer) {
                const html = window.renderCardStatsHtml(updatedItem.initial_stats, 0, updatedItem.content, true);
                window.displayCardStats(currentCardStatsContainer, html);
            }
        }

        return updatedItem;
    } catch (error) {
        console.error('Không thể tải lại thẻ sau khi chỉnh sửa:', error);
        if (window.showFlashMessage) {
            window.showFlashMessage(error.message || 'Không thể tải lại thẻ sau khi chỉnh sửa.', 'danger');
        }
        throw error;
    }
}

// --- Exports ---
window.currentFlashcardBatch = currentFlashcardBatch;
Object.defineProperty(window, 'currentFlashcardIndex', {
    get: () => currentFlashcardIndex,
    set: (v) => { currentFlashcardIndex = v; },
    configurable: true
});

Object.defineProperty(window, 'sessionScore', {
    get: () => sessionScore,
    set: (v) => { sessionScore = v; },
    configurable: true
});

Object.defineProperty(window, 'currentUserTotalScore', {
    get: () => currentUserTotalScore,
    set: (v) => { currentUserTotalScore = v; },
    configurable: true
});

window.previousCardStats = previousCardStats;
window.sessionAnswerHistory = sessionAnswerHistory;
window.getNextFlashcardBatch = getNextFlashcardBatch;
window.submitFlashcardAnswer = submitFlashcardAnswer;
window.updateFlashcardCard = updateFlashcardCard;
window.displayCurrentCard = displayCurrentCard;
window.ensureFlashcardBuffer = ensureFlashcardBuffer;
window.syncSettingsToServer = syncSettingsToServer;

// ── Driver session control ──────────────────────────────────────────
/**
 * Activate Driver-based session flow.
 * Called externally (e.g., from template or index.js) after starting
 * a driven session via POST /session/api/start.
 *
 * @param {number} sessionId - The DB session ID from start response.
 */
window.setDriverSessionId = function (sessionId) {
    _driverSessionId = sessionId;
    console.log('[Driver] Session activated, ID:', sessionId);
};
window.getDriverSessionId = function () {
    return _driverSessionId;
};

