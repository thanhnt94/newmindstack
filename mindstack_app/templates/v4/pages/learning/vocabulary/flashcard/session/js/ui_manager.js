/**
 * UI Manager for Flashcard Session
 */

// --- Global UI State ---
let isMediaHidden = false;
let showStats = true;

// --- Initialization ---

function initUiSettings() {
    // visualSettings from global config
    const visualSettings = window.FlashcardConfig ? window.FlashcardConfig.visualSettings : {};

    // 1. Load from Backend Settings (Highest priority)
    if (visualSettings.show_image !== undefined) {
        isMediaHidden = (visualSettings.show_image === false);
    }
    if (visualSettings.show_stats !== undefined) {
        showStats = (visualSettings.show_stats !== false);
    }

    // 2. Fallback to localStorage
    try {
        if (visualSettings.show_image === undefined) {
            const storedImageVisibility = localStorage.getItem('flashcardHideImages');
            if (storedImageVisibility === 'true') isMediaHidden = true;
        }
    } catch (err) {
        console.warn('Không thể đọc localStorage:', err);
    }

    // Hide stats if disabled
    if (!showStats) {
        const currentCardStatsContainer = document.getElementById('current-card-stats');
        const previousCardStatsContainer = document.getElementById('previous-card-stats');
        if (currentCardStatsContainer) currentCardStatsContainer.style.display = 'none';
        if (previousCardStatsContainer) previousCardStatsContainer.style.display = 'none';

        const mobileStats = document.getElementById('current-card-stats-mobile');
        if (mobileStats) mobileStats.style.display = 'none';
    }
}

// --- Viewport & Layout ---

const setVh = () => {
    if (window.flashcardViewport && typeof window.flashcardViewport.refresh === 'function') {
        window.flashcardViewport.refresh();
    }

    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
};

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

// --- Settings Menus ---

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

// --- Media Visibility ---

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
        btn.title = isMediaHidden ? 'Bật ảnh' : 'Tắt ảnh';
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
    if (window.syncSettingsToServer) window.syncSettingsToServer();
}

// --- Content Synchronization ---

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

function getVisibleFlashcardContentDiv() {
    const allContentDivs = document.querySelectorAll('.js-flashcard-content');
    for (const div of allContentDivs) {
        if (div.offsetParent !== null) return div;
    }
    return allContentDivs[0] || null;
}

// --- Card Rendering Logic ---

function shouldShowPreviewOnly(initialStats = {}) {
    const hasRealReviews = Boolean(initialStats.has_real_reviews);
    if (hasRealReviews) return false;

    const previewCount = initialStats.preview_count ?? 0;
    const hasPreviewHistory = Boolean(initialStats.has_preview_history);

    if (hasPreviewHistory && previewCount > 0) return false;
    return previewCount === 0;
}

function determineCardCategory(cardData) {
    if (!cardData) return '';
    const stats = cardData.initial_stats || {};
    const hasPreviewHistory = Boolean(stats.has_preview_history);
    const hasRealReviews = Boolean(stats.has_real_reviews);

    if (!hasPreviewHistory && !hasRealReviews) return 'new';
    if (stats.status === 'hard') return 'hard';
    if (stats.has_preview_only) return 'due';
    if (stats.next_review) {
        const dueDate = new Date(stats.next_review);
        if (!Number.isNaN(dueDate.getTime()) && dueDate <= new Date()) return 'due';
    }
    return '';
}

function getPreviewButtonHtml() {
    return '<button class="btn btn-continue" data-answer="continue"><i class="fas fa-arrow-right"></i>Tiếp tục</button>';
}

function generateDynamicButtons(buttonCount) {
    const buttonSets = {
        3: [
            { variant: 'again', value: 'quên', title: 'Quên', icon: 'fas fa-redo-alt' },
            { variant: 'hard', value: 'mơ_hồ', title: 'Mơ hồ', icon: 'fas fa-question-circle' },
            { variant: 'easy', value: 'nhớ', title: 'Nhớ', icon: 'fas fa-check-circle' }
        ],
        4: [
            { variant: 'again', value: 'again', title: 'Học lại', icon: 'fas fa-undo' },
            { variant: 'very-hard', value: 'hard', title: 'Khó', icon: 'fas fa-fire' },
            { variant: 'good', value: 'good', title: 'Bình thường', icon: 'fas fa-thumbs-up' },
            { variant: 'easy', value: 'easy', title: 'Dễ', icon: 'fas fa-smile' }
        ],
        6: [
            { variant: 'fail', value: 'fail', title: 'Rất khó', icon: 'fas fa-exclamation-circle' },
            { variant: 'very-hard', value: 'very_hard', title: 'Khó', icon: 'fas fa-fire' },
            { variant: 'hard', value: 'hard', title: 'Trung bình', icon: 'fas fa-adjust' },
            { variant: 'medium', value: 'medium', title: 'Dễ', icon: 'fas fa-leaf' },
            { variant: 'good', value: 'good', title: 'Rất dễ', icon: 'fas fa-thumbs-up' },
            { variant: 'very-easy', value: 'very_easy', title: 'Dễ dàng', icon: 'fas fa-star' }
        ]
    };
    const buttons = buttonSets[buttonCount] || buttonSets[3];
    return buttons.map(btn => {
        const iconHtml = btn.icon ? `<span class="rating-btn__icon"><i class="${btn.icon}"></i></span>` : '';
        return `<button class="btn rating-btn rating-btn--${btn.variant}" data-answer="${btn.value}">${iconHtml}<span class="rating-btn__title">${btn.title}</span></button>`;
    }).join('');
}

function revealBackSideForAutoplay(token) {
    if (window.currentAutoplayToken !== undefined && token !== window.currentAutoplayToken) return;

    // Logic from original file:
    const visibleContainer = getVisibleFlashcardContentDiv();
    const card = visibleContainer ? visibleContainer.querySelector('.js-flashcard-card') : document.querySelector('.js-flashcard-card');
    const actions = visibleContainer ? visibleContainer.querySelector('.js-internal-actions') : document.querySelector('.js-internal-actions');
    const flipBtn = visibleContainer ? visibleContainer.querySelector('.js-flip-card-btn') : document.querySelector('.js-flip-card-btn');

    if (!card) return;
    if (!card.classList.contains('flipped')) {
        window.stopAllFlashcardAudio ? window.stopAllFlashcardAudio() : null;
        card.classList.add('flipped');
        actions?.classList.add('visible');
        if (flipBtn) {
            flipBtn.style.display = 'none';
        }
        setTimeout(adjustCardLayout, 0);
    } else if (actions) {
        actions.classList.add('visible');
    }
}
window.revealBackSideForAutoplay = revealBackSideForAutoplay;

