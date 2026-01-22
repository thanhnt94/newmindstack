/**
 * Quiz Dashboard JavaScript
 * Version: 1.0
 * 
 * Unified logic for both mobile step navigation and desktop sidebar view.
 */

(function () {
    'use strict';

    // State
    let currentCategory = 'my';
    let currentSearch = '';
    let currentPage = 1;
    let selectedSetId = null;
    let selectedSetData = null;
    let selectedMode = null;

    // URLs (set from Jinja template)
    let apiSetsUrl = '';
    let apiSetDetailUrl = '';
    let startSessionUrl = '';
    let initialSetId = null;
    let savedBatchSize = 10;

    // DOM Elements - Mobile
    let stepBrowser, stepDetail, stepModes;
    let setsGrid, searchInput, modesContainer, startSessionBtn;
    let paginationBar, prevPageBtn, nextPageBtn;

    // DOM Elements - Desktop
    let desktopSetsGrid, desktopSearchInput, desktopPagination;
    let setDetailPanel, panelOverlay;

    /**
     * Initialize the dashboard
     */
    function init(config) {
        apiSetsUrl = config.apiSetsUrl;
        apiSetDetailUrl = config.apiSetDetailUrl;
        startSessionUrl = config.startSessionUrl;
        initialSetId = config.initialSetId;
        savedBatchSize = config.savedBatchSize || 10;

        // Mobile elements
        stepBrowser = document.getElementById('step-browser');
        stepDetail = document.getElementById('step-detail');
        stepModes = document.getElementById('step-modes');
        setsGrid = document.getElementById('sets-grid');
        searchInput = document.getElementById('search-input');
        modesContainer = document.querySelector('.js-modes-container');
        startSessionBtn = document.querySelector('.js-start-session');
        paginationBar = document.getElementById('pagination-bar');
        prevPageBtn = document.querySelector('.js-prev-page');
        nextPageBtn = document.querySelector('.js-next-page');

        // Desktop elements
        desktopSetsGrid = document.getElementById('desktop-sets-grid');
        desktopSearchInput = document.getElementById('desktop-search-input');
        desktopPagination = document.getElementById('desktop-pagination');
        setDetailPanel = document.getElementById('set-detail-panel');
        panelOverlay = document.getElementById('panel-overlay');

        bindEvents();
        initToggleState();

        // Check for initial set ID
        if (initialSetId) {
            loadSetDetail(initialSetId);
        } else {
            loadSets();
        }
    }

    /**
     * Bind all event listeners
     */
    function bindEvents() {
        // Mobile category tabs
        document.querySelectorAll('.quiz-tab').forEach(tab => {
            tab.addEventListener('click', function () {
                document.querySelectorAll('.quiz-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentCategory = tab.dataset.category;
                loadSets();
            });
        });

        // Desktop category tabs
        document.querySelectorAll('.content-tab').forEach(tab => {
            tab.addEventListener('click', function () {
                document.querySelectorAll('.content-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentCategory = tab.dataset.tab;
                loadSets();
            });
        });

        // Mobile search
        let searchTimeout;
        if (searchInput) {
            searchInput.addEventListener('input', function () {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    currentSearch = searchInput.value;
                    loadSets();
                }, 300);
            });
        }

        // Desktop search
        if (desktopSearchInput) {
            desktopSearchInput.addEventListener('input', function () {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    currentSearch = desktopSearchInput.value;
                    loadSets();
                }, 300);
            });
        }

        // Keyboard shortcut for search
        document.addEventListener('keydown', function (e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const input = desktopSearchInput || searchInput;
                if (input) input.focus();
            }
        });

        // Back buttons (mobile)
        document.querySelectorAll('.js-back-to-browser').forEach(btn => {
            btn.addEventListener('click', () => {
                showStep('browser');
                history.pushState(null, '', '/learn/quiz/');
            });
        });

        document.querySelectorAll('.js-back-to-detail').forEach(btn => {
            btn.addEventListener('click', () => showStep('detail'));
        });

        // Start Learning button (mobile - go to modes)
        document.querySelector('.js-start-learning')?.addEventListener('click', () => {
            showStep('modes');
            loadModes();
        });

        // Start Session button (mobile)
        startSessionBtn?.addEventListener('click', () => startSession('mobile'));

        // Desktop: Close panel
        document.querySelector('.js-close-panel')?.addEventListener('click', closeDetailPanel);
        panelOverlay?.addEventListener('click', closeDetailPanel);

        // Desktop: Start session
        document.querySelector('.js-desktop-start-session')?.addEventListener('click', () => startSession('desktop'));

        // Toggle logic
        document.addEventListener('change', handleToggleChange);

        // Pagination (mobile)
        prevPageBtn?.addEventListener('click', () => {
            if (currentPage > 1) loadSets(currentPage - 1);
        });

        nextPageBtn?.addEventListener('click', () => {
            loadSets(currentPage + 1);
        });

        // Browser back button
        window.addEventListener('popstate', handlePopState);

        // Desktop: Mode buttons in sidebar
        document.querySelectorAll('.mode-item[data-mode]').forEach(btn => {
            btn.addEventListener('click', function () {
                if (!selectedSetId) {
                    alert('Vui lòng chọn một bộ quiz trước');
                    return;
                }
                const mode = this.dataset.mode;
                // Navigate directly or show panel
                if (mode === 'battle') {
                    window.location.href = '/learn/quiz/battle/' + selectedSetId;
                } else {
                    openDetailPanel(selectedSetId);
                }
            });
        });
    }

    /**
     * Show mobile step
     */
    function showStep(step) {
        stepBrowser?.classList.remove('active');
        stepDetail?.classList.remove('active');
        stepModes?.classList.remove('active');

        if (step === 'browser') stepBrowser?.classList.add('active');
        else if (step === 'detail') stepDetail?.classList.add('active');
        else if (step === 'modes') stepModes?.classList.add('active');
    }

    /**
     * Load sets from API
     */
    function loadSets(page = 1) {
        currentPage = page;

        // Mobile grid
        if (setsGrid) {
            setsGrid.innerHTML = '<div class="quiz-loading" style="grid-column: 1/-1;"><i class="fas fa-spinner fa-spin"></i><p>Đang tải...</p></div>';
        }

        // Desktop grid
        if (desktopSetsGrid) {
            desktopSetsGrid.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin"></i><p>Đang tải bộ quiz...</p></div>';
        }

        let url = apiSetsUrl + '?category=' + currentCategory + '&page=' + page;
        if (currentSearch) url += '&q=' + encodeURIComponent(currentSearch);

        fetch(url)
            .then(r => r.json())
            .then(data => {
                if (data.success && data.sets.length > 0) {
                    renderSets(data.sets);
                    updatePagination(data.page, data.has_prev, data.has_next, data.total);

                    // Update desktop stats
                    if (data.stats) {
                        updateDesktopStats(data.stats);
                    }
                } else {
                    renderEmptyState();
                    hidePagination();
                }
            })
            .catch(() => {
                renderErrorState();
                hidePagination();
            });
    }

    /**
     * Render sets to both mobile and desktop grids
     */
    function renderSets(sets) {
        // Mobile render
        if (setsGrid) {
            let html = '';
            sets.forEach(s => {
                html += renderSetCardMobile(s);
            });
            setsGrid.innerHTML = html;

            // Bind click - mobile goes to detail page
            document.querySelectorAll('#sets-grid .quiz-set-card').forEach(card => {
                card.addEventListener('click', () => {
                    const setId = card.dataset.setId;
                    window.location.href = '/learn/quiz/set/' + setId;
                });
            });
        }

        // Desktop render
        if (desktopSetsGrid) {
            let html = '';
            sets.forEach(s => {
                html += renderSetCardDesktop(s);
            });
            desktopSetsGrid.innerHTML = html;

            // Bind click - desktop opens side panel
            document.querySelectorAll('#desktop-sets-grid .set-card-desktop').forEach(card => {
                card.addEventListener('click', () => {
                    const setId = card.dataset.setId;
                    openDetailPanel(setId);
                });
            });
        }
    }

    /**
     * Render mobile set card
     */
    function renderSetCardMobile(s) {
        const coverStyle = s.cover_image ? 'background-image: url(/static/' + s.cover_image + ')' : '';
        const authorInitial = (s.creator_name || 'U').charAt(0).toUpperCase();
        const authorName = s.creator_name || 'Unknown';

        return `
            <div class="quiz-set-card" data-set-id="${s.id}">
                <div class="quiz-set-cover" style="${coverStyle}">
                    ${!s.cover_image ? '<i class="fas fa-question-circle"></i>' : ''}
                </div>
                <div class="quiz-set-info">
                    <div class="quiz-set-title">${s.title}</div>
                    <div class="quiz-set-meta">
                        <div class="quiz-set-author">
                            <span class="quiz-set-avatar">${authorInitial}</span>
                            <span>${authorName}</span>
                        </div>
                        <div class="quiz-set-count"><i class="fas fa-list-check"></i>${s.question_count}</div>
                    </div>
                </div>
            </div>`;
    }

    /**
     * Render desktop set card
     */
    function renderSetCardDesktop(s) {
        const authorInitial = (s.creator_name || 'U').charAt(0).toUpperCase();
        const authorName = s.creator_name || 'Unknown';

        return `
            <div class="set-card-desktop" data-set-id="${s.id}">
                <div class="set-card-cover">
                    ${s.cover_image
                ? `<img src="/static/${s.cover_image}" alt="${s.title}">`
                : '<i class="fas fa-question-circle set-card-cover-placeholder"></i>'}
                </div>
                <div class="set-card-body">
                    <div class="set-card-title">${s.title}</div>
                    <div class="set-card-meta">
                        <div class="set-card-author">
                            <span class="set-card-author-avatar">${authorInitial}</span>
                            <span>${authorName}</span>
                        </div>
                        <div class="set-card-count">
                            <i class="fas fa-list-check"></i>
                            ${s.question_count}
                        </div>
                    </div>
                </div>
            </div>`;
    }

    /**
     * Render empty state
     */
    function renderEmptyState() {
        const html = '<div class="quiz-empty" style="grid-column: 1/-1;"><i class="fas fa-folder-open"></i><p>Không có bộ quiz nào</p></div>';
        const desktopHtml = '<div class="empty-state"><i class="fas fa-folder-open"></i><p>Không có bộ quiz nào</p></div>';

        if (setsGrid) setsGrid.innerHTML = html;
        if (desktopSetsGrid) desktopSetsGrid.innerHTML = desktopHtml;
    }

    /**
     * Render error state
     */
    function renderErrorState() {
        const html = '<div class="quiz-empty" style="grid-column: 1/-1;"><i class="fas fa-exclamation-triangle"></i><p>Lỗi tải dữ liệu</p></div>';
        const desktopHtml = '<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Lỗi tải dữ liệu</p></div>';

        if (setsGrid) setsGrid.innerHTML = html;
        if (desktopSetsGrid) desktopSetsGrid.innerHTML = desktopHtml;
    }

    /**
     * Update pagination (mobile)
     */
    function updatePagination(page, hasPrev, hasNext, total) {
        if (!paginationBar) return;

        const totalPages = Math.max(1, Math.ceil(total / 10));

        paginationBar.classList.add('visible');
        if (prevPageBtn) prevPageBtn.disabled = !hasPrev;
        if (nextPageBtn) nextPageBtn.disabled = !hasNext;

        const pageContainer = document.querySelector('.js-page-numbers');
        if (pageContainer) {
            let html = '';
            for (let i = 1; i <= totalPages; i++) {
                if (i === 1 || i === totalPages || (i >= page - 1 && i <= page + 1)) {
                    html += `<span class="page-num${i === page ? ' active' : ''}" data-page="${i}">${i}</span>`;
                } else if (i === 2 && page > 3) {
                    html += '<span class="page-num dots">...</span>';
                } else if (i === totalPages - 1 && page < totalPages - 2) {
                    html += '<span class="page-num dots">...</span>';
                }
            }
            pageContainer.innerHTML = html;

            pageContainer.querySelectorAll('.page-num:not(.dots)').forEach(el => {
                el.addEventListener('click', () => {
                    const p = parseInt(el.dataset.page);
                    if (p !== currentPage) loadSets(p);
                });
            });
        }

        // Desktop pagination
        if (desktopPagination) {
            desktopPagination.innerHTML = `
                <button class="pagination-nav-btn" ${!hasPrev ? 'disabled' : ''} onclick="QuizDashboard.loadSets(${page - 1})">
                    <i class="fas fa-chevron-left"></i>
                </button>
                <span class="page-info">Trang ${page} / ${totalPages}</span>
                <button class="pagination-nav-btn" ${!hasNext ? 'disabled' : ''} onclick="QuizDashboard.loadSets(${page + 1})">
                    <i class="fas fa-chevron-right"></i>
                </button>
            `;
        }
    }

    /**
     * Hide pagination
     */
    function hidePagination() {
        if (paginationBar) paginationBar.classList.remove('visible');
        if (desktopPagination) desktopPagination.innerHTML = '';
    }

    /**
     * Update desktop stats sidebar
     */
    function updateDesktopStats(stats) {
        const setEl = document.getElementById('desktop-total-sets');
        const questionEl = document.getElementById('desktop-total-questions');
        const masteredEl = document.getElementById('desktop-mastered-count');
        const dueEl = document.getElementById('desktop-due-count');

        if (setEl) setEl.textContent = stats.total_sets || '-';
        if (questionEl) questionEl.textContent = stats.total_questions || '-';
        if (masteredEl) masteredEl.textContent = stats.mastered || '-';
        if (dueEl) dueEl.textContent = stats.due || '-';
    }

    /**
     * Load set detail (mobile step navigation)
     */
    function loadSetDetail(setId) {
        showStep('detail');
        selectedSetId = setId;

        history.pushState({ setId: setId }, '', '/learn/quiz/set/' + setId);

        const url = apiSetDetailUrl.replace('/0', '/' + setId);

        fetch(url)
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    selectedSetData = data.set;
                    renderSetDetail(data.set, data.modes);
                }
            })
            .catch(err => {
                console.error('Error loading set detail:', err);
            });
    }

    /**
     * Render set detail (mobile)
     */
    function renderSetDetail(set, modes) {
        const headerInfo = stepDetail?.querySelector('.step-header-info');
        if (headerInfo) headerInfo.style.opacity = '1';

        const headerTitle = document.querySelector('.js-header-title');
        const headerCount = document.querySelector('.js-header-count');
        if (headerTitle) headerTitle.textContent = set.title;
        if (headerCount) headerCount.textContent = set.question_count;

        const content = stepDetail?.querySelector('.quiz-detail-content');
        if (content) content.style.opacity = '1';

        const els = {
            title: document.querySelector('.js-detail-title'),
            desc: document.querySelector('.js-detail-desc'),
            avatar: document.querySelector('.js-creator-avatar'),
            name: document.querySelector('.js-creator-name'),
            count: document.querySelector('.js-question-count'),
            progress: document.querySelector('.js-progress-count')
        };

        if (els.title) els.title.textContent = set.title;
        if (els.desc) els.desc.textContent = set.description || 'Không có mô tả';
        if (els.avatar) els.avatar.textContent = (set.creator_name || 'U').charAt(0).toUpperCase();
        if (els.name) els.name.textContent = set.creator_name || 'Unknown';
        if (els.count) els.count.textContent = set.question_count;
        if (els.progress) els.progress.textContent = '0/' + set.question_count;

        // Cover
        const cover = document.querySelector('.js-detail-cover');
        if (cover && set.cover_image) {
            cover.style.backgroundImage = 'url(/static/' + set.cover_image + ')';
            cover.innerHTML = '';
        }

        // Question list placeholder
        const questionList = document.querySelector('.js-question-list');
        if (questionList) {
            questionList.innerHTML = '<p class="text-center text-slate-400 py-4">Xem câu hỏi sau khi chọn chế độ học</p>';
        }
    }

    /**
     * Open desktop detail panel
     */
    function openDetailPanel(setId) {
        selectedSetId = setId;

        if (setDetailPanel) setDetailPanel.classList.add('open');
        if (panelOverlay) panelOverlay.classList.add('visible');

        const url = apiSetDetailUrl.replace('/0', '/' + setId);

        fetch(url)
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    selectedSetData = data.set;
                    renderDesktopDetail(data.set, data.modes);
                }
            });
    }

    /**
     * Close desktop detail panel
     */
    function closeDetailPanel() {
        if (setDetailPanel) setDetailPanel.classList.remove('open');
        if (panelOverlay) panelOverlay.classList.remove('visible');
        selectedSetId = null;
        selectedMode = null;
    }

    /**
     * Render detail in desktop panel
     */
    function renderDesktopDetail(set, modes) {
        const els = {
            title: document.querySelector('.js-desktop-detail-title'),
            desc: document.querySelector('.js-desktop-detail-desc'),
            avatar: document.querySelector('.js-desktop-creator-avatar'),
            name: document.querySelector('.js-desktop-creator-name'),
            count: document.querySelector('.js-desktop-question-count'),
            progress: document.querySelector('.js-desktop-progress-count')
        };

        if (els.title) els.title.textContent = set.title;
        if (els.desc) els.desc.textContent = set.description || 'Không có mô tả';
        if (els.avatar) els.avatar.textContent = (set.creator_name || 'U').charAt(0).toUpperCase();
        if (els.name) els.name.textContent = set.creator_name || 'Unknown';
        if (els.count) els.count.textContent = set.question_count;
        if (els.progress) els.progress.textContent = '0/' + set.question_count;

        // Cover
        const cover = document.querySelector('.js-desktop-detail-cover');
        if (cover && set.cover_image) {
            cover.style.backgroundImage = 'url(/static/' + set.cover_image + ')';
            cover.innerHTML = '';
        }

        // Render modes
        const modesContainer = document.querySelector('.js-desktop-modes-container');
        if (modesContainer && modes) {
            renderDesktopModes(modes, modesContainer);
        }
    }

    /**
     * Render modes in desktop panel
     */
    function renderDesktopModes(modes, container) {
        const icons = {
            'new_only': { icon: 'fa-star', color: 'yellow' },
            'due_only': { icon: 'fa-sync', color: 'green' },
            'hard_only': { icon: 'fa-times-circle', color: 'red' }
        };

        let html = '';
        modes.forEach(mode => {
            const iconData = icons[mode.id] || { icon: 'fa-question', color: 'blue' };
            const isDisabled = mode.count === 0;
            const disabledStyle = isDisabled ? 'opacity: 0.4; filter: grayscale(100%); pointer-events: none;' : '';

            html += `
                <div class="quiz-mode-card" data-mode-id="${mode.id}" style="${disabledStyle}">
                    <div class="quiz-mode-icon ${iconData.color}"><i class="fas ${iconData.icon}"></i></div>
                    <div class="quiz-mode-info">
                        <div class="quiz-mode-name">${mode.name}</div>
                        <div class="quiz-mode-desc">${mode.count} câu hỏi</div>
                    </div>
                    <div class="quiz-mode-count">${mode.count}</div>
                </div>`;
        });

        container.innerHTML = html;

        // Bind mode selection
        container.querySelectorAll('.quiz-mode-card').forEach(card => {
            card.addEventListener('click', () => {
                const count = parseInt(card.querySelector('.quiz-mode-count')?.textContent || '0');
                if (count === 0) return;

                container.querySelectorAll('.quiz-mode-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                selectedMode = card.dataset.modeId;

                const startBtn = document.querySelector('.js-desktop-start-session');
                if (startBtn) startBtn.disabled = false;
            });
        });
    }

    /**
     * Load modes (mobile)
     */
    function loadModes() {
        if (!modesContainer) return;
        modesContainer.innerHTML = '<div class="quiz-loading"><i class="fas fa-spinner fa-spin"></i></div>';

        const url = apiSetDetailUrl.replace('/0', '/' + selectedSetId);

        fetch(url)
            .then(r => r.json())
            .then(data => {
                if (data.success && data.modes) {
                    renderModes(data.modes);
                }
            });
    }

    /**
     * Render modes (mobile)
     */
    function renderModes(modes) {
        const icons = {
            'new_only': { icon: 'fa-star', color: 'yellow' },
            'due_only': { icon: 'fa-sync', color: 'green' },
            'hard_only': { icon: 'fa-times-circle', color: 'red' }
        };

        let html = '';
        modes.forEach(mode => {
            const iconData = icons[mode.id] || { icon: 'fa-question', color: 'blue' };
            const isDisabled = mode.count === 0;
            const disabledStyle = isDisabled ? 'opacity: 0.4; filter: grayscale(100%); pointer-events: none;' : '';
            const disabledClass = isDisabled ? ' disabled' : '';

            html += `
                <div class="quiz-mode-card${disabledClass}" data-mode-id="${mode.id}" style="${disabledStyle}">
                    <div class="quiz-mode-icon ${iconData.color}"><i class="fas ${iconData.icon}"></i></div>
                    <div class="quiz-mode-info">
                        <div class="quiz-mode-name">${mode.name}</div>
                        <div class="quiz-mode-desc">${mode.count} câu hỏi</div>
                    </div>
                    <div class="quiz-mode-count">${mode.count}</div>
                </div>`;
        });

        modesContainer.innerHTML = html;

        // Bind click
        document.querySelectorAll('.js-modes-container .quiz-mode-card').forEach(card => {
            card.addEventListener('click', () => {
                const count = parseInt(card.querySelector('.quiz-mode-count')?.textContent || '0');
                if (count === 0) return;

                document.querySelectorAll('.js-modes-container .quiz-mode-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                selectedMode = card.dataset.modeId;

                if (startSessionBtn) startSessionBtn.disabled = false;
            });
        });
    }

    /**
     * Start session
     */
    function startSession(source) {
        if (!selectedSetId || !selectedMode) return;

        const prefix = source === 'desktop' ? 'desktop-' : '';
        const limitToggle = document.getElementById(prefix + 'limit-toggle');
        const sessionSizeSelect = document.getElementById(prefix + 'session-size-select');
        const turnToggle = document.getElementById('turn-toggle');
        const turnSizeSelect = document.getElementById('turn-size-select');

        let sessionSize = 999999;
        let turnSize = 1;

        if (limitToggle && limitToggle.checked && sessionSizeSelect) {
            sessionSize = parseInt(sessionSizeSelect.value) || 10;
        }
        if (turnToggle && turnToggle.checked && turnSizeSelect) {
            turnSize = parseInt(turnSizeSelect.value) || 1;
        }

        const url = startSessionUrl
            .replace('/0/', '/' + selectedSetId + '/')
            .replace('/MODE', '/' + selectedMode) + '?session_size=' + sessionSize + '&turn_size=' + turnSize;

        // Clear stale state
        sessionStorage.removeItem('quiz_session_single_state');
        sessionStorage.removeItem('quiz_session_batch_state');

        window.location.href = url;
    }

    /**
     * Handle toggle change events
     */
    function handleToggleChange(e) {
        if (e.target && (e.target.id === 'limit-toggle' || e.target.id === 'desktop-limit-toggle')) {
            const prefix = e.target.id === 'desktop-limit-toggle' ? 'desktop-' : '';
            const options = document.getElementById(prefix + 'limit-options');
            const statusText = document.getElementById(prefix + 'limit-status-text');

            if (e.target.checked) {
                options?.classList.remove('hidden');
                statusText?.classList.add('hidden');
            } else {
                options?.classList.add('hidden');
                statusText?.classList.remove('hidden');
            }
        }
        if (e.target && e.target.id === 'turn-toggle') {
            const turnOptions = document.getElementById('turn-options');
            const turnStatusText = document.getElementById('turn-status-text');
            if (e.target.checked) {
                turnOptions?.classList.remove('hidden');
                turnStatusText?.classList.add('hidden');
            } else {
                turnOptions?.classList.add('hidden');
                turnStatusText?.classList.remove('hidden');
            }
        }
    }

    /**
     * Initialize toggle states
     */
    function initToggleState() {
        // Mobile
        const limitToggle = document.getElementById('limit-toggle');
        const limitOptions = document.getElementById('limit-options');
        const limitStatusText = document.getElementById('limit-status-text');
        const sessionSizeSelect = document.getElementById('session-size-select');

        if (limitToggle) {
            if (savedBatchSize && savedBatchSize < 999999) {
                limitToggle.checked = true;
                if (sessionSizeSelect) sessionSizeSelect.value = savedBatchSize;
                limitOptions?.classList.remove('hidden');
                limitStatusText?.classList.add('hidden');
            } else {
                limitToggle.checked = false;
                limitOptions?.classList.add('hidden');
                limitStatusText?.classList.remove('hidden');
            }
        }

        const turnToggle = document.getElementById('turn-toggle');
        const turnOptions = document.getElementById('turn-options');
        const turnStatusText = document.getElementById('turn-status-text');
        if (turnToggle) {
            turnToggle.checked = false;
            turnOptions?.classList.add('hidden');
            turnStatusText?.classList.remove('hidden');
        }

        // Desktop toggles
        const desktopLimitToggle = document.getElementById('desktop-limit-toggle');
        const desktopLimitOptions = document.getElementById('desktop-limit-options');
        const desktopLimitStatusText = document.getElementById('desktop-limit-status-text');

        if (desktopLimitToggle) {
            desktopLimitToggle.checked = false;
            desktopLimitOptions?.classList.add('hidden');
            desktopLimitStatusText?.classList.remove('hidden');
        }
    }

    /**
     * Handle browser back/forward
     */
    function handlePopState(event) {
        if (window.location.pathname.includes('/set/')) {
            const parts = window.location.pathname.split('/');
            const setId = parts[parts.length - 1];
            if (setId && !isNaN(setId)) {
                loadSetDetail(setId);
            }
        } else {
            showStep('browser');
            closeDetailPanel();
        }
    }

    // Expose public API
    window.QuizDashboard = {
        init: init,
        loadSets: loadSets,
        loadSetDetail: loadSetDetail,
        openDetailPanel: openDetailPanel,
        closeDetailPanel: closeDetailPanel
    };
})();
