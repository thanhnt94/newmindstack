document.addEventListener('DOMContentLoaded', function () {
    (function () {
        // State
        let currentCategory = 'my';
        let currentSearch = '';
        let currentPage = 1;
        let selectedSetId = null;
        let selectedSetData = null;
        let selectedMode = null;
        let currentStatsPage = 1;

        // Config from Global
        const config = window.VocabDashboardConfig || {};
        const activeSetId = config.activeSetId || null;
        const activeStep = config.activeStep || 'browser';

        // Elements
        const stepBrowser = document.getElementById('step-browser');
        const stepDetail = document.getElementById('step-detail');
        const stepModes = document.getElementById('step-modes');
        const stepFlashcardOptions = document.getElementById('step-flashcard-options');
        const stepMcqOptions = document.getElementById('step-mcq-options');

        const setsGrids = document.querySelectorAll('#sets-grid, #mobile-sets-grid');
        const searchInput = document.getElementById('search-input');
        const flashcardOptionsContainer = document.getElementById('flashcard-options-container');
        const mcqOptionsContainer = document.getElementById('mcq-options-container');

        const continueBtn = document.querySelector('.js-mode-continue');
        const paginationBars = document.querySelectorAll('#vocab-pagination-bar, #mobile-pagination-bar');
        const prevPageBtns = document.querySelectorAll('.js-vocab-prev-page');
        const nextPageBtns = document.querySelectorAll('.js-vocab-next-page');

        if (!stepBrowser || !stepDetail || setsGrids.length === 0) {
            console.error("Critical elements missing in DOM");
            return;
        }

        // Bind Mode Select Events
        document.querySelectorAll('.js-mode-select').forEach(card => {
            card.addEventListener('click', function () {
                document.querySelectorAll('.js-mode-select').forEach(c => c.classList.remove('selected'));
                this.classList.add('selected');
                selectedMode = this.dataset.mode;
                if (continueBtn) {
                    continueBtn.disabled = false;
                    continueBtn.classList.add('active');
                }
            });
        });

        // Init
        loadSets();
        loadDashboardStats();
        loadActiveSessions();

        // Handle inline capabilities (if passed from server)
        if (config.containerCapabilities && Array.isArray(config.containerCapabilities)) {
            const caps = config.containerCapabilities;
            document.querySelectorAll('.mode-select-card[data-capability]').forEach(card => {
                const req = card.getAttribute('data-capability');
                if (req && !caps.includes(req)) {
                    card.style.display = 'none';
                }
            });
        }

        // Category tabs
        document.querySelectorAll('.vocab-tab').forEach(function (tab) {
            tab.addEventListener('click', function () {
                document.querySelectorAll('.vocab-tab').forEach(function (t) { t.classList.remove('active'); });
                tab.classList.add('active');
                currentCategory = tab.dataset.category;
                loadSets();
            });
        });

        console.log("Deep Link Check:", activeSetId, "Step:", activeStep);

        if (activeSetId) {
            setsGrids.forEach(grid => {
                grid.innerHTML = '<div class="vocab-loading" style="grid-column: 1/-1;"><i class="fas fa-spinner fa-spin"></i><p>Đang chuẩn bị...</p></div>';
            });

            loadSetDetail(activeSetId, false)
                .then(function () {
                    if (activeStep && activeStep !== 'browser' && activeStep !== 'detail') {
                        showStep(activeStep);
                        updateModeVisibility();
                        if (activeStep === 'flashcard-options') {
                            loadFlashcardOptions(activeSetId);
                        } else if (activeStep === 'mcq-options') {
                            loadMcqOptions(activeSetId);
                        }
                    } else if (activeStep === 'detail') {
                        showStep('detail');
                    }
                })
                .catch(function (err) {
                    console.error("Init failed:", err);
                    alert("Không thể tải dữ liệu bộ thẻ. Vui lòng thử lại.");
                    showStep('browser');
                    loadSets();
                });
        } else {
            if (!activeStep || activeStep === 'browser') {
                showStep('browser');
            }
        }

        // Search
        let searchTimeout;
        if (searchInput) {
            searchInput.addEventListener('input', function () {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(function () {
                    currentSearch = searchInput.value;
                    loadSets();
                }, 300);
            });
        }

        // Back buttons
        document.querySelectorAll('.js-back-to-browser').forEach(function (btn) {
            btn.addEventListener('click', function () {
                showStep('browser');
                history.pushState(null, '', '/learn/vocabulary/');
            });
        });

        document.querySelectorAll('.js-back-to-detail').forEach(function (btn) {
            btn.addEventListener('click', function () {
                showStep('detail');
                history.pushState({ step: 'detail', setId: selectedSetId }, '', '/learn/vocabulary/set/' + selectedSetId);
            });
        });

        document.querySelectorAll('.js-back-to-modes').forEach(function (btn) {
            btn.addEventListener('click', function () {
                showStep('modes');
                history.pushState({ step: 'modes', setId: selectedSetId }, '', '/learn/vocabulary/set/' + selectedSetId + '/modes');
            });
        });

        // Handle Browser Back Button
        window.addEventListener('popstate', function (event) {
            const pathname = window.location.pathname;
            if (pathname.includes('/set/')) {
                const parts = pathname.split('/');
                const lastPart = parts[parts.length - 1];
                if (lastPart === 'modes') {
                    const setId = parts[parts.length - 2];
                    if (selectedSetId != setId) loadSetDetail(setId, false);
                    showStep('modes');
                } else if (lastPart === 'flashcard') {
                    const setId = parts[parts.length - 2];
                    if (selectedSetId != setId) loadSetDetail(setId, false);
                    showStep('flashcard-options');
                    loadFlashcardOptions(setId);
                } else if (lastPart === 'mcq') {
                    const setId = parts[parts.length - 2];
                    if (selectedSetId != setId) loadSetDetail(setId, false);
                    showStep('mcq-options');
                    loadMcqOptions(setId);
                } else if (!isNaN(lastPart)) {
                    const setId = lastPart;
                    if (selectedSetId != setId) loadSetDetail(setId, false);
                    showStep('detail');
                }
            } else {
                showStep('browser');
            }
        });

        // Global State for Responsive Step Tracking
        let currentActiveStep = 'browser';

        // Handle Window Resize
        window.addEventListener('resize', function () {
            handleResponsiveView(currentActiveStep);
        });

        function handleResponsiveView(step) {
            const desktopView = document.querySelector('.vocab-desktop-view');
            const mobileBrowser = document.getElementById('step-browser');
            const isDesktop = window.innerWidth >= 1024;

            if (step === 'browser') {
                if (isDesktop && desktopView) {
                    if (mobileBrowser) {
                        mobileBrowser.classList.remove('active');
                        mobileBrowser.style.display = 'none';
                    }
                    desktopView.style.display = 'block';
                    desktopView.classList.add('active');
                } else {
                    if (desktopView) {
                        desktopView.style.display = 'none';
                        desktopView.classList.remove('active');
                    }
                    if (mobileBrowser) {
                        mobileBrowser.classList.add('active');
                        mobileBrowser.style.display = 'flex';
                    }
                }
            } else {
                if (desktopView) {
                    desktopView.style.display = 'none';
                    desktopView.classList.remove('active');
                }
                const targetStep = document.getElementById('step-' + step) || document.getElementById(step);
                if (targetStep) {
                    targetStep.style.display = isDesktop ? 'block' : 'flex';
                }
            }
        }

        function showStep(step) {
            console.log("Showing Step:", step);
            currentActiveStep = step;
            document.querySelectorAll('.vocab-step').forEach(s => {
                if (s.id !== 'step-browser' && s.id !== ('step-' + step) && s.id !== step) {
                    s.classList.remove('active');
                    s.style.display = 'none';
                }
            });
            const targetStep = document.getElementById('step-' + step) || document.getElementById(step);
            if (targetStep) targetStep.classList.add('active');
            handleResponsiveView(step);
            window.scrollTo(0, 0);
            if (step !== 'browser') {
                hidePagination();
            }
        }

        function loadSets(page) {
            page = page || 1;
            currentPage = page;
            if (setsGrids.length === 0) return;
            setsGrids.forEach(grid => {
                grid.innerHTML = '<div class="vocab-loading" style="grid-column: 1/-1;"><i class="fas fa-spinner fa-spin"></i><p>Đang tải...</p></div>';
            });

            var url = '/learn/vocabulary/api/sets?category=' + currentCategory + '&page=' + page;
            if (currentSearch) url += '&q=' + encodeURIComponent(currentSearch);

            fetch(url)
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.success && data.sets.length > 0) {
                        renderSets(data.sets);
                        updatePagination(data.page, data.has_prev, data.has_next, data.total);
                    } else {
                        setsGrids.forEach(grid => {
                            grid.innerHTML = '<div class="vocab-empty" style="grid-column: 1/-1;"><i class="fas fa-folder-open"></i><p>Không có bộ thẻ nào</p></div>';
                        });
                        hidePagination();
                    }
                })
                .catch(function () {
                    setsGrids.forEach(grid => {
                        grid.innerHTML = '<div class="vocab-empty" style="grid-column: 1/-1;"><i class="fas fa-exclamation-triangle"></i><p>Lỗi tải dữ liệu</p></div>';
                    });
                    hidePagination();
                });
        }

        function loadActiveSessions() {
            const container = document.getElementById('active-sessions-container');
            const list = document.getElementById('active-sessions-list');
            if (!container || !list) return;

            fetch('/learn/api/learning/sessions/active?mode=flashcard')
                .then(r => r.json())
                .then(data => {
                    if (data.has_active) {
                        container.style.display = 'block';
                        renderActiveSession(data.session, list);
                    } else {
                        container.style.display = 'none';
                    }
                })
                .catch(err => console.warn('Active session check failed:', err));
        }

        function renderActiveSession(session, targetList) {
            const typeLabel = session.learning_mode === 'flashcard' ? 'Flashcard' : 'Học tập';
            const progress = session.total_items > 0
                ? Math.round((session.processed_item_ids.length / session.total_items) * 100)
                : 0;
            const title = session.set_title || ('Bộ thẻ #' + session.set_id_data);

            targetList.innerHTML = `
                <div class="active-session-card animate-fadeIn">
                    <div class="active-session-icon">
                        <i class="fas fa-play"></i>
                    </div>
                    <div class="active-session-info">
                        <div class="session-item-title">${title}</div>
                        <div class="session-details">
                            <span><i class="fas fa-layer-group mr-1"></i>${typeLabel}</span>
                            <span><i class="fas fa-tasks mr-1"></i>${progress}%</span>
                        </div>
                    </div>
                    <a href="/learn/vocabulary/flashcard/session" class="session-resume-btn">
                        Tiếp tục <i class="fas fa-chevron-right"></i>
                    </a>
                </div>
            `;
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
                        const btn = banner.querySelector('.js-resume-session');
                        if (btn) {
                            const newBtn = btn.cloneNode(true);
                            btn.parentNode.replaceChild(newBtn, btn);
                            newBtn.onclick = function (e) {
                                e.preventDefault();
                                e.stopPropagation();
                                window.location.href = data.resume_url;
                            };
                        }
                    } else {
                        banner.style.display = 'none';
                    }
                })
                .catch(e => console.warn("Check Set Session Failed:", e));
        }

        function loadDashboardStats() {
            fetch('/learn/vocabulary/api/dashboard-global-stats')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const stats = data.stats;
                        const mappings = {
                            'total-sets': stats.total_sets,
                            'total-cards': stats.total_cards,
                            'mastered-count': stats.mastered,
                            'due-count': stats.due
                        };
                        for (const [id, value] of Object.entries(mappings)) {
                            const el = document.getElementById(id);
                            if (el) el.textContent = value;
                        }
                    }
                })
                .catch(err => console.error('Failed to load dashboard stats:', err));
        }

        function renderSets(sets) {
            if (setsGrids.length === 0) return;
            var html = '';
            sets.forEach(function (s) {
                var coverStyle = s.cover_image ? 'background-image: url(/static/' + s.cover_image + ')' : '';
                var authorInitial = (s.creator_name || 'U').charAt(0).toUpperCase();
                var authorName = s.creator_name || 'Unknown';
                html += '<div class="vocab-set-card" data-set-id="' + s.id + '">';
                html += '<div class="vocab-set-cover" style="' + coverStyle + '">';
                if (!s.cover_image) html += '<i class="fas fa-book-open"></i>';
                html += '</div>';
                html += '<div class="vocab-set-info">';
                html += '<div class="vocab-set-title">' + s.title + '</div>';
                html += '<div class="vocab-set-meta">';
                html += '<div class="vocab-set-author">';
                html += '<span class="vocab-set-avatar">' + authorInitial + '</span>';
                html += '<span>' + authorName + '</span>';
                html += '</div>';
                html += '<div class="vocab-set-count"><i class="fas fa-clone"></i>' + s.card_count + '</div>';
                html += '</div>';
                html += '</div></div>';
            });
            setsGrids.forEach(grid => { grid.innerHTML = html; });
            document.querySelectorAll('.vocab-set-card').forEach(function (card) {
                card.addEventListener('click', function () {
                    selectedSetId = card.dataset.setId;
                    loadSetDetail(selectedSetId, true);
                });
            });
        }

        function updatePagination(page, hasPrev, hasNext, total) {
            if (paginationBars.length === 0) return;
            var totalPages = Math.max(1, Math.ceil(total / 10));
            paginationBars.forEach(bar => bar.classList.add('visible'));
            prevPageBtns.forEach(btn => btn.disabled = !hasPrev);
            nextPageBtns.forEach(btn => btn.disabled = !hasNext);
            var pageContainer = document.querySelector('.js-vocab-page-numbers');
            if (pageContainer) {
                var html = '';
                for (var i = 1; i <= totalPages; i++) {
                    if (i === 1 || i === totalPages || (i >= page - 1 && i <= page + 1)) {
                        html += '<span class="page-num' + (i === page ? ' active' : '') + '" data-page="' + i + '">' + i + '</span>';
                    } else if (i === 2 && page > 3) {
                        html += '<span class="page-num dots">...</span>';
                    } else if (i === totalPages - 1 && page < totalPages - 2) {
                        html += '<span class="page-num dots">...</span>';
                    }
                }
                pageContainer.innerHTML = html;
                pageContainer.querySelectorAll('.page-num:not(.dots)').forEach(function (el) {
                    el.addEventListener('click', function () {
                        var p = parseInt(el.dataset.page);
                        if (p !== currentPage) loadSets(p);
                    });
                });
            }
        }

        function hidePagination() {
            paginationBars.forEach(bar => bar.classList.remove('visible'));
        }

        prevPageBtns.forEach(btn => {
            btn.addEventListener('click', function () {
                if (currentPage > 1) loadSets(currentPage - 1);
            });
        });

        nextPageBtns.forEach(btn => {
            btn.addEventListener('click', function () {
                loadSets(currentPage + 1);
            });
        });

        function loadSetDetail(setId, pushState) {
            pushState = pushState === undefined ? true : pushState;
            showStep('detail');
            selectedSetId = setId;
            currentStatsPage = 1;
            if (pushState) {
                history.pushState({ setId: setId }, '', '/learn/vocabulary/set/' + setId);
            }
            console.log("Fetching set detail:", setId);
            return fetch('/learn/vocabulary/api/set/' + setId + '?page=1')
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.success) {
                        selectedSetData = data.set;
                        renderSetDetail(data.set, data.course_stats, false, data.pagination_html);
                        checkSetActiveSession(setId);
                        fetch('/learn/vocabulary/api/flashcard-modes/' + setId)
                            .then(r => r.json())
                            .then(modeData => {
                                if (modeData.success) {
                                    setupSettingsModal(setId, modeData);
                                }
                            })
                            .catch(e => console.warn("Failed to load settings:", e));
                    } else {
                        console.error('Failed to load set data:', data.message);
                        alert('Không thể tải thông tin bộ thẻ: ' + (data.message || 'Lỗi không xác định'));
                        throw new Error(data.message);
                    }
                })
                .catch(function (err) {
                    console.error('Error loading set detail:', err);
                    alert('Có lỗi xảy ra khi tải dữ liệu.');
                    throw err;
                });
        }

        const loadMoreBtn = document.querySelector('.js-load-more-words');
        if (loadMoreBtn) loadMoreBtn.style.display = 'none';

        function fetchCourseStatsPage(page) {
            if (!selectedSetId) return;
            const listContainer = document.querySelector('.js-word-list');
            if (listContainer) {
                listContainer.innerHTML = '<div class="py-12 flex justify-center"><i class="fas fa-spinner fa-spin text-2xl text-slate-300"></i></div>';
            }
            const url = '/learn/vocabulary/api/set/' + selectedSetId + '?page=' + page + '&_t=' + new Date().getTime();
            fetch(url)
                .then(r => r.json())
                .then(data => {
                    if (data.success && data.course_stats) {
                        renderSetDetail(selectedSetData, data.course_stats, false, data.pagination_html);
                        const overview = document.getElementById('course-overview-container');
                        if (overview) overview.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                })
                .catch(err => {
                    console.error("Pagination error:", err);
                    alert('Lỗi tải trang.');
                });
        }

        function renderSetDetail(s, stats, append, paginationHtml) {
            append = append || false;
            paginationHtml = paginationHtml || '';
            if (!append) {
                var coverEl = document.querySelector('.js-detail-cover');
                if (coverEl) {
                    if (s.cover_image) {
                        coverEl.style.backgroundImage = 'url(/static/' + s.cover_image + ')';
                        coverEl.innerHTML = '';
                    } else {
                        coverEl.style.backgroundImage = '';
                        coverEl.innerHTML = '<i class="fas fa-book-open"></i>';
                    }
                }
                const els = {
                    title: document.querySelector('.js-detail-title'),
                    titleFull: document.querySelector('.js-detail-title-full'),
                    desc: document.querySelector('.js-detail-desc'),
                    creator: document.querySelector('.js-creator-name'),
                    avatar: document.querySelector('.js-creator-avatar'),
                    cardCount: document.querySelector('.js-card-count'),
                    progressCount: document.querySelector('.js-progress-count')
                };
                if (els.title) els.title.textContent = s.title;
                if (els.titleFull) els.titleFull.textContent = s.title;
                if (els.desc) els.desc.textContent = s.description || 'Không có mô tả';
                if (els.creator) els.creator.textContent = s.creator_name;
                if (els.avatar) els.avatar.textContent = s.creator_name.charAt(0).toUpperCase();
                if (els.cardCount) els.cardCount.textContent = s.card_count;

                const learnedCount = stats && stats.learned_count !== undefined ? stats.learned_count : 0;
                const totalCount = stats && stats.total_count !== undefined ? stats.total_count : s.card_count;
                if (els.progressCount) els.progressCount.textContent = learnedCount + '/' + totalCount;

                const headerTitle = document.querySelector('.js-header-title');
                const headerCardCount = document.querySelector('.js-header-card-count');
                const headerProgressPercent = document.querySelector('.js-header-progress-percent');
                if (headerTitle) headerTitle.textContent = s.title;
                if (headerCardCount) headerCardCount.textContent = s.card_count;
                const progressPercent = totalCount > 0 ? Math.round((learnedCount / totalCount) * 100) : 0;
                if (headerProgressPercent) headerProgressPercent.textContent = progressPercent + '%';

                const detailContent = document.querySelector('.vocab-detail-content');
                if (detailContent) detailContent.style.opacity = '1';

                const editBtn = document.querySelector('.js-edit-set-btn');
                if (editBtn) {
                    if (s.can_edit) {
                        editBtn.style.display = 'flex';
                        editBtn.href = '/content/flashcards/edit/' + s.id;
                    } else {
                        editBtn.style.display = 'none';
                    }
                }
            }

            const overviewContainer = document.getElementById('course-overview-container');
            if (overviewContainer) overviewContainer.style.display = 'none';

            const vocabScroll = document.querySelector('#step-detail .vocab-scroll');
            const headerInfo = document.querySelector('.step-header-info');
            const detailTitle = document.querySelector('.vocab-detail-title');
            if (vocabScroll && headerInfo && detailTitle) {
                vocabScroll.addEventListener('scroll', function () {
                    const titleRect = detailTitle.getBoundingClientRect();
                    const headerHeight = document.querySelector('.step-header-left')?.offsetHeight || 60;
                    if (titleRect.bottom < headerHeight) {
                        headerInfo.style.opacity = '1';
                    } else {
                        headerInfo.style.opacity = '0';
                    }
                });
            }

            if (stats && stats.items) {
                const listContainer = document.querySelector('.js-word-list');
                if (listContainer) {
                    let listHtml = '';
                    if (stats.items && stats.items.length > 0) {
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
                            <div class="group p-4 bg-white border border-slate-100 rounded-xl hover:border-indigo-200 hover:shadow-lg transition-all duration-300 mb-3 relative overflow-hidden js-item-stats-trigger cursor-pointer" data-item-id="${item.item_id || item.id}" style="animation: slideIn 0.3s ease-out;">
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
                    } else {
                        listHtml = '<div class="py-12 text-center flex flex-col items-center justify-center text-slate-400"><i class="fas fa-inbox text-4xl mb-3 text-slate-200"></i><span class="text-sm">Chưa có từ vựng nào.</span></div>';
                    }
                    listContainer.innerHTML = listHtml;
                    bindStatsModalEvents();
                }

                const detailPaginationBar = document.querySelector('#detail-pagination-bar');
                if (detailPaginationBar && paginationHtml) {
                    detailPaginationBar.innerHTML = paginationHtml;
                    detailPaginationBar.classList.add('visible');
                    detailPaginationBar.querySelectorAll('a').forEach(link => {
                        link.addEventListener('click', function (e) {
                            e.preventDefault();
                            const url = new URL(this.href);
                            const page = url.searchParams.get('page');
                            if (page) fetchCourseStatsPage(page);
                        });
                    });
                } else if (detailPaginationBar && stats.pagination && stats.pagination.pages <= 1) {
                    detailPaginationBar.classList.remove('visible');
                }
            } else {
                const listContainer = document.querySelector('.js-word-list');
                if (listContainer) {
                    listContainer.innerHTML = '<div class="py-12 text-center flex flex-col items-center justify-center text-slate-400"><i class="fas fa-search text-4xl mb-3 text-slate-200"></i><span class="text-sm">Không tìm thấy từ vựng nào.</span></div>';
                }
                if (overviewContainer) overviewContainer.style.display = 'none';
            }
        }

        document.querySelectorAll('.js-start-learning').forEach(function (btn) {
            btn.addEventListener('click', function () {
                if (selectedSetId) {
                    window.location.href = '/learn/vocabulary/modes/' + selectedSetId;
                    return;
                }
            });
        });

        function updateModeVisibility() {
            if (!selectedSetData) return;
            // console.log("Updating visibility for set:", selectedSetData);
            if (!selectedSetData.capabilities || selectedSetData.capabilities.length === 0) {
                document.querySelectorAll('.js-mode-select').forEach(el => el.style.display = 'flex');
                return;
            }
            const caps = new Set(selectedSetData.capabilities);
            const mapping = {
                'flashcard': 'supports_flashcard',
                'mcq': 'supports_quiz',
                'typing': 'supports_writing',
                'matching': 'supports_matching',
                'speed': 'supports_speed',
                'listening': 'supports_listening',
                'mixed': 'supports_srs'
            };

            let hasVisible = false;
            document.querySelectorAll('.js-mode-select').forEach(card => {
                const mode = card.dataset.mode;
                const flag = mapping[mode];
                if (flag && caps.has(flag)) {
                    card.style.display = 'flex';
                    hasVisible = true;
                } else {
                    card.style.display = 'none';
                }
            });
            if (!hasVisible) {
                document.querySelectorAll('.js-mode-select').forEach(el => el.style.display = 'flex');
            }
        }

        if (continueBtn) {
            continueBtn.addEventListener('click', function () {
                if (!selectedMode) return;
                startSession(selectedMode);
            });
        }

        function startSession(mode) {
            if (!selectedSetId) return;
            if (mode === 'flashcard') {
                window.location.href = '/learn/vocabulary/flashcard/setup/' + selectedSetId;
            } else if (mode === 'mcq') {
                window.location.href = '/learn/vocabulary/mcq/setup/' + selectedSetId;
            } else if (mode === 'typing') {
                window.location.href = '/learn/vocabulary/typing/setup/' + selectedSetId;
            } else if (mode === 'mixed') {
                alert('Chế độ Học thông minh đang được phát triển');
            } else if (mode === 'matching') {
                window.location.href = '/learn/vocabulary/matching/session/' + selectedSetId;
            } else if (mode === 'speed') {
                window.location.href = '/learn/vocabulary/speed/setup/' + selectedSetId;
            } else if (mode === 'listening') {
                window.location.href = '/learn/vocabulary/listening/setup/' + selectedSetId;
            }
        }

        function loadFlashcardOptions(setId) {
            showStep('flashcard-options');
            history.pushState({ step: 'flashcard-options', setId: setId }, '', '/learn/vocabulary/set/' + setId + '/flashcard');

            var setNameEl = document.querySelector('.js-selected-set-name-fc');
            if (setNameEl) {
                if (selectedSetData && selectedSetData.title) {
                    setNameEl.textContent = selectedSetData.title;
                } else {
                    setNameEl.textContent = 'Đang tải...';
                    fetch('/learn/vocabulary/api/set/' + setId + '?page=1')
                        .then(function (r) { return r.json(); })
                        .then(function (data) {
                            if (data.success && data.set) {
                                setNameEl.textContent = data.set.title;
                                selectedSetData = data.set;
                                selectedSetId = setId;
                            }
                        })
                        .catch(function () { });
                }
            }

            var container = document.getElementById('flashcard-modes-container');
            if (!container) return;
            container.innerHTML = '<div class="vocab-loading"><i class="fas fa-spinner fa-spin"></i><p>Đang tải...</p></div>';

            fetch('/learn/vocabulary/api/flashcard-modes/' + setId)
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.success && data.modes) {
                        renderFlashcardModes(data.modes, setId, data.user_button_count);
                        setupSettingsModal(setId, data); // Ensure this is called
                    } else {
                        container.innerHTML = '<div class="vocab-empty"><i class="fas fa-exclamation-triangle"></i><p>Lỗi tải chế độ học</p></div>';
                    }
                })
                .catch(function (err) {
                    container.innerHTML = '<div class="vocab-empty"><i class="fas fa-exclamation-triangle"></i><p>Lỗi kết nối</p></div>';
                });
        }

        document.addEventListener('click', function (e) {
            const btn = e.target.closest('.js-open-flashcard-settings');
            if (btn) {
                e.preventDefault();
                if (!selectedSetId) {
                    console.warn("No set selected");
                    return;
                }
                const modal = document.getElementById('flashcard-settings-modal');
                if (modal) modal.style.display = 'flex';
            }
        });

        function renderFlashcardModes(modes, setId, userButtonCount) {
            var container = document.getElementById('flashcard-modes-container');
            if (!container) return;

            var modeIcons = {
                'new_only': { icon: 'fa-star', color: 'linear-gradient(135deg, #f59e0b, #fbbf24)' },
                'all_review': { icon: 'fa-redo', color: 'linear-gradient(135deg, #3b82f6, #60a5fa)' },
                'hard_only': { icon: 'fa-fire', color: 'linear-gradient(135deg, #ef4444, #f87171)' },
                'mixed_srs': { icon: 'fa-brain', color: 'linear-gradient(135deg, #8b5cf6, #a78bfa)' }
            };

            var modeNames = {
                'new_only': 'Chỉ làm mới',
                'all_review': 'Ôn tập đã làm',
                'hard_only': 'Ôn tập câu khó',
                'mixed_srs': 'Học thông minh (SRS)'
            };

            var html = '';
            modes.forEach(function (mode) {
                var iconInfo = modeIcons[mode.id] || { icon: 'fa-book', color: 'linear-gradient(135deg, #64748b, #94a3b8)' };
                var displayName = modeNames[mode.id] || mode.name;
                var isDisabled = mode.count === 0;

                html += '<div class="mode-select-card js-flashcard-mode-select' + (isDisabled ? ' disabled' : '') + '" data-mode-id="' + mode.id + '"' + (isDisabled ? ' style="opacity: 0.5; filter: grayscale(100%); pointer-events: none; background: #f1f5f9;"' : '') + '>';
                html += '<div class="mode-select-icon" style="background: ' + iconInfo.color + ';"><i class="fas ' + iconInfo.icon + '"></i></div>';
                html += '<div class="mode-select-info">';
                html += '<div class="mode-select-name">' + displayName + '</div>';
                html += '<div class="mode-select-desc">' + mode.count + ' thẻ</div>';
                html += '</div>';
                html += '<span class="mode-select-check"><i class="fas fa-check"></i></span>';
                html += '</div>';
            });

            container.innerHTML = html;
            bindFlashcardModeEvents(setId, userButtonCount);
        }

        var selectedFlashcardMode = null;
        function bindFlashcardModeEvents(setId, userButtonCount) {
            var container = document.getElementById('flashcard-modes-container');
            if (!container) return;
            var continueBtn = document.querySelector('.js-flashcard-mode-continue');

            container.querySelectorAll('.js-flashcard-mode-select').forEach(function (card) {
                if (card.classList.contains('disabled')) return;
                card.addEventListener('click', function () {
                    container.querySelectorAll('.js-flashcard-mode-select').forEach(function (c) {
                        c.classList.remove('selected');
                    });
                    card.classList.add('selected');
                    selectedFlashcardMode = card.dataset.modeId;
                    if (continueBtn) continueBtn.disabled = false;
                });
            });

            var stepContainer = document.getElementById('step-flashcard-options');
            var ratingInputs = stepContainer ? stepContainer.querySelectorAll('input[name="rating_levels"]') : [];

            function updateRatingVisuals() {
                ratingInputs.forEach(function (r) {
                    var label = r.closest('label');
                    if (r.checked) {
                        label.classList.remove('border-slate-200', 'bg-white', 'text-slate-700');
                        label.classList.add('border-indigo-500', 'bg-indigo-50', 'text-indigo-700');
                    } else {
                        label.classList.add('border-slate-200', 'bg-white', 'text-slate-700');
                        label.classList.remove('border-indigo-500', 'bg-indigo-50', 'text-indigo-700');
                    }
                });
            }

            var selectedButtonCount = userButtonCount || 4;
            ratingInputs.forEach(function (r) {
                if (parseInt(r.value) === parseInt(selectedButtonCount)) {
                    r.checked = true;
                } else {
                    r.checked = false;
                }
            });
            updateRatingVisuals();

            ratingInputs.forEach(function (radio) {
                radio.addEventListener('change', updateRatingVisuals);
            });

            if (continueBtn) {
                continueBtn.addEventListener('click', function () {
                    if (!selectedFlashcardMode || !selectedSetId) return;
                    var ratingLevel = document.querySelector('input[name="rating_levels"]:checked').value || 4;
                    window.location.href = '/learn/start_flashcard_session/' + selectedSetId + '/' + selectedFlashcardMode + '?rating_levels=' + ratingLevel;
                });
            }
        }

        function loadMcqOptions(setId) {
            showStep('mcq-options');
            history.pushState({ step: 'mcq-options', setId: setId }, '', '/learn/vocabulary/set/' + setId + '/mcq');
            mcqOptionsContainer.innerHTML = '<div class="flex justify-center py-8"><i class="fas fa-spinner fa-spin text-blue-500 text-3xl"></i></div>';

            fetch('/learn/get_quiz_modes_partial/' + setId)
                .then(r => r.text())
                .then(html => {
                    mcqOptionsContainer.innerHTML = html;
                    mcqOptionsContainer.querySelectorAll('script').forEach(function (oldScript) {
                        var newScript = document.createElement('script');
                        newScript.textContent = oldScript.textContent;
                        document.body.appendChild(newScript);
                    });
                    mcqOptionsContainer.querySelectorAll('.js-back-to-modes').forEach(function (btn) {
                        btn.addEventListener('click', function () { showStep('modes'); });
                    });
                    bindQuizModeEvents(setId);
                })
                .catch(err => {
                    mcqOptionsContainer.innerHTML = '<div class="text-center text-red-500 py-4">Lỗi tải tùy chọn. Vui lòng thử lại.</div>';
                });
        }

        function bindQuizModeEvents(setId) {
            if (!mcqOptionsContainer) return;
            var selectedQuizMode = null;
            var continueBtn = mcqOptionsContainer.querySelector('.js-quiz-continue');

            mcqOptionsContainer.querySelectorAll('.quiz-mode-item').forEach(function (card) {
                if (card.classList.contains('opacity-50')) return;
                card.addEventListener('click', function () {
                    mcqOptionsContainer.querySelectorAll('.quiz-mode-item').forEach(function (c) {
                        c.classList.remove('selected', 'border-indigo-500', 'bg-indigo-50');
                        c.classList.add('border-gray-200', 'bg-white');
                    });
                    card.classList.remove('border-gray-200', 'bg-white');
                    card.classList.add('selected', 'border-indigo-500', 'bg-indigo-50');
                    selectedQuizMode = card.dataset.modeId;
                    if (continueBtn) continueBtn.disabled = false;
                });
            });

            if (continueBtn) {
                continueBtn.addEventListener('click', function () {
                    if (!selectedQuizMode) return;
                    var batchSizeSelect = mcqOptionsContainer.querySelector('#session-size-select');
                    var batchSize = batchSizeSelect ? parseInt(batchSizeSelect.value) : 10;
                    window.location.href = '/learn/start_quiz_session/' + setId + '/' + selectedQuizMode + '?batch_size=' + (batchSize || 10);
                });
            }
        }

        function setupSettingsModal(setId, data) {
            const modal = document.getElementById('flashcard-settings-modal');
            const closeBtns = document.querySelectorAll('.js-close-settings-modal');
            const saveBtn = document.querySelector('.js-save-settings');
            const overlay = modal;

            const modeSelect = document.getElementById('setting-mode-select');
            const autoSaveToggle = document.getElementById('setting-auto-save');
            const modeSections = document.querySelectorAll('.mode-section');
            const viewStates = document.querySelectorAll('.js-state-view');
            const editStates = document.querySelectorAll('.js-state-edit');

            const fcFixedBtnButtons = document.querySelectorAll('.js-fixed-btn-count');
            const fcFixedBtnInput = document.getElementById('setting-fc-button-count');
            const fcAutoplayToggle = document.getElementById('setting-fc-autoplay');
            const fcShowImageToggle = document.getElementById('setting-fc-show-image');
            const fcShowStatsToggle = document.getElementById('setting-fc-show-stats');

            const labelFcBtnCount = document.querySelector('.js-last-btn-count');
            const labelFcAutoplay = document.querySelector('.js-last-autoplay');
            const labelFcShowImage = document.querySelector('.js-last-show-image');
            const labelFcShowStats = document.querySelector('.js-last-show-stats');

            if (!modal) return;

            let settings = data.settings || {};
            let isAuto = settings.auto_save !== false;
            let lastMode = settings.last_mode || 'flashcard';
            let fcSettings = settings.flashcard || {};

            // [DEBUG] Log settings
            // console.log('[MODAL DEBUG] data.settings:', data.settings);

            if (modeSelect) modeSelect.value = lastMode;
            if (autoSaveToggle) autoSaveToggle.checked = isAuto;

            const syncUI = () => {
                modeSections.forEach(s => s.id === 'mode-settings-' + modeSelect.value ? s.classList.remove('hidden') : s.classList.add('hidden'));
                const currentIsAuto = autoSaveToggle.checked;
                viewStates.forEach(v => currentIsAuto ? v.classList.remove('hidden') : v.classList.add('hidden'));
                editStates.forEach(e => currentIsAuto ? e.classList.add('hidden') : e.classList.remove('hidden'));
            };

            const initFlashcardData = () => {
                if (labelFcBtnCount) labelFcBtnCount.textContent = (fcSettings.button_count || data.user_button_count || 4) + ' nút';
                if (labelFcAutoplay) labelFcAutoplay.textContent = (fcSettings.autoplay !== false ? 'BẬT' : 'TẮT');
                if (labelFcShowImage) labelFcShowImage.textContent = (fcSettings.show_image !== false ? 'HIỆN' : 'ẨN');
                if (labelFcShowStats) labelFcShowStats.textContent = (fcSettings.show_stats !== false ? 'HIỆN' : 'ẨN');

                const btnCountToUse = fcSettings.button_count || data.user_button_count || 4;
                if (fcFixedBtnInput) fcFixedBtnInput.value = btnCountToUse;
                fcFixedBtnButtons.forEach(btn => {
                    if (parseInt(btn.dataset.value) === btnCountToUse) {
                        btn.classList.add('border-indigo-600', 'bg-indigo-50', 'text-indigo-600');
                    } else {
                        btn.classList.remove('border-indigo-600', 'bg-indigo-50', 'text-indigo-600');
                    }
                    btn.onclick = () => {
                        fcFixedBtnButtons.forEach(b => b.classList.remove('border-indigo-600', 'bg-indigo-50', 'text-indigo-600'));
                        btn.classList.add('border-indigo-600', 'bg-indigo-50', 'text-indigo-600');
                        if (fcFixedBtnInput) fcFixedBtnInput.value = btn.dataset.value;
                    };
                });

                if (fcAutoplayToggle) fcAutoplayToggle.checked = fcSettings.autoplay !== false;
                if (fcShowImageToggle) fcShowImageToggle.checked = fcSettings.show_image !== false;
                if (fcShowStatsToggle) fcShowStatsToggle.checked = fcSettings.show_stats !== false;
            };

            initFlashcardData();
            syncUI();

            if (modeSelect) modeSelect.onchange = syncUI;
            if (autoSaveToggle) autoSaveToggle.onchange = syncUI;

            const closeModal = () => modal.style.display = 'none';
            closeBtns.forEach(btn => btn.onclick = closeModal);
            if (overlay) overlay.onclick = function (e) { if (e.target === overlay) closeModal(); };

            if (saveBtn) {
                saveBtn.onclick = function () {
                    const currentAuto = autoSaveToggle.checked;
                    const activeMode = modeSelect.value;

                    const payload = {
                        ...settings,
                        auto_save: currentAuto,
                        last_mode: activeMode,
                        flashcard: {
                            autoplay: fcAutoplayToggle ? fcAutoplayToggle.checked : true,
                            show_image: fcShowImageToggle ? fcShowImageToggle.checked : true,
                            show_stats: fcShowStatsToggle ? fcShowStatsToggle.checked : true,
                            button_count: (!currentAuto && fcFixedBtnInput)
                                ? parseInt(fcFixedBtnInput.value)
                                : (fcSettings.button_count || data.user_button_count || 4)
                        }
                    };

                    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
                    const headers = { 'Content-Type': 'application/json' };
                    if (csrfToken) headers['X-CSRFToken'] = csrfToken;

                    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang lưu...';

                    fetch('/learn/vocabulary/api/settings/container/' + setId, {
                        method: 'POST',
                        headers: headers,
                        body: JSON.stringify(payload)
                    }).then(async r => {
                        if (!r.ok) {
                            const text = await r.text();
                            console.error('Server error:', text);
                            throw new Error('Server returned ' + r.status);
                        }
                        return r.json();
                    })
                        .then(d => {
                            if (d.success) {
                                closeModal();
                                if (typeof loadFlashcardOptions === 'function' && activeMode === 'flashcard') {
                                    const step = document.getElementById('step-flashcard-options');
                                    if (step && step.classList.contains('active')) loadFlashcardOptions(setId);
                                }
                                showToast('<i class="fas fa-check-circle text-emerald-400"></i> Cấu hình đã được lưu');
                            }
                        })
                        .finally(() => saveBtn.textContent = 'Lưu cấu hình');
                };
            }

            function showToast(html) {
                const toast = document.createElement('div');
                toast.className = 'fixed bottom-4 right-4 bg-slate-800 text-white px-6 py-3 rounded-2xl shadow-2xl z-[9999] flex items-center gap-3 animate-slideInUp';
                toast.innerHTML = html;
                document.body.appendChild(toast);
                setTimeout(() => {
                    toast.classList.replace('animate-slideInUp', 'animate-fadeOut');
                    setTimeout(() => toast.remove(), 500);
                }, 3000);
            }
        }

        function bindStatsModalEvents() {
            const triggers = document.querySelectorAll('.js-item-stats-trigger');
            triggers.forEach(trigger => {
                trigger.removeEventListener('click', handleStatsClick);
                trigger.addEventListener('click', handleStatsClick);
            });
        }

        function handleStatsClick(e) {
            if (e.target.closest('button') || e.target.closest('a')) return;
            const itemId = this.dataset.itemId;
            if (itemId) openStatsModal(itemId);
        }

        const statsModal = document.getElementById('item-stats-modal');
        const closeStatsBtns = document.querySelectorAll('.js-close-stats-modal');

        if (closeStatsBtns) {
            closeStatsBtns.forEach(btn => {
                btn.addEventListener('click', function () {
                    if (statsModal) statsModal.style.display = 'none';
                });
            });
        }

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && statsModal && statsModal.style.display !== 'none') {
                statsModal.style.display = 'none';
            }
        });

        function openStatsModal(itemId) {
            if (window.openVocabularyItemStats) {
                window.openVocabularyItemStats(itemId);
            } else {
                console.error("openVocabularyItemStats not found");
            }
        }

        window.showLogDetails = function (btn, index) {
            const container = btn.closest('.history-scroll');
            if (container) {
                container.querySelectorAll('.history-btn').forEach(b => {
                    b.style.borderColor = 'transparent';
                    b.style.transform = 'scale(1)';
                    b.style.boxShadow = 'none';
                });
            }
            btn.style.borderColor = '#6366f1';
            btn.style.transform = 'scale(1.1)';
            btn.style.boxShadow = '0 4px 6px -1px rgba(99, 102, 241, 0.3)';

            const timestampEl = document.getElementById('detail-timestamp');
            if (timestampEl) timestampEl.textContent = btn.dataset.timestamp;
            const modeEl = document.getElementById('detail-mode');
            if (modeEl) modeEl.textContent = btn.dataset.mode;
            const res = btn.dataset.result;
            const rEl = document.getElementById('detail-result');
            if (rEl) {
                rEl.textContent = res;
                rEl.style.color = res === 'Correct' ? '#16a34a' : '#dc2626';
            }
            const answerEl = document.getElementById('detail-answer');
            if (answerEl) answerEl.textContent = btn.dataset.answer;
            const durEl = document.getElementById('detail-duration');
            if (durEl) durEl.textContent = btn.dataset.duration;

            const panel = document.getElementById('log-detail-panel');
            if (panel) {
                panel.style.display = 'block';
                panel.style.animation = 'none';
                panel.offsetHeight;
                panel.style.animation = 'fadeIn 0.3s ease';
            }
        };

    })();
});