function renderCard(data) {
    const isAutoplaySession = window.FlashcardConfig.isAutoplaySession;
    const userButtonCount = window.FlashcardConfig.userButtonCount;

    if (isAutoplaySession) {
        if (window.cancelAutoplaySequence) window.cancelAutoplaySequence();
    }
    const c = data.content;
    const itemId = data.item_id;
    const setId = data.container_id;
    const fTxt = window.formatTextForHtml(c.front || '');
    const bTxt = window.formatTextForHtml(c.back || '');
    const initialStats = data.initial_stats || {};
    const cardCategory = determineCardCategory(data);
    const showPreviewOnly = shouldShowPreviewOnly(initialStats);
    const shouldRenderButtons = !isAutoplaySession && !showPreviewOnly;
    const buttonsHtml = showPreviewOnly ? getPreviewButtonHtml() : (shouldRenderButtons ? generateDynamicButtons(userButtonCount) : '');
    const buttonCount = showPreviewOnly ? 1 : (shouldRenderButtons ? userButtonCount : 0);

    const isMobile = window.innerWidth < 1024;

    const hasFrontAudio = c.front_audio_url || c.front_audio_content;
    const hasBackAudio = c.back_audio_url || c.back_audio_content;
    const canEditCurrentCard = Boolean(data.can_edit);

    let editUrl = "";
    if (canEditCurrentCard) {
        const urlTemplate = window.FlashcardConfig.editFlashcardUrlTemplate || '';
        if (urlTemplate) {
            editUrl = urlTemplate.replace('/0', '/' + setId).replace('/0', '/' + itemId);
        }
    }

    const renderOptions = {
        itemId, setId, fTxt, bTxt, cardCategory,
        isMediaHidden, isAudioAutoplayEnabled: window.isAudioAutoplayEnabled,
        hasFrontAudio, hasBackAudio,
        buttonsHtml, buttonCount,
        frontImg: c.front_img,
        backImg: c.back_img,
        frontAudioUrl: c.front_audio_url,
        backAudioUrl: c.back_audio_url,
        frontAudioContent: c.front_audio_content,
        backAudioContent: c.back_audio_content,
        canEditCurrentCard,
        editUrl
    };

    let desktopHtml = "";
    let mobileHtml = "";

    if (window.renderDesktopCardHtml) {
        desktopHtml = window.renderDesktopCardHtml(data, renderOptions);
    }
    if (window.renderMobileCardHtml) {
        mobileHtml = window.renderMobileCardHtml(data, renderOptions);
    }

    if (!desktopHtml && !mobileHtml) {
        console.error("Render functions not found!");
        return;
    }

    setFlashcardContent(desktopHtml, mobileHtml);

    // Explicitly update buttons state
    const btns = document.querySelectorAll('.audio-autoplay-toggle-btn');
    btns.forEach(btn => {
        const isActive = window.isAudioAutoplayEnabled;
        btn.classList.toggle('is-active', isActive);
        btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        const icon = btn.querySelector('i');
        if (icon) icon.className = `fas ${isActive ? 'fa-volume-up' : 'fa-volume-mute'}`;
    });

    closeAllSettingsMenus();

    const currentFlashcardIndex = window.currentFlashcardIndex;
    if (Array.isArray(window.currentFlashcardBatch) && window.currentFlashcardBatch[currentFlashcardIndex]) {
        window.currentFlashcardBatch[currentFlashcardIndex].card_category = cardCategory;
    }

    const visibleContainer = getVisibleFlashcardContentDiv();
    const card = visibleContainer ? visibleContainer.querySelector('.js-flashcard-card') : document.querySelector('.js-flashcard-card');
    const actions = visibleContainer ? visibleContainer.querySelector('.js-internal-actions') : document.querySelector('.js-internal-actions');
    // Fix: Handle both internal card button (Desktop) and external footer button (Mobile)
    const internalFlipBtn = visibleContainer ? visibleContainer.querySelector('.js-flip-card-btn') : null;
    const mobileFlipBtn = document.querySelector('.js-fc-flip-btn');

    // We want to control both if they exist
    const flipBtns = [];
    if (internalFlipBtn) flipBtns.push(internalFlipBtn);
    if (mobileFlipBtn) flipBtns.push(mobileFlipBtn);

    // [UX] Hide flip buttons initially until content loads
    flipBtns.forEach(btn => btn.style.display = 'none');

    const showFlipButtons = () => {
        console.log('[FlipButton] Content loaded, showing buttons');
        flipBtns.forEach(btn => {
            btn.style.display = '';
            // Ensure mobile button has correct display type if originally flex
            if (btn === mobileFlipBtn) {
                // Check computed style or just clear inline to let CSS take over? 
                // Clearing inline is safest if CSS sets it to flex/block.
                btn.style.removeProperty('display');
            }
        });
    };

    // Check if we need to wait for front image
    const frontImg = visibleContainer ? visibleContainer.querySelector('.front .media-container img') : null;
    const shouldWaitForImage = frontImg && !isMediaHidden && !frontImg.complete;

    if (shouldWaitForImage) {
        console.log('[FlipButton] Waiting for front image to load...');
        frontImg.onload = () => showFlipButtons();
        frontImg.onerror = () => showFlipButtons();
        // Fallback timeout
        setTimeout(showFlipButtons, 3000);
    } else {
        // No image or already loaded -> show after short paint delay
        setTimeout(showFlipButtons, 50);
    }

    if (window.flashcardViewport && typeof window.flashcardViewport.refresh === 'function') {
        window.flashcardViewport.refresh();
    }

    if (card) {
        card.dataset.cardCategory = cardCategory || 'default';
    }

    if (window.setupAudioErrorHandler) {
        window.setupAudioErrorHandler(itemId, c.front_audio_content || '', c.back_audio_content || '');
    }

    // --- Flip Interactions ---
    const flipToBack = () => {
        if (!card) {
            console.error('Flashcard element (.js-flashcard-card) not found!');
            return;
        }
        window.stopAllFlashcardAudio ? window.stopAllFlashcardAudio() : null;
        card.classList.add('flipped');
        actions?.classList.add('visible');
        // Hide all flip buttons
        flipBtns.forEach(btn => btn.style.display = 'none');

        // Mobile Support: Show footer rating buttons
        const mobileRatingBtns = document.querySelector('.js-fc-rating-btns');
        if (mobileRatingBtns) mobileRatingBtns.classList.add('show');

        setTimeout(adjustCardLayout, 0);
        if (!isAutoplaySession && window.autoPlayBackSide) {
            window.autoPlayBackSide();
        }
    };

    const flipToFront = () => {
        window.stopAllFlashcardAudio ? window.stopAllFlashcardAudio() : null;
        card.classList.remove('flipped');
        actions?.classList.remove('visible');
        // Show all flip buttons
        flipBtns.forEach(btn => btn.style.display = '');

        // Mobile Support: Hide footer rating buttons
        const mobileRatingBtns = document.querySelector('.js-fc-rating-btns');
        if (mobileRatingBtns) mobileRatingBtns.classList.remove('show');

        setTimeout(adjustCardLayout, 0);
    };

    flipBtns.forEach(btn => {
        // Use onclick to prevent listener accumulation
        btn.onclick = (ev) => {
            ev.stopPropagation();
            flipToBack();
        };
    });

    const frontLabel = card?.querySelector('.front .card-toolbar .label');
    const backLabel = card?.querySelector('.back .card-toolbar .label');

    if (frontLabel) frontLabel.addEventListener('click', (ev) => { ev.stopPropagation(); flipToBack(); });
    if (backLabel) backLabel.addEventListener('click', (ev) => { ev.stopPropagation(); flipToFront(); });

    document.querySelectorAll('.card-toolbar .icon-btn').forEach(btn => {
        btn.addEventListener('click', ev => {
            if (btn.classList.contains('settings-toggle-btn') || btn.classList.contains('audio-autoplay-toggle-btn')) {
                return;
            }
            ev.stopPropagation();
        });
    });

    document.querySelectorAll('.image-toggle-btn').forEach(btn => {
        btn.addEventListener('click', ev => {
            ev.stopPropagation();
            setMediaHiddenState(!isMediaHidden);
        });
    });

    if (!isAutoplaySession) {
        document.querySelectorAll('.actions .btn').forEach(b => b.addEventListener('click', ev => {
            ev.stopPropagation();
            if (window.submitFlashcardAnswer) {
                window.submitFlashcardAnswer(data.item_id, b.dataset.answer);
            }
        }));
    }

    document.querySelectorAll('.play-audio-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const audioPlayer = document.querySelector(btn.dataset.audioTarget);
            if (!audioPlayer || btn.classList.contains('is-disabled')) return;
            if (!audioPlayer.paused && audioPlayer.currentTime > 0) {
                audioPlayer.pause();
                audioPlayer.currentTime = 0;
                return;
            }
            if (window.playAudioForButton) {
                window.playAudioForButton(btn).catch(() => { });
            }
        });
    });

    document.querySelectorAll('.open-stats-modal-btn').forEach(btn => btn.addEventListener('click', () => toggleStatsModal(true)));

    document.querySelectorAll('.open-ai-modal-btn').forEach(btn => btn.addEventListener('click', () => {
        const currentCard = window.currentFlashcardBatch[window.currentFlashcardIndex];
        openAiModal(currentCard.item_id, currentCard.content.front);
    }));

    document.querySelectorAll('.open-note-panel-btn').forEach(btn => btn.addEventListener('click', () => {
        openNotePanel(btn.dataset.itemId);
    }));

    document.querySelectorAll('.open-feedback-modal-btn').forEach(btn => btn.addEventListener('click', () => {
        const currentCard = window.currentFlashcardBatch[window.currentFlashcardIndex];
        openFeedbackModal(currentCard.item_id, currentCard.content.front);
    }));

    applyMediaVisibility();

    // RPG HUD Update: Ensure "THẺ NÀY" stats are shown for the new card
    if (initialStats) {
        window.updateCardHudStats(initialStats);
    }

    setTimeout(adjustCardLayout, 0);

    // [UX-FIX] Only play audio immediately if NOT waiting for notification to complete
    // When notification is active, the notificationComplete handler will trigger audio
    // Use safe check: if pendingAudioAutoplay is undefined or false, allow audio to play
    const shouldDeferAudio = (typeof window.pendingAudioAutoplay !== 'undefined') && window.pendingAudioAutoplay === true;
    if (!shouldDeferAudio) {
        if (isAutoplaySession) {
            if (window.startAutoplaySequence) window.startAutoplaySequence();
        } else {
            if (window.autoPlayFrontSide) window.autoPlayFrontSide();
        }
    }
}

