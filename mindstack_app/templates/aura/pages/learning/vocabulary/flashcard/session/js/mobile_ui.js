(function () {
    // --- Mobile Logic & Events ---

    // Helper to get mobile stats container safely
    function getMobileStatsContainer() {
        // Check if template is already stamped
        const container = document.querySelector('.mobile-stats-container');
        if (container) return container;

        // Otherwise, clone from template
        const tmpl = document.getElementById('mobile-stats-template');
        if (tmpl) {
            // We don't clone here, usually we clone into a modal
            // But for now, let's assume it's used inside the stats modal
            return null;
        }
        return null;
    }

    // Helper to get user button count safely
    function getUserButtonCount() {
        return (window.FlashcardConfig && window.FlashcardConfig.userButtonCount) || window.userButtonCount || 4;
    }

    // Generate rating buttons logic
    function generateRatingButtons() {
        const container = document.querySelector('.fc-rating-btns');
        if (!container) return; // Not found (desktop view or not loaded)

        // Get user preferred count
        const btnCount = getUserButtonCount();
        let html = '';

        if (btnCount === 3) {
            html = `
                    <button class="fc-rating-btn again" onclick="submitAnswer('again')"><i class="fas fa-times-circle"></i>Quên</button>
                    <button class="fc-rating-btn good" onclick="submitAnswer('good')"><i class="fas fa-check-circle"></i>Nhớ</button>
                    <button class="fc-rating-btn easy" onclick="submitAnswer('easy')"><i class="fas fa-star"></i>Rất thuộc</button>
                `;
        } else if (btnCount === 4) {
            html = `
                    <button class="fc-rating-btn again" onclick="submitAnswer('again')"><i class="fas fa-times-circle"></i>Học lại</button>
                    <button class="fc-rating-btn hard" onclick="submitAnswer('hard')"><i class="fas fa-exclamation-circle"></i>Khó</button>
                    <button class="fc-rating-btn good" onclick="submitAnswer('good')"><i class="fas fa-check-circle"></i>Được</button>
                    <button class="fc-rating-btn easy" onclick="submitAnswer('easy')"><i class="fas fa-star"></i>Dễ</button>
                `;
        } else {
            html = `
                    <button class="fc-rating-btn again" onclick="submitAnswer('again')"><i class="fas fa-times-circle"></i>Học lại</button>
                    <button class="fc-rating-btn hard" onclick="submitAnswer('hard')"><i class="fas fa-exclamation-circle"></i>Khó</button>
                    <button class="fc-rating-btn good" onclick="submitAnswer('good')"><i class="fas fa-check-circle"></i>Được</button>
                    <button class="fc-rating-btn easy" onclick="submitAnswer('easy')"><i class="fas fa-star"></i>Dễ</button>
                `;
        }
        container.innerHTML = html;
    }

    // Run once
    generateRatingButtons();

    // Listen for flip/show/next events to toggle bottom bar buttons
    document.addEventListener('flashcardFlipped', function (e) {
        const isBack = e.detail && e.detail.side === 'back';
        const flipBtn = document.querySelector('.fc-flip-btn');
        const ratingBtns = document.querySelector('.fc-rating-btns');

        if (flipBtn && ratingBtns) {
            if (isBack) {
                flipBtn.style.display = 'none';
                ratingBtns.classList.add('show');
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
    const openStatsBtn = document.querySelector('.open-stats-modal-btn'); // In toolbar
    // Note: toolbar might be rebuilt, so we delegate or attach later?
    // Actually renderMobileCardHtml re-creates toolbar buttons.
    // We should use delegation on document or parent.

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

    // Audio autoplay check on mobile load? 
    // Handled by ui_manager.js generally.

    // Fix for iOS Safari 100vh issue
    const setAppHeight = () => {
        const doc = document.documentElement;
        doc.style.setProperty('--app-height', `${window.innerHeight}px`);
    };
    window.addEventListener('resize', setAppHeight);
    setAppHeight();

    // Prevent body scroll when modal is open?
    // Mobile only implementation.

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
        if (imageIcon) {
            imageIcon.className = isImageHidden ? 'fas fa-eye js-fc-image-icon' : 'fas fa-eye-slash js-fc-image-icon';
        }
        if (imageText) {
            imageText.textContent = isImageHidden ? 'Hiện ảnh' : 'Ẩn ảnh';
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

    // Generate rating buttons dynamically based on user_button_count
    function generateMobileRatingButtons() {
        const container = document.getElementById('mobile-rating-btns');
        if (!container) return;

        const buttonCount = getUserButtonCount();

        const buttonSets = {
            3: [
                { cssClass: 'again', value: '1', label: 'Quên', icon: 'fas fa-times' },
                { cssClass: 'hard', value: '2', label: 'Mơ hồ', icon: 'fas fa-question' },
                { cssClass: 'good', value: '3', label: 'Nhớ', icon: 'fas fa-check' }
            ],
            4: [
                { cssClass: 'again', value: '1', label: 'Học lại', icon: 'fas fa-undo' },
                { cssClass: 'hard', value: '2', label: 'Khó', icon: 'fas fa-fire' },
                { cssClass: 'good', value: '3', label: 'Ổn', icon: 'fas fa-thumbs-up' },
                { cssClass: 'easy', value: '4', label: 'Dễ', icon: 'fas fa-smile' }
            ],
            6: [
                { cssClass: 'again', value: '1', label: 'Rất khó', icon: 'fas fa-exclamation-circle' },
                { cssClass: 'hard', value: '2', label: 'Khó', icon: 'fas fa-fire' },
                { cssClass: 'medium', value: '3', label: 'TB', icon: 'fas fa-adjust' },
                { cssClass: 'good', value: '4', label: 'Dễ', icon: 'fas fa-leaf' },
                { cssClass: 'easy', value: '5', label: 'Rất dễ', icon: 'fas fa-thumbs-up' },
                { cssClass: 'veryeasy', value: '6', label: 'Dễ dàng', icon: 'fas fa-star' }
            ]
        };

        const buttons = buttonSets[buttonCount] || buttonSets[3];
        container.innerHTML = buttons.map(btn =>
            `<button class="fc-rating-btn ${btn.cssClass} js-rating-btn" data-rating="${btn.value}">
                    <i class="${btn.icon}"></i>
                    <span>${btn.label}</span>
                </button>`
        ).join('');
    }

    // Setup rating button handlers
    function setupRatingButtonHandlers() {
        const flipBtn = document.querySelector('.js-fc-flip-btn');
        const ratingBtnsContainer = document.querySelector('.js-fc-rating-btns');
        const ratingBtns = document.querySelectorAll('.js-rating-btn');
        ratingBtns.forEach(btn => {
            btn.addEventListener('click', function () {
                const rating = btn.dataset.rating;
                // Map our rating (1-6) to the answer values used by the card
                const buttonCount = getUserButtonCount();
                let answerMap;
                if (buttonCount === 3) {
                    answerMap = { '1': 'quên', '2': 'mơ_hồ', '3': 'nhớ' };
                } else if (buttonCount === 4) {
                    answerMap = { '1': 'again', '2': 'hard', '3': 'good', '4': 'easy' };
                } else {
                    // 6 buttons
                    answerMap = { '1': 'fail', '2': 'very_hard', '3': 'hard', '4': 'medium', '5': 'good', '6': 'very_easy' };
                }
                const answerValue = answerMap[rating] || 'good';

                // Call submitFlashcardAnswer directly instead of simulating button click
                if (window.currentFlashcardBatch &&
                    typeof window.currentFlashcardIndex !== 'undefined' &&
                    typeof window.submitFlashcardAnswer === 'function') {
                    const card = window.currentFlashcardBatch[window.currentFlashcardIndex];
                    if (card && card.item_id) {
                        window.submitFlashcardAnswer(card.item_id, answerValue);
                    }
                }

                // Reset for next card (will also be done by flashcardStatsUpdated event)
                setTimeout(() => {
                    if (flipBtn) flipBtn.style.display = 'flex';
                    if (ratingBtnsContainer) ratingBtnsContainer.classList.remove('show');
                }, 100);
            });
        });
    }

    // Update stats from custom event dispatched by main script
    function updateMobileStats(stats) {
        if (!stats) return;

        // Update Progress Bar & Text (Header)
        if (stats.total > 0) {
            const percent = Math.min(100, Math.round((stats.processed / stats.total) * 100));
            document.querySelectorAll('.js-fc-progress-fill').forEach(el => {
                el.style.width = percent + '%';
            });
            document.querySelectorAll('.js-fc-progress-text').forEach(el => {
                el.textContent = `${stats.processed}/${stats.total}`;
            });
        } else {
            document.querySelectorAll('.js-fc-progress-text').forEach(el => {
                el.textContent = `0/0`;
            });
        }

        // Update Header Badges
        document.querySelectorAll('.js-fc-session-score').forEach(el => {
            el.textContent = stats.session_score > 0 ? `+${stats.session_score}` : (stats.session_score || 0);
        });
        document.querySelectorAll('.js-fc-session-correct').forEach(el => {
            el.textContent = stats.correct || 0;
        });

        // Update total score badge
        if (typeof window.currentUserTotalScore !== 'undefined') {
            document.querySelectorAll('.js-fc-score').forEach(el => {
                el.textContent = parseInt(window.currentUserTotalScore).toLocaleString();
            });
        }

        // --- RENDER BEAUTIFUL STATS INSIDE MODAL (Current Tab) ---
        const container = document.getElementById('current-card-stats-mobile');
        if (container) {
            // Calculate percentages for Bar Chart
            const totalRatings = stats.times_reviewed || 0;
            const counts = stats.rating_counts || { 1: 0, 2: 0, 3: 0, 4: 0 };
            const p = totalRatings > 0 ? {
                1: (counts[1] / totalRatings) * 100,
                2: (counts[2] / totalRatings) * 100,
                3: (counts[3] / totalRatings) * 100,
                4: (counts[4] / totalRatings) * 100
            } : { 1: 0, 2: 0, 3: 0, 4: 0 };

            const reviewHistory = stats.recent_reviews || [];

            const html = `
                <div class="space-y-4">
                    <!-- 1. Metrics Grid (Reviews & Streak) -->
                    <div class="grid grid-cols-2 gap-3">
                        <div class="bg-white rounded-xl p-3 border border-slate-100 shadow-sm flex flex-col items-center justify-center text-center">
                            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Đã học</span>
                            <span class="text-2xl font-black text-slate-700">${totalRatings}</span>
                            <span class="text-[10px] text-slate-400">lần</span>
                        </div>
                        <div class="bg-white rounded-xl p-3 border border-slate-100 shadow-sm flex flex-col items-center justify-center text-center">
                            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Chuỗi</span>
                            <span class="text-2xl font-black text-amber-500">${stats.current_streak || 0}</span>
                            <span class="text-[10px] text-slate-400">liên tiếp</span>
                        </div>
                    </div>

                     <!-- 2. Rating Distribution -->
                    <div class="bg-white rounded-xl p-3 border border-slate-100 shadow-sm">
                        <div class="flex items-center justify-between mb-2">
                            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Phân bố đánh giá</span>
                            <span class="text-[10px] font-bold text-slate-500">${totalRatings} lượt</span>
                        </div>
                        <div class="h-3 w-full bg-slate-100 rounded-full overflow-hidden flex shadow-inner">
                            ${totalRatings > 0 ? `
                                <div class="h-full bg-rose-500" style="width: ${p[1]}%"></div>
                                <div class="h-full bg-amber-500" style="width: ${p[2]}%"></div>
                                <div class="h-full bg-emerald-500" style="width: ${p[3]}%"></div>
                                <div class="h-full bg-blue-500" style="width: ${p[4]}%"></div>
                            ` : '<div class="w-full h-full flex items-center justify-center text-[8px] text-slate-400 italic">Chưa có dữ liệu</div>'}
                        </div>
                         <div class="flex justify-between mt-2 px-1">
                            <div class="flex items-center gap-1"><div class="w-1.5 h-1.5 rounded-full bg-rose-500"></div><span class="text-[9px] text-slate-500">Q</span></div>
                            <div class="flex items-center gap-1"><div class="w-1.5 h-1.5 rounded-full bg-amber-500"></div><span class="text-[9px] text-slate-500">K</span></div>
                            <div class="flex items-center gap-1"><div class="w-1.5 h-1.5 rounded-full bg-emerald-500"></div><span class="text-[9px] text-slate-500">Đ</span></div>
                            <div class="flex items-center gap-1"><div class="w-1.5 h-1.5 rounded-full bg-blue-500"></div><span class="text-[9px] text-slate-500">D</span></div>
                        </div>
                    </div>

                    <!-- 3. Next Review & Stability -->
                    <div class="bg-blue-50 rounded-xl p-3 border border-blue-100 shadow-sm">
                        <div class="flex items-center gap-3 mb-2">
                             <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
                                <i class="fas fa-calendar-alt text-sm"></i>
                            </div>
                            <div>
                                <span class="text-[10px] font-bold text-blue-400 uppercase block">Lần tới</span>
                                <span class="text-sm font-bold text-slate-700">
                                     ${stats.interval_minutes ? (window.formatMinutesAsDuration ? window.formatMinutesAsDuration(stats.interval_minutes) : stats.interval_minutes + 'm') : (stats.next_review ? (window.formatDateTime ? window.formatDateTime(stats.next_review) : stats.next_review) : 'Ngay bây giờ')}
                                </span>
                            </div>
                        </div>
                        <div class="w-full bg-white rounded-lg h-1.5 overflow-hidden flex mb-1">
                            <div class="bg-blue-500 h-full rounded-full" style="width: ${Math.min(100, (stats.stability || 0) * 2)}%"></div>
                        </div>
                         <div class="flex justify-between">
                            <span class="text-[9px] text-slate-400">Độ ổn định</span>
                            <span class="text-[9px] font-bold text-blue-600">${(stats.stability || 0).toFixed(1)} ngày</span>
                        </div>
                    </div>

                    <!-- 4. History Timeline -->
                     <div class="bg-white rounded-xl p-3 border border-slate-100 shadow-sm">
                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-3">Lịch sử gần đây</span>
                         <div class="relative pl-3 border-l-2 border-slate-100 space-y-3">
                            ${reviewHistory.length > 0 ? reviewHistory.slice().reverse().slice(0, 5).map(h => `
                                <div class="relative">
                                    <div class="absolute -left-[17px] top-0.5 w-2 h-2 rounded-full border border-white shadow-sm ${h.user_answer_quality >= 3 ? 'bg-emerald-500' : (h.user_answer_quality === 2 ? 'bg-amber-500' : 'bg-rose-500')}"></div>
                                    <div class="flex justify-between items-start">
                                        <div class="flex flex-col">
                                            <span class="text-[11px] font-bold text-slate-700">
                                                ${h.user_answer_quality === 1 ? 'Quên' : (h.user_answer_quality === 2 ? 'Khó' : (h.user_answer_quality === 3 ? 'Được' : 'Dễ'))}
                                            </span>
                                            <span class="text-[9px] text-slate-400">${window.formatDateTime ? window.formatDateTime(h.timestamp) : h.timestamp}</span>
                                        </div>
                                        ${h.result === 'correct' ? '<i class="fas fa-check text-[10px] text-emerald-500"></i>' : ''}
                                    </div>
                                </div>
                            `).join('') : '<p class="text-[10px] text-slate-400 italic">Chưa có lịch sử</p>'}
                         </div>
                    </div>
                </div>
            `;
            container.innerHTML = html;
        }
    }

    // Wait for window.userButtonCount to be set (or FlashcardConfig)
    function initMobileRatingButtons() {
        if (typeof window.userButtonCount !== 'undefined' || (window.FlashcardConfig && window.FlashcardConfig.userButtonCount)) {
            generateMobileRatingButtons();
            setupRatingButtonHandlers();
        } else {
            setTimeout(initMobileRatingButtons, 100);
        }
    }

    initMobileRatingButtons();

})();