// Edit Set Logic
document.addEventListener('DOMContentLoaded', function () {
    const editSetModal = document.getElementById('edit-set-modal');
    const editSetFormContainer = document.getElementById('edit-set-form-container');
    const closeEditModalBtn = document.querySelector('.js-close-edit-modal');

    window.openEditSetModal = function (setId) {
        if (!editSetModal) return;
        editSetModal.classList.remove('hidden');
        editSetModal.style.display = 'flex';
        editSetFormContainer.innerHTML = '<div class="flex justify-center items-center h-64"><i class="fas fa-spinner fa-spin text-4xl text-blue-500"></i></div>';

        fetch('/content/flashcards/edit/' + setId + '?partial=true')
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.text();
            })
            .then(html => {
                editSetFormContainer.innerHTML = html;
                const scriptTags = editSetFormContainer.querySelectorAll('script');
                scriptTags.forEach(script => {
                    const newScript = document.createElement('script');
                    Array.from(script.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
                    newScript.appendChild(document.createTextNode(script.innerHTML));
                    script.parentNode.replaceChild(newScript, script);
                });

                const form = editSetFormContainer.querySelector('form');
                if (form) {
                    form.addEventListener('submit', function (e) {
                        e.preventDefault();
                        const formData = new FormData(form);
                        fetch(form.action, {
                            method: 'POST',
                            body: formData
                        }).then(r => r.json()).then(data => {
                            if (data.success) {
                                alert('Cập nhật thành công!');
                                editSetModal.style.display = 'none';
                                editSetModal.classList.add('hidden');
                                window.location.reload();
                            } else {
                                alert('Lỗi: ' + data.message);
                            }
                        }).catch(err => {
                            alert('Có lỗi xảy ra.');
                            console.error(err);
                        });
                    });
                }
            })
            .catch(error => {
                editSetFormContainer.innerHTML = '<div class="text-center text-red-500 mt-10">Cannot load edit form.<br>' + error.message + '</div>';
            });
    };

    if (closeEditModalBtn) {
        closeEditModalBtn.addEventListener('click', function () {
            editSetModal.style.display = 'none';
            editSetModal.classList.add('hidden');
        });
    }

    if (editSetModal) {
        editSetModal.addEventListener('click', function (e) {
            if (e.target === editSetModal) {
                editSetModal.style.display = 'none';
                editSetModal.classList.add('hidden');
            }
        });
    }
});
