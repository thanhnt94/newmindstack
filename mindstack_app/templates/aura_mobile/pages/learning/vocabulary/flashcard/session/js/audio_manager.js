/**
 * Audio Manager for Flashcard Session
 */

// Global State for Audio
let isAudioAutoplayEnabled = true;
let currentAutoplayToken = 0;
let currentAutoplayTimeouts = [];
let autoplayDelaySeconds = 2;

// Load autoplay settings from localStorage or config
function initAudioSettings() {
    // Try to load from visualSettings global if available, otherwise localStorage
    const visualSettings = window.FlashcardConfig ? window.FlashcardConfig.visualSettings : {};

    if (visualSettings && visualSettings.autoplay !== undefined) {
        isAudioAutoplayEnabled = (visualSettings.autoplay === true);
    } else {
        try {
            const storedAudioAutoplay = localStorage.getItem('flashcardAutoPlayAudio');
            if (storedAudioAutoplay === 'false') isAudioAutoplayEnabled = false;
        } catch (err) {
            console.warn('Không thể đọc localStorage:', err);
        }
    }

    // Autoplay Delay settings
    try {
        const storedSettings = localStorage.getItem('flashcardAutoplaySettings');
        if (storedSettings) {
            const parsedSettings = JSON.parse(storedSettings);
            if (parsedSettings && typeof parsedSettings.delaySeconds === 'number' && parsedSettings.delaySeconds >= 0) {
                autoplayDelaySeconds = parsedSettings.delaySeconds;
            }
        }
    } catch (err) {
        console.warn('Không thể đọc cấu hình AutoPlay:', err);
    }
    window.isAudioAutoplayEnabled = isAudioAutoplayEnabled;
}

function persistAudioAutoplayPreference(enabled) {
    try {
        localStorage.setItem('flashcardAutoPlayAudio', enabled ? 'true' : 'false');
    } catch (err) {
        console.warn('Không thể lưu cấu hình tự động phát audio:', err);
    }
}

function updateAudioAutoplayToggleButtons() {
    const isEnabled = isAudioAutoplayEnabled;
    document.querySelectorAll('.audio-autoplay-toggle-btn').forEach((btn) => {
        btn.classList.toggle('is-active', isEnabled);
        btn.setAttribute('aria-pressed', isEnabled ? 'true' : 'false');
        btn.title = isEnabled ? 'Tắt tự động phát audio' : 'Bật tự động phát audio';
        const icon = btn.querySelector('i');
        if (icon) {
            icon.className = `fas ${isEnabled ? 'fa-volume-up' : 'fa-volume-mute'}`;
        }
    });

    // Update overlay badge
    const badge = document.querySelector('.js-fc-autoplay-badge');
    if (badge) {
        if (isEnabled) {
            badge.classList.remove('scale-0');
            badge.classList.add('scale-100');
        } else {
            badge.classList.remove('scale-100');
            badge.classList.add('scale-0');
        }
    }
}

function setAudioAutoplayEnabled(enabled) {
    isAudioAutoplayEnabled = enabled;
    window.isAudioAutoplayEnabled = enabled; // Update global state
    persistAudioAutoplayPreference(enabled);
    updateAudioAutoplayToggleButtons();
    if (!enabled) {
        stopAllFlashcardAudio();
    }
    if (window.syncSettingsToServer) {
        window.syncSettingsToServer();
    }
}

