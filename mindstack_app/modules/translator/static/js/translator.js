/**
 * MindStack Translator Helper
 * Version: 1.0
 * Logic: "Select to Translate" with context restrictions.
 */

const MsTranslator = {
    state: {
        isVisible: false,
        selection: null,
        text: ''
    },

    init() {
        document.addEventListener('mouseup', (e) => this.handleSelection(e));
        document.addEventListener('mousedown', (e) => {
            // Close popup if clicking outside
            if (this.state.isVisible && !e.target.closest('#ms-translator-popup')) {
                this.hide();
            }
        });
    },

    isTranslationAllowed() {
        // 1. Check path constraints
        const path = window.location.pathname;
        const isFlashcard = path.includes('/flashcard');
        const isQuiz = path.includes('/quiz');

        if (!isFlashcard && !isQuiz) return false;

        // 2. Extra check for Quiz: Only allow if answer submitted / result shown
        if (isQuiz) {
            // Heuristic updates: Look for common indicators of a completed question
            // e.g., ".explanation-panel", ".result-card", or specific classes used in Quiz UI
            // Assuming MindStack uses '.explanation-container' or specific result classes
            const explanationVisible = document.querySelector('.explanation-container') ||
                document.querySelector('.result-feedback') ||
                document.querySelector('.correct-answer-display') ||
                // Also check if we are in "Review" mode or "History"
                path.includes('/review');

            if (!explanationVisible) return false;
        }

        return true;
    },

    handleSelection(e) {
        if (!this.isTranslationAllowed()) {
            this.hide();
            return;
        }

        // Timeout to ensure selection is complete
        setTimeout(() => {
            const selection = window.getSelection();
            const text = selection.toString().trim();

            if (text.length > 0 && text.length < 500) {
                // Ignore selection inside the translator itself
                if (e.target.closest('#ms-translator-popup')) return;

                const range = selection.getRangeAt(0);
                const rect = range.getBoundingClientRect();

                this.showButton(rect, text);
            } else {
                this.hide();
            }
        }, 10);
    },

    createPopupElement() {
        let el = document.getElementById('ms-translator-popup');
        if (!el) {
            el = document.createElement('div');
            el.id = 'ms-translator-popup';
            el.className = 'fixed z-[9999] bg-white shadow-xl rounded-xl border border-slate-200 transition-all duration-200 flex flex-col overflow-hidden';
            el.style.maxWidth = '300px';
            document.body.appendChild(el);
        }
        return el;
    },

    showButton(rect, text) {
        const popup = this.createPopupElement();
        this.state.text = text;
        this.state.isVisible = true;

        // Render "Translate" button
        popup.innerHTML = `
            <button onclick="MsTranslator.translate()" class="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white hover:bg-indigo-700 text-xs font-bold transition-colors">
                <i class="fa-solid fa-language"></i> Dịch
            </button>
        `;

        // Position: Above the selection
        this.positionPopup(popup, rect);
    },

    positionPopup(popup, rect) {
        const popupHeight = 40; // Approx default
        const top = rect.top - popupHeight - 8;
        const left = rect.left + (rect.width / 2); // Center horizontally

        popup.style.top = `${top > 0 ? top : rect.bottom + 8}px`; // Flip if too close to top
        popup.style.left = `${left}px`;
        popup.style.transform = 'translateX(-50%)';
    },

    async translate() {
        const popup = document.getElementById('ms-translator-popup');

        // Show Loading
        popup.innerHTML = `
            <div class="px-3 py-2 bg-white flex items-center gap-2 text-xs text-slate-500">
                <i class="fa-solid fa-spinner fa-spin"></i> Đang dịch...
            </div>
        `;

        try {
            const res = await fetch('/translator/api/translate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
                },
                body: JSON.stringify({ text: this.state.text })
            });
            const data = await res.json();

            if (data.translated) {
                this.showResult(data.translated, data.source);
            } else {
                this.showError();
            }
        } catch (e) {
            console.error(e);
            this.showError();
        }
    },

    showResult(translatedText, sourceLang) {
        const popup = document.getElementById('ms-translator-popup');
        popup.innerHTML = `
            <div class="p-3 bg-white text-sm w-full">
                <div class="flex justify-between items-center mb-1 text-[10px] text-slate-400 uppercase font-bold">
                    <span>${sourceLang || 'Auto'} <i class="fa-solid fa-arrow-right mx-1"></i> VI</span>
                    <button onclick="MsTranslator.hide()" class="hover:text-red-500"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <p class="font-medium text-slate-800 leading-relaxed">${translatedText}</p>
            </div>
        `;
    },

    showError() {
        const popup = document.getElementById('ms-translator-popup');
        popup.innerHTML = `
             <div class="p-2 bg-red-50 text-red-600 text-xs font-bold flex items-center gap-2">
                <i class="fa-solid fa-circle-exclamation"></i> Lỗi dịch thuật.
            </div>
        `;
        setTimeout(() => this.hide(), 2000);
    },

    hide() {
        const popup = document.getElementById('ms-translator-popup');
        if (popup) {
            popup.remove();
        }
        this.state.isVisible = false;
    }
};

// Auto-init
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => MsTranslator.init());
} else {
    MsTranslator.init();
}
