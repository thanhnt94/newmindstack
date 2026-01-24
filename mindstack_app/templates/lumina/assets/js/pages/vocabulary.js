/**
 * Lumina UI - Vocabulary Dashboard Logic
 * Handles loading sets, pagination, search, and tab filtering.
 */

(function () {
    'use strict';

    class VocabularyDashboard {
        constructor() {
            // State
            this.state = {
                category: 'learning', // 'learning' or 'explore'
                page: 1,
                search: '',
                isLoading: false
            };

            // Debounce timer for search
            this.searchTimer = null;

            // DOM Elements
            this.elements = {
                gridMobile: document.getElementById('vocab-grid-mobile'),
                gridDesktop: document.getElementById('vocab-grid-desktop'),
                searchInputs: document.querySelectorAll('.js-vocab-search-input'),
                tabs: document.querySelectorAll('.js-vocab-tab'),
                desktopTabs: document.querySelectorAll('.js-desktop-tab'),
                pagination: document.querySelectorAll('.js-vocab-pagination')
            };
        }

        init() {
            this.bindEvents();
            this.loadSets();
            this.checkDeepLink();
        }

        checkDeepLink() {
            // Check if we need to redirect to a specific set (handled by backend mostly, but we can alert)
            if (window.ComponentConfig && window.ComponentConfig.activeSetId) {
                console.log("Active Set ID:", window.ComponentConfig.activeSetId);
                // In a full SPA, we would load the detail view here.
                // For now, let's just log it.
            }
        }

        bindEvents() {
            // 1. Search Inputs (Mobile & Desktop)
            this.elements.searchInputs.forEach(input => {
                input.addEventListener('input', (e) => {
                    // Sync values
                    this.elements.searchInputs.forEach(el => {
                        if (el !== e.target) el.value = e.target.value;
                    });

                    this.state.search = e.target.value.trim();
                    clearTimeout(this.searchTimer);
                    this.searchTimer = setTimeout(() => {
                        this.state.page = 1;
                        this.loadSets();
                    }, 300);
                });
            });

            // 2. Mobile Tabs
            this.elements.tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    this.switchCategory(tab.dataset.category);
                });
            });

            // 3. Desktop Tabs
            this.elements.desktopTabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    this.switchCategory(tab.dataset.category);
                });
            });
        }

        switchCategory(category) {
            if (this.state.category === category) return;

            this.state.category = category;
            this.state.page = 1;

            // Update UI
            this.updateTabUI();
            this.loadSets();
        }

        updateTabUI() {
            // Mobile
            this.elements.tabs.forEach(t => {
                t.classList.toggle('active', t.dataset.category === this.state.category);
            });
            // Desktop
            this.elements.desktopTabs.forEach(t => {
                t.classList.toggle('active', t.dataset.category === this.state.category);
            });
        }

        async loadSets() {
            if (this.state.isLoading) return;
            this.state.isLoading = true;

            this.renderLoading();

            try {
                const params = new URLSearchParams({
                    category: this.state.category,
                    page: this.state.page,
                    q: this.state.search
                });

                const response = await fetch(`/learn/vocabulary/api/sets?${params}`);
                const data = await response.json();

                if (data.success) {
                    this.renderSets(data.sets);
                    this.renderPagination(data);
                } else {
                    this.renderError(data.message || 'Failed to load sets');
                }
            } catch (error) {
                console.error("Load sets error:", error);
                this.renderError('Network error');
            } finally {
                this.state.isLoading = false;
            }
        }

        renderLoading() {
            const html = `
                <div class="col-span-full flex flex-col items-center justify-center py-12 text-gray-400">
                    <i class="fa-solid fa-spinner fa-spin text-3xl mb-3"></i>
                    <p>Đang tải dữ liệu...</p>
                </div>
            `;
            if (this.elements.gridMobile) this.elements.gridMobile.innerHTML = html;
            if (this.elements.gridDesktop) this.elements.gridDesktop.innerHTML = html;
        }

        renderError(msg) {
            const html = `
                <div class="col-span-full flex flex-col items-center justify-center py-12 text-red-500">
                    <i class="fa-solid fa-triangle-exclamation text-3xl mb-3"></i>
                    <p>${msg}</p>
                    <button class="mt-4 px-4 py-2 bg-gray-100 rounded-lg text-gray-700 font-medium" onclick="window.LuminaVocab.loadSets()">Thử lại</button>
                </div>
            `;
            if (this.elements.gridMobile) this.elements.gridMobile.innerHTML = html;
            if (this.elements.gridDesktop) this.elements.gridDesktop.innerHTML = html;
        }

        renderSets(sets) {
            if (!sets || sets.length === 0) {
                this.renderEmpty();
                return;
            }

            const html = sets.map(set => this.createCardHTML(set)).join('');

            if (this.elements.gridMobile) this.elements.gridMobile.innerHTML = html;
            if (this.elements.gridDesktop) this.elements.gridDesktop.innerHTML = html;
        }

        createCardHTML(set) {
            const cover = this.normalizePath(set.cover_image);
            const count = set.card_count || 0;
            const title = set.title || 'Untitled';
            const author = set.creator_name || 'Unknown';

            // Cover visualization
            let coverHTML = '';
            if (cover) {
                coverHTML = `<img src="${cover}" alt="${title}">`;
            } else {
                coverHTML = `<i class="fa-solid fa-book-open"></i>`;
            }

            return `
                <div class="lumina-set-card animate-scale" onclick="window.location.href='/learn/vocabulary/set/${set.id}'">
                    <div class="lumina-set-cover">
                        ${coverHTML}
                    </div>
                    <div class="lumina-set-info">
                        <div class="lumina-set-title">${title}</div>
                        <div class="lumina-set-meta">
                            <span>${author}</span>
                            <div class="lumina-set-count">
                                <i class="fa-regular fa-clone"></i> ${count}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        normalizePath(path) {
            if (!path) return null;
            path = path.trim().replace(/\\/g, '/');
            if (path.startsWith('http') || path.startsWith('/')) return path;
            if (path.startsWith('uploads/')) return '/' + path;
            return '/static/' + path;
        }

        renderEmpty() {
            const html = `
                <div class="lumina-empty-state">
                    <div class="lumina-empty-icon">
                        <i class="fa-regular fa-folder-open"></i>
                    </div>
                    <p>Chưa có bộ thẻ nào.</p>
                </div>
            `;
            if (this.elements.gridMobile) this.elements.gridMobile.innerHTML = html;
            if (this.elements.gridDesktop) this.elements.gridDesktop.innerHTML = html;
        }

        renderPagination(data) {
            const { page, total, has_next, has_prev } = data;
            const totalPages = Math.ceil(total / 10) || 1;

            if (totalPages <= 1) {
                if (this.elements.gridMobile) this.hidePagination(this.elements.gridMobile.parentElement);
                if (this.elements.gridDesktop) this.hidePagination(this.elements.gridDesktop.parentElement);
                return;
            }

            const html = `
                <div class="lumina-pagination">
                    <button class="lumina-page-btn" ${!has_prev ? 'disabled' : ''} onclick="window.LuminaVocab.goToPage(${page - 1})">
                        <i class="fa-solid fa-chevron-left"></i>
                    </button>
                    <span class="text-sm font-medium text-gray-500">Trang ${page} / ${totalPages}</span>
                    <button class="lumina-page-btn" ${!has_next ? 'disabled' : ''} onclick="window.LuminaVocab.goToPage(${page + 1})">
                        <i class="fa-solid fa-chevron-right"></i>
                    </button>
                </div>
            `;

            // Append to containers
            this.updatePaginationContainer('mobile-pagination', html);
            this.updatePaginationContainer('desktop-pagination', html);
        }

        updatePaginationContainer(id, html) {
            const container = document.getElementById(id);
            if (container) {
                container.innerHTML = html;
                container.style.display = 'block';
            }
        }

        hidePagination(parent) {
            // Implementation depends on DOM structure, cleaner to just empty the container
            this.updatePaginationContainer('mobile-pagination', '');
            this.updatePaginationContainer('desktop-pagination', '');
        }

        goToPage(page) {
            if (page < 1) return;
            this.state.page = page;
            this.loadSets();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    }

    // Export and Init
    window.LuminaVocab = new VocabularyDashboard();

    document.addEventListener('DOMContentLoaded', () => {
        window.LuminaVocab.init();
    });

})();