// --- Stats Renderers ---

function renderCardStatsHtml(stats, scoreChange = 0, cardContent = {}, isInitial = false) {
    if (!stats) {
        return `<div class="empty-state"><i class="fas fa-info-circle"></i> ${isInitial ? 'Đây là thẻ mới.' : 'Không có dữ liệu thống kê.'}</div>`;
    }

    const { formatTextForHtml, formatDateTime, formatMinutesAsDuration, formatRecentTimestamp } = window;

    // Safety check just in case
    if (!formatTextForHtml) return "Error: utils.js not loaded.";

    const totalReviews = Number(stats.times_reviewed) || 0;
    const correctCount = Number(stats.correct_count) || 0;
    const incorrectCount = Number(stats.incorrect_count) || 0;
    const vagueCount = Number(stats.vague_count) || 0;
    const previewCount = Number(stats.preview_count) || 0;
    const correctWidth = totalReviews > 0 ? (correctCount / totalReviews) * 100 : 0;
    const vagueWidth = totalReviews > 0 ? (vagueCount / totalReviews) * 100 : 0;
    const incorrectWidth = totalReviews > 0 ? (incorrectCount / totalReviews) * 100 : 0;
    const correctPercentDisplay = Math.round(correctWidth);
    const vaguePercentDisplay = Math.round(vagueWidth);
    const incorrectPercentDisplay = Math.round(incorrectWidth);
    const dueTime = formatDateTime(stats.next_review, 'Chưa có');
    const lastReviewed = formatDateTime(stats.last_reviewed, totalReviews > 0 ? 'Chưa có' : 'Chưa ôn');
    const firstSeen = formatDateTime(stats.first_seen, 'Chưa mở');
    const formattedIntervalDisplay = formatMinutesAsDuration(stats.interval);
    const scoreChangeSign = scoreChange > 0 ? '+' : '';
    const scoreChangeClass = scoreChange > 0 ? 'positive' : (scoreChange < 0 ? 'negative' : '');
    const isBrandNew = !stats.has_preview_history && !stats.has_real_reviews;
    const isPreviewStage = stats.has_preview_history && !stats.has_real_reviews;
    const statusKeyRaw = (stats.status || 'new').toString();
    const statusKey = statusKeyRaw.toLowerCase().replace(/\s+/g, '-');
    const statusLabelMap = {
        'new': 'Mới',
        'learning': 'Đang học',
        'review': 'Ôn tập',
        'relearning': 'Ôn lại',
        'hard': 'Khó',
        'easy': 'Dễ',
        'suspended': 'Tạm dừng'
    };
    const statusLabel = statusLabelMap[statusKeyRaw.toLowerCase()] || statusKeyRaw;
    const correctRateDisplay = typeof stats.correct_rate === 'number' ? Math.round(stats.correct_rate) : correctPercentDisplay;
    const repetitions = Number(stats.repetitions) || 0;
    const easinessFactor = typeof stats.easiness_factor === 'number' ? Number(stats.easiness_factor).toFixed(2) : '—';
    const currentStreak = Number(stats.current_streak) || 0;
    const longestStreak = Number(stats.longest_streak) || 0;
    const recentReviews = Array.isArray(stats.recent_reviews) ? [...stats.recent_reviews].slice(-10).reverse() : [];
    const recentReviewConfig = {
        'correct': { label: 'Nhớ', icon: 'fas fa-check-circle' },
        'vague': { label: 'Mơ hồ', icon: 'fas fa-adjust' },
        'incorrect': { label: 'Quên', icon: 'fas fa-times-circle' },
        'preview': { label: 'Xem trước', icon: 'fas fa-eye' }
    };
    const introNotice = isBrandNew
        ? `<div class="insight-banner"><i class="fas fa-seedling"></i><span>Thẻ mới - khám phá nội dung trước khi chấm điểm.</span></div>`
        : (isPreviewStage
            ? `<div class="insight-banner"><i class="fas fa-hourglass-half"></i><span>Thẻ đang ở giai đoạn giới thiệu. Nhấn "Tiếp tục" để bước vào phần đánh giá.</span></div>`
            : '');

    const hasHistoricData = totalReviews > 0 || previewCount > 0;
    const progressSection = hasHistoricData
        ? `
            <div class="stats-section stats-section--performance">
                <div class="stats-section__header">
                    <div class="icon-bubble"><i class="fas fa-chart-line"></i></div>
                    <div>
                        <h4>Hiệu suất trả lời</h4>
                        <p>Tỷ lệ ghi nhớ dựa trên toàn bộ lịch sử của thẻ.</p>
                    </div>
                </div>
                <div class="progress-stack">
                    <div class="progress-bar-group">
                        <div class="progress-bar-label">
                            <span class="label-title"><span class="progress-dot"></span> Nhớ</span>
                            <span class="progress-bar-stat">${correctCount} lượt · ${correctPercentDisplay}%</span>
                        </div>
                        <div class="progress-bar-container"><div class="progress-bar-fill progress-bar-fill-correct" style="--progress:${correctWidth}%;"></div></div>
                    </div>
                    <div class="progress-bar-group">
                        <div class="progress-bar-label">
                            <span class="label-title"><span class="progress-dot vague"></span> Mơ hồ</span>
                            <span class="progress-bar-stat">${vagueCount} lượt · ${vaguePercentDisplay}%</span>
                        </div>
                        <div class="progress-bar-container"><div class="progress-bar-fill progress-bar-fill-vague" style="--progress:${vagueWidth}%;"></div></div>
                    </div>
                    <div class="progress-bar-group">
                        <div class="progress-bar-label">
                            <span class="label-title"><span class="progress-dot incorrect"></span> Quên</span>
                            <span class="progress-bar-stat">${incorrectCount} lượt · ${incorrectPercentDisplay}%</span>
                        </div>
                        <div class="progress-bar-container"><div class="progress-bar-fill progress-bar-fill-incorrect" style="--progress:${incorrectWidth}%;"></div></div>
                    </div>
                </div>
            </div>
        `
        : `
            <div class="stats-section stats-section--performance">
                <div class="stats-section__header">
                    <div class="icon-bubble"><i class="fas fa-chart-line"></i></div>
                    <div>
                        <h4>Hiệu suất trả lời</h4>
                        <p>Thống kê sẽ xuất hiện sau khi bạn chấm điểm thẻ này.</p>
                    </div>
                </div>
                <div class="empty-state"><i class="fas fa-info-circle"></i> Bắt đầu trả lời để mở khóa biểu đồ hiệu suất.</div>
            </div>
        `;

    const insightSection = `
        <div class="stats-section stats-section--insight">
            <div class="stats-section__header">
                <div class="icon-bubble"><i class="fas fa-bullseye"></i></div>
                <div>
                    <h4>Chỉ số ghi nhớ</h4>
                    <p>Tổng hợp theo thuật toán SM-2.</p>
                </div>
            </div>
            <div class="insight-grid">
                ${!isInitial ? `<div class="insight-card insight-card--highlight"><span class="insight-card__label">Điểm phiên này</span><span class="insight-card__value ${scoreChangeClass}">${scoreChangeSign}${scoreChange}</span><span class="insight-card__muted">Sau lượt trả lời vừa rồi</span></div>` : ''}
                <div class="insight-card">
                    <span class="insight-card__label">Trạng thái</span>
                    <span class="status-chip status-${statusKey}"><i class="fas fa-circle"></i> ${statusLabel}</span>
                    <span class="insight-card__muted">Theo tiến trình hiện tại</span>
                </div>
                <div class="insight-card">
                    <span class="insight-card__label">Tỷ lệ chính xác</span>
                    <span class="insight-card__value">${correctRateDisplay}%</span>
                    <span class="insight-card__muted">${totalReviews > 0 ? `${correctCount} đúng · ${incorrectCount} sai` : 'Chưa có lượt ôn'}</span>
                </div>
                <div class="insight-card">
                    <span class="insight-card__label">Lượt ôn</span>
                    <span class="insight-card__value">${totalReviews}</span>
                    <span class="insight-card__muted">${previewCount > 0 ? `${previewCount} lần xem thử` : 'Chưa xem trước'}</span>
                </div>
                <div class="insight-card">
                    <span class="insight-card__label">Chuỗi hiện tại</span>
                    <span class="insight-card__value">${currentStreak}</span>
                    <span class="insight-card__muted">${currentStreak > 0 ? 'Lượt đúng liên tiếp' : 'Chưa có chuỗi'}</span>
                </div>
                <div class="insight-card">
                    <span class="insight-card__label">Chuỗi dài nhất</span>
                    <span class="insight-card__value">${longestStreak}</span>
                    <span class="insight-card__muted">${longestStreak > 0 ? 'Kỷ lục ghi nhớ' : 'Chưa xác định'}</span>
                </div>
                <div class="insight-card">
                    <span class="insight-card__label">Hệ số dễ (EF)</span>
                    <span class="insight-card__value">${easinessFactor}</span>
                    <span class="insight-card__muted">Điều chỉnh sau mỗi lần ôn</span>
                </div>
                <div class="insight-card">
                    <span class="insight-card__label">Lặp lại (n)</span>
                    <span class="insight-card__value">${repetitions}</span>
                    <span class="insight-card__muted">Số lần đã ghi nhớ</span>
                </div>
                <div class="insight-card">
                    <span class="insight-card__label">Khoảng cách (I)</span>
                    <span class="insight-card__value">${formattedIntervalDisplay || 'Chưa có'}</span>
                    <span class="insight-card__muted">Thời gian đến lần ôn tiếp theo</span>
                </div>
            </div>
        </div>
    `;

    const recentSection = recentReviews.length
        ? `
            <div class="stats-section stats-section--recent">
                <div class="stats-section__header">
                    <div class="icon-bubble"><i class="fas fa-history"></i></div>
                    <div>
                        <h4>Lượt trả lời gần đây</h4>
                        <p>Theo dõi tối đa 10 lượt mới nhất bằng biểu tượng màu sắc.</p>
                    </div>
                </div>
                <div class="recent-answers-track" role="list">
                    ${recentReviews.map(entry => {
            const resultKey = (entry.result || '').toLowerCase();
            const config = recentReviewConfig[resultKey] || recentReviewConfig.preview;
            const timestampDisplay = formatRecentTimestamp(entry.timestamp);
            const qualityScore = typeof entry.user_answer_quality === 'number' ? entry.user_answer_quality : '—';
            const tooltip = `${config.label} · ${timestampDisplay} · Điểm: ${qualityScore}`;
            return `
                            <div class="recent-answer-dot recent-answer-dot--${resultKey || 'preview'}" role="listitem" title="${tooltip}">
                                <i class="${config.icon}" aria-hidden="true"></i>
                                <span class="sr-only">${tooltip}</span>
                            </div>
                        `;
        }).join('')}
                </div>
            </div>
        `
        : '';

    const timelineSection = `
        <div class="stats-section stats-section--timeline">
            <div class="stats-section__header">
                <div class="icon-bubble"><i class="fas fa-route"></i></div>
                <div>
                    <h4>Mốc thời gian học</h4>
                    <p>Quản lý lịch sử ôn tập của riêng bạn.</p>
                </div>
            </div>
            <div class="timeline-card">
                <div class="timeline-item">
                    <div class="timeline-icon"><i class="fas fa-flag"></i></div>
                    <div>
                        <div class="timeline-label">Lần đầu gặp</div>
                        <div class="timeline-value">${firstSeen}</div>
                        <div class="timeline-subtle">Thời điểm bạn mở thẻ lần đầu</div>
                    </div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-icon"><i class="fas fa-redo"></i></div>
                    <div>
                        <div class="timeline-label">Ôn gần nhất</div>
                        <div class="timeline-value">${lastReviewed}</div>
                        <div class="timeline-subtle">${totalReviews > 0 ? `${totalReviews} lượt đã ghi nhận` : 'Chưa có lượt ôn thực tế'}</div>
                    </div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-icon"><i class="fas fa-calendar-check"></i></div>
                    <div>
                        <div class="timeline-label">Lịch ôn tiếp theo</div>
                        <div class="timeline-value">${dueTime}</div>
                        <div class="timeline-subtle">${stats.has_real_reviews ? 'Theo lịch SM-2 cá nhân hóa' : 'Cần trả lời để tạo lịch ôn'}</div>
                    </div>
                </div>
            </div>
        </div>
    `;

    const cardDetails = cardContent.front ? `
        <div class="card-info-section">
            <div class="card-info-title collapsed" data-toggle="card-details-content">
                <i class="fas fa-caret-right"></i><span>Chi tiết thẻ</span>
            </div>
            <div class="card-info-content">
                <p><span class="label">Mặt trước</span>${formatTextForHtml(cardContent.front)}</p>
                <p><span class="label">Mặt sau</span>${formatTextForHtml(cardContent.back)}</p>
            </div>
        </div>
    `.trim() : '';

    return [
        cardDetails,
        introNotice,
        progressSection,
        insightSection,
        recentSection,
        timelineSection
    ].join('');
}

