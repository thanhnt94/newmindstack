/**
 * Lumina UI - Core App JavaScript
 * Utilities, flash messages, fetch helpers
 */

(function () {
    'use strict';

    // === CSRF Token Helper ===
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    // === Fetch Wrapper with CSRF ===
    async function luminaFetch(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
                ...options.headers
            }
        };

        const mergedOptions = { ...defaultOptions, ...options };

        try {
            const response = await fetch(url, mergedOptions);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Lumina Fetch Error:', error);
            throw error;
        }
    }

    // === Flash Message System ===
    function showFlash(message, type = 'info', duration = 5000) {
        const container = document.getElementById('lumina-flash-container');
        if (!container) return;

        const iconMap = {
            success: 'fa-check-circle',
            error: 'fa-times-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };

        const colorMap = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            warning: 'bg-amber-500',
            info: 'bg-blue-500'
        };

        const flash = document.createElement('div');
        flash.className = `flash-message flex items-center gap-3 px-4 py-3 rounded-xl text-white shadow-lg ${colorMap[type] || colorMap.info} transform translate-x-full opacity-0 transition-all duration-300`;
        flash.innerHTML = `
            <i class="fas ${iconMap[type] || iconMap.info}"></i>
            <span class="flex-1">${message}</span>
            <button onclick="this.parentNode.remove()" class="opacity-70 hover:opacity-100">
                <i class="fas fa-times"></i>
            </button>
        `;

        container.appendChild(flash);

        // Animate in
        requestAnimationFrame(() => {
            flash.classList.remove('translate-x-full', 'opacity-0');
        });

        // Auto dismiss
        if (duration > 0) {
            setTimeout(() => {
                flash.classList.add('translate-x-full', 'opacity-0');
                setTimeout(() => flash.remove(), 300);
            }, duration);
        }
    }

    // === Confirm Dialog ===
    function confirmAction(message, onConfirm, onCancel) {
        const result = window.confirm(message);
        if (result && onConfirm) onConfirm();
        else if (!result && onCancel) onCancel();
        return result;
    }

    // === Format Numbers ===
    function formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }

    // === Format Date Relative ===
    function formatRelativeTime(date) {
        const now = new Date();
        const diff = now - new Date(date);
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 7) return new Date(date).toLocaleDateString('vi-VN');
        if (days > 0) return `${days} ngày trước`;
        if (hours > 0) return `${hours} giờ trước`;
        if (minutes > 0) return `${minutes} phút trước`;
        return 'Vừa xong';
    }

    // === Initialize Flash Container ===
    function initFlashContainer() {
        if (!document.getElementById('lumina-flash-container')) {
            const container = document.createElement('div');
            container.id = 'lumina-flash-container';
            container.className = 'fixed top-4 right-4 z-[9999] flex flex-col gap-2 max-w-sm';
            document.body.appendChild(container);
        }
    }

    // === Initialize on DOM Ready ===
    document.addEventListener('DOMContentLoaded', () => {
        initFlashContainer();
    });

    // === Export Lumina App Utilities ===
    window.LuminaApp = {
        fetch: luminaFetch,
        getCsrfToken: getCsrfToken,
        showFlash: showFlash,
        confirmAction: confirmAction,
        formatNumber: formatNumber,
        formatRelativeTime: formatRelativeTime
    };
})();
