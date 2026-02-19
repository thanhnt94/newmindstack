// ============================================================
// Audio Manager — Clean Rewrite (v2)
// ============================================================
// State is ONLY persisted in localStorage. No server sync for autoplay.
// No Object.defineProperty. No master toggle. No UI update responsibility.
// ============================================================

// --- Global State ---
window.isAudioAutoplayFrontEnabled = true;
window.isAudioAutoplayBackEnabled = true;

// Internal variables
let currentAutoplayToken = 0;
let currentAutoplayTimeouts = [];
let autoplayDelaySeconds = 2;
let currentAudioStopVersion = 0;

// --- Simple Getters (no Object.defineProperty magic) ---
window.getAudioAutoplayEnabled = function () {
    return window.isAudioAutoplayFrontEnabled || window.isAudioAutoplayBackEnabled;
};
// Legacy alias — returns the computed master state, read-only semantics
Object.defineProperty(window, 'isAudioAutoplayEnabled', {
    get: () => window.isAudioAutoplayFrontEnabled || window.isAudioAutoplayBackEnabled,
    set: () => { /* no-op: use toggleSideAutoplay('front'/'back') instead */ },
    configurable: true
});

// --- Init: localStorage ONLY, server setting ignored ---
function initAudioSettings() {
    // Front
    try {
        const v = localStorage.getItem('flashcardAutoPlayFront');
        if (v !== null) window.isAudioAutoplayFrontEnabled = (v === 'true');
    } catch (_) { }

    // Back
    try {
        const v = localStorage.getItem('flashcardAutoPlayBack');
        if (v !== null) window.isAudioAutoplayBackEnabled = (v === 'true');
    } catch (_) { }

    // Delay
    try {
        const s = localStorage.getItem('flashcardAutoplaySettings');
        if (s) {
            const p = JSON.parse(s);
            if (p && typeof p.delaySeconds === 'number' && p.delaySeconds >= 0) {
                autoplayDelaySeconds = p.delaySeconds;
            }
        }
    } catch (_) { }

    console.log('[Audio] Settings initialized:', {
        front: window.isAudioAutoplayFrontEnabled,
        back: window.isAudioAutoplayBackEnabled
    });

    // Sync modal UI if it exists
    if (window.syncAudioModalUI) window.syncAudioModalUI();
}

// --- Persist to localStorage ---
function persistSideAutoplayPreference(side, enabled) {
    const key = side === 'front' ? 'flashcardAutoPlayFront' : 'flashcardAutoPlayBack';
    try { localStorage.setItem(key, enabled ? 'true' : 'false'); } catch (_) { }
}

// --- Set Side (the ONLY way to change autoplay state) ---
function setSideAutoplayEnabled(side, enabled) {
    console.log(`[Audio] setSideAutoplayEnabled(${side}, ${enabled})`);
    if (side === 'front') {
        window.isAudioAutoplayFrontEnabled = !!enabled;
    } else {
        window.isAudioAutoplayBackEnabled = !!enabled;
    }
    persistSideAutoplayPreference(side, !!enabled);
    // Sync modal UI if open
    if (window.syncAudioModalUI) window.syncAudioModalUI();
}

// --- Toggle Side ---
window.toggleSideAutoplay = function (side) {
    const cur = side === 'front' ? window.isAudioAutoplayFrontEnabled : window.isAudioAutoplayBackEnabled;
    setSideAutoplayEnabled(side, !cur);
};

// --- Legacy compat: setAudioAutoplayEnabled → toggles BOTH sides ---
function setAudioAutoplayEnabled(enabled) {
    setSideAutoplayEnabled('front', !!enabled);
    setSideAutoplayEnabled('back', !!enabled);
    if (!enabled) stopAllFlashcardAudio();
}

// Legacy toggle
window.toggleAudioAutoplay = function () {
    const cur = window.getAudioAutoplayEnabled();
    setAudioAutoplayEnabled(!cur);
};