function renderMobileCardStatsHtml(stats, scoreChange = 0, cardContent = {}, isInitial = false) {
    if (!stats) return '<div class="p-4 text-center text-slate-400">Chưa có dữ liệu</div>';

    // Deconstruct utils
    const { formatTextForHtml, formatDateTime } = window;

    const totalReviews = Number(stats.times_reviewed) || 0;
    const correctCount = Number(stats.correct_count) || 0;
    const incorrectCount = Number(stats.incorrect_count) || 0;
    const correctRate = totalReviews > 0 ? Math.round((correctCount / totalReviews) * 100) : 0;
    const nextReview = formatDateTime(stats.next_review, 'Sẵn sàng');
    const statusLabel = (stats.status || 'New').toString().toUpperCase();
    const streak = stats.current_streak || 0;
    const ef = Number(stats.easiness_factor || 2.5).toFixed(2);

    // Status Colors
    const statusColors = {
        'new': 'bg-blue-100 text-blue-700',
        'learning': 'bg-orange-100 text-orange-700',
        'review': 'bg-emerald-100 text-emerald-700',
        'relearning': 'bg-purple-100 text-purple-700',
        'hard': 'bg-red-100 text-red-700'
    };
    const statusClass = statusColors[String(stats.status).toLowerCase()] || 'bg-slate-100 text-slate-700';

    // Recent History Section
    let historyHtml = '';
    if (stats.recent_reviews && stats.recent_reviews.length > 0) {
        const icons = stats.recent_reviews.slice().reverse().map((review, idx) => {
            const isCorrect = review.result === 'correct';
            const isWrong = review.result === 'incorrect';
            const colorClass = isCorrect ? 'bg-emerald-500' : (isWrong ? 'bg-rose-500' : 'bg-slate-400');
            const icon = isCorrect ? 'fa-check' : (isWrong ? 'fa-times' : 'fa-minus');

            const timeDate = review.timestamp ? new Date(review.timestamp) : null;
            const timeStr = timeDate ? timeDate.toLocaleString('vi-VN', {
                day: '2-digit', month: '2-digit', year: 'numeric',
                hour: '2-digit', minute: '2-digit', second: '2-digit'
            }) : 'Review';

            const typeLabel = review.type === 'preview' ? 'Học lần đầu' : 'Ôn tập';
            const tooltipTitle = `${typeLabel}\n${timeStr}`;

            return `<span class="w-6 h-6 rounded-full ${colorClass} flex items-center justify-center cursor-help shrink-0 ring-1 ring-white shadow-sm" title="${tooltipTitle}">
                <i class="fas ${icon} text-white text-[10px]"></i>
            </span>`;
        }).join('');

        historyHtml = `
            <div class="mb-3 bg-white border border-slate-100 p-3 rounded-2xl shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
                 <div class="flex items-center gap-2 mb-2">
                    <i class="fas fa-history text-xs text-slate-400"></i>
                    <span class="text-xs uppercase font-bold text-slate-400">Lịch sử thẻ này</span>
                </div>
                <div class="flex flex-wrap gap-1.5 direction-rtl">
                    ${icons}
                </div>
            </div>`;
    }

    return `
        <div class="mobile-stats-content">
            <!-- Top Row: Status & Next Review -->
            <div class="flex items-center justify-between mb-5">
                <span class="px-3 py-1 rounded-full text-xs font-bold ${statusClass}">${statusLabel}</span>
                <div class="text-right">
                    <div class="text-[10px] text-slate-400 uppercase font-bold">Lần ôn tới</div>
                    <div class="text-xs font-semibold text-slate-700">${nextReview}</div>
                </div>
            </div>

            <!-- Accuracy Bar -->
            <div class="mb-6 bg-white border border-slate-100 p-4 rounded-2xl shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
                <div class="flex justify-between items-end mb-2">
                    <span class="text-sm font-bold text-slate-700">Độ chính xác</span>
                    <span class="text-2xl font-black text-slate-800">${correctRate}%</span>
                </div>
                <div class="h-3 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div class="h-full bg-gradient-to-r from-blue-500 to-emerald-400" style="width: ${correctRate}%"></div>
                </div>
                <div class="mt-2 flex justify-between text-xs font-medium text-slate-400">
                    <span>${correctCount} đúng</span>
                    <span>${incorrectCount} sai</span>
                </div>
            </div>

            <!-- Metrics Grid -->
            <div class="grid grid-cols-3 gap-3 mb-6">
                <div class="bg-slate-50 p-3 rounded-2xl flex flex-col items-center justify-center text-center">
                    <span class="text-[10px] uppercase font-bold text-slate-400 mb-1">Chuỗi</span>
                    <span class="text-lg font-black text-slate-700">${streak}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-2xl flex flex-col items-center justify-center text-center">
                    <span class="text-[10px] uppercase font-bold text-slate-400 mb-1">Lượt ôn</span>
                    <span class="text-lg font-black text-slate-700">${totalReviews}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-2xl flex flex-col items-center justify-center text-center">
                    <span class="text-[10px] uppercase font-bold text-slate-400 mb-1">Độ khó</span>
                    <span class="text-lg font-black text-slate-700">${ef}</span>
                </div>
            </div>

            ${historyHtml}

            <!-- Card Info Toggle (App style) -->
            <div class="bg-white border border-slate-200 rounded-2xl overflow-hidden">
                <button class="w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100 transition-colors" onclick="this.nextElementSibling.classList.toggle('hidden'); this.querySelector('.fa-chevron-down').classList.toggle('rotate-180')">
                    <span class="text-sm font-bold text-slate-700">Chi tiết nội dung thẻ</span>
                    <i class="fas fa-chevron-down text-slate-400 transition-transform"></i>
                </button>
                <div class="hidden p-4 border-t border-slate-200 space-y-3 bg-white">
                    <div>
                        <span class="text-[10px] uppercase font-bold text-slate-400">Mặt trước</span>
                        <div class="text-sm text-slate-700 mt-1">${formatTextForHtml(cardContent.front)}</div>
                    </div>
                    <div class="pt-3 border-t border-slate-100">
                        <span class="text-[10px] uppercase font-bold text-slate-400">Mặt sau</span>
                        <div class="text-sm text-slate-700 mt-1">${formatTextForHtml(cardContent.back)}</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// --- Stats Modal & Display ---

function updateSessionSummary() {
    const sessionScore = window.sessionScore || 0;
    const currentUserTotalScore = window.currentUserTotalScore || 0;

    const desktopTotalScore = document.querySelector('.statistics-card #total-score-display span');
    const desktopSessionScore = document.querySelector('.statistics-card #session-score-display');

    const mobileTotalScore = document.getElementById('total-score-display-mobile');
    const mobileSessionScore = document.getElementById('session-score-display-mobile');

    if (desktopTotalScore) desktopTotalScore.textContent = currentUserTotalScore;
    if (desktopSessionScore) desktopSessionScore.textContent = `+${sessionScore}`;

    if (mobileTotalScore) mobileTotalScore.textContent = currentUserTotalScore;
    if (mobileSessionScore) mobileSessionScore.textContent = `+${sessionScore}`;
}

function displayCardStats(container, html) {
    if (!container) return;
    container.innerHTML = html;
    initializeStatsToggleListeners(container);
}

function initializeStatsToggleListeners(rootElement) {
    if (!rootElement) return;

    rootElement.querySelectorAll('[data-toggle]').forEach(toggleBtn => {
        if (toggleBtn.dataset.toggleListenerAttached === 'true') return;

        toggleBtn.addEventListener('click', function () {
            const content = this.nextElementSibling;
            this.classList.toggle('collapsed');

            if (!content) return;

            content.classList.toggle('open');

            if (content.classList.contains('open')) {
                content.style.maxHeight = content.scrollHeight + 'px';
            } else {
                content.style.maxHeight = null;
            }
        });

        toggleBtn.dataset.toggleListenerAttached = 'true';
    });
}

function toggleStatsModal(show) {
    const statsModal = document.getElementById('statsModal');
    const statsModalContent = document.getElementById('statsModalContent');

    if (show) {
        statsModal.classList.add('open');
        statsModalContent.classList.add('open');
        document.body.style.overflow = 'hidden';

        if (!statsModalContent.querySelector('.mobile-stats-container')) {
            const template = document.getElementById('mobile-stats-template');
            if (template) {
                statsModalContent.innerHTML = '';
                statsModalContent.appendChild(template.content.cloneNode(true));

                // Bind Events for Mobile Stats
                document.getElementById('close-stats-mobile-btn')?.addEventListener('click', () => toggleStatsModal(false));
                const endSessionBtn = document.getElementById('end-session-btn');
                document.getElementById('end-session-mobile-btn')?.addEventListener('click', () => endSessionBtn?.click());

                document.querySelectorAll('.stats-mobile-tab').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const targetId = e.currentTarget.dataset.target;
                        document.querySelectorAll('.stats-mobile-tab').forEach(t => t.classList.toggle('active', t === e.currentTarget));
                        document.querySelectorAll('.stats-mobile-pane').forEach(p => p.classList.toggle('hidden', p.id !== targetId));
                    });
                });
            }
        }

        updateSessionSummary();

        // We access global state from window. 
        // Note: session_manager updates these globals.
        const currentFlashcardBatch = window.currentFlashcardBatch || [];
        const currentFlashcardIndex = window.currentFlashcardIndex || 0;
        const currentCardData = currentFlashcardBatch.length > 0 ? currentFlashcardBatch[currentFlashcardIndex] : null;
        const mobileCurrentContainer = document.getElementById('current-card-stats-mobile');

        if (mobileCurrentContainer) {
            if (currentCardData && currentCardData.initial_stats) {
                const html = renderMobileCardStatsHtml(currentCardData.initial_stats, 0, currentCardData.content, true);
                mobileCurrentContainer.innerHTML = html;
            } else {
                mobileCurrentContainer.innerHTML = '<div class="flex flex-col items-center justify-center h-40 text-slate-400"><p>Chưa có dữ liệu.</p></div>';
            }
        }

        const mobilePrevContainer = document.getElementById('previous-card-stats-mobile');
        const previousCardStats = window.previousCardStats;
        if (mobilePrevContainer && previousCardStats) {
            const html = renderMobileCardStatsHtml(previousCardStats.stats, previousCardStats.scoreChange, previousCardStats.cardContent, false);
            mobilePrevContainer.innerHTML = html;
        }

    } else {
        statsModal.classList.remove('open');
        statsModalContent.classList.remove('open');
        document.body.style.overflow = '';
    }
}

// --- Utils: Custom Alert ---
function showCustomAlert(message) {
    const modalHtml = `<div id="custom-alert-modal" class="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50"><div class="bg-white p-6 rounded-lg shadow-xl max-w-sm w-full text-center"><p class="text-lg font-semibold text-gray-800 mb-4">${window.formatTextForHtml ? window.formatTextForHtml(message) : message}</p><button id="custom-alert-ok-btn" class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">OK</button></div></div>`;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    document.getElementById('custom-alert-ok-btn').addEventListener('click', () => document.getElementById('custom-alert-modal').remove());
}


