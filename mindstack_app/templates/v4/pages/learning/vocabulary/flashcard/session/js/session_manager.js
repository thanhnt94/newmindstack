/**
 * Session Manager for Flashcard Session
 */

// Global State
let currentFlashcardBatch = [];
let currentFlashcardIndex = 0;
let previousCardStats = null;
let sessionScore = 0;
let currentUserTotalScore = 0;
let sessionAnswerHistory = [];
let currentStreak = 0;
let currentCardStartTime = 0;


// Local stats
let sessionStatsLocal = {
    processed: 0,
    total: 0,
    correct: 0,
    incorrect: 0,
    vague: 0
};

// --- Settings Sync ---

function syncSettingsToServer() {
    const saveSettingsUrl = window.FlashcardConfig.saveSettingsUrl;
    if (!saveSettingsUrl) return;

    // We need to read current state from UI/Audio managers
    // Assuming they export their state or we strictly use globals
    const isAudioAutoplayEnabled = window.isAudioAutoplayEnabled;
    const isMediaHidden = window.isMediaHidden;
    const showStats = window.showStats;

    const payload = {
        visual_settings: {
            autoplay: isAudioAutoplayEnabled,
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

// --- Batch Management ---

async function getNextFlashcardBatch() {
    window.stopAllFlashcardAudio();
    window.setFlashcardContent(`<div class="flex flex-col items-center justify-center h-full text-blue-500 min-h-[300px]"><i class="fas fa-spinner fa-spin text-4xl mb-3"></i><p>Đang tải thẻ...</p></div>`);

    const getFlashcardBatchUrl = window.FlashcardConfig.getFlashcardBatchUrl;

    try {
        const res = await fetch(getFlashcardBatchUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        if (!res.ok) {
            if (res.status === 404) {
                const end = await res.json();
                if (window.FlashcardConfig.isAutoplaySession) {
                    window.cancelAutoplaySequence();
                }
                window.setFlashcardContent(`<div class="text-center py-12 text-gray-600"><i class="fas fa-check-circle text-5xl text-green-500 mb-4"></i><h3 class="text-xl font-semibold text-gray-700 mb-2">Hoàn thành phiên học!</h3><p class="text-gray-500">${window.formatTextForHtml(end.message)}</p><button id="return-to-dashboard-btn" class="mt-6 px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 shadow-sm"><i class="fas fa-home mr-2"></i> Quay lại Dashboard</button></div>`);
                const dashboardUrl = window.FlashcardConfig.vocabDashboardUrl;
                document.getElementById('return-to-dashboard-btn').addEventListener('click', () => { window.location.href = dashboardUrl; });
                return;
            }
            throw new Error('HTTP ' + res.status);
        }
        const batch = await res.json();
        currentFlashcardBatch = batch.items;
        currentFlashcardIndex = 0;
        const currentCardData = currentFlashcardBatch[currentFlashcardIndex];

        // Stats Rendering
        const currentCardStatsContainer = document.getElementById('current-card-stats');
        // renderCardStatsHtml should be available globally from ui_manager but it was internal?
        // Ah, in previous file I forgot to export `renderCardStatsHtml`. 
        // I should have checked. It was `renderCardStatsHtml`.
        // Actually, `renderCardStatsHtml` was defined inside renderCard scope in the original file???
        // No, it was global in original.
        // I define it in `ui_manager.js`? Wait, I think I MISSED adding `renderCardStatsHtml` / `renderMobileCardStatsHtml` into `ui_manager.js`
        // I need to add them. They were quite long functions.
        // Let's assume for a moment I DID add them (or I will fix ui_manager in next step).
        // Actually looking at my previous tool call output... I DID NOT include `renderCardStatsHtml` in `ui_manager.js`.
        // I included `renderCard` and smaller functions.
        // I MUST fix `ui_manager.js` or define them here. They belong in UI Manager.

        // I will finish creating `session_manager.js` assuming they exist, and then I will APPENT/FIX `ui_manager.js`.

        // const initialStatsHtml = window.renderCardStatsHtml(currentCardData.initial_stats, 0, currentCardData.content, true);
        // window.displayCardStats(currentCardStatsContainer, initialStatsHtml);

        // const mobileCurrent = document.getElementById('current-card-stats-mobile');
        // if (mobileCurrent) {
        //     const mobileHtml = window.renderMobileCardStatsHtml(currentCardData.initial_stats, 0, currentCardData.content, true);
        //     mobileCurrent.innerHTML = mobileHtml;
        // }

        // Actually if I fix ui_manager, I can export a function `renderCurrentBatchStats` to encapsulation this.
        // But for now let's call the render functions.
        if (window.renderCardStatsHtml && currentCardStatsContainer) {
            const html = window.renderCardStatsHtml(currentCardData.initial_stats, 0, currentCardData.content, true);
            window.displayCardStats(currentCardStatsContainer, html);
        }

        const mobileCurrent = document.getElementById('current-card-stats-mobile');
        if (mobileCurrent && window.renderMobileCardStatsHtml) {
            const html = window.renderMobileCardStatsHtml(currentCardData.initial_stats, 0, currentCardData.content, true);
            mobileCurrent.innerHTML = html;
        }

        window.renderCard(currentCardData);
        currentCardStartTime = Date.now(); // [NEW] Start timer
        window.updateSessionSummary();

        // Update local session stats from batch
        sessionStatsLocal.processed = batch.session_processed_count || 1;
        sessionStatsLocal.total = batch.session_total_items || batch.total_items_in_session || 0;
        sessionStatsLocal.correct = batch.session_correct_answers || sessionStatsLocal.correct || 0;
        sessionStatsLocal.incorrect = batch.session_incorrect_answers || sessionStatsLocal.incorrect || 0;
        sessionStatsLocal.vague = batch.session_vague_answers || sessionStatsLocal.vague || 0;

        // [NEW] Restore session score from backend on page load
        if (batch.session_points !== undefined && batch.session_points > 0) {
            sessionScore = batch.session_points;
            console.log('[Session] Restored session_points from backend:', sessionScore);
        }

        // Update container name from batch
        if (batch.container_name) {
            document.querySelectorAll('.js-fc-title').forEach(el => {
                el.textContent = batch.container_name;
            });
        }

        // Expose stats to window for mobile view
        window.flashcardSessionStats = {
            progress: sessionStatsLocal.processed + '/' + sessionStatsLocal.total,
            processed: sessionStatsLocal.processed,
            total: sessionStatsLocal.total,
            correct: sessionStatsLocal.correct,
            incorrect: sessionStatsLocal.incorrect,
            vague: sessionStatsLocal.vague,
            session_score: sessionScore,
            // Stats for Box B (Current Card)
            current_card_mem_percent: currentCardData.initial_stats ? currentCardData.initial_stats.memory_power : 0,
            current_card_history_right: currentCardData.initial_stats ? currentCardData.initial_stats.correct_count : 0,
            current_card_history_wrong: currentCardData.initial_stats ? (currentCardData.initial_stats.incorrect_count + (currentCardData.initial_stats.vague_count || 0)) : 0
        };
        // Dispatch custom event for mobile stats update
        document.dispatchEvent(new CustomEvent('flashcardStatsUpdated', { detail: window.flashcardSessionStats }));

    } catch (e) {
        console.error('Lỗi khi tải nhóm thẻ:', e);
        window.setFlashcardContent(`<p class='text-red-500 text-center'>Không thể tải thẻ. Vui lòng thử lại.</p>`);
    }
}


// ... (inside renderNewBatchItems or wherever card is shown)
// Finding render rendering point is key. It's window.renderCard(currentCardData) at line 152.

async function submitFlashcardAnswer(itemId, answer) {
    window.stopAllFlashcardAudio();
    const submitAnswerUrl = window.FlashcardConfig.submitAnswerUrl;

    // [NEW] Calculate duration
    const durationMs = currentCardStartTime > 0 ? (Date.now() - currentCardStartTime) : 0;

    try {
        const res = await fetch(submitAnswerUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...window.FlashcardConfig.csrfHeaders },
            body: JSON.stringify({ item_id: itemId, user_answer: answer, duration_ms: durationMs })
        });
        // ...
        if (!res.ok) {
            const errorText = await res.text();
            throw new Error(`HTTP error! status: ${res.status}, body: ${errorText}`);
        }
        const data = await res.json();

        sessionScore += data.score_change;
        currentUserTotalScore = data.updated_total_score;

        // Gamified Notification
        let notificationPromise = Promise.resolve();

        if (data.score_change > 0 && typeof window.showScoreToast === 'function') {
            window.showScoreToast(data.score_change);
        }

        // Memory Power Notification - await its animation
        if (data.memory_power && typeof window.showMemoryPowerFeedback === 'function') {
            notificationPromise = window.showMemoryPowerFeedback(data.memory_power.old_memory_power, data.memory_power.memory_power);
        }

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
        const answerResult = data.answer_result || answer;
        if (['good', 'easy', 'very_easy', 'nhớ', 'medium'].includes(answerResult)) {
            sessionStatsLocal.correct++;
            window.currentStreak = (window.currentStreak || 0) + 1;
        } else if (['fail', 'again', 'quên'].includes(answerResult)) {
            sessionStatsLocal.incorrect++;
            window.currentStreak = 0;
        } else {
            sessionStatsLocal.vague++;
            // Vague answers typically break streak or keep it? Let's keep it but not increment?
            // Or treat as break? Let's reset for now to be strict, or keep. 
            // Let's reset if it's not "correct".
            window.currentStreak = 0;
        }
        sessionStatsLocal.processed++;

        // Calculate Accuracy
        const totalAnswered = sessionStatsLocal.correct + sessionStatsLocal.incorrect + sessionStatsLocal.vague;
        const accuracy = totalAnswered > 0 ? Math.round((sessionStatsLocal.correct / totalAnswered) * 100) : 100;

        // Update window stats and dispatch event immediately
        window.flashcardSessionStats = {
            progress: sessionStatsLocal.processed + '/' + sessionStatsLocal.total,
            processed: sessionStatsLocal.processed,
            total: sessionStatsLocal.total,
            correct: sessionStatsLocal.correct,
            incorrect: sessionStatsLocal.incorrect,
            vague: sessionStatsLocal.vague,
            streak: window.currentStreak,
            accuracy: accuracy,
            session_score: sessionScore,
            // Include card-specific stats (Box B)
            current_card_mem_percent: data.statistics ? data.statistics.memory_power : 0,
            current_card_history_right: data.statistics ? data.statistics.correct_count : 0,
            current_card_history_wrong: data.statistics ? (data.statistics.incorrect_count + data.statistics.vague_count) : 0
        };

        // Update HUD immediately for the card we just answered
        if (window.updateCardHudStats) {
            window.updateCardHudStats(data.statistics);
        }

        document.dispatchEvent(new CustomEvent('flashcardStatsUpdated', { detail: window.flashcardSessionStats }));

        currentFlashcardIndex++;

        // Wait for notification animation to complete before loading next card
        await notificationPromise;
        getNextFlashcardBatch();
    } catch (e) {
        console.error('Lỗi khi gửi đáp án:', e);
        if (window.showCustomAlert) window.showCustomAlert('Có lỗi khi gửi đáp án. Vui lòng thử lại.');
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

// Export 
window.syncSettingsToServer = syncSettingsToServer;
window.getNextFlashcardBatch = getNextFlashcardBatch;
window.submitFlashcardAnswer = submitFlashcardAnswer;
window.updateFlashcardCard = updateFlashcardCard;

// Global State Getters
Object.defineProperty(window, 'currentFlashcardBatch', {
    get: () => currentFlashcardBatch,
    configurable: true
});
Object.defineProperty(window, 'currentFlashcardIndex', {
    get: () => currentFlashcardIndex,
    configurable: true
});
Object.defineProperty(window, 'sessionScore', {
    get: () => sessionScore,
    set: (v) => sessionScore = v,
    configurable: true
});
Object.defineProperty(window, 'currentUserTotalScore', {
    get: () => currentUserTotalScore,
    set: (v) => currentUserTotalScore = v,
    configurable: true
});
Object.defineProperty(window, 'previousCardStats', {
    get: () => previousCardStats,
    configurable: true
});
Object.defineProperty(window, 'sessionAnswerHistory', { // Expose for mobile stats
    get: () => sessionAnswerHistory,
    configurable: true
});