// [NEW] Helper for robust side detection
function getCurrentVisibleSide() {
    const visibleContainer = window.getVisibleFlashcardContentDiv ? window.getVisibleFlashcardContentDiv() : document;
    const card = visibleContainer.querySelector('.js-flashcard-card') || document.querySelector('.js-flashcard-card');

    if (!card) return 'front'; // Fallback

    const isFlipped = card.classList.contains('flipped')
        || card.classList.contains('is-flipped')
        || (card.querySelector('.flashcard-inner') && card.querySelector('.flashcard-inner').classList.contains('is-flipped'));

    return isFlipped ? 'back' : 'front';
}

function playAudioAfterLoad(audioPlayer, { restart = true, awaitCompletion = false } = {}) {
    return new Promise(resolve => {
        if (!audioPlayer) {
            resolve();
            return;
        }

        const startedAtVersion = currentAudioStopVersion;

        const updateAudioUI = (isPlaying) => {
            // 1. Update Mobile Overlay Icon
            const icon = document.querySelector('.js-fc-audio-icon-overlay');
            if (icon) {
                if (isPlaying) {
                    icon.classList.remove('fa-volume-high', 'fa-volume-low', 'fa-volume-up', 'fa-volume-xmark');
                    icon.classList.add('fa-pause', 'animate-pulse');
                } else {
                    icon.classList.remove('fa-pause', 'animate-pulse');
                    // Reset based on state
                    const btn = document.querySelector('.js-fc-audio-btn-overlay');
                    const hasAudio = btn && btn.dataset.hasAudio === 'true';
                    icon.classList.add(hasAudio ? 'fa-volume-high' : 'fa-volume-xmark');
                }
            }

            // 2. Update all associated play buttons on the card/panel
            const audioId = audioPlayer.getAttribute('id');
            if (audioId) {
                const buttons = document.querySelectorAll(`.play-audio-btn[data-audio-target="#${audioId}"]`);
                buttons.forEach(btn => {
                    if (isPlaying) {
                        if (!btn.dataset.originalHtml) {
                            btn.dataset.originalHtml = btn.innerHTML;
                        }
                        btn.innerHTML = '<i class="fas fa-pause animate-pulse"></i>';
                    } else {
                        btn.innerHTML = btn.dataset.originalHtml || '<i class="fas fa-volume-up"></i>';
                    }
                });
            }
        };

        const onPlaying = () => updateAudioUI(true);
        const onPause = () => updateAudioUI(false);

        const cleanup = () => {
            audioPlayer.removeEventListener('canplay', onCanPlay);
            audioPlayer.removeEventListener('playing', onPlaying);
            audioPlayer.removeEventListener('pause', onPause);
            audioPlayer.removeEventListener('ended', handleFinish);
            audioPlayer.removeEventListener('error', handleFinish);
        };

        const handleFinish = () => {
            updateAudioUI(false);
            cleanup();
            resolve();
        };

        const onCanPlay = () => {
            audioPlayer.removeEventListener('canplay', onCanPlay);

            if (startedAtVersion !== currentAudioStopVersion) {
                cleanup();
                resolve();
                return;
            }

            audioPlayer.addEventListener('playing', onPlaying);
            audioPlayer.addEventListener('pause', onPause);
            audioPlayer.addEventListener('ended', handleFinish, { once: true });
            audioPlayer.addEventListener('error', handleFinish, { once: true });

            if (restart) {
                try {
                    audioPlayer.pause();
                    audioPlayer.currentTime = 0;
                } catch (err) {
                    console.warn('Không thể đặt lại audio:', err);
                }
            }
            if (audioPlayer.src) {
                console.log(`[Audio] 🔊 Playing: ${audioPlayer.src}`);
            }

            const playPromise = audioPlayer.play();
            if (!awaitCompletion) {
                // We don't cleanup() here anymore because we need 
                // onPlaying/onPause/handleFinish to update the overlay icon.
                // They will call cleanup() when the audio actually stops.
                if (playPromise && typeof playPromise.catch === 'function') {
                    playPromise.catch(() => { });
                }
                resolve();
            } else if (playPromise && typeof playPromise.catch === 'function') {
                playPromise.catch(() => {
                    cleanup();
                    resolve();
                });
            }
        };

        // Always listen for end/error to cleanup and reset icon, even if !awaitCompletion
        audioPlayer.addEventListener('ended', handleFinish, { once: true });
        audioPlayer.addEventListener('error', handleFinish, { once: true });

        if (audioPlayer.readyState >= 2) {
            onCanPlay();
        } else {
            audioPlayer.addEventListener('canplay', onCanPlay);
            try {
                audioPlayer.load();
            } catch (err) {
                cleanup();
                resolve();
            }
        }
    });
}