// --- Feedback Animations ---


// --- AI Modal ---
function openAiModal(itemId, termContent) {
    const aiModal = document.getElementById('ai-modal');
    if (aiModal && aiModal.classList.contains('open')) {
        console.warn("AI modal đã được mở, bỏ qua lệnh gọi.");
        return;
    }

    const aiModalTerm = document.getElementById('ai-modal-term');

    window.currentAiItemId = itemId;
    if (aiModalTerm) aiModalTerm.textContent = termContent;
    aiModal.classList.add('open');

    if (window.fetchAiResponse) window.fetchAiResponse();
}

function closeAiModal() {
    const aiModal = document.getElementById('ai-modal');
    const aiResponseContainer = document.getElementById('ai-response-container');

    aiModal.classList.remove('open');
    window.currentAiItemId = null;
    if (aiResponseContainer) aiResponseContainer.innerHTML = `<div class="text-gray-500">Câu trả lời của AI sẽ xuất hiện ở đây.</div>`;
}

// --- Note Panel ---
let currentNoteItemId = null;
let lastLoadedNoteContent = '';

function setNoteMode(mode) {
    const noteViewSection = document.getElementById('note-view-section');
    const noteEditSection = document.getElementById('note-edit-section');
    const editNoteBtn = document.getElementById('edit-note-btn');
    const noteTextarea = document.getElementById('note-textarea');

    if (mode === 'view') {
        noteViewSection.classList.remove('note-panel-hidden');
        noteEditSection.classList.add('note-panel-hidden');
        if (editNoteBtn) editNoteBtn.classList.remove('note-panel-hidden');
    } else {
        noteViewSection.classList.add('note-panel-hidden');
        noteEditSection.classList.remove('note-panel-hidden');
        if (editNoteBtn) editNoteBtn.classList.add('note-panel-hidden');
        noteTextarea.focus();
    }
}