function playAudioAfterLoad(audioPlayer, { restart = true, awaitCompletion = false } = {}) {
    return new Promise(resolve => {
        if (!audioPlayer) {
            resolve();
            return;
        }

        const updateOverlayIcon = (isPlaying) => {
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
        };

        const onPlaying = () => updateOverlayIcon(true);
        const onPause = () => updateOverlayIcon(false);

        const cleanup = () => {
            audioPlayer.removeEventListener('canplay', onCanPlay);
            audioPlayer.removeEventListener('playing', onPlaying);
            audioPlayer.removeEventListener('pause', onPause);
            audioPlayer.removeEventListener('ended', handleFinish);
            audioPlayer.removeEventListener('error', handleFinish);
        };

        const handleFinish = () => {
            updateOverlayIcon(false);
            cleanup();
            resolve();
        };

        const onCanPlay = () => {
            audioPlayer.removeEventListener('canplay', onCanPlay);
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
    const audioElements = document.querySelectorAll('audio.hidden');
    // console.log(`[Audio] Stopping all audio (count: ${audioElements.length}), except:`, exceptAudio ? exceptAudio.id : 'none');
    audioElements.forEach(audioEl => {
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
            audioPlayer.src = result.audio_url;
            playbackPromise = playAudioAfterLoad(audioPlayer, { restart, awaitCompletion });
            if (awaitCompletion) {
                await playbackPromise;
            }
        } else {
            if (window.showCustomAlert) window.showCustomAlert(result.message || 'Lỗi khi tạo audio.');
        }
    } catch (error) {
        console.error('Lỗi khi tạo audio:', error);
        if (window.showCustomAlert) window.showCustomAlert('Không thể kết nối đến máy chủ để tạo audio.');
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
    // console.log('[Audio] Request play for button:', button);
    const audioPlayer = document.querySelector(button.dataset.audioTarget);
    // console.log('[Audio] Found player:', audioPlayer ? audioPlayer.id : 'NONE', 'Target:', button.dataset.audioTarget);

    if (!audioPlayer || button.classList.contains('is-disabled')) {
        return Promise.resolve();
    }

    const awaitCompletion = options.await === true;
    const restart = options.restart !== false;
    const suppressLoadingUi = options.suppressLoadingUi === true;
    const hasAudioSource = audioPlayer.src && audioPlayer.src !== window.location.href;

    if (hasAudioSource) {
        stopAllFlashcardAudio(audioPlayer);
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

            // CRITICAL: Set new src AND reload the audio element
            audioEl.src = `${result.audio_url}?t=${new Date().getTime()}`;
            audioEl.load(); // ⭐ Force browser to reload the audio source
        } else {
            console.warn(`[AudioRecovery] ${sideLabel} - ❌ Tái tạo thất bại: ${result.message}`);
        }
    } catch (err) {
        console.error(`[AudioRecovery] ${sideLabel} - ❌ Lỗi kết nối API:`, err);
    }
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
}

// --- Autoplay Logic ---

function autoPlaySide(side) {
    if (!isAudioAutoplayEnabled) return;

    // Tìm button trong container hiển thị (desktop hoặc mobile)
    const visibleContainer = window.getVisibleFlashcardContentDiv ? window.getVisibleFlashcardContentDiv() : document;
    // console.log('[Audio] AutoPlay side:', side);

    const button = visibleContainer.querySelector
        ? visibleContainer.querySelector(`.play-audio-btn[data-side="${side}"]`)
        : document.querySelector(`.play-audio-btn[data-side="${side}"]`);

    if (!button) {
        console.warn('[Audio] AutoPlay button not found for side:', side);
        return;
    }
    playAudioForButton(button, { suppressLoadingUi: true }).catch(err => console.error('[Audio] AutoPlay error:', err));
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

    // Tìm button trong container hiển thị (desktop hoặc mobile)
    const visibleContainer = window.getVisibleFlashcardContentDiv ? window.getVisibleFlashcardContentDiv() : document;
    const button = visibleContainer.querySelector
        ? visibleContainer.querySelector(`.play-audio-btn[data-side="${side}"]`)
        : document.querySelector(`.play-audio-btn[data-side="${side}"]`);

    if (!button) return;
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
window.isAudioAutoplayEnabled = isAudioAutoplayEnabled; // Getter might be needed, or property access
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

// Add simple getters mainly for external checks if needed
/*
Object.defineProperty(window, 'isAudioAutoplayEnabled', {
    get: () => isAudioAutoplayEnabled,
    set: (val) => { isAudioAutoplayEnabled = val; }, // Allow setter
    configurable: true
});
*/