function stopAllFlashcardAudio(exceptAudio = null) {
    currentAudioStopVersion++;
    const audioElements = document.querySelectorAll('audio'); // Target ALL audio elements, even if not marked hidden
    // console.log(`[Audio] Stopping all audio (count: ${audioElements.length}), except:`, exceptAudio ? exceptAudio.id : 'none');
    audioElements.forEach(audioEl => {
        // Clear manual retrigger flag on EVERY stop/reset
        if (audioEl.dataset) {
            audioEl.dataset.manualRetrigger = 'false';
        }

        if (exceptAudio && audioEl === exceptAudio) {
            return;
        }
        try {
            if (!audioEl.paused) {
                audioEl.pause();
            }
            audioEl.currentTime = 0;
        } catch (err) {
            console.warn('Không thể dừng audio:', err);
        }
    });
}

async function generateAndPlayAudio(button, audioPlayer, options = {}) {
    const itemId = button.dataset.itemId;
    const side = button.dataset.side;
    const contentToRead = button.dataset.contentToRead;
    const awaitCompletion = options.awaitCompletion === true;
    const suppressLoadingUi = options.suppressLoadingUi === true;
    const restart = options.restart !== false;

    const originalHtml = button.dataset.originalHtml || button.innerHTML;
    if (!button.dataset.originalHtml) {
        button.dataset.originalHtml = originalHtml;
    }

    if (!suppressLoadingUi) {
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }

    button.classList.add('is-disabled');
    let playbackPromise = Promise.resolve();

    const regenerateAudioUrl = window.FlashcardConfig ? window.FlashcardConfig.regenerateAudioUrl : '';
    const csrfHeaders = window.FlashcardConfig ? window.FlashcardConfig.csrfHeaders : {};

    try {
        const response = await fetch(regenerateAudioUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...csrfHeaders },
            body: JSON.stringify({ item_id: itemId, side: side, content_to_read: contentToRead })
        });
        const result = await response.json();
        if (result.success && result.audio_url) {
            const cacheBustedUrl = `${result.audio_url}${result.audio_url.includes('?') ? '&' : '?'}t=${Date.now()}`;
            console.log(`[Audio] Generated new audio: ${cacheBustedUrl}`);
            audioPlayer.src = cacheBustedUrl;
            playbackPromise = playAudioAfterLoad(audioPlayer, { restart, awaitCompletion });
            if (awaitCompletion) {
                await playbackPromise;
            }
        } else {
            // [SUPPRESSED] if (window.showCustomAlert) window.showCustomAlert(result.message || 'Lỗi khi tạo audio.');
            console.warn('[Audio] Failed to generate audio:', result.message);
        }
    } catch (error) {
        console.error('Lỗi khi tạo audio:', error);
        // [SUPPRESSED] if (window.showCustomAlert) window.showCustomAlert('Không thể kết nối đến máy chủ để tạo audio.');
        console.error('Lỗi khi tải audio:', error);
    } finally {
        button.classList.remove('is-disabled');
        if (!suppressLoadingUi) {
            button.innerHTML = button.dataset.originalHtml || '<i class="fas fa-volume-up"></i>';
        }
    }

    return playbackPromise;
}