function updateNoteView(content) {
    lastLoadedNoteContent = content || '';
    const hasContent = lastLoadedNoteContent.trim().length > 0;
    const noteDisplay = document.getElementById('note-display');
    const noteTextarea = document.getElementById('note-textarea');

    noteDisplay.innerHTML = hasContent ? (window.formatTextForHtml ? window.formatTextForHtml(lastLoadedNoteContent) : lastLoadedNoteContent) : '<span class="italic text-gray-500">Chưa có ghi chú.</span>';
    noteTextarea.value = lastLoadedNoteContent;
    setNoteMode(hasContent ? 'view' : 'edit');
}

async function openNotePanel(itemId) {
    if (!itemId) return;
    const notePanel = document.getElementById('note-panel');
    const noteTextarea = document.getElementById('note-textarea');
    const editNoteBtn = document.getElementById('edit-note-btn');
    const getNoteUrl = window.FlashcardConfig.getNoteUrl;

    currentNoteItemId = itemId;
    notePanel.classList.add('open');

    noteTextarea.value = 'Đang tải ghi chú...';
    noteTextarea.disabled = true;
    if (editNoteBtn) editNoteBtn.classList.add('note-panel-hidden');


    try {
        const response = await fetch(getNoteUrl.replace('/0', `/${itemId}`));
        const result = await response.json();
        if (response.ok && result.success) {
            updateNoteView(result.content || '');
        } else {
            updateNoteView('');
        }
    } catch (error) {
        console.error('Lỗi khi tải ghi chú:', error);
        updateNoteView('');
    } finally {
        noteTextarea.disabled = false;
    }
}

