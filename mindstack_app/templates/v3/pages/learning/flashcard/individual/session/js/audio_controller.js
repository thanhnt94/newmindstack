/**
 * Audio Controller for Flashcard Session
 * Handles audio playback, autoplay sequences, and error recovery.
 */
window.FlashcardAudioController = (function () {
    let currentAutoplayToken = 0;
    let currentAutoplayTimeouts = [];

    /**
     * Stop all audio elements in the flashcard session.
     * @param {Object} options - { exceptAudio: AudioElement, selector: string }
     */
    function stopAllAudio(options = {}) {
        const selector = options.selector || 'audio.hidden, .js-flashcard-content audio';
        const audioElements = document.querySelectorAll(selector);

        // console.log(`[AudioController] Stopping all audio (count: ${audioElements.length})`);

        audioElements.forEach(audioEl => {
            if (options.exceptAudio && audioEl === options.exceptAudio) {
                return;
            }
            try {
                if (!audioEl.paused) {
                    audioEl.pause();
                }
                audioEl.currentTime = 0;
            } catch (err) {
                console.warn('[AudioController] Error stopping audio:', err);
            }
        });
    }

    /**
     * Play audio after ensuring it's loaded.
     * @param {HTMLAudioElement} audioPlayer 
     * @param {Object} options - { restart: boolean, awaitCompletion: boolean }
     */
    function playAudioAfterLoad(audioPlayer, { restart = true, awaitCompletion = false } = {}) {
        return new Promise(resolve => {
            if (!audioPlayer) {
                resolve();
                return;
            }

            const cleanup = () => {
                audioPlayer.removeEventListener('canplay', onCanPlay);
                if (awaitCompletion) {
                    audioPlayer.removeEventListener('ended', onEnded);
                    audioPlayer.removeEventListener('error', onError);
                }
            };

            const onEnded = () => {
                cleanup();
                resolve();
            };

            const onError = () => {
                cleanup();
                resolve();
            };

            const onCanPlay = () => {
                audioPlayer.removeEventListener('canplay', onCanPlay);
                if (restart) {
                    try {
                        audioPlayer.pause();
                        audioPlayer.currentTime = 0;
                    } catch (err) {
                        console.warn('[AudioController] Could not reset audio:', err);
                    }
                }
                const playPromise = audioPlayer.play();
                if (!awaitCompletion) {
                    cleanup();
                    if (playPromise && typeof playPromise.catch === 'function') {
                        playPromise.catch(() => { });
                    }
                    resolve();
                } else if (playPromise && typeof playPromise.catch === 'function') {
                    playPromise.catch(err => {
                        // console.warn('[AudioController] Play interrupted or failed:', err);
                        cleanup();
                        resolve();
                    });
                }
            };

            if (awaitCompletion) {
                audioPlayer.addEventListener('ended', onEnded, { once: true });
                audioPlayer.addEventListener('error', onError, { once: true });
            }

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

    /**
     * Generate audio from text (TTS) and play it.
     * Use this when audio_url is missing.
     */
    async function generateAndPlayAudio(button, audioPlayer, options = {}) {
        const itemId = button.dataset.itemId;
        const side = button.dataset.side;
        const contentToRead = button.dataset.contentToRead;
        const url = options.url || (window.FlashcardConfig ? window.FlashcardConfig.regenerateAudioUrl : null);

        if (!url || !itemId || !contentToRead) return Promise.resolve();

        // Check if already generating for this button to avoid double taps
        if (button.dataset.generating === 'true') return Promise.resolve();
        button.dataset.generating = 'true';

        const originalIcon = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(options.csrfHeaders || {})
                },
                body: JSON.stringify({ item_id: itemId, side: side, content_to_read: contentToRead })
            });
            const result = await response.json();

            if (result.success && result.audio_url && audioPlayer) {
                audioPlayer.src = result.audio_url;
                await playAudioAfterLoad(audioPlayer, {
                    restart: options.restart !== false,
                    awaitCompletion: options.awaitCompletion === true
                });
            } else {
                console.warn('[AudioController] TTS generation failed:', result.message);
            }
        } catch (err) {
            console.error('[AudioController] TTS request error:', err);
        } finally {
            button.innerHTML = originalIcon;
            delete button.dataset.generating;
        }
    }

    /**
     * Handle audio error event - attempt auto-recovery (regenerate).
     */
    async function handleAudioError(audioEl, itemId, side, contentToRead, csrfHeaders = {}) {
        if (!audioEl || audioEl.dataset.retried === 'true' || !contentToRead) return;

        // Prevent infinite retry loops
        audioEl.dataset.retried = 'true';

        const url = window.FlashcardConfig ? window.FlashcardConfig.regenerateAudioUrl : null;
        if (!url) return;

        // console.log(`[AudioRecovery] Attempting to regenerate audio for ${side}...`);

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...csrfHeaders },
                body: JSON.stringify({ item_id: itemId, side: side, content_to_read: contentToRead })
            });
            const result = await response.json();

            if (result.success && result.audio_url) {
                // console.log(`[AudioRecovery] Success! Reloading audio source.`);
                audioEl.src = `${result.audio_url}?t=${new Date().getTime()}`;
                audioEl.load();
                // Optional: try to play if it was supposed to play? 
                // For now, just fixing the source is enough, user can click play again.
            }
        } catch (err) {
            console.error('[AudioRecovery] API Error:', err);
        }
    }

    function cancelAutoplay() {
        currentAutoplayToken++;
        currentAutoplayTimeouts.forEach(id => clearTimeout(id));
        currentAutoplayTimeouts = [];
        stopAllAudio();
        return currentAutoplayToken;
    }

    function getCurrentToken() {
        return currentAutoplayToken;
    }

    function waitForDelay(token, delaySeconds) {
        return new Promise(resolve => {
            const delayMs = Math.max(0, delaySeconds) * 1000;
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

    return {
        stopAllAudio,
        playAudioAfterLoad,
        generateAndPlayAudio,
        handleAudioError,
        cancelAutoplay,
        waitForDelay,
        getCurrentToken
    };
})();