function playAudioForButton(button, options = {}) {
    if (!button) return Promise.resolve();

    // ⭐ [FIX] Scope the search for the audio player to the nearest container if possible
    // This prevents picking up stale audio elements from previous cards during transitions
    const targetSelector = button.dataset.audioTarget;
    let audioPlayer = null;

    // Try to find within the same flashcard container first
    const container = button.closest('.js-flashcard-card') || button.closest('.flashcard-panel');
    if (container) {
        audioPlayer = container.querySelector(targetSelector);
    }

    // Fallback to global if not found (though should be in container)
    if (!audioPlayer) {
        audioPlayer = document.querySelector(targetSelector);
    }

    const awaitCompletion = options.await === true;
    const restart = options.restart !== false;
    const suppressLoadingUi = options.suppressLoadingUi === true;
    const force = options.force === true;
    const hasAudioSource = audioPlayer && audioPlayer.src && audioPlayer.src !== window.location.href;

    // ⭐ Mark as manual retrigger to ensure it plays after regeneration even if autoplay is OFF
    if (audioPlayer) audioPlayer.dataset.manualRetrigger = 'true';

    if (!audioPlayer || (button.classList.contains('is-disabled') && !force)) {
        return Promise.resolve();
    }

    // Ensure original HTML is saved before any changes (spinner or icon swap)
    if (!button.dataset.originalHtml) {
        button.dataset.originalHtml = button.innerHTML;
    }

    if (hasAudioSource) {
        stopAllFlashcardAudio(audioPlayer);
        // Add cache buster if not present
        if (!audioPlayer.src.includes('t=')) {
            const separator = audioPlayer.src.includes('?') ? '&' : '?';
            audioPlayer.src = `${audioPlayer.src}${separator}t=${Date.now()}`;
        }
        return playAudioAfterLoad(audioPlayer, { restart, awaitCompletion });
    }

    stopAllFlashcardAudio(audioPlayer);
    return generateAndPlayAudio(button, audioPlayer, { awaitCompletion, suppressLoadingUi, restart });
}

async function handleAudioError(audioEl, itemId, side, contentToRead) {
    if (!audioEl || audioEl.dataset.retried === 'true') return;
    if (!contentToRead) return;

    const sideLabel = side === 'front' ? '🔵 MẶT TRƯỚC' : '🔴 MẶT SAU';
    console.log(`[AudioRecovery] ${sideLabel} - Phát hiện lỗi audio, đang tái tạo...`);

    audioEl.dataset.retried = 'true';

    const regenerateAudioUrl = window.FlashcardConfig ? window.FlashcardConfig.regenerateAudioUrl : '';
    const csrfHeaders = window.FlashcardConfig ? window.FlashcardConfig.csrfHeaders : {};

    try {
        const response = await fetch(regenerateAudioUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...csrfHeaders },
            body: JSON.stringify({ item_id: itemId, side: side, content_to_read: contentToRead })
        });
        const result = await response.json();

        if (result.success && result.audio_url) {
            console.log(`[AudioRecovery] ${sideLabel} - ✅ Tái tạo thành công!`);

            // Check if this was a manual request OR autoplay is enabled
            const isManualRetrigger = audioEl.dataset.manualRetrigger === 'true';
            // Important: Clear the flag immediately so it doesn't affect subsequent cards
            audioEl.dataset.manualRetrigger = 'false';

            // CRITICAL: Set new src AND reload the audio element
            audioEl.src = `${result.audio_url}?t=${new Date().getTime()}`;
            audioEl.load(); // ⭐ Force browser to reload the audio source

            // ⭐ RE-ENABLE THE BUTTONS for this side
            const buttons = document.querySelectorAll(`.play-audio-btn[data-side="${side}"]`);
            buttons.forEach(btn => {
                btn.classList.remove('is-disabled');
                btn.disabled = false;
                btn.dataset.hasAudio = 'true';
                // If it's a mobile overlay icon, we might need more logic, but classList.remove('is-disabled') usually covers it
            });

            // ⭐ Auto-play if autoplay is enabled OR it was a manual request
            if (isAudioAutoplayEnabled || isManualRetrigger) {
                // [FIX] Use robust side detection
                const currentVisibleSide = getCurrentVisibleSide();

                // [NEW] Check side-specific autoplay setting
                const sideAutoplayEnabled = (side === 'front' ? isAudioAutoplayFrontEnabled : isAudioAutoplayBackEnabled);
                const shouldAutoPlay = isManualRetrigger || (isAudioAutoplayEnabled && sideAutoplayEnabled);

                if (side === currentVisibleSide && shouldAutoPlay) {
                    console.log(`[AudioRecovery] ${sideLabel} - 🔊 Phát audio sau tái tạo (Autoplay: ${isAudioAutoplayEnabled}, Manual: ${isManualRetrigger})`);
                    audioEl.addEventListener('canplay', function onCanPlay() {
                        audioEl.removeEventListener('canplay', onCanPlay);
                        audioEl.play().catch(err => {
                            if (err.name === 'NotAllowedError') {
                                console.warn('[AudioRecovery] Autoplay blocked, waiting for interaction...');
                                // Add one-time listener to document to resume audio on interaction
                                const resumeAudio = () => {
                                    audioEl.play().catch(e => console.error('[AudioRecovery] Interaction play failed:', e));
                                    document.removeEventListener('click', resumeAudio);
                                    document.removeEventListener('touchstart', resumeAudio);
                                };
                                document.addEventListener('click', resumeAudio);
                                document.addEventListener('touchstart', resumeAudio);
                            } else {
                                console.warn('[AudioRecovery] Autoplay failed:', err);
                            }
                        });
                    }, { once: true });
                } else {
                    console.log(`[AudioRecovery] ${sideLabel} - ⏸️ Không phát (đang ở mặt ${currentVisibleSide})`);
                }
            }
        } else {
            console.warn(`[AudioRecovery] ${sideLabel} - ❌ Tái tạo thất bại: ${result.message}`);
        }
    } catch (err) {
        console.error(`[AudioRecovery] ${sideLabel} - ❌ Lỗi kết nối API:`, err);
    }
}