function closeNotePanel() {
    const notePanel = document.getElementById('note-panel');
    const noteTextarea = document.getElementById('note-textarea');
    const editNoteBtn = document.getElementById('edit-note-btn');

    notePanel.classList.remove('open');
    currentNoteItemId = null;
    lastLoadedNoteContent = '';
    noteTextarea.value = '';
    if (editNoteBtn) editNoteBtn.classList.add('note-panel-hidden');

}

async function saveNote() {
    if (!currentNoteItemId) return;

    const noteTextarea = document.getElementById('note-textarea');
    const saveNoteBtn = document.getElementById('save-note-btn');
    const saveNoteUrl = window.FlashcardConfig.saveNoteUrl;
    const csrfHeaders = window.FlashcardConfig.csrfHeaders;

    const content = noteTextarea.value;
    saveNoteBtn.disabled = true;
    saveNoteBtn.textContent = 'Đang lưu...';

    try {
        const response = await fetch(saveNoteUrl.replace('/0', `/${currentNoteItemId}`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...csrfHeaders },
            body: JSON.stringify({ content: content })
        });
        const result = await response.json();
        if (response.ok && result.success) {
            window.showFlashMessage(result.message, 'success');
            updateNoteView(content);
        } else {
            window.showFlashMessage(result.message || 'Lỗi khi lưu ghi chú.', 'danger');
        }
    } catch (error) {
        console.error('Lỗi khi lưu ghi chú:', error);
        window.showFlashMessage('Lỗi kết nối khi lưu ghi chú.', 'danger');
    } finally {
        saveNoteBtn.disabled = false;
        saveNoteBtn.textContent = 'Lưu Ghi chú';
    }
}

function handleCancelNote() {
    if (lastLoadedNoteContent.trim()) {
        setNoteMode('view');
    } else {
        closeNotePanel();
    }
}


// Export
window.initUiSettings = initUiSettings;
window.setVh = setVh;
window.renderCard = renderCard;
window.displayCardStats = displayCardStats;
window.renderCardStatsHtml = renderCardStatsHtml;
window.renderMobileCardStatsHtml = renderMobileCardStatsHtml;
window.updateSessionSummary = updateSessionSummary;
window.setFlashcardContent = setFlashcardContent;
window.getVisibleFlashcardContentDiv = getVisibleFlashcardContentDiv;
window.setMediaHiddenState = setMediaHiddenState;
window.isMediaHidden = isMediaHidden;
window.showStats = showStats;
window.openAiModal = openAiModal;
window.closeAiModal = closeAiModal;
window.openNotePanel = openNotePanel;
window.closeNotePanel = closeNotePanel;
window.saveNote = saveNote;
window.handleCancelNote = handleCancelNote;
window.setNoteMode = setNoteMode;
window.toggleStatsModal = toggleStatsModal;
window.showCustomAlert = showCustomAlert;
window.adjustCardLayout = adjustCardLayout;
window.determineCardCategory = determineCardCategory;
window.closeAllSettingsMenus = closeAllSettingsMenus;
window.toggleSettingsMenu = toggleSettingsMenu;


Object.defineProperty(window, 'isMediaHidden', {
    get: () => isMediaHidden,
    set: (val) => isMediaHidden = val,
    configurable: true
});
Object.defineProperty(window, 'showStats', {
    get: () => showStats,
    set: (val) => showStats = val,
    configurable: true
});
Object.defineProperty(window, 'flashcardSessionStats', {
    get: () => window._fStats,
    set: (val) => { window._fStats = val; },
    configurable: true
});

/**
 * Cập nhật các chỉ số RPG HUD ("THẺ NÀY" box)
 * @param {Object} stats - Dữ liệu thống kê từ backend
 */
window.updateCardHudStats = function (stats) {
    if (!stats) return;

    // 1. Memory Power (Percentage)
    const memPowerEls = document.querySelectorAll('.js-fc-memory-score');
    memPowerEls.forEach(el => {
        const val = stats.memory_power || 0;
        el.textContent = val + '%';

        // Optional: color based on value
        if (val >= 90) el.className = 'hud-value-lg text-emerald-500 js-fc-memory-score';
        else if (val >= 70) el.className = 'hud-value-lg text-purple-600 js-fc-memory-score';
        else if (val >= 40) el.className = 'hud-value-lg text-indigo-600 js-fc-memory-score';
        else el.className = 'hud-value-lg text-slate-500 js-fc-memory-score';
    });

    // 2. Correct Count for this card
    const correctEls = document.querySelectorAll('.js-fc-card-right');
    correctEls.forEach(el => {
        el.textContent = stats.correct_count || 0;
    });

    // 3. Incorrect Count for this card
    const incorrectEls = document.querySelectorAll('.js-fc-card-wrong');
    incorrectEls.forEach(el => {
        el.textContent = (stats.incorrect_count || 0) + (stats.vague_count || 0);
    });
};
// --- Marker Interactions (Difficult, Ignore, Favorite) ---

