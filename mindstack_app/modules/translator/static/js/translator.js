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
        // Debounce timer
        let selectionTimeout;

        const handler = () => {
            clearTimeout(selectionTimeout);
            selectionTimeout = setTimeout(() => {
                this.handleSelection();
            }, 600); // 600ms wait for selection to settle (mobile handles)
        };

        document.addEventListener('selectionchange', handler);

        // Close popup if clicking/touching outside
        const closeHandler = (e) => {
            if (this.state.isVisible && !e.target.closest('#ms-translator-popup')) {
                this.hide();
            }
        };

        document.addEventListener('mousedown', closeHandler);
        document.addEventListener('touchstart', closeHandler, { passive: true });

        // Hide on scroll to prevent floating weirdness
        window.addEventListener('scroll', () => {
            if (this.state.isVisible) this.hide();
        }, { passive: true });
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
                document.querySelector('.option-button.correct') || /* Quiz Answered */
                document.querySelector('.js-result-panel:not(.hidden)') || /* Single Mode Result */
                document.querySelector('.qb-modal-overlay.open') || /* Hub/Modal Open */
                document.querySelector('.question-insights:not(.hidden)') || /* Batch Inline (if used) */
                // Also check if we are in "Review" mode or "History"
                path.includes('/review');

            if (!explanationVisible) return false;
        }

        return true;
    },

    handleSelection() {
        if (!this.isTranslationAllowed()) {
            this.hide();
            return;
        }

        const selection = window.getSelection();
        const text = selection.toString().trim();

        if (text.length > 0 && text.length < 500) {
            // Ignore if selection is inside the popup itself
            const anchorNode = selection.anchorNode;
            if (anchorNode && anchorNode.parentElement && anchorNode.parentElement.closest('#ms-translator-popup')) {
                return;
            }

            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                const rect = range.getBoundingClientRect();
                this.showButton(rect, text);
            }
        } else {
            this.hide();
        }
    },

    createPopupElement() {
        let el = document.getElementById('ms-translator-popup');
        if (!el) {
            el = document.createElement('div');
            el.id = 'ms-translator-popup';
            el.className = 'fixed z-[10000] bg-white shadow-xl rounded-xl border border-slate-200 flex flex-col'; // Removed duration-200 and overflow-hidden
            el.style.maxWidth = 'none';
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
        // Temporarily make it visible but outside flow to measure
        popup.style.visibility = 'hidden';
        popup.style.display = 'block';

        // Reset max-width to ensure accurate measurement before setting
        popup.style.maxWidth = '320px'; // Set a reasonable max width for measurement
        const popupRect = popup.getBoundingClientRect();

        // Restore
        popup.style.visibility = '';
        popup.style.display = '';

        const margin = 8; // Margin from selection and viewport edges
        let finalTop, finalLeft;

        // 1. Vertical Positioning (Prioritize above, then below)
        const spaceAbove = rect.top;
        const spaceBelow = window.innerHeight - rect.bottom;

        if (spaceAbove >= popupRect.height + margin) {
            finalTop = rect.top - popupRect.height - margin;
        } else if (spaceBelow >= popupRect.height + margin) {
            finalTop = rect.bottom + margin;
        } else {
            // Not enough space above or below, try to center vertically
            finalTop = (window.innerHeight - popupRect.height) / 2;
            if (finalTop < margin) finalTop = margin;
        }

        // 2. Horizontal Positioning (Center, then adjust for viewport edges)
        finalLeft = rect.left + (rect.width / 2) - (popupRect.width / 2);

        // Adjust if it goes off the left edge
        if (finalLeft < margin) {
            finalLeft = margin;
        }
        // Adjust if it goes off the right edge
        if (finalLeft + popupRect.width > window.innerWidth - margin) {
            finalLeft = window.innerWidth - popupRect.width - margin;
            if (finalLeft < margin) finalLeft = margin; // Ensure it doesn't go off left if very narrow
        }

        popup.style.top = `${finalTop}px`; // Fixed position doesn't need window.scrollY
        popup.style.left = `${finalLeft}px`;
        popup.style.transform = 'none';
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

            if (data.success && data.data && data.data.translated) {
                this.showResult(data.data);
            } else {
                console.error('Translation response error:', data);
                this.showError();
            }
        } catch (e) {
            console.error(e);
            this.showError();
        }
    },

    showResult(data) {
        const { translated, source, kanji_details, original } = data;
        const popup = document.getElementById('ms-translator-popup');
        popup.style.maxWidth = '320px'; // Slightly wider for tabs

        const hasKanji = kanji_details && kanji_details.length > 0;

        let tabsHtml = '';
        if (hasKanji) {
            tabsHtml = `
                <div class="flex border-b border-slate-100 bg-slate-50">
                    <button onclick="MsTranslator.switchTab('translate')" id="ms-tab-btn-translate" class="flex-1 py-2 text-[10px] font-bold uppercase border-b-2 border-indigo-600 text-indigo-600 transition-all">Dịch</button>
                    <button onclick="MsTranslator.switchTab('kanji')" id="ms-tab-btn-kanji" class="flex-1 py-2 text-[10px] font-bold uppercase border-b-2 border-transparent text-slate-400 hover:text-slate-600 transition-all">Kanji (${kanji_details.length})</button>
                </div>
            `;
        }

        popup.innerHTML = `
            <div class="bg-white text-sm w-full">
                <div id="ms-translator-header" class="flex justify-between items-center p-2 border-b border-slate-100 text-[10px] text-slate-400 uppercase font-bold cursor-move select-none hover:bg-slate-50 transition-colors" title="Kéo thả để di chuyển">
                    <span class="pointer-events-none">${source || 'Auto'} <i class="fa-solid fa-arrow-right mx-1"></i> VI</span>
                    <div class="flex gap-2">
                        <a href="/translator/history" target="_blank" title="Xem lịch sử đầy đủ" class="hover:text-indigo-600 px-1"><i class="fa-solid fa-history"></i></a>
                        <button onclick="MsTranslator.hide()" class="hover:text-red-500 px-1"><i class="fa-solid fa-xmark"></i></button>
                    </div>
                </div>
                ${tabsHtml}
                <div id="ms-tab-content-translate" class="p-3 max-h-[250px] overflow-y-auto">
                    <p class="font-medium text-slate-800 leading-relaxed whitespace-pre-wrap">${translated}</p>
                </div>
                <div id="ms-tab-content-kanji" class="hidden p-3 max-h-[250px] overflow-y-auto">
                    ${this.renderKanjiList(original, kanji_details)}
                </div>
            </div>
        `;

        this.makeDraggable(popup);
    },

    makeDraggable(el) {
        const header = el.querySelector('#ms-translator-header');
        if (!header) return;

        let isDragging = false;
        let startX, startY;
        let initialX, initialY;
        let rafId = null;

        const onStart = (e) => {
            if (e.target.closest('button') || e.target.closest('a')) return;

            isDragging = true;
            el.classList.add('dragging');
            el.style.transition = 'none'; // Force disable any transitions

            const clientX = e.type === 'mousedown' ? e.clientX : e.touches[0].clientX;
            const clientY = e.type === 'mousedown' ? e.clientY : e.touches[0].clientY;

            startX = clientX;
            startY = clientY;

            const rect = el.getBoundingClientRect();
            initialX = rect.left;
            initialY = rect.top;

            document.addEventListener('mousemove', onMove, { passive: false });
            document.addEventListener('mouseup', onEnd);
            document.addEventListener('touchmove', onMove, { passive: false });
            document.addEventListener('touchend', onEnd);

            if (e.type === 'mousedown') e.preventDefault();
        };

        const onMove = (e) => {
            if (!isDragging) return;
            if (e.cancelable) e.preventDefault();

            const clientX = e.type === 'mousemove' ? e.clientX : e.touches[0].clientX;
            const clientY = e.type === 'mousemove' ? e.clientY : e.touches[0].clientY;

            const dx = clientX - startX;
            const dy = clientY - startY;

            if (rafId) cancelAnimationFrame(rafId);

            rafId = requestAnimationFrame(() => {
                let newX = initialX + dx;
                let newY = initialY + dy;

                // Boundary check
                const margin = 10;
                const rect = el.getBoundingClientRect();

                newX = Math.max(margin, Math.min(newX, window.innerWidth - rect.width - margin));
                newY = Math.max(margin, Math.min(newY, window.innerHeight - rect.height - margin));

                el.style.left = `${newX}px`;
                el.style.top = `${newY}px`;
            });
        };

        const onEnd = () => {
            isDragging = false;
            el.classList.remove('dragging');
            el.style.transition = ''; // Restore transitions

            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onEnd);
            document.removeEventListener('touchmove', onMove);
            document.removeEventListener('touchend', onEnd);

            if (rafId) cancelAnimationFrame(rafId);
        };

        header.addEventListener('mousedown', onStart);
        header.addEventListener('touchstart', onStart, { passive: false });
    },

    renderKanjiList(original, kanjis) {
        if (!kanjis || kanjis.length === 0) return '';

        return kanjis.map(k => {
            const meanings = Array.isArray(k.meanings) ? k.meanings.join(', ') : (k.meanings || 'N/A');
            const char = k.kanji || '?';
            const hanviet = k.hanviet && k.hanviet !== '—' ? k.hanviet.split(/[,\s]+/).filter(Boolean).join(' / ') : '---';

            return `
                <div class="mb-4 last:mb-0 bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden flex flex-col">
                    <div class="p-4 flex gap-4 bg-slate-50/50">
                        <div class="flex flex-col items-center space-y-2">
                            <div class="text-4xl font-bold text-slate-800 font-jp leading-none tracking-tighter">${char}</div>
                            <div class="px-2 py-1 bg-indigo-600 text-white text-[9px] font-black rounded-lg uppercase tracking-wider shadow-md shadow-indigo-100">${hanviet}</div>
                        </div>
                        
                        <div class="flex-1 flex flex-col justify-center min-w-0">
                            <div class="text-[10px] font-bold text-indigo-500/60 uppercase tracking-widest mb-1.5">Nghĩa Tiếng Việt</div>
                            <div class="text-sm font-bold text-slate-800 leading-tight">
                                ${meanings}
                            </div>
                        </div>
                    </div>

                    <div class="px-4 py-3 bg-white border-t border-slate-100 flex items-center justify-between gap-2 overflow-x-auto">
                        <div class="flex gap-4 shrink-0">
                            <div class="flex flex-col">
                                <span class="text-[9px] text-slate-400 font-bold uppercase tracking-tighter">Số nét</span>
                                <span class="text-xs font-black text-slate-700">${k.strokes || '--'}</span>
                            </div>
                            <div class="flex flex-col">
                                <span class="text-[9px] text-slate-400 font-bold uppercase tracking-tighter">Cấp độ</span>
                                <span class="text-xs font-black text-slate-700">${k.jlpt ? 'N' + k.jlpt : 'Nhỏ'}</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0 ml-auto">
                            <a href="https://mazii.net/vi-VN/search/kanji/javi/${encodeURIComponent(char)}" target="_blank" class="h-8 px-2.5 bg-blue-500 text-white text-[10px] font-black rounded-lg hover:bg-blue-600 transition-all flex items-center shadow-sm whitespace-nowrap">
                                <i class="fas fa-external-link-alt mr-1"></i> MAZII
                            </a>
                            <a href="/kanji/${encodeURIComponent(char)}" target="_blank" class="h-8 px-2.5 bg-indigo-50 text-indigo-600 text-[10px] font-black rounded-lg hover:bg-indigo-100 transition-all flex items-center shadow-sm whitespace-nowrap">
                                CHI TIẾT <i class="fa-solid fa-arrow-right-long ml-1 opacity-60"></i>
                            </a>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    },

    switchTab(tab) {
        const translateTab = document.getElementById('ms-tab-content-translate');
        const kanjiTab = document.getElementById('ms-tab-content-kanji');
        const translateBtn = document.getElementById('ms-tab-btn-translate');
        const kanjiBtn = document.getElementById('ms-tab-btn-kanji');

        if (tab === 'translate') {
            translateTab.classList.remove('hidden');
            kanjiTab.classList.add('hidden');
            translateBtn.classList.add('border-indigo-600', 'text-indigo-600');
            translateBtn.classList.remove('border-transparent', 'text-slate-400');
            kanjiBtn.classList.remove('border-indigo-600', 'text-indigo-600');
            kanjiBtn.classList.add('border-transparent', 'text-slate-400');
        } else {
            translateTab.classList.add('hidden');
            kanjiTab.classList.remove('hidden');
            kanjiBtn.classList.add('border-indigo-600', 'text-indigo-600');
            kanjiBtn.classList.remove('border-transparent', 'text-slate-400');
            translateBtn.classList.remove('border-indigo-600', 'text-indigo-600');
            translateBtn.classList.add('border-transparent', 'text-slate-400');
        }
    },

    showError() {
        const popup = document.getElementById('ms-translator-popup');
        popup.innerHTML = `
             <div class="p-2 bg-red-50 text-red-600 text-xs font-bold flex items-center gap-2">
                <i class="fa-solid fa-circle-exclamation"></i> Lỗi hệ thống.
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