// ⭐ NEW: Prefetch audio for upcoming cards in the queue
async function prefetchAudioForUpcomingCards(count = 3) {
    // [DISABLED] User requested to ignore audio cache/prefetching
    // console.log('[AudioPrefetch] Disabled by user request');
}

function setupAudioErrorHandler(itemId, frontContent, backContent) {
    const audioIds = [
        'front-audio-desktop', 'back-audio-desktop',
        'front-audio-mobile', 'back-audio-mobile'
    ];

    audioIds.forEach(id => {
        const audioEl = document.getElementById(id);
        if (audioEl) {
            const isFront = id.includes('front');
            const content = isFront ? frontContent : backContent;
            const side = isFront ? 'front' : 'back';
            // Remove previous listeners to avoid duplicates if re-rendering
            // Note: anonymous functions can't be removed easily, but since we re-render the audio tag entirely usually, it might be fine.
            // But if audio tags are static and recycled, we need to be careful.
            // Here we assume audio tags might be in the partials that get re-rendered.

            // Allow one-time error handler per render
            audioEl.onerror = () => handleAudioError(audioEl, itemId, side, content);
        }
    });

    // ⭐ NEW: Trigger prefetch for upcoming cards (non-blocking)
    setTimeout(() => prefetchAudioForUpcomingCards(3), 100);
}

// --- Autoplay Logic ---

function autoPlaySide(side, retryCount = 0, force = false) {
    console.log('[Audio] autoPlaySide requested for:', side, 'Enabled:', isAudioAutoplayEnabled, 'Force:', force, 'Retry:', retryCount);

    // [NEW] Granular check
    const sideAutoplayEnabled = (side === 'front' ? isAudioAutoplayFrontEnabled : isAudioAutoplayBackEnabled);
    if (!force && (!isAudioAutoplayEnabled || !sideAutoplayEnabled)) return;

    // ⭐ [FIX] Strictly use the active container to avoid picking up stale cards
    const visibleContainer = document.querySelector('.is-active-card-container') ||
        (window.getVisibleFlashcardContentDiv ? window.getVisibleFlashcardContentDiv() : document);

    const button = visibleContainer.querySelector(`.play-audio-btn[data-side="${side}"]`);

    if (!button) {
        if (retryCount < 10) {
            console.log(`[Audio] Button not found for ${side}, retrying (${retryCount + 1})...`);
            setTimeout(() => autoPlaySide(side, retryCount + 1, force), 50);
            return;
        }
        console.warn('[Audio] AutoPlay button not found for side:', side, 'in container:', visibleContainer, 'after retries');
        return;
    }
    console.log('[Audio] AutoPlay triggering for button:', button);
    playAudioForButton(button, { suppressLoadingUi: true, force: force }).catch(err => console.error('[Audio] AutoPlay error:', err));
}