function setupMarkerHandlers() {
    // 1. Toggle Dropdown
    document.addEventListener('click', function (e) {
        const toggleBtn = e.target.closest('.js-fc-marker-toggle');
        if (toggleBtn) {
            e.stopPropagation();
            const container = toggleBtn.closest('.marker-dropdown-container') || toggleBtn.closest('.relative');
            const dropdown = container.querySelector('.marker-dropdown') || container.querySelector('.js-fc-marker-menu');

            // Close other open markers
            document.querySelectorAll('.marker-dropdown, .js-fc-marker-menu').forEach(d => {
                if (d !== dropdown) d.classList.add('hidden')
                if (d !== dropdown) d.classList.remove('show'); // Mobile uses 'show'
            });

            if (dropdown) {
                if (dropdown.classList.contains('js-fc-marker-menu')) {
                    dropdown.classList.toggle('show'); // Mobile
                } else {
                    dropdown.classList.toggle('hidden'); // Desktop
                }
            }
        } else {
            // Click outside - close all
            if (!e.target.closest('.marker-dropdown') && !e.target.closest('.js-fc-marker-menu')) {
                document.querySelectorAll('.marker-dropdown').forEach(d => d.classList.add('hidden'));
                document.querySelectorAll('.js-fc-marker-menu').forEach(d => d.classList.remove('show'));
            }
        }
    });

    // 2. Handle Marker Actions
    const markerTypes = ['difficult', 'ignored', 'favorite'];
    markerTypes.forEach(type => {
        document.addEventListener('click', function (e) {
            const btn = e.target.closest(`.js-fc-mark-${type}`);
            if (btn) {
                e.stopPropagation();
                if (window.currentFlashcardBatch && typeof window.currentFlashcardIndex !== 'undefined') {
                    const card = window.currentFlashcardBatch[window.currentFlashcardIndex];
                    if (card && card.item_id) {
                        toggleMarker(card.item_id, type, btn);
                    }
                }
                // Close dropdowns
                document.querySelectorAll('.marker-dropdown').forEach(d => d.classList.add('hidden'));
                document.querySelectorAll('.js-fc-marker-menu').forEach(d => d.classList.remove('show'));
            }
        });
    });
}

function toggleMarker(itemId, markerType, btnElement) {
    if (!itemId || !markerType) return;

    // Optimistic UI Update (optional, but API is fast enough usually)
    // Send API Request
    fetch('/api/v3/learning/markers/toggle', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.csrfToken || '' // Ensure CSRF if needed
        },
        body: JSON.stringify({ item_id: itemId, marker_type: markerType })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log(`Marker ${markerType} toggled: ${data.is_marked}`);
                updateMarkerUI(markerType, data.is_marked);
                // Show toast/notification
                if (window.showToast) {
                    const action = data.is_marked ? 'Đã đánh dấu' : 'Đã bỏ đánh dấu';
                    let label = markerType;
                    if (markerType === 'difficult') label = 'Khó';
                    if (markerType === 'ignored') label = 'Bỏ qua';
                    if (markerType === 'favorite') label = 'Yêu thích';
                    window.showToast(`${action} ${label}`, 'success');
                }
            } else {
                console.error('Marker toggle failed:', data.message);
            }
        })
        .catch(err => console.error('Error toggling marker:', err));
}

function updateMarkerUI(markerType, isMarked) {
    // Determine visuals based on type
    let iconClass = '';
    let activeClass = ''; // Class to add to the button if active

    if (markerType === 'difficult') {
        iconClass = 'fa-fire text-orange-500';
        activeClass = 'bg-orange-100 font-bold';
    } else if (markerType === 'ignored') {
        iconClass = 'fa-eye-slash text-slate-500';
        activeClass = 'bg-slate-200 font-bold';
    } else if (markerType === 'favorite') {
        iconClass = 'fa-heart text-rose-500';
        activeClass = 'bg-rose-100 font-bold';
    }

    // Update buttons in dropdown
    const btns = document.querySelectorAll(`.js-fc-mark-${markerType}`);
    btns.forEach(btn => {
        if (isMarked) {
            btn.classList.add(...activeClass.split(' '));
            // Change icon to solid if applicable
            const icon = btn.querySelector('i');
            if (icon) {
                icon.classList.remove('far');
                icon.classList.add('fas');
            }
        } else {
            btn.classList.remove(...activeClass.split(' '));
            const icon = btn.querySelector('i');
            if (icon) {
                icon.classList.remove('fas');
                icon.classList.add('far'); // Back to regular
                if (markerType === 'difficult') icon.className = 'far fa-tired text-orange-500 mr-2 w-4'; // Reset specific classes if needed
                if (markerType === 'ignored') icon.className = 'far fa-eye-slash text-slate-400 mr-2 w-4';
                if (markerType === 'favorite') icon.className = 'far fa-heart text-rose-500 mr-2 w-4';
            }
        }
    });

    // Update main toggle button icon if any marker is active (prioritize difficult > favorite > ignored)
    updateMainMarkerIcon();
}

function updateMainMarkerIcon() {
    // This is tricky because we need to know the state of ALL markers for the current card.
    // We should probably fetch or store this state.
    // simpler: If user just clicked, we know that one changed.
    // But for full sync, we need item state.
}

// Call init
setupMarkerHandlers();

function applyMarkers(markers) {
    // Reset all first
    ['difficult', 'ignored', 'favorite'].forEach(type => updateMarkerUI(type, false));

    if (Array.isArray(markers)) {
        markers.forEach(type => updateMarkerUI(type, true));
    }
    updateMainMarkerIcon();
}

// Hook into flashcard loading
document.addEventListener('flashcardStatsUpdated', function (e) {
    // Note: 'flashcardStatsUpdated' usually passes stats, not full item data.
    // We need to access the current batch item.
    if (window.currentFlashcardBatch && typeof window.currentFlashcardIndex !== 'undefined') {
        const card = window.currentFlashcardBatch[window.currentFlashcardIndex];
        if (card && card.markers) {
            applyMarkers(card.markers);
        } else {
            applyMarkers([]);
        }
    }
});

// =========================================
// [UX-FIX] Notification Lifecycle Handlers
// =========================================

// Track if we should defer audio playback
let pendingAudioAutoplay = false;

// When notification starts: hide card content and bottom bar
document.addEventListener('notificationStart', function () {
    console.log('[Notification] Start - hiding card content');
    const mobileView = document.querySelector('.flashcard-mobile-view');
    if (mobileView) {
        mobileView.classList.add('notification-active');
    }
    // Also hide bottom bar explicitly for safety
    const bottomBar = document.querySelector('.fc-bottom-bar');
    if (bottomBar) {
        bottomBar.style.display = 'none';
    }
    // Set flag so renderCard knows to defer audio
    pendingAudioAutoplay = true;
});

// When notification completes: show card content and play audio
document.addEventListener('notificationComplete', function () {
    console.log('[Notification] Complete - showing card content');
    const mobileView = document.querySelector('.flashcard-mobile-view');
    if (mobileView) {
        mobileView.classList.remove('notification-active');
    }
    // Show bottom bar again
    const bottomBar = document.querySelector('.fc-bottom-bar');
    if (bottomBar) {
        bottomBar.style.display = '';
    }
    // Reset flip button visibility
    const flipBtn = document.querySelector('.js-fc-flip-btn');
    if (flipBtn) {
        flipBtn.style.display = '';
    }
    // Hide rating buttons
    const ratingBtns = document.querySelector('.js-fc-rating-btns');
    if (ratingBtns) {
        ratingBtns.classList.remove('show');
    }

    // Now trigger audio autoplay if enabled
    setTimeout(() => {
        if (pendingAudioAutoplay) {
            pendingAudioAutoplay = false;
            const isAutoplaySession = window.FlashcardConfig && window.FlashcardConfig.isAutoplaySession;
            if (isAutoplaySession) {
                if (window.startAutoplaySequence) window.startAutoplaySequence();
            } else {
                if (window.autoPlayFrontSide) window.autoPlayFrontSide();
            }
        }
    }, 100); // Small delay to let card fully render
});

// Export for external access using getter/setter for live value
Object.defineProperty(window, 'pendingAudioAutoplay', {
    get: () => pendingAudioAutoplay,
    set: (val) => { pendingAudioAutoplay = val; },
    configurable: true
});

