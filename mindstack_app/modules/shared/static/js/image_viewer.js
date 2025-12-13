/**
 * MindStack Image Viewer (Lightbox)
 * Feature: Fullscreen, Zoom (Double Tap), Pan (Drag)
 * Usage: MsImageViewer.init('.zoomable');
 */

const MsImageViewer = {
    settings: {
        selector: '.zoomable, .quiz-image, .markdown-body img, .js-question-text img, .js-question-media img, .option-button img, .content-display img, .explanation-content img',
        maxScale: 2.5,
        minScale: 1
    },
    state: {
        isOpen: false,
        scale: 1,
        panning: false,
        pointX: 0,
        pointY: 0,
        startX: 0,
        startY: 0
    },
    elements: {
        overlay: null,
        img: null,
        closeBtn: null
    },

    init(customSelector) {
        if (customSelector) this.settings.selector = customSelector;

        // Delegated event listener for dynamic content
        document.body.addEventListener('click', (e) => {
            const target = e.target.closest(this.settings.selector);
            if (target && target.tagName === 'IMG') {
                e.preventDefault();
                this.open(target.src);
            }
        });

        this.createDom();
    },

    createDom() {
        if (document.getElementById('ms-image-viewer')) return;

        const overlay = document.createElement('div');
        overlay.id = 'ms-image-viewer';
        overlay.className = 'ms-iv-overlay';
        overlay.innerHTML = `
            <div class="ms-iv-header">
                <button class="ms-iv-close"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="ms-iv-container">
                <img src="" class="ms-iv-img" alt="Fullscreen View">
            </div>
            <div class="ms-iv-hint flex items-center justify-center gap-2">
                <i class="fa-solid fa-expand"></i> <span>Chạm 2 lần để phóng to</span>
            </div>
        `;

        document.body.appendChild(overlay);

        this.elements.overlay = overlay;
        this.elements.img = overlay.querySelector('.ms-iv-img');
        this.elements.closeBtn = overlay.querySelector('.ms-iv-close');

        this.bindEvents();
    },

    bindEvents() {
        const { overlay, img, closeBtn } = this.elements;

        // Close actions
        closeBtn.addEventListener('click', () => this.close());
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay || e.target.closest('.ms-iv-container')) {
                // If not dragging, close (handled in pointer up, but safe here)
            }
        });

        // IMG Interactions
        // Using Pointer Events for unified Touch/Mouse handling
        img.addEventListener('dblclick', (e) => this.handleDoubleTap(e));

        // Touch handling for mobile specific feel
        let lastTap = 0;
        img.addEventListener('touchend', (e) => {
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTap;
            if (tapLength < 500 && tapLength > 0) {
                this.handleDoubleTap(e);
                e.preventDefault();
            }
            lastTap = currentTime;
        });

        // Pan Logic
        img.addEventListener('pointerdown', (e) => this.onPointerDown(e));
        img.addEventListener('pointermove', (e) => this.onPointerMove(e));
        img.addEventListener('pointerup', (e) => this.onPointerUp(e));
        img.addEventListener('pointercancel', (e) => this.onPointerUp(e));

        // Prevent default drag
        img.addEventListener('dragstart', (e) => e.preventDefault());
    },

    open(src) {
        this.elements.img.src = src;
        this.elements.overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
        this.resetTransform();
        this.state.isOpen = true;
    },

    close() {
        this.elements.overlay.classList.remove('active');
        document.body.style.overflow = '';
        this.elements.img.src = '';
        this.state.isOpen = false;
    },

    resetTransform() {
        this.state.scale = 1;
        this.state.pointX = 0;
        this.state.pointY = 0;
        this.updateTransform();
    },

    handleDoubleTap(e) {
        if (this.state.scale > 1) {
            this.state.scale = 1;
            this.state.pointX = 0;
            this.state.pointY = 0;
        } else {
            this.state.scale = this.settings.maxScale;
            // Optional: Zoom to point could be added here, currently zooms to center for simplicity
        }
        this.updateTransform();
    },

    onPointerDown(e) {
        if (this.state.scale <= 1) return; // Only pan if zoomed in
        e.preventDefault();
        this.state.panning = true;
        this.state.startX = e.clientX - this.state.pointX;
        this.state.startY = e.clientY - this.state.pointY;
        this.elements.img.classList.add('panning');
    },

    onPointerMove(e) {
        if (!this.state.panning) return;
        e.preventDefault();
        this.state.pointX = e.clientX - this.state.startX;
        this.state.pointY = e.clientY - this.state.startY;
        this.updateTransform(); // Live update
    },

    onPointerUp(e) {
        this.state.panning = false;
        this.elements.img.classList.remove('panning');
    },

    updateTransform() {
        const { scale, pointX, pointY } = this.state;
        this.elements.img.style.transform = `translate(${pointX}px, ${pointY}px) scale(${scale})`;
    }
};

// Auto Init
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => MsImageViewer.init());
} else {
    MsImageViewer.init();
}
