// Filter modes based on container capabilities
(function () {

    const capabilities = window.ComponentConfig.capabilities || [];
    const modeCards = document.querySelectorAll('.mode-select-card[data-capability]');

    modeCards.forEach(card => {
        const requiredCapability = card.getAttribute('data-capability');
        if (requiredCapability && !capabilities.includes(requiredCapability)) {
            card.style.display = 'none';
        }
    });

})();

document.addEventListener('DOMContentLoaded', function () {

    (function () {

        // State

        let currentCategory = 'my';
        let currentActiveStep = 'browser';

        let currentSearch = '';

        let currentPage = 1;

        let selectedSetId = null;

        let selectedSetData = null;

        let selectedMode = null;

        let currentStatsPage = 1;



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

                // Reset all

                document.querySelectorAll('.js-mode-select').forEach(c => c.classList.remove('selected'));

                // Select current

                this.classList.add('selected');

                selectedMode = this.dataset.mode;



                // Enable continue button

                if (continueBtn) {

                    continueBtn.disabled = false;

                    continueBtn.classList.add('active'); // If using specific active style

                }

            });

        });



        // Init

        loadSets();
        loadDashboardStats();
        loadActiveSessions();



        // Category tabs

        document.querySelectorAll('.vocab-tab').forEach(function (tab) {

            tab.addEventListener('click', function () {

                document.querySelectorAll('.vocab-tab').forEach(function (t) { t.classList.remove('active'); });

                tab.classList.add('active');

                currentCategory = tab.dataset.category;

                loadSets();

            });

        });



        // Check for active set ID and step from server template

        const activeSetId = window.ComponentConfig.activeSetId || null;

        const activeStep = window.ComponentConfig.activeStep || "browser";

        console.log("Deep Link Check:", activeSetId, "Step:", activeStep);



        if (activeSetId) {

            // Show immediate loading state if possible, or keep hidden until loaded

            // But better to show *something*.

            setsGrids.forEach(grid => {
                grid.innerHTML = '<div class="vocab-loading" style="grid-column: 1/-1;"><i class="fas fa-spinner fa-spin"></i><p>Đang chuẩn bị...</p></div>';
            });



            // Load set detail data first

            loadSetDetail(activeSetId, false)

                .then(function () {

                    // Wait for data to load then show appropriate step

                    if (activeStep && activeStep !== 'browser' && activeStep !== 'detail') {

                        showStep(activeStep);

                        updateModeVisibility();



                        // Load mode data if needed

                        if (activeStep === 'flashcard-options') {

                            loadFlashcardOptions(activeSetId);

                        } else if (activeStep === 'mcq-options') {

                            loadMcqOptions(activeSetId);

                        }

                    } else if (activeStep === 'detail') {

                        // Already handled by loadSetDetail's showStep('detail') but ensure consistency

                        showStep('detail');

                    }

                })

                .catch(function (err) {

                    console.error("Init failed:", err);

                    // Fallback to browser or show error

                    alert("Không thể tải dữ liệu bộ thẻ. Vui lòng thử lại.");

                    showStep('browser');

                    loadSets();

                });

        } else {
            console.log("No activeSetId, loading browser default");
            loadSets();
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

                // Check for step suffix

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
                    // Just set ID - show detail
                    const setId = lastPart;
                    if (selectedSetId != setId) loadSetDetail(setId, false);
                    showStep('detail');
                }
            } else {
                showStep('browser');
            }
        });




        // Handle Window Resize
        window.addEventListener('resize', function () {
            handleResponsiveView(currentActiveStep);
        });

        function handleResponsiveView(step) {
            const desktopView = document.querySelector('.vocab-desktop-view');
            const mobileBrowser = document.getElementById('step-browser');
            const isDesktop = window.innerWidth >= 1024;

            // Desktop View Containers
            const desktopDashboard = document.getElementById('desktop-dashboard-view');
            const desktopDetail = document.getElementById('desktop-detail-view');

            if (step === 'browser') {
                if (isDesktop && desktopView) {
                    // Desktop: Show Main Dashboard View
                    if (mobileBrowser) {
                        mobileBrowser.classList.remove('active');
                        mobileBrowser.style.display = 'none';
                    }
                    desktopView.style.display = 'block';
                    desktopView.classList.add('active');

                    // View Switching
                    if (desktopDashboard) desktopDashboard.style.display = 'block';
                    if (desktopDetail) desktopDetail.style.display = 'none';

                } else {
                    // Mobile: Show Mobile Browser
                    if (desktopView) {
                        desktopView.style.display = 'none';
                        desktopView.classList.remove('active');
                    }
                    if (mobileBrowser) {
                        mobileBrowser.classList.add('active');
                        mobileBrowser.style.display = 'flex';
                    }
                }
            } else if (step === 'detail') {
                if (isDesktop && desktopView) {
                    // Desktop: Show Detail View
                    if (mobileBrowser) {
                        mobileBrowser.classList.remove('active');
                        mobileBrowser.style.display = 'none';
                    }
                    desktopView.style.display = 'block';
                    desktopView.classList.add('active');

                    // View Switching
                    if (desktopDashboard) desktopDashboard.style.display = 'none';
                    if (desktopDetail) desktopDetail.style.display = 'block';
                } else {
                    // Mobile: Show Mobile Detail Step
                    if (desktopView) {
                        desktopView.style.display = 'none';
                        desktopView.classList.remove('active');
                    }
                    const targetStep = document.getElementById('step-' + step) || document.getElementById(step);
                    if (targetStep) {
                        targetStep.style.display = 'flex';
                    }
                }
            } else {
                // Other steps (Modes, Options, etc.) -> Standard Logic
                // Always hide desktop view (unless we want those steps embedded in desktop too? For now standard full modal-like steps)
                if (desktopView) {
                    desktopView.style.display = 'none';
                    desktopView.classList.remove('active');
                }

                // Ensure specific step is shown
                const targetStep = document.getElementById('step-' + step) || document.getElementById(step);
                if (targetStep) {
                    targetStep.style.display = isDesktop ? 'block' : 'flex';
                }
            }
        }

        function showStep(step) {
            console.log("Showing Step:", step);
            currentActiveStep = step;

            // Reset all steps active state first (helper)
            document.querySelectorAll('.vocab-step').forEach(s => {
                // specific logic handled by handleResponsiveView, but good to clean up others
                if (s.id !== 'step-browser' && s.id !== ('step-' + step) && s.id !== step) {
                    s.classList.remove('active');
                    s.style.display = 'none';
                }
            });

            const targetStep = document.getElementById('step-' + step) || document.getElementById(step);
            if (targetStep) targetStep.classList.add('active');

            // Apply Responsive Logic
            handleResponsiveView(step);

            // Scroll to top
            window.scrollTo(0, 0);

            // Hide pagination if not browser
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
                        hidePagination();

                    });

                });

            // Desktop Back Button
            document.querySelectorAll('.js-back-to-dashboard-desktop').forEach(btn => {
                btn.addEventListener('click', function (e) {
                    e.preventDefault();
                    showStep('browser');
                    // Update URL to dashboard
                    history.pushState({ step: 'browser' }, '', '/learn/vocabulary/dashboard');
                });
            });

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

                // Try to get title from session data if we can
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



            // [NEW] Check active session within Set Detail
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

                setsGrids.forEach(grid => {
                    grid.innerHTML = html;
                });



                // Bind click

                document.querySelectorAll('.vocab-set-card').forEach(function (card) {

                    card.addEventListener('click', function () {

                        selectedSetId = card.dataset.setId;

                        loadSetDetail(selectedSetId, true); // true = push state

                    });

                });

            }



            function updatePagination(page, hasPrev, hasNext, total) {

                if (paginationBars.length === 0) return;



                var totalPages = Math.max(1, Math.ceil(total / 10)); // 10 per page, at least 1



                paginationBars.forEach(bar => bar.classList.add('visible'));

                prevPageBtns.forEach(btn => btn.disabled = !hasPrev);

                nextPageBtns.forEach(btn => btn.disabled = !hasNext);



                // Render page numbers

                var pageContainer = document.querySelector('.js-vocab-page-numbers');

                if (pageContainer) {

                    var html = '';



                    for (var i = 1; i <= totalPages; i++) {

                        if (i === 1 || i === totalPages ||

                            (i >= page - 1 && i <= page + 1)) {

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



            // Pagination button events

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



            function loadSetDetail(setId, pushState = true) {
                console.log("loadSetDetail called for id:", setId);
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

                            // [NEW] Check for active session in this set
                            checkSetActiveSession(setId);

                            // [NEW] Init settings modal for this set immediately
                            fetch('/learn/vocabulary/api/flashcard-modes/' + setId)
                                .then(r => r.json())
                                .then(modeData => {
                                    if (modeData.success) {
                                        setupSettingsModal(setId, modeData);
                                    }
                                })
                                .catch(e => console.warn("Failed to load settings:", e));

                            return data.set;

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



            // Load More Button - replaced by pagination

            const loadMoreBtn = document.querySelector('.js-load-more-words');

            if (loadMoreBtn) loadMoreBtn.style.display = 'none';



            function fetchCourseStatsPage(page) {

                if (!selectedSetId) return;



                // Find list container to show loading state

                const listContainer = document.querySelector('.js-word-list');

                if (listContainer) {

                    listContainer.innerHTML = '<div class="py-12 flex justify-center"><i class="fas fa-spinner fa-spin text-2xl text-slate-300"></i></div>';

                }



                fetch('/learn/vocabulary/api/set/' + selectedSetId + '?page=' + page)

                    .then(r => r.json())

                    .then(data => {

                        if (data.success && data.course_stats) {

                            // Pass pagination_html if available

                            renderSetDetail(selectedSetData, data.course_stats, false, data.pagination_html);

                            // Scroll to top of list

                            const overview = document.getElementById('course-overview-container');

                            if (overview) overview.scrollIntoView({ behavior: 'smooth', block: 'start' });

                        } else {

                            console.error("API Error:", data.message);

                            alert("Lỗi server: " + (data.message || "Không thể tải dữ liệu."));

                            // Restore/Clear spinner

                            const listContainer = document.querySelector('.js-word-list');

                            if (listContainer) listContainer.innerHTML = '<div class="text-center text-red-500 py-4">Thử lại sau.</div>';

                        }

                    })

                    .catch(err => {

                        console.error("Pagination error:", err);

                        alert('Lỗi kết nối.');

                    });

            }



            function renderSetDetail(s, stats, append = false, paginationHtml = '') {

                // Cover & Info only update on fresh load

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



                    // Info

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



                    // Update progress stat as count

                    const learnedCount = stats && stats.learned_count !== undefined ? stats.learned_count : 0;

                    const totalCount = stats && stats.total_count !== undefined ? stats.total_count : s.card_count;

                    if (els.progressCount) els.progressCount.textContent = learnedCount + '/' + totalCount;



                    // Update header info (for sticky header)

                    const headerTitle = document.querySelector('.js-header-title');

                    const headerCardCount = document.querySelector('.js-header-card-count');

                    const headerProgressPercent = document.querySelector('.js-header-progress-percent');

                    if (headerTitle) headerTitle.textContent = s.title;

                    if (headerCardCount) headerCardCount.textContent = s.card_count;

                    const progressPercent = totalCount > 0 ? Math.round((learnedCount / totalCount) * 100) : 0;

                    if (headerProgressPercent) headerProgressPercent.textContent = progressPercent + '%';



                    // Show content after data is loaded

                    const detailContent = document.querySelector('.vocab-detail-content');

                    if (detailContent) {

                        detailContent.style.opacity = '1';
                    }

                    // Update Edit Button
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



                // Hide Course Overview Stats section completely

                const overviewContainer = document.getElementById('course-overview-container');

                if (overviewContainer) {

                    overviewContainer.style.display = 'none';

                }



                // Scroll handler for sticky header info

                const vocabScroll = document.querySelector('#step-detail .vocab-scroll');

                const headerInfo = document.querySelector('.step-header-info');

                const detailTitle = document.querySelector('.vocab-detail-title');

                if (vocabScroll && headerInfo && detailTitle) {

                    vocabScroll.addEventListener('scroll', function () {

                        // Show header when title is scrolled out of view

                        const titleRect = detailTitle.getBoundingClientRect();

                        const headerHeight = document.querySelector('.step-header-left')?.offsetHeight || 60;



                        if (titleRect.bottom < headerHeight) {

                            headerInfo.style.opacity = '1';

                        } else {

                            headerInfo.style.opacity = '0';

                        }

                    });

                }



                // Word List - sort and render if stats available

                if (stats && stats.items) {

                    const listContainer = document.querySelector('.js-word-list');

                    if (listContainer) {

                        let listHtml = '';



                        if (stats.items && stats.items.length > 0) {

                            // Sort: Words needing review (low %) first, new words last

                            const sortedItems = [...stats.items].sort((a, b) => {

                                // New items go to end

                                if (a.status === 'new' && b.status !== 'new') return 1;

                                if (b.status === 'new' && a.status !== 'new') return -1;

                                // Both new or both not new: sort by mastery (ascending - low % first)

                                return a.mastery - b.mastery;

                            });



                            sortedItems.forEach(item => {

                                let barColor = 'bg-red-500';

                                let progressGradient = 'linear-gradient(135deg, #ef4444, #dc2626)';

                                if (item.mastery >= 80) {

                                    barColor = 'bg-green-500';

                                    progressGradient = 'linear-gradient(135deg, #10b981, #059669)';

                                } else if (item.mastery >= 50) {

                                    barColor = 'bg-yellow-500';

                                    progressGradient = 'linear-gradient(135deg, #f59e0b, #d97706)';

                                }



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



                        listContainer.innerHTML = listHtml; // Always replace

                        bindStatsModalEvents();

                    }



                    // Pagination Controls - Target fixed pagination bar

                    const detailPaginationBar = document.querySelector('#detail-pagination-bar');

                    if (detailPaginationBar && paginationHtml) {

                        // Inject pagination HTML into fixed bar

                        detailPaginationBar.innerHTML = paginationHtml;

                        detailPaginationBar.classList.add('visible');



                        // Re-bind events for the new HTML links

                        detailPaginationBar.querySelectorAll('a').forEach(link => {

                            link.addEventListener('click', function (e) {

                                e.preventDefault();

                                const url = new URL(this.href);

                                const page = url.searchParams.get('page');

                                if (page) fetchCourseStatsPage(page);

                            });

                        });

                    } else if (detailPaginationBar && stats.pagination && stats.pagination.pages <= 1) {

                        // Hide if only 1 page

                        detailPaginationBar.classList.remove('visible');

                    }



                } else {
                    // Stats null or no items -> Show empty state / error
                    const listContainer = document.querySelector('.js-word-list');
                    if (listContainer) {
                        listContainer.innerHTML = '<div class="py-12 text-center flex flex-col items-center justify-center text-slate-400"><i class="fas fa-search text-4xl mb-3 text-slate-200"></i><span class="text-sm">Không tìm thấy từ vựng nào.</span></div>';
                    }

                    if (overviewContainer) {
                        overviewContainer.style.display = 'none';
                    }
                }

            }



            function fetchCourseStatsPage(page) {

                if (!selectedSetId) return;



                // Find list container to show loading state

                const listContainer = document.querySelector('.js-word-list');

                if (listContainer) {

                    listContainer.innerHTML = '<div class="py-12 flex justify-center"><i class="fas fa-spinner fa-spin text-2xl text-slate-300"></i></div>';

                }



                const url = '/learn/vocabulary/api/set/' + selectedSetId + '?page=' + page + '&_t=' + new Date().getTime();



                fetch(url)

                    .then(r => r.json())

                    .then(data => {

                        if (data.success && data.course_stats) {

                            renderSetDetail(selectedSetData, data.course_stats, false, data.pagination_html); // Pass pagination HTML

                            // Scroll to top of list

                            const overview = document.getElementById('course-overview-container');

                            if (overview) overview.scrollIntoView({ behavior: 'smooth', block: 'start' });

                        }

                    })

                    .catch(err => {

                        console.error("Pagination error:", err);

                        alert('Lỗi tải trang.');

                    });

            }



            // Start learning button

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



                console.log("Updating visibility for set:", selectedSetData);



                // If no capabilities defined or empty, show flashcard and mcq as default or show all?

                // Let's safe default: SHOW ALL if no capabilities found to avoid "blank" screen

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

                    // Fallback: if logic hides everything, show everything to be safe

                    console.warn("All modes hidden by capabilities, forcing show.");

                    document.querySelectorAll('.js-mode-select').forEach(el => el.style.display = 'flex');

                }

            }



            // Continue button handler

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

                    // Redirect to MCQ setup page for options

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



                // Update set name display - fetch if not available

                var setNameEl = document.querySelector('.js-selected-set-name-fc');

                if (setNameEl) {

                    if (selectedSetData && selectedSetData.title) {

                        setNameEl.textContent = selectedSetData.title;

                    } else {

                        setNameEl.textContent = 'Đang tải...';

                        // Fetch set info for display

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

                            // [NEW] Settings Modal Logic
                            setupSettingsModal(setId, data);

                        } else {
                            container.innerHTML = '<div class="vocab-empty"><i class="fas fa-exclamation-triangle"></i><p>Lỗi tải chế độ học</p></div>';
                        }
                    })
                    .catch(function (err) {
                        container.innerHTML = '<div class="vocab-empty"><i class="fas fa-exclamation-triangle"></i><p>Lỗi kết nối</p></div>';
                    });
            }

            // [NEW] Settings Modal Functions
            // [NEW] Settings Modal Functions (Redesigned)
            // Global event delegation for opening settings
            document.addEventListener('click', function (e) {
                const btn = e.target.closest('.js-open-flashcard-settings');
                if (btn) {
                    e.preventDefault();
                    if (!selectedSetId) {
                        console.warn("No set selected");
                        return;
                    }

                    const modal = document.getElementById('flashcard-settings-modal');
                    if (modal) {
                        modal.style.display = 'flex';
                        // Fetch latest settings if needed, or rely on cached data
                        // Ideally we refresh data here if possible
                    }
                }
            });

            function setupSettingsModal(setId, data) {
                const modal = document.getElementById('flashcard-settings-modal');
                const closeBtns = document.querySelectorAll('.js-close-settings-modal');
                const overlay = document.querySelector('.vocab-modal-overlay.js-close-settings-modal');
                const saveBtn = document.querySelector('.js-save-settings');

                // Main Controls
                const modeSelect = document.getElementById('setting-mode-select');
                const autoSaveToggle = document.getElementById('setting-auto-save');

                // Sections
                const modeSections = document.querySelectorAll('.mode-section');
                const viewStates = document.querySelectorAll('.js-state-view');
                const editStates = document.querySelectorAll('.js-state-edit');

                // Flashcard Elements
                const fcFixedBtnButtons = document.querySelectorAll('.js-fixed-btn-count');
                const fcFixedBtnInput = document.getElementById('setting-fc-button-count');
                const fcAutoplayToggle = document.getElementById('setting-fc-autoplay');
                const fcShowImageToggle = document.getElementById('setting-fc-show-image');
                const fcShowStatsToggle = document.getElementById('setting-fc-show-stats');

                // Flashcard Status Labels
                const labelFcBtnCount = document.querySelector('.js-last-btn-count');
                const labelFcAutoplay = document.querySelector('.js-last-autoplay');
                const labelFcShowImage = document.querySelector('.js-last-show-image');
                const labelFcShowStats = document.querySelector('.js-last-show-stats');

                if (!modal) return;

                // 1. Initial State Initialization
                let settings = data.settings || {};
                let isAuto = settings.auto_save !== false;
                let lastMode = settings.last_mode || 'flashcard';
                let fcSettings = settings.flashcard || {};

                // [DEBUG] Log settings
                console.log('[MODAL DEBUG] data.settings:', data.settings);
                console.log('[MODAL DEBUG] fcSettings:', fcSettings);
                console.log('[MODAL DEBUG] isAuto:', isAuto);

                // 2. Set UI Initial State
                if (modeSelect) modeSelect.value = lastMode;
                if (autoSaveToggle) autoSaveToggle.checked = isAuto;

                // Sync Sections
                const syncUI = () => {
                    // Show correct mode section
                    modeSections.forEach(s => s.id === 'mode-settings-' + modeSelect.value ? s.classList.remove('hidden') : s.classList.add('hidden'));

                    // Toggle between View (Auto) and Edit (Fixed)
                    const currentIsAuto = autoSaveToggle.checked;
                    viewStates.forEach(v => currentIsAuto ? v.classList.remove('hidden') : v.classList.add('hidden'));
                    editStates.forEach(e => currentIsAuto ? e.classList.add('hidden') : e.classList.remove('hidden'));
                };

                // 3. Initialize Flashcard Data
                const initFlashcardData = () => {
                    // Labels (View State)
                    if (labelFcBtnCount) labelFcBtnCount.textContent = (fcSettings.button_count || data.user_button_count || 4) + ' nút';
                    if (labelFcAutoplay) labelFcAutoplay.textContent = (fcSettings.autoplay !== false ? 'BẬT' : 'TẮT');
                    if (labelFcShowImage) labelFcShowImage.textContent = (fcSettings.show_image !== false ? 'HIỆN' : 'ẨN');
                    if (labelFcShowStats) labelFcShowStats.textContent = (fcSettings.show_stats !== false ? 'HIỆN' : 'ẨN');

                    // Inputs (Edit State)
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

                // 4. Events
                if (modeSelect) modeSelect.onchange = syncUI;
                if (autoSaveToggle) autoSaveToggle.onchange = syncUI;

                const closeModal = () => modal.style.display = 'none';
                closeBtns.forEach(btn => btn.onclick = closeModal);
                if (overlay) overlay.onclick = closeModal;

                // 5. Save Logic
                if (saveBtn) {
                    saveBtn.onclick = function () {
                        const currentAuto = autoSaveToggle.checked;
                        const activeMode = modeSelect.value;

                        // [DEBUG] Log toggle states before creating payload
                        console.log('[SAVE DEBUG] fcAutoplayToggle element:', fcAutoplayToggle);
                        console.log('[SAVE DEBUG] fcAutoplayToggle.checked:', fcAutoplayToggle ? fcAutoplayToggle.checked : 'N/A');
                        console.log('[SAVE DEBUG] fcShowImageToggle.checked:', fcShowImageToggle ? fcShowImageToggle.checked : 'N/A');
                        console.log('[SAVE DEBUG] fcShowStatsToggle.checked:', fcShowStatsToggle ? fcShowStatsToggle.checked : 'N/A');

                        const payload = {
                            ...settings,
                            auto_save: currentAuto,
                            last_mode: activeMode,
                            flashcard: {
                                // Always include all flashcard settings
                                autoplay: fcAutoplayToggle ? fcAutoplayToggle.checked : true,
                                show_image: fcShowImageToggle ? fcShowImageToggle.checked : true,
                                show_stats: fcShowStatsToggle ? fcShowStatsToggle.checked : true,
                                // Always include button_count - from input if Fixed mode, else preserve existing/default
                                button_count: (!currentAuto && fcFixedBtnInput)
                                    ? parseInt(fcFixedBtnInput.value)
                                    : (fcSettings.button_count || data.user_button_count || 4)
                            }
                        };

                        console.log('[SAVE DEBUG] Payload to send:', payload);

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
                        // Deselect all
                        container.querySelectorAll('.js-flashcard-mode-select').forEach(function (c) {
                            c.classList.remove('selected');
                        });
                        // Select this one
                        card.classList.add('selected');
                        selectedFlashcardMode = card.dataset.modeId;

                        // Enable continue button
                        if (continueBtn) continueBtn.disabled = false;
                    });
                });

                // Rating button visual logic
                // Rating inputs are now in the bottom bar, query from the whole step container
                var stepContainer = document.getElementById('step-flashcard-options');
                var ratingInputs = stepContainer ? stepContainer.querySelectorAll('input[name="rating_levels"]') : [];

                // [NEW] Helper to visual update
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

                // [DEBUG] Log the values for debugging
                console.log('[SETTINGS DEBUG] userButtonCount from API:', userButtonCount);
                console.log('[SETTINGS DEBUG] ratingInputs count:', ratingInputs.length);

                // [FIX] Apply persisted setting or default to 4
                var selectedButtonCount = userButtonCount || 4;
                console.log('[SETTINGS DEBUG] selectedButtonCount to apply:', selectedButtonCount);

                ratingInputs.forEach(function (r) {
                    if (parseInt(r.value) === parseInt(selectedButtonCount)) {
                        r.checked = true;
                        console.log('[SETTINGS DEBUG] Setting checked for value:', r.value);
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

                        // Redirect to flashcard session with rating level

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

                        // Execute scripts from injected HTML

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

                    if (card.classList.contains('opacity-50')) return; // Check if disabled



                    card.addEventListener('click', function () {

                        // Deselect all

                        mcqOptionsContainer.querySelectorAll('.quiz-mode-item').forEach(function (c) {

                            c.classList.remove('selected', 'border-indigo-500', 'bg-indigo-50');

                            c.classList.add('border-gray-200', 'bg-white');

                        });

                        // Select this one

                        card.classList.remove('border-gray-200', 'bg-white');

                        card.classList.add('selected', 'border-indigo-500', 'bg-indigo-50');



                        selectedQuizMode = card.dataset.modeId;

                        // Enable continue button

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



            // --- Stats Modal Functions ---

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

            const statsContainer = document.getElementById('item-stats-container');

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

            // Global Helper for Item Stats Modal (Ajax Content)

            window.showLogDetails = function (btn, index) {

                // Reset active state

                const container = btn.closest('.history-scroll');

                if (container) {

                    container.querySelectorAll('.history-btn').forEach(b => {

                        b.style.borderColor = 'transparent';

                        b.style.transform = 'scale(1)';

                        b.style.boxShadow = 'none';

                    });

                }



                // Set active

                btn.style.borderColor = '#6366f1';

                btn.style.transform = 'scale(1.1)';

                btn.style.boxShadow = '0 4px 6px -1px rgba(99, 102, 241, 0.3)';



                // Update Data using IDs from the partial

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



                // Duration not strictly shown but logic matches

                const durEl = document.getElementById('detail-duration'); // If exists

                if (durEl) durEl.textContent = btn.dataset.duration;



                // Show panel

                const panel = document.getElementById('log-detail-panel');

                if (panel) {

                    panel.style.display = 'block';

                    panel.style.animation = 'none';

                    panel.offsetHeight; /* trigger reflow */

                    panel.style.animation = 'fadeIn 0.3s ease';

                }

            };



        })();

});

// Edit Set Modal Handler - Enhanced UX
document.addEventListener('DOMContentLoaded', function () {
    const editBtn = document.querySelector('.step-edit-btn');
    const modal = document.getElementById('editSetModal');
    const modalContent = document.getElementById('editSetModalContent');

    if (editBtn && modal) {
        editBtn.addEventListener('click', function (e) {
            e.preventDefault();
            const editUrl = this.href;
            const loadUrl = editUrl + '?is_modal=true';

            // Show modal with smooth animation
            modal.classList.add('active');

            // HIDE all floating buttons to prevent overlap
            document.querySelectorAll('.step-home-btn, .btn-save-set, [style*="position: fixed"]').forEach(el => {
                el.style.opacity = '0';
                el.style.pointerEvents = 'none';
            });

            modalContent.innerHTML = `
                <div class="edit-modal-loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Đang tải form...</p>
                </div>
            `;

            // Load content via AJAX
            fetch(loadUrl)
                .then(response => response.text())
                .then(html => {
                    modalContent.innerHTML = html;

                    // Inject CSS to ensure clean rendering
                    const styleOverride = document.createElement('style');
                    styleOverride.textContent = `
                        /* Form cleanup */
                        #editSetModalContent form {
                            max-width: 100% !important;
                            margin: 0 !important;
                            padding: 1rem !important;
                            box-shadow: none !important;
                            border: none !important;
                        }
                        
                        /* Hide only the potential double title if partially renders */
                        #editSetModalContent h2.text-2xl {
                            display: none; 
                        }

                        /* Ensure submit button is visible and styled if needed */
                        #editSetModalContent button[type="submit"] {
                            display: inline-block !important;
                            visibility: visible !important;
                            opacity: 1 !important;
                            pointer-events: auto !important;
                            width: 100%;
                            margin-top: 2rem;
                            padding: 0.75rem 1.5rem;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            border: none;
                            border-radius: 0.5rem;
                            font-size: 1rem;
                            font-weight: 600;
                            cursor: pointer;
                        }
                    `;
                    modalContent.appendChild(styleOverride);

                    // Inject "Save" button into Header
                    const modalHeader = modal.querySelector('.edit-modal-header');
                    // Remove existing if any (cleanup)
                    const existingSaveBtn = modalHeader.querySelector('.header-save-btn');
                    if (existingSaveBtn) existingSaveBtn.remove();

                    const headerSaveBtn = document.createElement('button');
                    headerSaveBtn.className = 'header-save-btn';
                    headerSaveBtn.innerHTML = '<i class="fas fa-save"></i> Lưu';
                    headerSaveBtn.style.cssText = `
                            margin-left: auto;
                            margin-right: 1rem;
                            padding: 0.5rem 1rem;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            border: none;
                            border-radius: 0.5rem;
                            font-weight: 600;
                            cursor: pointer;
                            display: flex;
                            align-items: center;
                            gap: 0.5rem;
                            font-size: 0.9rem;
                            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                        `;

                    // Insert before the close button
                    const closeBtn = modalHeader.querySelector('.edit-modal-close');
                    modalHeader.insertBefore(headerSaveBtn, closeBtn);

                    /* JS Button Removal REMOVED - Template is now clean */
                    // Handle form submission
                    const form = modalContent.querySelector('form');
                    if (form) {
                        form.action = editUrl;

                        // Link header button to form submit
                        headerSaveBtn.onclick = () => {
                            // Trigger native form validation and submit
                            if (form.reportValidity()) {
                                form.dispatchEvent(new Event('submit'));
                            }
                        };

                        form.addEventListener('submit', function (e) {
                            e.preventDefault();

                            // Show loading on header button
                            headerSaveBtn.disabled = true;
                            headerSaveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang lưu...';

                            const formData = new FormData(form);

                            fetch(form.action + '?is_modal=true', {
                                method: 'POST',
                                body: formData,
                                headers: {
                                    'X-Requested-With': 'XMLHttpRequest'
                                }
                            })
                                .then(response => response.json())
                                .then(data => {
                                    if (data.success) {
                                        // Success animation
                                        modalContent.innerHTML = `
                                        <div class="edit-modal-loading">
                                            <i class="fas fa-check-circle" style="color: #10b981; font-size: 3rem;"></i>
                                            <p style="color: #10b981; font-weight: 600; margin-top: 1rem;">${data.message}</p>
                                        </div>
                                    `;
                                        // Remove header button nicely
                                        headerSaveBtn.remove();

                                        setTimeout(() => {
                                            modal.classList.remove('active');
                                            location.reload();
                                        }, 1500);
                                    } else {
                                        alert('Lỗi: ' + (data.message || JSON.stringify(data.errors || 'Không thể lưu')));
                                        headerSaveBtn.disabled = false;
                                        headerSaveBtn.innerHTML = '<i class="fas fa-save"></i> Lưu';
                                    }
                                })
                                .catch(error => {
                                    alert('Lỗi: ' + error.message);
                                    headerSaveBtn.disabled = false;
                                    headerSaveBtn.innerHTML = '<i class="fas fa-save"></i> Lưu';
                                });
                        });
                    }
                })
                .catch(error => {
                    modalContent.innerHTML = `
                        <div class="edit-modal-loading">
                            <i class="fas fa-exclamation-circle" style="color: #ef4444;"></i>
                            <p style="color: #ef4444;">Lỗi: ${error.message}</p>
                        </div>
                    `;
                });
        });

        // Close on background click
        modal.addEventListener('click', function (e) {
            if (e.target === modal) {
                closeModal();
            }
        });

        // Close on Escape key
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && modal.classList.contains('active')) {
                closeModal();
            }
        });

        // Close modal function
        function closeModal() {
            modal.classList.remove('active');

            // Remove header save button if exists
            const saveBtn = modal.querySelector('.header-save-btn');
            if (saveBtn) saveBtn.remove();

            // Restore floating buttons
            document.querySelectorAll('.step-home-btn, .btn-save-set, [style*="position: fixed"]').forEach(el => {
                el.style.opacity = '';
                el.style.pointerEvents = '';
            });
        }

        // Update close button to use function
        document.querySelector('.edit-modal-close').onclick = closeModal;
    }
})();
});