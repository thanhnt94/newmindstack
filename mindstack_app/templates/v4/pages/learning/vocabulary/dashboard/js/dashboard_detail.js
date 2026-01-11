/**
 * dashboard_detail.js - V4 Vocabulary Set Detail Logic
 */

document.addEventListener('DOMContentLoaded', function () {
    (function () {
        // State
        let selectedSetId = null;

        let selectedSetData = null;
        let selectedMode = null;
        let currentStatsPage = 1;
        let currentActiveStep = 'detail';
        let selectedFlashcardMode = null;

        // Elements
        const stepDetail = document.getElementById('step-detail');
        const stepDetailDesktop = document.getElementById('step-detail-desktop');
        const stepModes = document.getElementById('step-modes');
        const stepFlashcardOptions = document.getElementById('step-flashcard-options');
        const stepMcqOptions = document.getElementById('step-mcq-options');
        const mcqOptionsContainer = document.getElementById('mcq-options-container');
        const continueBtn = document.querySelector('.js-mode-continue');

        // --- Navigation Logic ---
        function showStep(step) {
            console.log("Showing Step:", step);
            currentActiveStep = step;

            document.querySelectorAll('.vocab-step').forEach(s => {
                s.classList.remove('active');
                s.style.display = 'none';
            });

            const isDesktop = window.innerWidth >= 1024;

            if (step === 'detail') {
                if (isDesktop) {
                    if (stepDetailDesktop) {
                        stepDetailDesktop.classList.add('active');
                        stepDetailDesktop.style.display = 'block';
                    }
                } else {
                    if (stepDetail) {
                        stepDetail.classList.add('active');
                        stepDetail.style.display = 'flex';
                    }
                }
            } else {
                const targetStep = document.getElementById('step-' + step) || document.getElementById(step);
                if (targetStep) {
                    targetStep.classList.add('active');
                    targetStep.style.display = isDesktop ? 'block' : 'flex';
                }
            }
            window.scrollTo(0, 0);
        }

        // --- Core Data Loading ---
        function loadSetDetail(setId, pushState = false) {
            selectedSetId = setId;
            if (pushState) history.pushState({ setId: setId }, '', '/learn/vocabulary/set/' + setId);

            return fetch('/learn/vocabulary/api/set/' + setId + '?page=1')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        selectedSetData = data.set;
                        renderSetDetail(data.set, data.course_stats, false, data.pagination_html);
                        checkSetActiveSession(setId);
                        loadSettingsData(setId);
                        return data.set;
                    }
                });
        }

        function loadSettingsData(setId) {
            fetch('/learn/vocabulary/api/flashcard-modes/' + setId)
                .then(r => r.json())
                .then(modeData => {
                    if (modeData.success) setupSettingsModal(setId, modeData);
                })
                .catch(e => console.warn("Failed to load settings:", e));
        }

        function renderSetDetail(s, stats, append = false, paginationHtml = '') {
            if (!append) {
                // Update ALL matching elements (for both desktop and mobile)
                document.querySelectorAll('.js-detail-title-full').forEach(el => el.textContent = s.title);
                document.querySelectorAll('.js-detail-desc').forEach(el => el.textContent = s.description || 'Không có mô tả');
                document.querySelectorAll('.js-card-count').forEach(el => el.textContent = s.card_count);
                document.querySelectorAll('.js-detail-title').forEach(el => el.textContent = s.title);
                document.querySelectorAll('.js-header-title').forEach(el => el.textContent = s.title);
                document.querySelectorAll('.js-header-card-count').forEach(el => el.textContent = s.card_count);

                if (stats) {
                    const progressText = (stats.learned_count || 0) + '/' + (stats.total_count || s.card_count);
                    document.querySelectorAll('.js-progress-count').forEach(el => el.textContent = progressText);

                    const progressPercent = stats.total_count ? Math.round((stats.learned_count / stats.total_count) * 100) : 0;
                    document.querySelectorAll('.js-header-progress-percent').forEach(el => el.textContent = progressPercent + '%');
                }

                document.querySelectorAll('.vocab-detail-content').forEach(el => el.style.opacity = '1');
                document.querySelectorAll('.step-header-info').forEach(el => el.style.opacity = '1');

                document.querySelectorAll('.js-edit-set-btn').forEach(btn => {
                    if (s.can_edit) {
                        btn.style.display = 'flex';
                        btn.href = '/content/flashcards/edit/' + s.id;
                    } else {
                        btn.style.display = 'none';
                    }
                });
            }


            // Render word list to ALL containers (desktop + mobile)
            const listContainers = document.querySelectorAll('.js-word-list');
            if (listContainers.length > 0 && stats && stats.items) {
                let listHtml = '';

                if (stats.items && stats.items.length > 0) {
                    // Sort: Words needing review (low %) first, new words last
                    const sortedItems = [...stats.items].sort((a, b) => {
                        if (a.status === 'new' && b.status !== 'new') return 1;
                        if (b.status === 'new' && a.status !== 'new') return -1;
                        return a.mastery - b.mastery;
                    });

                    sortedItems.forEach(item => {
                        let statusBadge = '';
                        if (item.status === 'new') {
                            statusBadge = '<span class="px-2 py-1 bg-gradient-to-r from-blue-500 to-blue-600 text-white text-[10px] font-bold uppercase rounded-full tracking-wider shadow-sm">Mới</span>';
                        }

                        let dueBadge = '';
                        if (item.is_due) {
                            dueBadge = '<span class="px-2 py-1 bg-gradient-to-r from-red-500 to-red-600 text-white text-[10px] font-bold uppercase rounded-full tracking-wider shadow-sm animate-pulse">Ôn tập</span>';
                        }

                        listHtml += `
                    <div class="group p-4 bg-white border border-slate-100 rounded-xl hover:border-indigo-200 hover:shadow-lg transition-all duration-300 mb-3 relative overflow-hidden js-item-stats-trigger cursor-pointer" data-item-id="${item.item_id || item.id}">
                        <div class="absolute inset-0 bg-gradient-to-r from-indigo-50/0 via-indigo-50/50 to-indigo-50/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                        <div class="flex items-start justify-between gap-4 relative z-10">
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center gap-2 mb-2">
                                    <span class="text-base font-bold text-slate-800 truncate">${item.term}</span>
                                    ${statusBadge}
                                    ${dueBadge}
                                </div>
                                <p class="text-sm text-slate-500 leading-relaxed truncate group-hover:text-slate-700 transition-colors">${item.definition}</p>
                            </div>
                            <div class="flex flex-col items-center gap-2 flex-shrink-0">
                                <div class="relative w-14 h-14">
                                    <svg class="transform -rotate-90 w-14 h-14">
                                        <circle cx="28" cy="28" r="24" stroke="#e2e8f0" stroke-width="4" fill="none" />
                                        <circle cx="28" cy="28" r="24" stroke="url(#gradient-${item.item_id})" stroke-width="4" fill="none" 
                                            stroke-dasharray="${2 * Math.PI * 24}" 
                                            stroke-dashoffset="${2 * Math.PI * 24 * (1 - item.mastery / 100)}"
                                            stroke-linecap="round"
                                            class="transition-all duration-500" />
                                        <defs>
                                            <linearGradient id="gradient-${item.item_id}" x1="0%" y1="0%" x2="100%" y2="100%">
                                                ${item.mastery >= 80 ? '<stop offset="0%" style="stop-color:#10b981;stop-opacity:1" /><stop offset="100%" style="stop-color:#059669;stop-opacity:1" />' :
                                item.mastery >= 50 ? '<stop offset="0%" style="stop-color:#f59e0b;stop-opacity:1" /><stop offset="100%" style="stop-color:#d97706;stop-opacity:1" />' :
                                    '<stop offset="0%" style="stop-color:#ef4444;stop-opacity:1" /><stop offset="100%" style="stop-color:#dc2626;stop-opacity:1" />'}
                                            </linearGradient>
                                        </defs>
                                    </svg>
                                    <div class="absolute inset-0 flex items-center justify-center">
                                        <span class="text-xs font-bold ${item.mastery >= 80 ? 'text-green-600' : item.mastery >= 50 ? 'text-yellow-600' : 'text-red-600'}">${item.mastery}%</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>`;
                    });

                    // Render to ALL word list containers
                    listContainers.forEach(container => {
                        container.innerHTML = listHtml;
                        // Bind click events for item stats
                        container.querySelectorAll('.js-item-stats-trigger').forEach(card => {
                            card.onclick = function (e) {
                                if (e.target.closest('button') || e.target.closest('a')) return;
                                const itemId = this.dataset.itemId;
                                if (itemId && window.openVocabularyItemStats) {
                                    window.openVocabularyItemStats(itemId);
                                }
                            };
                        });
                    });
                }


                const paginationBars = document.querySelectorAll('.vocab-pagination-bar, .js-detail-pagination-bar-desktop');
                if (paginationBars.length > 0 && paginationHtml) {
                    paginationBars.forEach(bar => {
                        bar.innerHTML = paginationHtml;
                        bar.classList.add('visible');
                        bar.querySelectorAll('a').forEach(link => {
                            link.onclick = (e) => {
                                e.preventDefault();
                                const url = new URL(link.href);
                                fetchCourseStatsPage(url.searchParams.get('page'));
                            };
                        });
                    });
                }
            }
        }

        function fetchCourseStatsPage(page) {

            if (!selectedSetId) return;
            fetch('/learn/vocabulary/api/set/' + selectedSetId + '?page=' + page)
                .then(r => r.json())
                .then(data => {
                    if (data.success) renderSetDetail(selectedSetData, data.course_stats, false, data.pagination_html);
                });
        }

        function checkSetActiveSession(setId) {
            const banner = document.getElementById('active-session-banner-detail');
            if (!banner) return;
            fetch('/learn/api/check_active_vocab_session/' + setId)
                .then(r => r.json())
                .then(data => {
                    if (data.has_active) {
                        banner.style.display = 'block';
                        const nameEl = banner.querySelector('.js-active-mode-name');
                        if (nameEl) nameEl.textContent = data.active_mode_display || data.active_mode;
                        const resumeBtn = banner.querySelector('.js-resume-session');
                        if (resumeBtn) resumeBtn.onclick = () => window.location.href = data.resume_url;
                    } else {
                        banner.style.display = 'none';
                    }
                });
        }

        function loadFlashcardOptions(setId) {
            showStep('flashcard-options');
            const container = document.getElementById('flashcard-modes-container');
            if (!container) return;

            container.innerHTML = '<div class="vocab-loading"><i class="fas fa-spinner fa-spin"></i><p>Đang tải...</p></div>';
            fetch('/learn/vocabulary/api/flashcard-modes/' + setId)
                .then(r => r.json())
                .then(data => {
                    if (data.success) renderFlashcardModes(data.modes, setId, data.user_button_count);
                });
        }

        function renderFlashcardModes(modes, setId, userButtonCount) {
            const container = document.getElementById('flashcard-modes-container');
            if (!container) return;

            const modeIcons = {
                'new_only': { icon: 'fa-star', color: 'linear-gradient(135deg, #f59e0b, #fbbf24)' },
                'all_review': { icon: 'fa-redo', color: 'linear-gradient(135deg, #3b82f6, #60a5fa)' },
                'hard_only': { icon: 'fa-fire', color: 'linear-gradient(135deg, #ef4444, #f87171)' },
                'mixed_srs': { icon: 'fa-brain', color: 'linear-gradient(135deg, #8b5cf6, #a78bfa)' }
            };

            let html = '';
            modes.forEach(mode => {
                const icon = modeIcons[mode.id] || { icon: 'fa-book', color: 'linear-gradient(135deg, #64748b, #94a3b8)' };
                const isDisabled = mode.count === 0;
                html += `
                <div class="mode-select-card js-flashcard-mode-select ${isDisabled ? 'disabled' : ''}" 
                     data-mode-id="${mode.id}"
                     ${isDisabled ? 'style="opacity: 0.5; filter: grayscale(100%); pointer-events: none;"' : ''}>
                    <div class="mode-select-icon" style="background: ${icon.color}"><i class="fas ${icon.icon}"></i></div>
                    <div class="mode-select-info">
                        <div class="mode-select-name font-bold">${mode.name}</div>
                        <div class="mode-select-desc text-xs text-slate-500">${mode.count} thẻ</div>
                    </div>
                </div>`;
            });
            container.innerHTML = html;
            bindFlashcardModeEvents(setId, userButtonCount);
        }

        function bindFlashcardModeEvents(setId, userButtonCount) {
            const container = document.getElementById('flashcard-modes-container');
            const continueBtn = document.querySelector('.js-flashcard-mode-continue');

            container.querySelectorAll('.js-flashcard-mode-select').forEach(card => {
                card.onclick = function () {
                    container.querySelectorAll('.js-flashcard-mode-select').forEach(c => c.classList.remove('selected'));
                    this.classList.add('selected');
                    selectedFlashcardMode = this.dataset.modeId;
                    if (continueBtn) continueBtn.disabled = false;
                };
            });

            const ratingInputs = document.querySelectorAll('input[name="rating_levels"]');
            ratingInputs.forEach(r => {
                if (parseInt(r.value) === (userButtonCount || 4)) r.checked = true;
            });

            if (continueBtn) {
                continueBtn.onclick = () => {
                    const rating = document.querySelector('input[name="rating_levels"]:checked')?.value || 4;
                    window.location.href = `/learn/start_flashcard_session/${setId}/${selectedFlashcardMode}?rating_levels=${rating}`;
                };
            }
        }

        function setupSettingsModal(setId, data) {
            const modal = document.getElementById('flashcard-settings-modal');
            const saveBtn = document.querySelector('.js-save-settings');
            if (!modal || !saveBtn) return;

            saveBtn.onclick = function () {
                // Simplified save payload for now
                const payload = {
                    auto_save: document.getElementById('setting-auto-save')?.checked !== false,
                    flashcard: {
                        button_count: parseInt(document.querySelector('.js-fixed-btn-count.border-indigo-600')?.dataset.value || 4)
                    }
                };
                fetch('/learn/vocabulary/api/settings/container/' + setId, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content },
                    body: JSON.stringify(payload)
                }).then(r => r.json()).then(d => {
                    if (d.success) modal.style.display = 'none';
                });
            };
        }

        // Init
        function initialize() {
            const urlParts = window.location.pathname.split('/');
            selectedSetId = urlParts.find(p => !isNaN(p) && p !== '');

            // Handle Back Buttons
            document.querySelectorAll('.js-back-to-dashboard-desktop, .step-back-btn').forEach(btn => {
                if (btn.classList.contains('step-back-btn') && btn.getAttribute('href') !== '/learn/vocabulary/') return;
                btn.onclick = (e) => {
                    if (currentActiveStep === 'detail') {
                        // Actual back to dashboard
                        window.location.href = '/learn/vocabulary/';
                    } else if (currentActiveStep === 'modes') {
                        showStep('detail');
                    } else if (currentActiveStep === 'flashcard-options' || currentActiveStep === 'mcq-options') {
                        showStep('modes');
                    }
                    e.preventDefault();
                };
            });

            // Handle Start Learning / Modes - Navigate to modes page
            const startBtns = document.querySelectorAll('.js-start-learning, .vocab-start-btn');
            console.log('Found start learning buttons:', startBtns.length);
            startBtns.forEach(btn => {
                btn.onclick = (e) => {
                    e.preventDefault();
                    if (selectedSetId) {
                        console.log('Navigating to modes for set:', selectedSetId);
                        window.location.href = '/learn/vocabulary/modes/' + selectedSetId;
                    } else {
                        console.error('No set selected');
                    }
                };
            });


            // Handle Settings Modal
            document.querySelectorAll('.js-open-flashcard-settings').forEach(btn => {
                btn.onclick = () => {
                    const modal = document.getElementById('flashcard-settings-modal');
                    if (modal) modal.style.display = 'flex';
                };
            });

            document.querySelectorAll('.js-close-settings-modal').forEach(btn => {
                btn.onclick = () => {
                    const modal = document.getElementById('flashcard-settings-modal');
                    if (modal) modal.style.display = 'none';
                };
            });

            if (selectedSetId) loadSetDetail(selectedSetId);
            showStep(currentActiveStep);

            // Handle resize - debounced to avoid thrashing
            let lastWidth = window.innerWidth;
            let resizeTimeout;
            window.addEventListener('resize', function () {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(function () {
                    const newWidth = window.innerWidth;
                    const crossedBreakpoint = (lastWidth < 1024 && newWidth >= 1024) || (lastWidth >= 1024 && newWidth < 1024);
                    if (crossedBreakpoint) {
                        console.log('Breakpoint crossed, refreshing view');
                        lastWidth = newWidth;
                        showStep(currentActiveStep);
                        if (selectedSetId && selectedSetData) {
                            // Re-render to ensure both views are updated
                            fetch('/learn/vocabulary/api/set/' + selectedSetId + '?page=1')
                                .then(r => r.json())
                                .then(data => {
                                    if (data.success) {
                                        renderSetDetail(data.set, data.course_stats, false, data.pagination_html);
                                    }
                                });
                        }
                    }
                    lastWidth = newWidth;
                }, 250);
            });
        }

        initialize();
    })();
});
