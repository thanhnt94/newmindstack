/**
 * Lumina UI - Navigation JavaScript
 * Handles sidebar toggle, bottom nav, and menu states
 */

(function () {
    'use strict';

    // === Sidebar Toggle (Desktop) ===
    const sidebar = document.querySelector('.lumina-sidebar');
    const sidebarToggle = document.querySelector('.lumina-sidebar__toggle');
    const SIDEBAR_COLLAPSED_KEY = 'lumina_sidebar_collapsed';

    function initSidebar() {
        if (!sidebar || !sidebarToggle) return;

        // Restore collapsed state from localStorage
        const isCollapsed = localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true';
        if (isCollapsed) {
            sidebar.classList.add('collapsed');
        }

        // Toggle sidebar on button click
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            const nowCollapsed = sidebar.classList.contains('collapsed');
            localStorage.setItem(SIDEBAR_COLLAPSED_KEY, nowCollapsed);

            // Update toggle icon
            const icon = sidebarToggle.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-chevron-left', !nowCollapsed);
                icon.classList.toggle('fa-chevron-right', nowCollapsed);
            }
        });
    }

    // === Bottom Nav Active State (Mobile) ===
    function initBottomNav() {
        const bottomNavItems = document.querySelectorAll('.lumina-bottomnav__item');
        const currentPath = window.location.pathname;

        bottomNavItems.forEach(item => {
            const href = item.getAttribute('href');
            if (href && currentPath.startsWith(href)) {
                item.classList.add('active');
            }
        });
    }

    // === Learning Menu (Mobile Floating Menu) ===
    let isLearningMenuOpen = false;
    const learningMenuBtn = document.getElementById('lumina-learn-btn');
    const learningMenu = document.getElementById('lumina-learn-menu');
    const learningMenuOverlay = document.getElementById('lumina-learn-overlay');

    function toggleLearningMenu() {
        isLearningMenuOpen = !isLearningMenuOpen;

        if (isLearningMenuOpen) {
            learningMenu?.classList.add('is-visible');
            learningMenuOverlay?.classList.add('is-visible');
            learningMenuBtn?.classList.add('is-active');
        } else {
            learningMenu?.classList.remove('is-visible');
            learningMenuOverlay?.classList.remove('is-visible');
            learningMenuBtn?.classList.remove('is-active');
        }
    }

    function initLearningMenu() {
        if (learningMenuBtn) {
            learningMenuBtn.addEventListener('click', toggleLearningMenu);
        }
        if (learningMenuOverlay) {
            learningMenuOverlay.addEventListener('click', () => {
                if (isLearningMenuOpen) toggleLearningMenu();
            });
        }
    }

    // === Initialize on DOM Ready ===
    document.addEventListener('DOMContentLoaded', () => {
        initSidebar();
        initBottomNav();
        initLearningMenu();
    });

    // Export for external use
    window.LuminaNav = {
        toggleSidebar: () => sidebar?.classList.toggle('collapsed'),
        toggleLearningMenu: toggleLearningMenu
    };
})();
