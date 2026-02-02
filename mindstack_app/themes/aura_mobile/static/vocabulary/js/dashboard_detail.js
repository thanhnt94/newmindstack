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
        // --- Navigation Logic ---
        function showStep(step) {
            console.log("Showing Step (Unified):", step);
            currentActiveStep = step;

            document.querySelectorAll('.vocab-step').forEach(s => {
                s.classList.remove('active');
                s.style.display = 'none';
            });

            if (step === 'detail') {
                if (stepDetail) {
                    stepDetail.classList.add('active');
                    stepDetail.style.display = 'flex';
                }
            } else {
                const targetStep = document.getElementById('step-' + step) || document.getElementById(step);
                if (targetStep) {
                    targetStep.classList.add('active');
                    targetStep.style.display = 'flex';
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
                    console.log('API Response for set detail:', data);
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

                // New header selectors from render_unified_header
                document.querySelectorAll('h1.text-base.font-bold.text-slate-800').forEach(el => el.textContent = s.title);

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
                        btn.dataset.modalUrl = '/content/manage/edit/' + s.id;
                    } else {
                        btn.style.display = 'none';
                    }
                });

                // [FIX] Render Cover Image - Backend now returns full URL
                document.querySelectorAll('.js-detail-cover').forEach(coverEl => {
                    var coverPath = s.cover_image || '';
                    if (coverPath) {
                        coverEl.style.backgroundImage = 'url(' + coverPath + ')';
                        // [FORCE FIX] Use inline styles to guarantee containment
                        coverEl.style.backgroundSize = 'contain';
                        coverEl.style.backgroundRepeat = 'no-repeat';
                        coverEl.style.backgroundPosition = 'center';
                        coverEl.style.backgroundColor = '#f1f5f9';
                        coverEl.style.animation = 'none';
                        coverEl.classList.add('has-image');
                        coverEl.innerHTML = '';
                    } else {
                        coverEl.style.backgroundImage = '';
                        coverEl.classList.remove('has-image');
                        // Only add icon if it's the mobile container (has fa-book-open usually)
                        // Or just standard icon.
                        coverEl.innerHTML = '<i class="fas fa-book-open"></i>';
                    }
                });
            }


            // Render word list to ALL containers (desktop + mobile)
            const listContainers = document.querySelectorAll('.js-word-list');

            if (listContainers.length > 0) {
                if (stats && stats.items && stats.items.length > 0) {
                    let listHtml = '';
                    // Sort: Words needing review (low %) first, new words last
                    const sortedItems = [...stats.items].sort((a, b) => {
                        if (a.status === 'new' && b.status !== 'new') return 1;
                        if (b.status === 'new' && a.status !== 'new') return -1;
                        return a.mastery - b.mastery;
                    });

                    // Feature Icons helpers (defined once)
                    const iconClass = (active, colorClass) => `flex items-center justify-center w-7 h-7 rounded-lg transition-colors ${active ? colorClass + ' shadow-sm' : 'bg-slate-50 text-slate-300'}`;

                    sortedItems.forEach((item, index) => {
                        let statusBadge = '';
                        if (item.status === 'new') {
                            statusBadge = '<span class="px-2 py-0.5 bg-blue-50 text-blue-600 text-[10px] font-bold uppercase rounded-md tracking-wider border border-blue-100">Mới</span>';
                        }

                        let dueBadge = '';
                        if (item.is_due) {
                            dueBadge = '<span class="px-2 py-0.5 bg-red-50 text-red-600 text-[10px] font-bold uppercase rounded-md tracking-wider border border-red-100 animate-pulse">Ôn tập</span>';
                        }

                        const stability = item.fsrs_stability ? parseFloat(item.fsrs_stability).toFixed(1) : '-';
                        const difficulty = item.fsrs_difficulty ? parseFloat(item.fsrs_difficulty).toFixed(1) : '-';
                        const retrievability = item.retrievability ? Math.round(item.retrievability * 100) + '%' : '-';
                        const fsrsState = item.state_label || 'New';
                        const nextReview = item.next_review || '-';

                        listHtml += `
                    <div class="group bg-white border border-slate-200 rounded-2xl hover:border-indigo-300 hover:shadow-xl transition-all duration-300 mb-6 relative overflow-hidden js-item-stats-trigger cursor-pointer" data-item-id="${item.item_id || item.id}">
                        <!-- Top Bar: Index, ID & FSRS Stats Grid -->
                        <div class="bg-slate-50/50 border-b border-slate-100 p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div class="flex items-center gap-3">
                                <span class="w-8 h-8 rounded-lg bg-white border border-slate-200 flex items-center justify-center font-mono font-bold text-slate-500 text-xs shadow-sm">#${index + 1}</span>
                                <div class="flex flex-col">
                                    <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">ID Thẻ</span>
                                    <span class="font-mono text-xs font-bold text-slate-600">#${item.item_id || item.id}</span>
                                </div>
                                <div class="h-6 w-px bg-slate-200 mx-1 hidden sm:block"></div>
                                <div class="flex flex-col">
                                    <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Trạng thái</span>
                                    <span class="text-xs font-bold text-indigo-600">${fsrsState}</span>
                                </div>
                            </div>
                            
                            <!-- FSRS Stats Mini-Grid -->
                            <div class="flex items-center gap-4 bg-white px-3 py-1.5 rounded-lg border border-slate-100 shadow-sm overflow-x-auto">
                                <div class="flex flex-col items-center min-w-[40px]" title="Khả năng nhớ lại (Retrievability)">
                                    <span class="text-[10px] text-slate-400 font-bold">R</span>
                                    <span class="text-xs font-bold text-emerald-600">${retrievability}</span>
                                </div>
                                <div class="w-px h-6 bg-slate-100"></div>
                                <div class="flex flex-col items-center min-w-[40px]" title="Độ bền nhớ (Stability)">
                                    <span class="text-[10px] text-slate-400 font-bold">S</span>
                                    <span class="text-xs font-bold text-indigo-600">${stability}</span>
                                </div>
                                <div class="w-px h-6 bg-slate-100"></div>
                                <div class="flex flex-col items-center min-w-[40px]" title="Độ khó (Difficulty)">
                                    <span class="text-[10px] text-slate-400 font-bold">D</span>
                                    <span class="text-xs font-bold text-orange-600">${difficulty}</span>
                                </div>
                                <div class="w-px h-6 bg-slate-100"></div>
                                <div class="flex flex-col items-center min-w-[40px]" title="Lần học (Repetitions)">
                                    <span class="text-[10px] text-slate-400 font-bold">Reps</span>
                                    <span class="text-xs font-bold text-slate-600">${item.repetitions || 0}</span>
                                </div>
                            </div>
                        </div>

                        <div class="p-4">
                             <div class="flex flex-col gap-4">
                                <!-- Main Content Area -->
                                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <!-- Front Side -->
                                    <div class="flex flex-col">
                                        <div class="flex items-center justify-between mb-2">
                                            <div class="flex items-center gap-2">
                                                <div class="w-1.5 h-1.5 rounded-full bg-indigo-500"></div>
                                                <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Mặt trước</span>
                                            </div>
                                            ${statusBadge}
                                        </div>
                                        <div class="bg-indigo-50/30 border border-indigo-100 rounded-xl p-4 min-h-[80px] flex items-center shadow-sm">
                                           <div class="text-lg font-bold text-slate-800 leading-relaxed w-full">${item.term}</div>
                                        </div>
                                    </div>
                                    
                                    <!-- Back Side -->
                                    <div class="flex flex-col">
                                        <div class="flex items-center justify-between mb-2">
                                            <div class="flex items-center gap-2">
                                                <div class="w-1.5 h-1.5 rounded-full bg-amber-500"></div>
                                                <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Mặt sau</span>
                                            </div>
                                             ${dueBadge}
                                        </div>
                                        <div class="bg-amber-50/30 border border-amber-100 rounded-xl p-4 min-h-[80px] flex items-center shadow-sm">
                                            <div class="text-sm font-medium text-slate-700 leading-relaxed w-full">${item.definition}</div>
                                        </div>
                                    </div>
                                </div>

                                <!-- Footer Info -->
                                <div class="flex items-center justify-between pt-2 border-t border-slate-50">
                                    <div class="flex items-center gap-3">
                                        <div class="flex items-center gap-2 px-3 py-1 bg-slate-50 rounded-lg border border-slate-100">
                                            <i class="fas fa-clock text-slate-400 text-xs"></i>
                                            <span class="text-xs font-medium text-slate-600">Ôn tập: <span class="font-bold text-indigo-600">${nextReview}</span></span>
                                        </div>
                                    </div>

                                    <div class="flex items-center gap-2">
                                        <div class="${iconClass(item.has_ai, 'bg-purple-100 text-purple-600 ring-1 ring-purple-200')}" title="${item.has_ai ? 'Có giải thích AI' : 'Chưa có giải thích AI'}">
                                            <i class="fas fa-robot text-xs"></i>
                                        </div>
                                        <div class="${iconClass(item.has_note, 'bg-yellow-100 text-yellow-600 ring-1 ring-yellow-200')}" title="${item.has_note ? 'Có ghi chú' : 'Không có ghi chú'}">
                                            <i class="fas fa-sticky-note text-xs"></i>
                                        </div>
                                        <div class="${iconClass(item.is_hard, 'bg-red-100 text-red-600 ring-1 ring-red-200')}" title="${item.is_hard ? 'Thẻ khó' : 'Bình thường'}">
                                            <i class="fas fa-fire text-xs"></i>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>`;
                    });

                    listContainers.forEach(container => {
                        container.innerHTML = listHtml;
                        container.querySelectorAll('.js-item-stats-trigger').forEach(card => {
                            card.onclick = function (e) {
                                if (e.target.closest('button') || e.target.closest('a')) return;
                                const itemId = this.dataset.itemId;
                                if (itemId) {
                                    if (typeof window.openVocabularyItemStats === 'function') {
                                        window.openVocabularyItemStats(itemId);
                                    } else if (typeof window.openStatsModal === 'function') {
                                        window.openStatsModal(itemId);
                                    }
                                }
                            };
                        });
                    });

                } else {
                    // Empty state or missing stats
                    listContainers.forEach(container => {
                        container.innerHTML = '<div class="text-center py-10 text-slate-400"><i class="fas fa-inbox text-4xl mb-3 opacity-50"></i><p>Chưa có từ vựng nào.</p></div>';
                    });
                }
            }

            // Render Pagination
            const paginationBars = document.querySelectorAll('#detail-pagination-bar, .js-detail-pagination-bar-desktop');
            console.log('Pagination bars found:', paginationBars.length, 'HTML length:', paginationHtml ? paginationHtml.length : 0);

            if (paginationBars.length > 0 && paginationHtml && paginationHtml.trim().length > 0) {
                paginationBars.forEach(bar => {
                    bar.innerHTML = paginationHtml;
                    bar.classList.add('visible');
                    console.log('Pagination bar updated and shown:', bar.id);
                    bar.querySelectorAll('a').forEach(link => {
                        link.onclick = (e) => {
                            e.preventDefault();
                            const url = new URL(link.href);
                            fetchCourseStatsPage(url.searchParams.get('page'));
                        };
                    });
                });
            }
        } // End renderSetDetail

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
            fetch('/session/api/check_active/' + setId)
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

        }

        initialize();
    })();
});
