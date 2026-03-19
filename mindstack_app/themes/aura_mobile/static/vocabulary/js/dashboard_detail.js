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

    // [NEW] URL State Sync Helper
    function updateUrlState() {
        if (!selectedSetId) return;
        const url = new URL(window.location);
        if (currentFilter && currentFilter !== 'all') {
            url.searchParams.set('filter', currentFilter);
        } else {
            url.searchParams.delete('filter');
        }
        if (currentStatsPage > 1) {
            url.searchParams.set('page', currentStatsPage);
        } else {
            url.searchParams.delete('page');
        }
        history.replaceState({ setId: selectedSetId }, '', url);
    }

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
    function loadSetDetail(setId, pushState = false, page = 1) {
        selectedSetId = setId;
        currentStatsPage = page;

        // [UPDATED] Pass sort and filter param
        const searchQ = document.getElementById('searchInput')?.value || '';
        return fetch('/learn/vocabulary/api/set/' + setId + '?page=' + page + '&sort=' + currentSort + '&filter=' + currentFilter + '&q=' + encodeURIComponent(searchQ))
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
                    updateUrlState();
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
            document.querySelectorAll('.js-header-title').forEach(el => el.textContent = s.title);
            document.querySelectorAll('.js-header-subtitle').forEach(el => el.textContent = 'Hi, ' + (window.MindStack?.username || 'user') + '!');

            document.querySelectorAll('.js-header-title').forEach(el => el.textContent = s.title);
            document.querySelectorAll('.js-header-card-count').forEach(el => el.textContent = s.card_count);

            document.querySelectorAll('.js-creator-name').forEach(el => el.textContent = s.creator_name || 'Admin');
            document.querySelectorAll('.js-creator-avatar').forEach(el => el.textContent = (s.creator_name || 'A').charAt(0).toUpperCase());

            if (stats) {
                try {
                    const progressText = (stats.learned_count || 0); // Only show the learned count
                    document.querySelectorAll('.js-progress-count').forEach(el => el.textContent = progressText);

                    // Hide the labels below them
                    document.querySelectorAll('.vocab-stat-label').forEach(el => el.style.display = 'none');

                    // Update Tab Count
                    const tabCountEl = document.getElementById('tab-list-count');
                    if (tabCountEl) {
                        tabCountEl.textContent = progressText;
                        tabCountEl.classList.remove('hidden');
                    }

                    // Update Filter Tabs Counts
                    const totalObjCount = s.card_count || stats.total_count || 0;
                    document.querySelectorAll('.js-filter-count-all').forEach(el => el.textContent = `(${totalObjCount})`);

                    const learnedObjCount = stats.learned_count || 0;
                    document.querySelectorAll('.js-filter-count-learned').forEach(el => el.textContent = `(${learnedObjCount})`);

                    const dueObjCount = stats.due_count || 0;
                    document.querySelectorAll('.js-filter-count-due').forEach(el => {
                        if (dueObjCount > 0) {
                            el.textContent = `(${dueObjCount})`;
                            el.style.display = 'inline-block';
                        } else {
                            el.style.display = 'none';
                        }
                    });

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

            // [FIX] Render Cover Image - Support Advanced Blurred Background Layout
            const coverPath = s.cover_image || '';
            const hasCover = !!coverPath && coverPath.trim() !== '';

            // 1. Crisp Foreground Image
            document.querySelectorAll('.js-detail-cover-main').forEach(coverEl => {
                if (hasCover) {
                    coverEl.style.backgroundImage = 'url(' + coverPath + ')';
                    coverEl.style.backgroundSize = 'contain';
                    coverEl.style.backgroundRepeat = 'no-repeat';
                    coverEl.style.backgroundPosition = 'center';
                    coverEl.style.backgroundColor = 'transparent';
                    coverEl.style.opacity = '1';
                } else {
                    coverEl.style.backgroundImage = '';
                    coverEl.style.opacity = '0'; // Hide crisp layer so placeholder shows through
                }
            });

            // 2. Blurred Background Layer
            document.querySelectorAll('.js-detail-cover-blur').forEach(coverEl => {
                if (hasCover) {
                    coverEl.style.backgroundImage = 'url(' + coverPath + ')';
                    coverEl.style.backgroundSize = 'cover';
                    coverEl.style.backgroundPosition = 'center';
                    coverEl.style.opacity = '0.5';
                } else {
                    coverEl.style.backgroundImage = '';
                    coverEl.style.opacity = '0';
                }
            });

            // 3. Title display
            document.querySelectorAll('.js-detail-title-hero').forEach(el => el.textContent = s.title);
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
                        statusBadge = '<span class="px-2 py-0.5 bg-blue-50 text-blue-600 text-[10px] font-bold uppercase rounded-md tracking-wider border border-blue-100">New</span>';
                    }

                    let dueBadge = '';
                    if (item.is_due) {
                        dueBadge = '<span class="px-2 py-0.5 bg-red-50 text-red-600 text-[10px] font-bold uppercase rounded-md tracking-wider border border-red-100 animate-pulse">Review</span>';
                    }

                    const stability = item.fsrs_stability ? parseFloat(item.fsrs_stability).toFixed(1) : '-';
                    const difficulty = item.fsrs_difficulty ? parseFloat(item.fsrs_difficulty).toFixed(1) : '-';
                    const retrievability = item.retrievability ? Math.round(item.retrievability * 100) + '%' : '-';
                    const fsrsState = item.state_label || 'New';
                    const nextReview = item.next_review || '-';

                    // To exactly match his screenshot's "Learning" pill
                    let stateColorClass = 'bg-blue-50 text-blue-600 border-blue-100';
                    if (fsrsState === 'Review') stateColorClass = 'bg-emerald-50 text-emerald-600 border-emerald-100';
                    if (fsrsState === 'Learning' || fsrsState === 'Relearning') stateColorClass = 'bg-indigo-50 text-indigo-600 border-indigo-100';
                    if (fsrsState === 'New') stateColorClass = 'bg-slate-50 text-slate-600 border-slate-200';

                    listHtml += `
                    <div class="bg-white border border-slate-100 rounded-2xl shadow-[0_2px_8px_-2px_rgba(0,0,0,0.03)] hover:shadow-lg transition-all duration-300 mb-5 px-4 py-4 relative js-item-stats-trigger cursor-pointer flex flex-col group/card" data-item-id="${item.item_id || item.id}">
                        
                        <!-- Top status line -->
                        <div class="flex items-center justify-between mb-4">
                            <div class="flex items-center gap-2">
                                <span class="bg-slate-50 text-slate-400 px-1.5 py-0.5 rounded-lg text-[10px] font-bold border border-slate-100">#${index + 1}</span>
                                <span class="px-2.5 py-0.5 rounded-lg text-[10px] font-bold border ${stateColorClass} uppercase tracking-tight">${fsrsState}</span>
                            </div>
                            
                            <div class="flex items-center gap-2 text-[10px] font-bold text-slate-500 bg-slate-50/50 px-2.5 py-1 rounded-lg border border-slate-100/60">
                                <div class="flex items-center gap-1" title="Khả năng nhớ (R)"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.3)]"></span> ${retrievability}</div>
                                <div class="text-slate-200">|</div>
                                <div title="Độ bền nhớ (S)"><span class="text-slate-400">S:</span>${stability}</div>
                                <div class="text-slate-200">|</div>
                                <div title="Độ khó (D)"><span class="text-slate-400">D:</span>${difficulty}</div>
                                <div class="text-slate-200">|</div>
                                <div title="Số lần học">R:${item.repetitions || 0}</div>
                            </div>
                        </div>

                        <!-- Main Content Area -->
                        <div class="flex flex-col relative mb-4">
                            
                            <!-- Front Side -->
                            <div class="relative">
                                <div class="flex items-center justify-between mb-2">
                                    <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest pl-1">Mặt trước</p>
                                    ${item.is_due ? '<span class="px-2 py-0.5 bg-rose-500 text-white text-[9px] font-black uppercase rounded shadow-sm tracking-widest ring-2 ring-rose-100">Ôn tập</span>' : ''}
                                </div>
                                <div class="text-[20px] font-black text-slate-800 leading-tight pl-3 border-l-[3px] border-indigo-500/80 group-hover/card:border-indigo-600 transition-colors">${item.term}</div>
                            </div>
                            
                            <!-- Back Side -->
                            <div class="bg-indigo-50/30 p-3.5 rounded-xl border border-indigo-100/40 mt-3.5 mx-0.5">
                                <p class="text-[9px] font-bold text-indigo-400 uppercase tracking-widest mb-2 flex items-center gap-1.5"><i class="fas fa-lightbulb text-indigo-300"></i> Mặt sau</p>
                                <div class="text-[14px] font-medium text-slate-600 leading-relaxed">${item.definition}</div>
                            </div>
                        </div>

                        <!-- Footer Info -->
                        <div class="flex items-center justify-between mt-auto pt-1">
                            <div class="flex items-center gap-2 text-[11px] font-bold text-slate-400 bg-white px-2 py-1 rounded-lg border border-slate-50">
                                <i class="fas fa-history opacity-50"></i> ${nextReview}
                            </div>
                            <div class="flex items-center gap-2">
                                ${item.has_ai ? '<div class="w-6 h-6 rounded-lg bg-white text-slate-300 flex items-center justify-center text-[10px] border border-slate-100"><i class="fas fa-robot"></i></div>' : ''}
                                ${item.has_note ? '<div class="w-6 h-6 rounded-lg bg-white text-slate-300 flex items-center justify-center text-[10px] border border-slate-100"><i class="fas fa-sticky-note"></i></div>' : ''}
                                ${item.is_hard ? '<div class="w-6 h-6 rounded-lg bg-red-50 text-red-500 flex items-center justify-center text-[10px] border border-red-100"><i class="fas fa-fire"></i></div>' : ''}
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
                
                // Normal Page Links
                bar.querySelectorAll('a').forEach(link => {
                    link.onclick = (e) => {
                        e.preventDefault();
                        const url = new URL(link.href);
                        fetchCourseStatsPage(url.searchParams.get('page'));
                    };
                });

                // Jump to Page Handlers
                bar.querySelectorAll('.js-jump-page-input').forEach(input => {
                    input.addEventListener('keydown', (e) => {
                        if (e.key === 'Enter') {
                            e.preventDefault();
                            const page = parseInt(input.value);
                            if (page && page > 0) fetchCourseStatsPage(page);
                        }
                    });
                });
                bar.querySelectorAll('.js-jump-page-btn').forEach(btn => {
                    btn.addEventListener('click', () => {
                        const input = btn.previousElementSibling;
                        if (input && input.classList.contains('js-jump-page-input')) {
                            const page = parseInt(input.value);
                            if (page && page > 0) fetchCourseStatsPage(page);
                        }
                    });
                });
            });
        }
    } // End renderSetDetail

    function fetchCourseStatsPage(page) {

        if (!selectedSetId) return;
        currentStatsPage = parseInt(page) || 1;
        // [UPDATED] Pass sort param
        fetch('/learn/vocabulary/api/set/' + selectedSetId + '?page=' + page + '&sort=' + currentSort + '&filter=' + currentFilter)
            .then(r => r.json())
            .then(data => {
                if (data.success) renderSetDetail(selectedSetData, data.course_stats, false, data.pagination_html);
                updateUrlState();
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
        } else if (e.target.closest('.js-filter-tab-btn')) {
            // [FIXED] Use closest() to catch clicks on inner spans
            const btn = e.target.closest('.js-filter-tab-btn');
            const filterType = btn.dataset.filter;

            // Update UI (Elegant Pills - Tight)
            document.querySelectorAll('.js-filter-tab-btn').forEach(b => {
                const isActive = b.dataset.filter === filterType;
                if (isActive) {
                    b.className = 'whitespace-nowrap py-1 px-3 rounded-full text-[10px] font-bold transition-all duration-300 bg-indigo-600 text-white shadow-lg shadow-indigo-100 border-0 js-filter-tab-btn flex items-center gap-1.5';
                } else {
                    b.className = 'whitespace-nowrap py-1 px-3 rounded-full text-[10px] font-medium transition-all duration-300 bg-white text-slate-500 border border-slate-100 shadow-sm hover:border-indigo-100 hover:text-indigo-600 js-filter-tab-btn flex items-center gap-1.5';
                }
            });

            currentFilter = filterType;
            if (selectedSetId) {
                // Start Loading State
                const listContainer = document.querySelector('.js-word-list'); // Use class selector used in render
                if (listContainer) {
                    listContainer.innerHTML = '<div class="text-center py-10 text-slate-400"><i class="fas fa-spinner fa-spin text-2xl"></i><p class="mt-2 text-sm">Đang tải...</p></div>';
                }
                loadSetDetail(selectedSetId);
                updateUrlState();
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

        // [NEW] Read URL params to restore state on page load
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('filter')) {
            currentFilter = urlParams.get('filter');
            // Update filter tab UI to match (Elegant Pills - Tight)
            document.querySelectorAll('.js-filter-tab-btn').forEach(b => {
                if (b.dataset.filter === currentFilter) {
                    b.className = 'whitespace-nowrap py-1 px-3 rounded-full text-[10px] font-bold transition-all duration-300 bg-indigo-600 text-white shadow-lg shadow-indigo-100 border-0 js-filter-tab-btn flex items-center gap-1.5';
                } else {
                    b.className = 'whitespace-nowrap py-1 px-3 rounded-full text-[10px] font-medium transition-all duration-300 bg-white text-slate-500 border border-slate-100 shadow-sm hover:border-indigo-100 hover:text-indigo-600 js-filter-tab-btn flex items-center gap-1.5';
                }
            });
        }
        const urlPage = parseInt(urlParams.get('page')) || 1;

        if (selectedSetId) loadSetDetail(selectedSetId, false, urlPage);
        showStep(currentActiveStep);

    }

    initialize();
    // --- Tab Logic ---
    window.switchDetailTab = function (tabName) {
        // Update Tab Buttons (Premium Navigation Style - Tight)
        document.querySelectorAll('#tab-btn-list, #tab-btn-stats').forEach(btn => {
            if (btn.id === 'tab-btn-' + tabName) {
                btn.className = 'flex-1 py-1 rounded-lg text-[13px] font-bold transition-all duration-300 bg-white text-indigo-600 shadow-sm border-0 js-main-tab-btn';
            } else {
                btn.className = 'flex-1 py-1 rounded-lg text-[13px] font-medium transition-all duration-300 text-slate-400 hover:text-indigo-600 border-0 js-main-tab-btn';
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
