/**
 * dashboard_detail.js - V4 Vocabulary Set Detail Logic
 */

document.addEventListener('DOMContentLoaded', function () {
    // (function () { REMOVED IIFE WRAPPER
    // State
    let selectedSetId = null;

    let selectedSetData = null;
    let selectedMode = null;
    let currentStatsPage = 1;
    let currentActiveStep = 'detail';
    let selectedFlashcardMode = null;
    let currentSort = 'default'; // [NEW] Sort state
    let currentFilter = 'all'; // [NEW] Filter state

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

        // [UPDATED] Pass sort and filter param
        const searchQ = document.getElementById('searchInput')?.value || '';
        return fetch('/learn/vocabulary/api/set/' + setId + '?page=1&sort=' + currentSort + '&filter=' + currentFilter + '&q=' + encodeURIComponent(searchQ))
            .then(r => r.json())
            .then(data => {
                console.log('API Response for set detail:', data);
                if (data.success) {
                    selectedSetData = data.set;
                    renderSetDetail(data.set, data.course_stats, false, data.pagination_html);

                    // [NEW] Update Mode Visibility based on Set Capabilities
                    if (data.set.ai_capabilities) {
                        updateModeVisibility(data.set.ai_capabilities);
                    } else {
                        // If None/Empty, handle as "Enable All" OR "Disable All"?
                        // Based on logic, if capabilities is empty, updateModeVisibility hides all.
                        // But usually empty means legacy/all allowed? 
                        // Current Logic: Empty list -> Hide All. 
                        // If user wants all, they must be in the list.
                        updateModeVisibility(data.set.ai_capabilities);
                    }
                    checkSetActiveSession(setId);

                    // [NEW] Init settings modal for this set immediately
                    loadSettingsData(setId);

                    if (pushState) {
                        history.pushState({ setId: setId }, '', '/learn/vocabulary/set/' + setId);
                    }

                    return data.set;

                } else {
                    console.error('Failed to load set data:', data.message);
                    alert('Không thể tải thông tin bộ thẻ: ' + (data.message || 'Lỗi không xác định'));
                    throw new Error(data.message);
                }
            })
            .catch(err => {
                console.error('Error loading set detail:', err);
                alert('Có lỗi xảy ra khi tải dữ liệu.');
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
                try {
                    const progressText = (stats.learned_count || 0) + '/' + (stats.total_count || s.card_count);
                    document.querySelectorAll('.js-progress-count').forEach(el => el.textContent = progressText);

                    // Update Tab Count
                    const tabCountEl = document.getElementById('tab-list-count');
                    if (tabCountEl) {
                        tabCountEl.textContent = progressText;
                        tabCountEl.classList.remove('hidden');
                    }

                    const progressPercent = stats.total_count ? Math.round((stats.learned_count / stats.total_count) * 100) : 0;
                    document.querySelectorAll('.js-header-progress-percent').forEach(el => el.textContent = progressPercent + '%');
                } catch (e) {
                    console.error("Error rendering stats:", e);
                }
            }

            // Use requestAnimationFrame to ensure style application
            requestAnimationFrame(() => {
                document.querySelectorAll('.vocab-detail-content').forEach(el => {
                    el.style.opacity = '1';
                    el.style.pointerEvents = 'auto';
                });
                document.querySelectorAll('.step-header-info').forEach(el => el.style.opacity = '1');
            });

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
                // If filter is active, backend handles sorting mostly, but we can respect it here if needed.
                // Assuming backend sort is sufficient.
                const sortedItems = stats.items;

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
                    <div class="group bg-white border border-slate-300 rounded-2xl hover:border-indigo-500 hover:shadow-xl transition-all duration-300 mb-4 relative overflow-hidden js-item-stats-trigger cursor-pointer ring-0 hover:ring-4 hover:ring-indigo-50/50" data-item-id="${item.item_id || item.id}">
                        <!-- Compact Top Bar -->
                        <div class="px-3 py-2 bg-slate-50 border-b border-slate-200 flex items-center justify-between gap-2">
                            <div class="flex items-center gap-2">
                                <span class="font-mono font-bold text-xs text-slate-500 w-6">#${index + 1}</span>
                                <span class="px-1.5 py-0.5 bg-white border border-slate-300 rounded text-[10px] text-slate-600 font-mono shadow-sm">ID:${item.item_id || item.id}</span>
                                <span class="text-[10px] font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-200">${fsrsState}</span>
                            </div>
                            
                            <!-- Stats Compact Row -->
                            <div class="flex items-center gap-3 text-[10px] font-bold text-slate-600">
                                <div class="flex items-center gap-1" title="Khả năng nhớ (R)">
                                    <span class="text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">${retrievability}</span>
                                </div>
                                <div class="w-px h-3 bg-slate-300"></div>
                                <div class="flex items-center gap-1" title="Độ bền nhớ (S)">
                                    <span class="text-indigo-700">S:${stability}</span>
                                </div>
                                <div class="flex items-center gap-1" title="Độ khó (D)">
                                    <span class="text-orange-700">D:${difficulty}</span>
                                </div>
                                <div class="w-px h-3 bg-slate-300"></div>
                                <div class="flex items-center gap-1" title="Số lần học">
                                    <span class="text-slate-700">Reps:${item.repetitions || 0}</span>
                                </div>
                            </div>
                        </div>

                        <div class="p-3">
                             <div class="flex flex-col gap-2">
                                <!-- Main Content Area -->
                                <div class="grid grid-cols-1 gap-2">
                                    <!-- Front Side -->
                                    <div class="flex flex-col relative">
                                        <div class="absolute top-2 right-2 z-10">
                                            ${statusBadge}
                                        </div>
                                        <div class="bg-gradient-to-br from-indigo-50/50 to-white border border-indigo-200 rounded-lg p-3 min-h-[50px] flex items-center shadow-sm relative overflow-hidden group-hover:border-indigo-300 transition-colors">
                                           <div class="w-1 h-full absolute left-0 top-0 bg-indigo-500"></div>
                                           <div class="text-base font-bold text-slate-900 leading-snug pl-2 w-full pr-14">${item.term}</div>
                                        </div>
                                    </div>
                                    
                                    <!-- Back Side -->
                                    <div class="flex flex-col relative">
                                        <div class="absolute top-2 right-2 z-10">
                                            ${dueBadge}
                                        </div>
                                        <div class="bg-amber-50/40 border border-amber-200 rounded-lg p-3 min-h-[50px] flex items-center shadow-sm relative overflow-hidden group-hover:border-amber-300 transition-colors">
                                            <div class="w-1 h-full absolute left-0 top-0 bg-amber-400"></div>
                                            <div class="text-sm font-medium text-slate-800 leading-relaxed pl-2 w-full pr-14 line-clamp-3" title="${item.definition}">${item.definition}</div>
                                        </div>
                                    </div>
                                </div>

                                <!-- Compact Footer -->
                                <div class="flex items-center justify-between mt-1 pt-2 border-t border-slate-200">
                                    <div class="flex items-center gap-2 text-[10px] text-slate-600">
                                        <i class="fas fa-history text-slate-400"></i>
                                        <span>Ôn tập: <span class="font-bold text-slate-800">${nextReview}</span></span>
                                    </div>

                                    <div class="flex items-center gap-1.5">
                                        ${item.has_ai ? '<i class="fas fa-robot text-purple-600 text-xs bg-purple-100 border border-purple-200 p-1 rounded"></i>' : ''}
                                        ${item.has_note ? '<i class="fas fa-sticky-note text-yellow-600 text-xs bg-yellow-100 border border-yellow-200 p-1 rounded"></i>' : ''}
                                        ${item.is_hard ? '<i class="fas fa-fire text-red-600 text-xs bg-red-100 border border-red-200 p-1 rounded"></i>' : ''}
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
                if (bar.classList.contains('vocab-pagination-bar')) {
                    bar.classList.add('visible');
                }
                console.log('Pagination bar updated:', bar.id);
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
        // [UPDATED] Pass sort param
        fetch('/learn/vocabulary/api/set/' + selectedSetId + '?page=' + page + '&sort=' + currentSort + '&filter=' + currentFilter)
            .then(r => r.json())
            .then(data => {
                if (data.success) renderSetDetail(selectedSetData, data.course_stats, false, data.pagination_html);
            });
    }


    // [NEW] Bind Sorting Events
    document.addEventListener('click', function (e) {
        if (e.target.classList.contains('js-sort-btn')) {
            // ... existing sort logic ...
            const btn = e.target;
            const sortType = btn.dataset.sort;
            // ...
            document.querySelectorAll('.js-sort-btn').forEach(b => {
                b.classList.remove('active', 'bg-white', 'text-indigo-600', 'shadow-sm');
                b.classList.add('text-slate-500');
            });
            btn.classList.add('active', 'bg-white', 'text-indigo-600', 'shadow-sm');
            btn.classList.remove('text-slate-500');

            currentSort = sortType;
            if (selectedSetId) {
                const listContainer = document.getElementById('detail-vocab-list');
                if (listContainer) {
                    listContainer.innerHTML = '<div class="text-center py-10 text-slate-400"><i class="fas fa-spinner fa-spin text-2xl"></i><p class="mt-2 text-sm">Đang sắp xếp...</p></div>';
                }
                loadSetDetail(selectedSetId);
            }
        } else if (e.target.classList.contains('js-filter-tab-btn')) {
            // [NEW] Filter Tab Logic
            const btn = e.target;
            const filterType = btn.dataset.filter;

            // Update UI
            document.querySelectorAll('.js-filter-tab-btn').forEach(b => {
                // Reset to default inactive style
                b.className = 'flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all duration-200 text-slate-500 hover:text-indigo-600 js-filter-tab-btn';
            });
            // Set active style
            btn.className = 'flex-1 py-2 px-3 rounded-lg text-sm font-bold transition-all duration-200 text-indigo-700 bg-white shadow-sm js-filter-tab-btn';

            currentFilter = filterType;
            if (selectedSetId) {
                // Start Loading State
                const listContainer = document.querySelector('.js-word-list'); // Use class selector used in render
                if (listContainer) {
                    listContainer.innerHTML = '<div class="text-center py-10 text-slate-400"><i class="fas fa-spinner fa-spin text-2xl"></i><p class="mt-2 text-sm">Đang tải...</p></div>';
                }
                loadSetDetail(selectedSetId);
            }
        }
    });

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
            'new_only': { icon: 'fa-seedling', color: 'linear-gradient(135deg, #3b82f6, #60a5fa)' },
            'all_review': { icon: 'fa-layer-group', color: 'linear-gradient(135deg, #64748b, #94a3b8)' },
            'hard_only': { icon: 'fa-fire', color: 'linear-gradient(135deg, #ef4444, #f87171)' },
            'mixed_srs': { icon: 'fa-random', color: 'linear-gradient(135deg, #8b5cf6, #a78bfa)' },
            'sequential': { icon: 'fa-list-ol', color: 'linear-gradient(135deg, #f59e0b, #fbbf24)' }
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
        }
    }

    // [NEW] Mode Visibility Logic (mirrors dashboard.js)
    function updateModeVisibility(capabilities) {
        capabilities = capabilities || [];
        console.log("Updating detail mode visibility with capabilities:", capabilities);
        const modeCards = document.querySelectorAll('.mode-select-card[data-capability]');
        modeCards.forEach(card => {
            const requiredCapability = card.getAttribute('data-capability');
            if (requiredCapability) {
                const hasCap = capabilities.includes(requiredCapability) ||
                    capabilities.includes(requiredCapability.replace('supports_', ''));

                if (hasCap) {
                    card.style.display = 'flex';
                    card.classList.remove('disabled');
                } else {
                    card.style.display = 'none';
                }
            }
        });
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
    // --- Tab Logic ---
    window.switchDetailTab = function (tabName) {
        // Update Tab Buttons
        document.querySelectorAll('#tab-btn-list, #tab-btn-stats').forEach(btn => {
            if (btn.id === 'tab-btn-' + tabName) {
                btn.classList.add('text-indigo-600', 'border-indigo-600');
                btn.classList.remove('text-slate-500', 'border-transparent');
            } else {
                btn.classList.remove('text-indigo-600', 'border-indigo-600');
                btn.classList.add('text-slate-500', 'border-transparent');
            }
        });

        // Update Tab Content
        document.getElementById('tab-content-list').classList.add('hidden');
        document.getElementById('tab-content-stats').classList.add('hidden');
        document.getElementById('tab-content-' + tabName).classList.remove('hidden');

        // Toggle Pagination Visibility
        const paginations = document.querySelectorAll('#detail-pagination-bar, #detail-pagination-bar-desktop');
        if (tabName === 'stats') {
            paginations.forEach(el => el.classList.add('hidden'));
            // Default to Personal Stats when opening Stats Tab
            switchStatsSubTab('personal');
        } else {
            paginations.forEach(el => el.classList.remove('hidden'));
        }
    };

    // --- Enhanced Stats Logic (Personal & Leaderboard) ---
    let timelineChartInstance = null;
    let activityChartInstance = null;
    let distributionChartInstance = null;

    window.switchStatsSubTab = function (subTab) {
        console.log("Switching Stats Subtab:", subTab);

        // Update sub-tab buttons
        document.querySelectorAll('.js-stats-subtab-btn').forEach(btn => {
            if (btn.dataset.subtab === subTab) {
                btn.classList.add('bg-white', 'text-indigo-700', 'shadow-sm', 'font-bold');
                btn.classList.remove('text-slate-500', 'font-medium');
            } else {
                btn.classList.remove('bg-white', 'text-indigo-700', 'shadow-sm', 'font-bold');
                btn.classList.add('text-slate-500', 'font-medium');
            }
        });

        // Toggle sub-tab content
        document.querySelectorAll('.js-stats-subtab-content').forEach(content => {
            if (content.id === 'subtab-' + subTab) {
                content.classList.remove('hidden');
            } else {
                content.classList.add('hidden');
            }
        });

        if (subTab === 'personal' && selectedSetId) {
            fetchPersonalStats(selectedSetId);
        } else if (subTab === 'leaderboard' && selectedSetId) {
            fetchSetLeaderboard(selectedSetId);
        }
    };

    function fetchPersonalStats(setId) {
        // Show loading state if needed
        fetch('/learn/vocabulary/api/stats/container/' + setId)
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    // Summary Cards: Retention rate from FSRS
                    document.getElementById('personal-mp').textContent = data.retention_rate + '%';
                    document.getElementById('personal-learned').textContent = data.learned_items;
                    document.getElementById('personal-mastered').textContent = data.mastered_items;
                    document.getElementById('personal-due').textContent = data.due_items;

                    // Update timezone labels in UI
                    if (data.timezone_label) {
                        document.querySelectorAll('.js-tz-label').forEach(el => {
                            el.textContent = '(' + data.timezone_label + ')';
                        });
                    }

                    // Charts
                    if (data.chart_data) {
                        initPersonalCharts(data.chart_data, data.timezone_label);
                    }
                }
            })
            .catch(err => console.error("Error fetching personal stats:", err));
    }

    function initPersonalCharts(chartData, tzLabel) {
        // 1. Mastery Timeline
        initTimelineChart(chartData.timeline, tzLabel);
        // 2. Activity Chart
        initActivityChart(chartData.activity, chartData.timeline.dates, tzLabel);
        // 3. Distribution Chart
        initDistributionChart(chartData.distribution);
    }

    function initTimelineChart(data, tzLabel) {
        const ctx = document.getElementById('personalTimelineChart');
        if (!ctx) return;
        if (timelineChartInstance) timelineChartInstance.destroy();

        timelineChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [{
                    label: 'Khả năng ghi nhớ (' + (tzLabel || 'UTC') + ')',
                    data: data.values,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    borderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
                scales: {
                    y: { min: 0, max: 100, ticks: { callback: v => v + '%' }, grid: { borderDash: [5, 5] } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    function initActivityChart(data, dates, tzLabel) {
        const ctx = document.getElementById('personalActivityChart');
        if (!ctx) return;
        if (activityChartInstance) activityChartInstance.destroy();

        activityChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: 'Học mới (' + (tzLabel || 'UTC') + ')',
                        data: data.new_items,
                        backgroundColor: '#10b981',
                        borderRadius: 4
                    },
                    {
                        label: 'Ôn tập (' + (tzLabel || 'UTC') + ')',
                        data: data.reviews,
                        backgroundColor: '#6366f1',
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, usePointStyle: true } } },
                scales: {
                    x: { stacked: true, grid: { display: false } },
                    y: { stacked: true, beginAtZero: true, grid: { borderDash: [5, 5] } }
                }
            }
        });
    }

    function initDistributionChart(data) {
        const ctx = document.getElementById('personalDistributionChart');
        if (!ctx) return;
        if (distributionChartInstance) distributionChartInstance.destroy();

        distributionChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Yếu', 'Trung bình', 'Tốt'],
                datasets: [{
                    data: [data.weak, data.medium, data.strong],
                    backgroundColor: ['#f43f5e', '#f59e0b', '#10b981'],
                    borderWidth: 0,
                    cutout: '75%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: true }
                }
            }
        });
    }

    // Global variable for current timeframe
    let currentLeaderboardTimeframe = 'all';

    function fetchSetLeaderboard(setId, timeframe = null) {
        if (timeframe) currentLeaderboardTimeframe = timeframe;
        const tf = currentLeaderboardTimeframe;

        const container = document.getElementById('set-leaderboard-container');
        container.innerHTML = '<div class="text-center py-8 text-slate-400"><i class="fas fa-spinner fa-spin text-2xl mb-2"></i><p>Đang tải bảng xếp hạng...</p></div>';

        // [FIXED] Added /stats prefix to API call
        fetch('/stats/api/leaderboard/container/' + setId + '?timeframe=' + tf)
            .then(r => r.json())
            .then(data => {
                if (data.success && data.data.length > 0) {
                    let html = '';
                    data.data.forEach((user, index) => {
                        let rankBadge = '';
                        if (user.rank === 1) rankBadge = '<span class="text-xl">🥇</span>';
                        else if (user.rank === 2) rankBadge = '<span class="text-xl">🥈</span>';
                        else if (user.rank === 3) rankBadge = '<span class="text-xl">🥉</span>';
                        else rankBadge = `<span class="font-bold text-slate-400 w-6 text-center">${user.rank}</span>`;

                        const avatar = user.avatar_url ?
                            `<img src="${user.avatar_url}" class="w-10 h-10 rounded-full object-cover border border-slate-200">` :
                            `<div class="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold">${user.username.charAt(0).toUpperCase()}</div>`;

                        html += `
                                <div class="bg-white rounded-xl p-3 border border-slate-100 flex items-center gap-3 shadow-sm">
                                    <div class="flex items-center justify-center w-8">
                                        ${rankBadge}
                                    </div>
                                    ${avatar}
                                    <div class="flex-1">
                                        <div class="font-bold text-slate-800 text-sm">${user.username}</div>
                                        <div class="text-xs text-slate-500">Điểm: <span class="font-bold text-indigo-600">${user.total_score}</span> • Ôn tập: ${user.review_count} lần</div>
                                    </div>
                                    <div class="flex flex-col items-end">
                                        <span class="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full border border-emerald-100">
                                            ${user.mastered_count} Mastered
                                        </span>
                                    </div>
                                </div>
                            `;
                    });
                    container.innerHTML = html;
                } else {
                    container.innerHTML = `
                            <div class="text-center py-8 text-slate-400">
                                <i class="fas fa-trophy text-4xl mb-3 opacity-30"></i>
                                <p>Chưa có dữ liệu xếp hạng trong khoảng thời gian này.</p>
                                <p class="text-xs mt-1">Hãy là người đầu tiên chinh phục bảng vàng!</p>
                            </div>`;
                }
            })
            .catch(err => {
                console.error('Leaderboard error:', err);
                container.innerHTML = '<div class="text-center py-4 text-red-500">Lỗi tải dữ liệu.</div>';
            });
    }

    // Bind filter events (delegation or direct find)
    document.addEventListener('click', function (e) {
        if (e.target.classList.contains('js-lb-filter')) {
            const btn = e.target;
            document.querySelectorAll('.js-lb-filter').forEach(b => {
                b.classList.remove('active', 'bg-white', 'text-indigo-700', 'shadow-sm');
                b.classList.add('text-indigo-100', 'hover:bg-white/10');
            });
            btn.classList.add('active', 'bg-white', 'text-indigo-700', 'shadow-sm');
            btn.classList.remove('text-indigo-100', 'hover:bg-white/10');

            if (selectedSetId) {
                fetchSetLeaderboard(selectedSetId, btn.dataset.tf);
            }
        }
    });
    // })(); REMOVED IIFE WRAPPER
});
