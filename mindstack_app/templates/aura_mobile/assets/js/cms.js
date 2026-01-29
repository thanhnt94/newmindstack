/**
 * CMS Logic for Aura Mobile
 */

const MindStackCMS = (function() {
    let config = {};
    let activeTab = 'flashcards'; // Default

    function initMobile(settings) {
        config = settings;
        
        // Tab switching logic
        document.querySelectorAll('.mobile-tab-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const target = this.dataset.target;
                switchTab(target);
            });
        });

        // Initialize with default tab (or URL param)
        const urlParams = new URLSearchParams(window.location.search);
        const tabParam = urlParams.get('tab');
        if (tabParam && config.urls[tabParam]) {
            switchTab(tabParam);
        } else {
            switchTab('flashcards');
        }

        // Search toggle
        const searchBtn = document.getElementById('mobile-search-toggle-btn');
        const searchBar = document.getElementById('mobile-search-bar');
        if (searchBtn && searchBar) {
            searchBtn.addEventListener('click', () => {
                searchBar.classList.toggle('hidden');
            });
        }
    }

    function switchTab(target) {
        activeTab = target;
        
        // Update tab UI
        document.querySelectorAll('.mobile-tab-btn').forEach(btn => {
            const isSelected = btn.dataset.target === target;
            btn.setAttribute('aria-selected', isSelected);
        });

        // Update Add Button
        const addBtn = document.getElementById('mobile-add-btn');
        if (addBtn && config.addUrls && config.addUrls[target]) {
            addBtn.dataset.modalUrl = config.addUrls[target];
        }

        // Load Content
        loadContent(target);
    }

    function loadContent(target) {
        const container = document.getElementById('mobile-tab-content');
        if (!container) return;
        
        container.innerHTML = `
            <div class="flex flex-col items-center justify-center gap-4 text-slate-400 py-12">
                <div class="w-16 h-16 rounded-full bg-indigo-50 flex items-center justify-center">
                    <i class="fa-solid fa-rotate animate-spin text-indigo-400 text-2xl"></i>
                </div>
                <p class="text-sm font-medium text-slate-500">Đang tải...</p>
            </div>
        `;

        const url = config.urls[target];
        if (!url) return;

        // Add AJAX param to request partial content if backend supports it
        // Or assume backend returns full page and we strip?
        // Usually, these endpoints might return a partial HTML if requested via AJAX or specific header.
        // Let's assume standard fetch for now.
        
        fetch(url)
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.text();
            })
            .then(html => {
                // If the response is a full page, we might need to extract the relevant part.
                // However, based on the endpoint naming `list_containers`, it might return a full page.
                // A robust way is to parse the HTML and extract the main content container.
                // But let's see. If we dump full HTML into a div, it might duplicate headers/footers.
                
                // Hack: if html contains <html, it's a full page.
                if (html.includes('<html') || html.includes('<!DOCTYPE html>')) {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    // Try to find the content container. Assuming it's similar to current page structure.
                    // Or maybe we should look for a specific partial ID.
                    // If no specific container, use body content?
                    
                    // For now, let's assume the endpoints render full pages and we need to extract.
                    // Ideally, we should request a partial.
                    // Let's try to find a common content wrapper class or ID.
                    
                    // Note: This is a simplified "PJAX" approach.
                    // Let's look for .app-container or specific list container.
                    const content = doc.querySelector('.app-container') || doc.body;
                    container.innerHTML = content.innerHTML;
                } else {
                    container.innerHTML = html;
                }
                
                processContentUpdates();
            })
            .catch(error => {
                console.error('Error loading content:', error);
                container.innerHTML = '<div class="text-center py-10 text-red-500">Lỗi tải nội dung. Vui lòng thử lại.</div>';
            });
    }

    function processContentUpdates() {
        // 1. Move search form if it exists in the loaded content
        const searchFormSource = document.querySelector('#mobile-tab-content .search-form-container-source');
        const searchBarTarget = document.getElementById('mobile-search-form-container');
        
        if (searchFormSource && searchBarTarget) {
            searchBarTarget.innerHTML = '';
            searchBarTarget.appendChild(searchFormSource.cloneNode(true));
            // Ensure the form is visible/clean inside the wrapper
            if (searchBarTarget.firstElementChild) {
                searchBarTarget.firstElementChild.classList.remove('hidden');
                searchBarTarget.firstElementChild.style.display = 'block';
            }
        } else if (searchBarTarget) {
            searchBarTarget.innerHTML = '<div class="text-sm text-slate-400 text-center py-2">Không có bộ lọc cho mục này</div>';
        }

        // 2. Move pagination to fixed bar
        const paginationSource = document.querySelector('#mobile-tab-content .pagination-container-source');
        const paginationBar = document.getElementById('mobile-fixed-pagination-bar');
        const paginationSlot = document.getElementById('mobile-fixed-pagination-slot');

        if (paginationSource && paginationBar && paginationSlot) {
            paginationSlot.innerHTML = '';
            // Clone or move
            const paginationContent = paginationSource.cloneNode(true);
            paginationSlot.appendChild(paginationContent);
            paginationBar.classList.remove('hidden');
            paginationBar.style.display = 'flex';
        } else if (paginationBar) {
            paginationBar.classList.add('hidden');
            paginationBar.style.display = 'none';
        }
    }

    return {
        initMobile: initMobile
    };
})();
