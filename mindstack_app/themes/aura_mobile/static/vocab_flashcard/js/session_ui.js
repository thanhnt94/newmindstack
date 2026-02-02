(function () {
    console.warn('[FSRS Mobile] session_ui.js LOADED (Inline Handler Version)');

    // --- Mobile Logic & Events ---

    // 1. Define global handler for inline onclick
    window.onMobileRatingClick = function (ratingValue) {
        if (window.hidePreviewTooltip) window.hidePreviewTooltip();
        console.log('[FSRS Mobile] Button clicked via inline handler:', ratingValue);

        // Map rating to answer strings
        const answerMap = { '1': 'again', '2': 'hard', '3': 'good', '4': 'easy' };
        const answerValue = answerMap[ratingValue] || 'good';

        if (window.currentFlashcardBatch &&
            typeof window.currentFlashcardIndex !== 'undefined' &&
            typeof window.submitFlashcardAnswer === 'function') {

            const card = window.currentFlashcardBatch[window.currentFlashcardIndex];
            if (card && card.item_id) {
                console.log('[FSRS Mobile] Submitting answer:', answerValue);
                window.submitFlashcardAnswer(card.item_id, answerValue);
            } else {
                console.error('[FSRS Mobile] No current card found');
            }
        } else {
            console.error('[FSRS Mobile] submitFlashcardAnswer not found or batch empty');
        }

        // UI Reset
        const flipBtn = document.querySelector('.fc-flip-btn');
        const ratingBtnsContainer = document.querySelector('.fc-rating-btns');
        setTimeout(() => {
            if (flipBtn) flipBtn.style.display = 'flex';
            if (ratingBtnsContainer) ratingBtnsContainer.classList.remove('show');
        }, 100);
    };

    // Helper to get mobile stats container safely
    function getMobileStatsContainer() {
        // Check if template is already stamped
        const container = document.querySelector('.mobile-stats-container');
        if (container) return container;

        // Otherwise, clone from template
        const tmpl = document.getElementById('mobile-stats-template');
        if (tmpl) {
            return null;
        }
        return null;
    }

    // Helper to get user button count safely
    function getUserButtonCount() {
        return (window.FlashcardConfig && window.FlashcardConfig.userButtonCount) || window.userButtonCount || 4;
    }

    // Generate rating buttons (Strictly 4 buttons for Aura Mobile)
    function generateMobileRatingButtons() {
        const container = document.getElementById('mobile-rating-btns');
        if (!container) return;

        // Force 4 buttons regardless of user setting for consistency in Aura Mobile
        const buttons = [
            { cssClass: 'again', value: '1', label: 'Học lại', icon: 'fas fa-undo' },
            { cssClass: 'hard', value: '2', label: 'Khó', icon: 'fas fa-fire' },
            { cssClass: 'good', value: '3', label: 'Ổn', icon: 'fas fa-thumbs-up' },
            { cssClass: 'easy', value: '4', label: 'Dễ', icon: 'fas fa-smile' }
        ];

        // Use inline onclick to guarantee event firing
        container.innerHTML = buttons.map(btn =>
            `<button class="fc-rating-btn ${btn.cssClass} js-rating-btn" 
                     data-rating="${btn.value}"
                     onclick="window.onMobileRatingClick('${btn.value}')">
                    <i class="${btn.icon}"></i>
                    <span>${btn.label}</span>
                </button>`
        ).join('');
    }

    // Run once
    generateMobileRatingButtons();

    // Listen for flip/show/next events to toggle bottom bar buttons
    document.addEventListener('flashcardFlipped', function (e) {
        const isBack = e.detail && e.detail.side === 'back';
        const flipBtn = document.querySelector('.fc-flip-btn');
        const ratingBtns = document.querySelector('.fc-rating-btns');

        if (flipBtn && ratingBtns) {
            if (isBack) {
                flipBtn.style.display = 'none';
                ratingBtns.classList.add('show');

                // [PROACTIVE] When user flips a card, it's the perfect time to prefetch 
                // the NEXT items because the user will spend a few seconds reading the back.
                if (window.prefetchAudioForUpcomingCards) {
                    console.log('[FSRS Mobile] Card flipped - Triggering proactive prefetch for next 2 cards');
                    window.prefetchAudioForUpcomingCards(2);
                }
            } else {
                flipBtn.style.display = 'flex';
                ratingBtns.classList.remove('show');
            }
        }
    });

    // Flip button in sticky bottom bar
    const bottomFlipBtn = document.querySelector('.fc-flip-btn');
    if (bottomFlipBtn) {
        bottomFlipBtn.addEventListener('click', function () {
            if (window.flipCard) window.flipCard();
        });
    }

    // Stats Modal Logic
    const statsModalOverlay = document.getElementById('stats-mobile-modal');

    document.addEventListener('click', function (e) {
        if (e.target.closest('.open-stats-modal-btn') || e.target.closest('.js-fc-stats-toggle-mobile')) {
            openStatsModal();
        }
    });

    const closeStatsBtn = document.getElementById('close-stats-mobile-btn');
    if (closeStatsBtn) {
        closeStatsBtn.addEventListener('click', closeStatsModal);
    }

    function openStatsModal() {
        if (statsModalOverlay) {
            statsModalOverlay.classList.add('open');
            const content = statsModalOverlay.querySelector('.stats-modal-content');
            if (content) content.classList.add('open');
        }
    }

    function closeStatsModal() {
        if (statsModalOverlay) {
            const content = statsModalOverlay.querySelector('.stats-modal-content');
            if (content) content.classList.remove('open');
            setTimeout(() => {
                statsModalOverlay.classList.remove('open');
            }, 300);
        }
    }

    // Tab Switching in Mobile Stats
    const tabBtns = document.querySelectorAll('.stats-mobile-tab');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            // active class
            tabBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            // show target pane
            const targetId = this.dataset.target;
            document.querySelectorAll('.stats-mobile-pane').forEach(p => p.classList.add('hidden'));
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.remove('hidden');
                targetPane.classList.add('active');
            }
        });
    });

    // End session button in mobile modal
    const endSessionMobileBtn = document.getElementById('end-session-mobile-btn');
    if (endSessionMobileBtn) {
        endSessionMobileBtn.addEventListener('click', function () {
            if (window.endSession) window.endSession();
        });
    }

    // Fix for iOS Safari 100vh issue
    const setAppHeight = () => {
        const doc = document.documentElement;
        doc.style.setProperty('--app-height', `${window.innerHeight}px`);
    };
    window.addEventListener('resize', setAppHeight);
    setAppHeight();

    // Note button in header - open note panel for current card
    const noteBtn = document.querySelector('.js-fc-note-btn');
    if (noteBtn) {
        noteBtn.addEventListener('click', function () {
            if (window.currentFlashcardBatch &&
                typeof window.currentFlashcardIndex !== 'undefined' &&
                typeof window.openNotePanel === 'function') {
                const card = window.currentFlashcardBatch[window.currentFlashcardIndex];
                if (card && card.item_id) {
                    window.openNotePanel(card.item_id);
                }
            }
        });
    }

    // Settings dropdown toggle
    const settingsToggle = document.querySelector('.js-fc-settings-toggle');
    const settingsMenu = document.querySelector('.js-fc-settings-menu');

    if (settingsToggle && settingsMenu) {
        settingsToggle.addEventListener('click', function (e) {
            e.stopPropagation();
            settingsMenu.classList.toggle('show');
        });

        // Close when clicking outside
        document.addEventListener('click', function () {
            settingsMenu.classList.remove('show');
        });

        settingsMenu.addEventListener('click', function (e) {
            e.stopPropagation();
        });
    }

    // Image toggle with dynamic text/icon
    const imageToggleBtn = document.querySelector('.js-fc-image-toggle');
    const imageIcon = document.querySelector('.js-fc-image-icon');
    const imageText = document.querySelector('.js-fc-image-text');

    // Get initial state from localStorage
    const storedImageHidden = localStorage.getItem('flashcardHideImages');
    let isImageHidden = storedImageHidden === 'true';

    function updateImageToggleUI() {
        // Update header toggle button
        if (imageIcon) {
            imageIcon.className = isImageHidden ? 'fas fa-eye js-fc-image-icon' : 'fas fa-eye-slash js-fc-image-icon';
        }
        if (imageText) {
            imageText.textContent = isImageHidden ? 'Hiện ảnh' : 'Ẩn ảnh';
        }

        // Update overlay toggle button icon
        const overlayIcon = document.querySelector('.js-fc-image-icon-overlay');
        if (overlayIcon) {
            overlayIcon.className = isImageHidden ? 'fas fa-eye text-sm js-fc-image-icon-overlay' : 'fas fa-image text-sm js-fc-image-icon-overlay';
        }
    }

    function applyImageVisibility() {
        const mediaContainers = document.querySelectorAll('.media-container');
        mediaContainers.forEach(container => {
            container.style.display = isImageHidden ? 'none' : '';
        });
    }

    // Apply initial state
    applyImageVisibility();
    updateImageToggleUI();

    // Header image toggle button
    if (imageToggleBtn) {
        imageToggleBtn.addEventListener('click', function () {
            isImageHidden = !isImageHidden;
            localStorage.setItem('flashcardHideImages', isImageHidden);
            applyImageVisibility();
            updateImageToggleUI();

            // [FIX] Sync to server
            if (window.updateVisualSettings) {
                window.updateVisualSettings({ show_image: !isImageHidden });
            }
        });
    }

    // Overlay image toggle button
    document.addEventListener('click', function (e) {
        const overlayImageBtn = e.target.closest('.js-fc-image-toggle-overlay');
        if (overlayImageBtn) {
            isImageHidden = !isImageHidden;
            localStorage.setItem('flashcardHideImages', isImageHidden);
            applyImageVisibility();
            updateImageToggleUI();

            // [FIX] Sync to server
            if (window.updateVisualSettings) {
                window.updateVisualSettings({ show_image: !isImageHidden });
            }
        }
    });

    // Item stats detail button in card overlay
    document.addEventListener('click', function (e) {
        const statsDetailBtn = e.target.closest('.js-fc-stats-detail-overlay');
        if (statsDetailBtn) {
            if (window.currentFlashcardBatch &&
                typeof window.currentFlashcardIndex !== 'undefined') {
                const card = window.currentFlashcardBatch[window.currentFlashcardIndex];
                if (card && card.item_id) {
                    if (typeof window.openVocabularyItemStats === 'function') {
                        window.openVocabularyItemStats(card.item_id);
                    } else {
                        // Fallback to iframe modal if specialized modal not found
                        const urlTemplate = (window.FlashcardConfig && window.FlashcardConfig.itemStatsUrlTemplate) || "";
                        if (urlTemplate) {
                            const statsUrl = urlTemplate.replace('/0', '/' + card.item_id) + '?is_modal=true';
                            if (typeof window.openModal === 'function') {
                                window.openModal(statsUrl);
                            } else if (window.parent && typeof window.parent.openModal === 'function') {
                                window.parent.openModal(statsUrl);
                            }
                        }
                    }
                }
            }
        }
    });

    // Re-apply image visibility when new cards load
    document.addEventListener('flashcardStatsUpdated', function () {
        setTimeout(applyImageVisibility, 100);
    });

    // Audio autoplay toggle with dynamic text/icon
    const autoplayToggleBtn = document.querySelector('.js-fc-autoplay-toggle');
    const autoplayIcon = document.querySelector('.js-fc-autoplay-icon');
    const autoplayText = document.querySelector('.js-fc-autoplay-text');

    // Get initial state from localStorage
    const storedAutoplay = localStorage.getItem('flashcardAutoplayAudio');
    let isAutoplayOn = storedAutoplay === 'true';

    function updateAutoplayToggleUI() {
        if (autoplayIcon) {
            // When ON: show volume-up (audio playing), when OFF: show volume-mute (audio off)
            autoplayIcon.className = isAutoplayOn ? 'fas fa-volume-up js-fc-autoplay-icon' : 'fas fa-volume-mute js-fc-autoplay-icon';
        }
        if (autoplayText) {
            autoplayText.textContent = isAutoplayOn ? 'Tắt tự động' : 'Tự động phát';
        }
    }
    updateAutoplayToggleUI();

    if (autoplayToggleBtn) {
        autoplayToggleBtn.addEventListener('click', function () {
            isAutoplayOn = !isAutoplayOn;
            localStorage.setItem('flashcardAutoplayAudio', isAutoplayOn);
            // Try to call global toggle function if exists
            if (typeof window.toggleAudioAutoplay === 'function') {
                window.toggleAudioAutoplay();
            }
            updateAutoplayToggleUI();

            // [FIX] Sync to server
            if (window.updateVisualSettings) {
                window.updateVisualSettings({ autoplay: isAutoplayOn });
            }
        });
    }

    // Stats row toggle
    const statsToggleBtn = document.querySelector('.js-fc-stats-toggle');
    const statsIcon = document.querySelector('.js-fc-stats-icon');
    const statsText = document.querySelector('.js-fc-stats-text');
    const statsRow = document.querySelector('.fc-stats-row');
    let isStatsHidden = false;

    function updateStatsToggleUI() {
        if (statsIcon) {
            statsIcon.className = isStatsHidden ? 'fas fa-chart-line js-fc-stats-icon' : 'fas fa-chart-line js-fc-stats-icon';
        }
        if (statsText) {
            statsText.textContent = isStatsHidden ? 'Hiện tiến độ' : 'Ẩn tiến độ';
        }
        if (statsRow) {
            statsRow.style.display = isStatsHidden ? 'none' : 'flex';
        }
    }

    if (statsToggleBtn) {
        statsToggleBtn.addEventListener('click', function () {
            isStatsHidden = !isStatsHidden;
            updateStatsToggleUI();

            // [FIX] Sync to server
            if (window.updateVisualSettings) {
                window.updateVisualSettings({ show_stats: !isStatsHidden });
            }
        });
    }

    // Feedback button - call existing function
    const feedbackBtn = document.querySelector('.js-fc-feedback-btn');
    if (feedbackBtn) {
        feedbackBtn.addEventListener('click', function () {
            if (typeof window.openFeedbackModal === 'function' &&
                window.currentFlashcardBatch &&
                typeof window.currentFlashcardIndex !== 'undefined') {
                const card = window.currentFlashcardBatch[window.currentFlashcardIndex];
                if (card) {
                    window.openFeedbackModal(card.item_id, card.content?.front || '');
                }
            }
        });
    }

    // Edit button - construct URL and open modal
    const editBtn = document.querySelector('.js-fc-edit-btn');
    if (editBtn) {
        // Use config provided by session_init.js
        const editUrlTemplate = (window.FlashcardConfig && window.FlashcardConfig.editFlashcardUrlTemplate) || "";
        editBtn.addEventListener('click', function () {
            if (window.currentFlashcardBatch &&
                typeof window.currentFlashcardIndex !== 'undefined') {
                const card = window.currentFlashcardBatch[window.currentFlashcardIndex];
                if (card && card.item_id && card.container_id) {
                    // Replace placeholder IDs with actual values
                    const editUrl = editUrlTemplate.replace('/0', '/' + card.container_id).replace('/0', '/' + card.item_id) + '?is_modal=true';
                    if (typeof window.openModal === 'function') {
                        window.openModal(editUrl);
                    } else if (window.parent && typeof window.parent.openModal === 'function') {
                        window.parent.openModal(editUrl);
                    } else {
                        // Fallback: navigate directly
                        window.location.href = editUrl;
                    }
                }
            }
        });
    }

    // Render session answer history as compact icons in mobile stats
    function renderSessionHistoryList() {
        const container = document.getElementById('session-history-icons-mobile');
        if (!container) return;

        const history = window.sessionAnswerHistory || [];

        if (history.length === 0) {
            container.innerHTML = `<span class="text-xs text-slate-300">Chưa có dữ liệu</span>`;
            return;
        }

        // Render compact icons - green check for correct, red x for wrong
        const iconsHtml = history.map((item, index) => {
            const isCorrect = item.scoreChange > 0;
            const isWrong = item.scoreChange < 0;
            const colorClass = isCorrect ? 'bg-emerald-500' : (isWrong ? 'bg-rose-500' : 'bg-slate-400');
            const icon = isCorrect ? 'fa-check' : (isWrong ? 'fa-times' : 'fa-minus');
            const num = index + 1;
            const scoreText = item.scoreChange > 0 ? `+${item.scoreChange}` : item.scoreChange;

            return `<span class="history-icon w-6 h-6 rounded-full ${colorClass} flex items-center justify-center cursor-pointer hover:ring-2 hover:ring-offset-1 hover:ring-slate-300 transition-all"
                    data-num="${num}"
                    data-front="${item.front.replace(/"/g, '&quot;')}"
                    data-answer="${item.answer}"
                    data-score="${scoreText}"
                    data-time="${item.timestamp}">
                    <i class="fas ${icon} text-white text-[10px]"></i>
                </span>`;
        }).join('');

        container.innerHTML = iconsHtml;

        // Add click handlers for tooltip
        container.querySelectorAll('.history-icon').forEach(icon => {
            icon.addEventListener('click', function (e) {
                e.stopPropagation();
                showHistoryTooltip(this);
            });
        });
    }

    // Show tooltip for history icon
    function showHistoryTooltip(iconEl) {
        // Remove existing tooltip
        const existingTooltip = document.querySelector('.history-tooltip');
        if (existingTooltip) existingTooltip.remove();

        const num = iconEl.dataset.num;
        const front = iconEl.dataset.front;
        const answer = iconEl.dataset.answer;
        const score = iconEl.dataset.score;
        const timestamp = parseInt(iconEl.dataset.time);
        const timeStr = timestamp ? new Date(timestamp).toLocaleString('vi-VN', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit', second: '2-digit'
        }) : '';
        const scoreClass = score.startsWith('+') ? 'text-emerald-600' : (score.startsWith('-') ? 'text-rose-600' : 'text-slate-500');

        const tooltip = document.createElement('div');
        tooltip.className = 'history-tooltip absolute z-50 bg-white rounded-xl shadow-lg border border-slate-200 p-3 min-w-[200px] max-w-[280px]';
        tooltip.innerHTML = `
                <div class="flex items-center justify-between mb-2">
                    <span class="text-xs font-bold text-slate-400">#${num}</span>
                    <span class="${scoreClass} font-bold text-sm">${score} điểm</span>
                </div>
                <p class="text-sm font-semibold text-slate-800 mb-1">${front}</p>
                <p class="text-xs text-slate-500">Đáp án: <span class="font-medium">${answer}</span></p>
                ${timeStr ? `<p class="text-xs text-slate-400 mt-1"><i class="fas fa-clock mr-1"></i>${timeStr}</p>` : ''}
            `;

        // Position tooltip
        const rect = iconEl.getBoundingClientRect();
        const container = document.getElementById('session-history-icons-mobile').parentElement;
        container.style.position = 'relative';
        container.appendChild(tooltip);

        // Close tooltip when clicking outside
        setTimeout(() => {
            document.addEventListener('click', function closeTooltip() {
                tooltip.remove();
                document.removeEventListener('click', closeTooltip);
            });
        }, 10);
    }

    // Update history when new card is answered
    document.addEventListener('flashcardStatsUpdated', function () {
        renderSessionHistoryList();
    });

    // [REFACTOR] Update rating buttons with FSRS intervals via Backend API
    window.updateRatingButtonEstimates = function (cardData) {
        // console.log('[FSRS Mobile] updateRatingButtonEstimates called', cardData);
        if (!cardData) return;

        const itemId = cardData.item_id;
        if (!itemId) return;

        // Ensure buttons are generated
        const btnContainer = document.getElementById('mobile-rating-btns');
        if (btnContainer && btnContainer.children.length === 0) {
            generateMobileRatingButtons();
        }

        const buttons = document.querySelectorAll('.js-rating-btn');

        // Clear previous badges/tooltips first
        buttons.forEach(btn => {
            const existingBadge = btn.querySelector('.fc-time-badge');
            if (existingBadge) existingBadge.remove();

            // Clean up title (remove old interval text like "(3d)")
            const titleSpan = btn.querySelector('span');
            if (titleSpan) {
                const baseLabel = btn.getAttribute('data-base-label');
                if (baseLabel) {
                    titleSpan.textContent = baseLabel;
                } else {
                    // Start fresh if no base label saved yet
                    const text = titleSpan.textContent;
                    if (text.includes('(')) {
                        const clean = text.split('(')[0].trim();
                        btn.setAttribute('data-base-label', clean);
                        titleSpan.textContent = clean;
                    } else {
                        btn.setAttribute('data-base-label', text);
                    }
                }
            }

            // Reset tooltip logic
            btn.onmouseenter = null;
            btn.onmouseleave = null;
        });

        // Function to update UI with data
        const applyPreviewData = (previews) => {
            buttons.forEach(btn => {
                const rating = btn.dataset.rating; // "1", "2", "3", "4"
                const info = previews[rating];

                if (info) {
                    // Update Time Badge/Text
                    const timeText = info.interval;
                    const titleSpan = btn.querySelector('span');
                    if (titleSpan && timeText) {
                        const baseLabel = btn.getAttribute('data-base-label');
                        titleSpan.textContent = `${baseLabel} (${timeText})`;
                        titleSpan.style.whiteSpace = 'nowrap';
                    }

                    // Setup Tooltip with actual data

                    // [REMOVED] Tooltip disabled by user request (Step 184)
                    // const handleShowTooltip = () => { ... };
                    // btn.onmouseenter = handleShowTooltip;
                    // ...

                    // Clear any existing listeners if needed, but for now just don't add them.
                    btn.onmouseenter = null;
                    btn.onmouseleave = null;
                }
            });
        };

        // Check Cache first?
        // Actually, let's just fetch. It's fast.

        // Call Backend API
        fetch('/learn/vocab-flashcard/api/preview_fsrs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(window.FlashcardConfig && window.FlashcardConfig.csrfHeaders ? window.FlashcardConfig.csrfHeaders : {})
            },
            body: JSON.stringify({ item_id: itemId })
        })
            .then(res => res.json())
            .then(data => {
                if (data.success && data.previews) {
                    applyPreviewData(data.previews);
                }
            })
            .catch(err => console.error("Error fetching FSRS preview:", err));

    };

    // Update stats from custom event dispatched by main script
    document.addEventListener('flashcardStatsUpdated', function (e) {
        if (e.detail) {
            updateMobileStats(e.detail);
        }
    });

    function updateMobileStats(stats) {
        if (!stats) return;

        // 1. Session Progress (Left Header: 0/0)
        // Selectors: .js-fc-progress-text, .js-fc-answered-count
        if (stats.total > 0) {
            const percent = Math.min(100, Math.round((stats.processed / stats.total) * 100));
            document.querySelectorAll('.js-fc-progress-fill').forEach(el => el.style.width = percent + '%');

            const progressText = `${stats.processed}/${stats.total}`;
            document.querySelectorAll('.js-fc-progress-text').forEach(el => el.textContent = progressText);

            // Also update any standalone counters
            document.querySelectorAll('.js-fc-answered-count').forEach(el => el.textContent = stats.processed);
            document.querySelectorAll('.js-fc-total-count').forEach(el => el.textContent = stats.total);
        }

        // 2. Session Correct Count (Green Check)
        document.querySelectorAll('.js-fc-session-correct').forEach(el => {
            el.textContent = stats.correct || 0;
        });

        // 3. Session Points (Diamond)
        document.querySelectorAll('.js-fc-session-points').forEach(el => {
            const val = stats.session_score || 0;
            const sign = val > 0 ? '+' : '';
            el.textContent = sign + val;
        });

        // [FIX] Update Global Score Header
        if (typeof window.currentUserTotalScore !== 'undefined') {
            document.querySelectorAll('.js-fc-score').forEach(el => {
                // Determine animation or direct set
                // For now, direct set formatted with commas
                el.textContent = window.currentUserTotalScore.toLocaleString('en-US');
            });
        }

        // 4. Secondary Row Stats (Current Card Context)

        // 4a. Streak (Fire)
        document.querySelectorAll('.js-fc-streak-count').forEach(el => {
            el.textContent = stats.streak || 0;
        });

        // 4d. Difficulty (D)
        document.querySelectorAll('.js-fc-difficulty-val, .js-card-overlay-difficulty').forEach(el => {
            const val = stats.difficulty !== undefined ? parseFloat(stats.difficulty).toFixed(1) :
                (stats.easiness_factor !== undefined ? parseFloat(stats.easiness_factor).toFixed(1) : '0.0');
            el.textContent = val;
        });

        // 4e. Stability (S)
        document.querySelectorAll('.js-fc-stability-days, .js-card-overlay-stability').forEach(el => {
            const val = stats.stability !== undefined ? parseFloat(stats.stability).toFixed(1) : '0';
            // If it's 0.0, show 0
            el.textContent = (val === '0.0' || val === '0.00') ? '0' : val;
        });

        // 4f. Retention (R)
        document.querySelectorAll('.js-fc-retention-percent, .js-card-overlay-retrievability').forEach(el => {
            const val = stats.retrievability !== undefined ? Math.round(stats.retrievability) : 0;
            el.textContent = val;
        });

        // 4g. Review Counts (Refresh Icon)
        document.querySelectorAll('.js-fc-review-count').forEach(el => {
            el.textContent = (stats.times_reviewed || 0) + ' lần';
        });

        // 5. State Badge (MỚI / learning...) - controlled by updateStateBadge
        // converting status 'new', 'learning', etc to display text happens in updateStateBadge
        // We can call it here if we have status
        if (stats.status && window.updateStateBadge) {
            window.updateStateBadge(stats.status);
        }
    }

    // --- Smart Transition Helpers ---

    window.hideRatingButtons = function () {
        const ratingBtns = document.querySelector('.fc-rating-btns');
        if (ratingBtns) {
            // Use opacity for immediate visual feedback without layout shift
            ratingBtns.style.opacity = '0';
            ratingBtns.style.pointerEvents = 'none'; // Disable clicks
        }
        const bottomFlipBtn = document.querySelector('.fc-flip-btn');
        if (bottomFlipBtn) {
            bottomFlipBtn.style.opacity = '0';
            bottomFlipBtn.style.pointerEvents = 'none';
        }
    };

    window.showRatingButtons = function () {
        const ratingBtns = document.querySelector('.fc-rating-btns');
        if (ratingBtns) {
            ratingBtns.style.opacity = '';
            ratingBtns.style.pointerEvents = '';
        }
        const bottomFlipBtn = document.querySelector('.fc-flip-btn');
        if (bottomFlipBtn) {
            bottomFlipBtn.style.opacity = '';
            bottomFlipBtn.style.pointerEvents = '';
        }
    };

    // Promise-based Toast (Dynamic Wait)
    // Promise-based Toast (Dynamic Wait)
    window.showMobileToast = function (htmlContent, duration, position) {
        // Fallback to config or defaults
        const config = window.FlashcardConfig?.notifications || {};
        const finalDuration = duration || config.score_duration || 1500;
        const finalPosition = position || config.score_position || 'center';

        return new Promise((resolve) => {
            // Create or reuse toast element
            let toast = document.getElementById('mobile-smart-toast');
            if (!toast) {
                toast = document.createElement('div');
                toast.id = 'mobile-smart-toast';
                toast.className = 'fixed transform z-[99999] pointer-events-none transition-all duration-300';
                document.body.appendChild(toast);
            }

            // Apply Position Classes
            toast.className = 'fixed transform z-[99999] pointer-events-none transition-all duration-300';
            if (finalPosition === 'top-center') {
                toast.style.left = '50%';
                toast.style.top = '10%';
                toast.style.bottom = 'auto';
                toast.style.transform = 'translate(-50%, -40%) scale(0.9)';
            } else if (finalPosition === 'top-right') {
                toast.style.right = '1rem';
                toast.style.left = 'auto';
                toast.style.top = '10%';
                toast.style.bottom = 'auto';
                toast.style.transform = 'translate(0, -40%) scale(0.9)';
            } else if (finalPosition === 'bottom-right') {
                toast.style.right = '1rem';
                toast.style.left = 'auto';
                toast.style.bottom = '10%';
                toast.style.top = 'auto';
                toast.style.transform = 'translate(0, 40%) scale(0.9)';
            } else {
                // center
                toast.style.left = '50%';
                toast.style.top = '50%';
                toast.style.bottom = 'auto';
                toast.style.transform = 'translate(-50%, -40%) scale(0.9)';
            }

            // Reset state for animation
            toast.style.opacity = '0';

            // Set Content
            toast.innerHTML = `
                <div class="bg-slate-800/95 backdrop-blur-md text-white px-6 py-4 rounded-2xl shadow-2xl flex flex-col items-center gap-2 border border-slate-700/50 min-w-[200px]">
                    ${htmlContent}
                </div>
            `;

            // Animate In
            requestAnimationFrame(() => {
                toast.style.opacity = '1';
                if (finalPosition === 'top-right' || finalPosition === 'bottom-right') {
                    toast.style.transform = 'translate(0, 0) scale(1)';
                } else {
                    toast.style.transform = 'translate(-50%, -50%) scale(1)';
                }
            });

            // Wait Duration
            setTimeout(() => {
                // Animate Out
                toast.style.opacity = '0';
                if (finalPosition === 'top-right' || finalPosition === 'bottom-right') {
                    toast.style.transform = 'translate(0, 20%) scale(0.95)';
                } else {
                    toast.style.transform = 'translate(-50%, -40%) scale(0.95)';
                }

                // Resolve after animation matches CSS duration (300ms)
                setTimeout(() => {
                    document.dispatchEvent(new CustomEvent('notificationComplete'));
                    resolve();
                }, 300);
            }, finalDuration);
        });
    };

    // Alias for Score Toast
    window.showScoreToast = function (scoreChange) {
        const config = window.FlashcardConfig?.notifications || {};
        const sign = scoreChange > 0 ? '+' : '';
        const color = scoreChange > 0 ? 'text-emerald-400' : 'text-rose-400';
        return window.showMobileToast(`
            <div class="text-3xl font-bold ${color}">${sign}${scoreChange}</div>
            <div class="text-xs text-slate-400 uppercase tracking-widest font-bold">Điểm kinh nghiệm</div>
        `, config.score_duration, config.score_position);
    };


    // [UX-IMMEDIATE] Update specific card stats immediately after rating (before transition)
    window.updateFlashcardStats = function (data) {
        console.log('[UI] Updating stats immediate:', data);

        // Helper cập nhật text
        const setText = (selector, value) => {
            document.querySelectorAll(selector).forEach(el => el.innerText = value);
        };

        if (data.statistics) {
            // Update both info bar and overlay
            setText('.js-card-times-reviewed', data.statistics.times_reviewed || 0);
            setText('.js-card-overlay-times-reviewed', data.statistics.times_reviewed || 0);

            setText('.js-card-streak', data.statistics.current_streak || 0);
            setText('.js-card-overlay-streak', data.statistics.current_streak || 0);

            // Update FSRS metrics in overlay
            const sVal = data.statistics.stability !== undefined ? parseFloat(data.statistics.stability).toFixed(1) : '0';
            setText('.js-card-overlay-stability', (sVal === '0.0' || sVal === '0.00') ? '0' : sVal);

            const dVal = data.statistics.difficulty !== undefined ? parseFloat(data.statistics.difficulty).toFixed(1) : '0.0';
            setText('.js-card-overlay-difficulty', dVal);

            const rVal = data.statistics.retrievability !== undefined ? Math.round(data.statistics.retrievability) : 0;
            setText('.js-card-overlay-retrievability', rVal);
        }

        // FSRS metrics display removed as per user request

        // Cập nhật trạng thái (Badge) - both info bar and overlay
        if (data.new_progress_status) {
            setText('.js-card-status-text', data.new_progress_status.toUpperCase());
            setText('.js-card-overlay-status-text', data.new_progress_status.toUpperCase());

            // Update badge color based on status
            const overlayBadge = document.querySelector('.js-card-overlay-status-badge');
            if (overlayBadge) {
                // Remove old status classes
                overlayBadge.className = overlayBadge.className.replace(/bg-\w+-\d+\/\d+/g, '');

                // Apply new color based on status
                const statusColors = {
                    'new': 'bg-blue-500/90',
                    'learning': 'bg-amber-500/90',
                    'review': 'bg-emerald-500/90',
                    'relearning': 'bg-rose-500/90'
                };
                const colorClass = statusColors[data.new_progress_status.toLowerCase()] || 'bg-slate-500/90';
                overlayBadge.classList.add(colorClass);
            }

            // (Tùy chọn) Gọi lại hàm updateStateBadge nếu cần đổi màu
            if (window.updateStateBadge) window.updateStateBadge(data.new_progress_status);
        }
    };

    // Card Overlay Stats Toggle Logic
    document.addEventListener('click', function (e) {
        const badge = e.target.closest('.js-card-overlay-status-badge');
        if (badge) {
            const stats = badge.parentNode.querySelector('.js-card-overlay-stats');
            if (stats) {
                const isHidden = stats.style.display === 'none';
                stats.style.display = isHidden ? 'flex' : 'none';
                stats.style.opacity = isHidden ? '0' : '1';
                if (isHidden) {
                    setTimeout(() => {
                        stats.style.opacity = '1';
                    }, 10);
                }
            }
        }
    });

})();
