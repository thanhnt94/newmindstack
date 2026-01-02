const FlashcardAudioController = (function () {
    let isAudioAutoplayEnabled = true;
    let autoplayDelaySeconds = 2;
    let currentAutoplayToken = 0;
    let currentAutoplayTimeouts = [];

    return {
        init(options = {}) {
            isAudioAutoplayEnabled = options.isAudioAutoplayEnabled !== false;
            autoplayDelaySeconds = options.autoplayDelaySeconds || 2;
            console.log('[AUDIO] Controller initialized', { isAudioAutoplayEnabled, autoplayDelaySeconds });
        },

        setAudioAutoplayEnabled(enabled) {
            isAudioAutoplayEnabled = enabled;
            console.log('[AUDIO] Autoplay enabled:', isAudioAutoplayEnabled);
        },

        setAutoplayDelay(seconds) {
            autoplayDelaySeconds = seconds;
        },

        stopAllAudio(options = {}) {
            const { exceptAudio = null, selector = 'audio' } = options;
            const audioElements = document.querySelectorAll(selector);
            audioElements.forEach(audioEl => {
                if (exceptAudio && audioEl === exceptAudio) return;
                try {
                    if (!audioEl.paused) {
                        audioEl.pause();
                    }
                    audioEl.currentTime = 0;
                } catch (err) {
                    console.warn('[AUDIO] Failed to stop audio:', err);
                }
            });
        },

        playAudioAfterLoad(audioPlayer, { restart = true, awaitCompletion = false } = {}) {
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
                            console.warn('[AUDIO] Failed to reset audio:', err);
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
                        playPromise.catch(() => {
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
        },

        async generateAndPlayAudio(button, audioPlayer, config = {}) {
            const { url, csrfHeaders, awaitCompletion = false, suppressLoadingUi = false, restart = true } = config;
            if (!button || !audioPlayer) return Promise.resolve();

            const itemId = button.dataset.itemId;
            const side = button.dataset.side;
            const contentToRead = button.dataset.contentToRead;

            const originalHtml = button.dataset.originalHtml || button.innerHTML;
            if (!button.dataset.originalHtml) {
                button.dataset.originalHtml = originalHtml;
            }

            if (!suppressLoadingUi) {
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            }

            button.classList.add('is-disabled');
            let playbackPromise = Promise.resolve();

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', ...csrfHeaders },
                    body: JSON.stringify({ item_id: itemId, side: side, content_to_read: contentToRead })
                });
                const result = await response.json();
                if (result.success && result.audio_url) {
                    audioPlayer.src = result.audio_url;
                    playbackPromise = this.playAudioAfterLoad(audioPlayer, { restart, awaitCompletion });
                    if (awaitCompletion) {
                        await playbackPromise;
                    }
                } else {
                    console.error('[AUDIO] TTS failed:', result.message);
                }
            } catch (error) {
                console.error('[AUDIO] TTS error:', error);
            } finally {
                button.classList.remove('is-disabled');
                if (!suppressLoadingUi) {
                    button.innerHTML = button.dataset.originalHtml;
                }
            }

            return playbackPromise;
        },

        cancelAutoplay() {
            currentAutoplayToken += 1;
            this.clearAllTimeouts();
            this.stopAllAudio();
            console.log('[AUTOPLAY] Cancelled. New token:', currentAutoplayToken);
            return currentAutoplayToken;
        },

        clearAllTimeouts() {
            currentAutoplayTimeouts.forEach(id => clearTimeout(id));
            currentAutoplayTimeouts = [];
        },

        registerTimeout(timeoutId) {
            if (timeoutId) {
                currentAutoplayTimeouts.push(timeoutId);
            }
        },

        getNextToken() {
            currentAutoplayToken += 1;
            return currentAutoplayToken;
        },

        waitForDelay(token) {
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
                this.registerTimeout(timeoutId);
            });
        },

        getCurrentToken() {
            return currentAutoplayToken;
        },

        getDelaySeconds() {
            return autoplayDelaySeconds;
        }
    };
})();

window.FlashcardAudioController = FlashcardAudioController;