function autoPlayFrontSide() {
    autoPlaySide('front');
}

function autoPlayBackSide() {
    autoPlaySide('back');
}

function cancelAutoplaySequence() {
    currentAutoplayToken += 1;
    currentAutoplayTimeouts.forEach(timeoutId => clearTimeout(timeoutId));
    currentAutoplayTimeouts = [];
    stopAllFlashcardAudio();
}

function waitForAutoplayDelay(token) {
    return new Promise(resolve => {
        const delayMs = Math.max(0, autoplayDelaySeconds) * 1000;
        if (delayMs === 0) {
            resolve();
            return;
        }
        const timeoutId = setTimeout(() => {
            currentAutoplayTimeouts = currentAutoplayTimeouts.filter(id => id !== timeoutId);
            if (token === currentAutoplayToken) {
                resolve();
            }
        }, delayMs);
        currentAutoplayTimeouts.push(timeoutId);
    });
}

async function playAutoplayAudioForSide(side, token) {
    if (token !== currentAutoplayToken) return;

    // ⭐ [FIX] Strictly use the active container
    const visibleContainer = document.querySelector('.is-active-card-container') ||
        (window.getVisibleFlashcardContentDiv ? window.getVisibleFlashcardContentDiv() : document);

    let button = null;
    let retries = 0;

    while (!button && retries < 10) {
        if (token !== currentAutoplayToken) return;

        button = visibleContainer.querySelector(`.play-audio-btn[data-side="${side}"]`);

        if (!button) {
            retries++;
            await new Promise(r => setTimeout(r, 50));
        }
    }

    if (!button) {
        console.warn('Không tìm thấy nút audio tự động cho side:', side);
        return;
    }
    try {
        await playAudioForButton(button, { await: true, suppressLoadingUi: true });
    } catch (err) {
        console.warn('Không thể phát audio tự động:', err);
    }
}

async function startAutoplaySequence() {
    cancelAutoplaySequence();
    const token = currentAutoplayToken;
    try {
        await playAutoplayAudioForSide('front', token);
        if (token !== currentAutoplayToken) return;
        await waitForAutoplayDelay(token);
        if (token !== currentAutoplayToken) return;

        // This function should be defined in session/ui manager or we need to dispatch event/call callback
        if (window.revealBackSideForAutoplay) {
            window.revealBackSideForAutoplay(token);
        } else {
            console.warn("Missing window.revealBackSideForAutoplay");
            return;
        }

        await playAutoplayAudioForSide('back', token);
        if (token !== currentAutoplayToken) return;
        await waitForAutoplayDelay(token);
        if (token !== currentAutoplayToken) return;

        if (window.getNextFlashcardBatch) {
            window.getNextFlashcardBatch();
        }
    } catch (err) {
        console.warn('AutoPlay gặp lỗi:', err);
    }
}


// Export to global
window.initAudioSettings = initAudioSettings;
window.setAudioAutoplayEnabled = setAudioAutoplayEnabled;
window.stopAllFlashcardAudio = stopAllFlashcardAudio;
window.playAudioForButton = playAudioForButton;
window.setupAudioErrorHandler = setupAudioErrorHandler;
window.autoPlayFrontSide = autoPlayFrontSide;
window.autoPlayBackSide = autoPlayBackSide;
window.autoPlaySide = autoPlaySide;
window.startAutoplaySequence = startAutoplaySequence;
window.cancelAutoplaySequence = cancelAutoplaySequence;
window.autoplayDelaySeconds = autoplayDelaySeconds;
window.currentAutoplayToken = currentAutoplayToken; // used by revealBackSide dependencies
window.prefetchAudioForUpcomingCards = prefetchAudioForUpcomingCards;
window.setSideAutoplayEnabled = setSideAutoplayEnabled;
window.getCurrentVisibleSide = getCurrentVisibleSide;
