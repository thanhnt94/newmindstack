// UI Management and Layout functions

// Update session summary in the UI (progress bar, stats counters)
function updateSessionSummary() {
    const progressSpan = document.querySelector('.js-fc-progress');
    const masteredSpan = document.querySelector('.js-fc-mastered');
    const reviewSpan = document.querySelector('.js-fc-review');
    const titleSpan = document.querySelector('.js-fc-title');

    if (progressSpan && typeof sessionStatsLocal !== 'undefined') {
        progressSpan.textContent = `${sessionStatsLocal.processed}/${sessionStatsLocal.total}`;
    }
    if (masteredSpan && typeof sessionStatsLocal !== 'undefined') {
        masteredSpan.textContent = sessionStatsLocal.correct || 0;
    }
    if (reviewSpan && typeof sessionStatsLocal !== 'undefined') {
        reviewSpan.textContent = sessionStatsLocal.incorrect || 0;
    }
}

// Helper function Ä‘á»ƒ sync ná»™i dung giá»¯a desktop vÃ  mobile (dÃ¹ng shared classes)
function setFlashcardContent(desktopHtml, mobileHtml = null) {
    document.querySelectorAll('.js-flashcard-content').forEach(el => {
        const isInDesktopView = el.closest('.flashcard-desktop-view');
        const isInMobileView = el.closest('.flashcard-mobile-view');

        if (mobileHtml !== null) {
            if (isInDesktopView) {
                el.innerHTML = desktopHtml;
            } else if (isInMobileView) {
                el.innerHTML = mobileHtml;
            }
        } else {
            el.innerHTML = desktopHtml;
        }
    });
}

// Helper function Ä‘á»ƒ láº¥y element hiá»ƒn thá»‹ hiá»‡n táº¡i (desktop hoáº·c mobile)
function getVisibleFlashcardContentDiv() {
    const allContentDivs = document.querySelectorAll('.js-flashcard-content');
    for (const div of allContentDivs) {
        if (div.offsetParent !== null) return div;
    }
    return allContentDivs[0] || null;
}

function formatTextForHtml(text) {
    if (text == null) return '';
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML.replace(/\r?\n/g, '<br>');
}

function extractPlainText(text) {
    if (text == null) return '';
    if (typeof text !== 'string') {
        text = String(text);
    }
    const temp = document.createElement('div');
    temp.innerHTML = text;
    const plain = temp.textContent || temp.innerText || '';
    return plain.trim();
}

function applyMediaVisibility() {
    const mediaContainers = document.querySelectorAll('.media-container');
    const cardContainers = document.querySelectorAll('._card-container');

    mediaContainers.forEach(container => {
        container.classList.toggle('hidden', isMediaHidden);
    });

    cardContainers.forEach(container => {
        container.classList.toggle('media-hidden', isMediaHidden);
    });

    document.querySelectorAll('.image-toggle-btn').forEach(btn => {
        btn.classList.toggle('is-active', isMediaHidden);
        btn.setAttribute('aria-pressed', isMediaHidden ? 'true' : 'false');
        btn.title = isMediaHidden ? 'Báº­t áº£nh' : 'Táº¯t áº£nh';
        const icon = btn.querySelector('i');
        if (icon) {
            icon.className = `fas ${isMediaHidden ? 'fa-image-slash' : 'fa-image'}`;
        }
    });

    if (window.flashcardViewport && typeof window.flashcardViewport.refresh === 'function') {
        window.flashcardViewport.refresh();
    }

    setTimeout(adjustCardLayout, 0);
}

function setMediaHiddenState(hidden) {
    isMediaHidden = hidden;
    try {
        localStorage.setItem('flashcardHideImages', hidden ? 'true' : 'false');
    } catch (err) { }
    applyMediaVisibility();
    syncSettingsToServer();
}

function updateAudioAutoplayToggleButtons() {
    document.querySelectorAll('.audio-autoplay-toggle-btn').forEach((btn) => {
        btn.classList.toggle('is-active', isAudioAutoplayEnabled);
        btn.setAttribute('aria-pressed', isAudioAutoplayEnabled ? 'true' : 'false');
        btn.title = isAudioAutoplayEnabled ? 'Táº¯t tá»± Ä‘á»™ng phÃ¡t audio' : 'Báº­t tá»± Ä‘á»™ng phÃ¡t audio';
        const icon = btn.querySelector('i');
        if (icon) {
            icon.className = `fas ${isAudioAutoplayEnabled ? 'fa-volume-up' : 'fa-volume-mute'}`;
        }
    });
}

function setAudioAutoplayEnabled(enabled) {
    isAudioAutoplayEnabled = enabled;
    try {
        localStorage.setItem('flashcardAutoPlayAudio', enabled ? 'true' : 'false');
    } catch (err) { }
    updateAudioAutoplayToggleButtons();
    if (!enabled) {
        FlashcardAudioController.stopAllAudio({ selector: '.js-flashcard-content audio, audio' });
    }
    syncSettingsToServer();
}

function closeAllSettingsMenus() {
    document.querySelectorAll('.toolbar-settings').forEach((menu) => {
        menu.classList.remove('is-open');
        const toggleBtn = menu.querySelector('.settings-toggle-btn');
        if (toggleBtn) {
            toggleBtn.setAttribute('aria-expanded', 'false');
        }
    });
}

function toggleSettingsMenu(menuEl) {
    if (!menuEl) return;
    const isOpen = menuEl.classList.contains('is-open');
    closeAllSettingsMenus();
    menuEl.classList.toggle('is-open', !isOpen);
    const toggleBtn = menuEl.querySelector('.settings-toggle-btn');
    if (toggleBtn) {
        toggleBtn.setAttribute('aria-expanded', (!isOpen).toString());
    }
}

function adjustCardLayout() {
    document.querySelectorAll('.js-flashcard-card').forEach(card => {
        if (!card) return;
        const textAreas = card.querySelectorAll('.text-area');
        textAreas.forEach(scrollArea => {
            const txt = scrollArea.querySelector('.flashcard-content-text');
            if (!txt) return;

            txt.style.fontSize = '';
            scrollArea.classList.remove('has-scroll');
            scrollArea.parentElement?.classList?.remove('has-scroll');

            setTimeout(() => {
                const hasScroll = scrollArea.scrollHeight > scrollArea.clientHeight;
                if (hasScroll) {
                    scrollArea.classList.add('has-scroll');
                    scrollArea.parentElement?.classList?.add('has-scroll');
                    scrollArea.scrollTop = 0;
                }

                let current = parseFloat(getComputedStyle(txt).fontSize) || 22;
                const min = 18;
                while (scrollArea.scrollHeight > scrollArea.clientHeight && current > min) {
                    current -= 1;
                    txt.style.fontSize = current + 'px';
                }
            }, 0);
        });
    });
}
