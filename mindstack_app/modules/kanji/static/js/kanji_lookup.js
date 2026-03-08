/**
 * MindStack Kanji Selection Lookup
 * Provides instant Kanji definitions on text selection.
 */

const MsKanjiLookup = {
    state: {
        isVisible: false,
        triggerVisible: false,
        activeKanji: [],
        currentIdx: 0
    },

    init() {
        let selectionTimeout;
        const handler = () => {
            clearTimeout(selectionTimeout);
            selectionTimeout = setTimeout(() => {
                this.handleSelection();
            }, 600);
        };

        document.addEventListener('selectionchange', handler);

        const closeHandler = (e) => {
            if (this.state.isVisible && !e.target.closest('#ms-kanji-popup')) {
                this.hide();
            }
            if (this.state.triggerVisible && !e.target.closest('#ms-kanji-trigger')) {
                this.hideTrigger();
            }
        };

        document.addEventListener('mousedown', closeHandler);
        document.addEventListener('touchstart', closeHandler, { passive: true });

        window.addEventListener('scroll', () => {
            if (this.state.isVisible || this.state.triggerVisible) this.hide();
        }, { passive: true });
    },

    isKanji(char) {
        return /[\u4E00-\u9FFF\u3400-\u4DBF]/.test(char);
    },

    handleSelection() {
        const selection = window.getSelection();
        const text = selection.toString().trim();

        // Extract all Kanji from selection
        const kanjis = [...text].filter(c => this.isKanji(c));

        if (kanjis.length > 0 && text.length < 50) {
            // Check if inside our own popup to ignore
            const anchor = selection.anchorNode;
            if (anchor && anchor.parentElement && (anchor.parentElement.closest('#ms-kanji-popup') || anchor.parentElement.closest('#ms-kanji-trigger'))) {
                return;
            }

            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                const rect = range.getBoundingClientRect();
                this.state.activeKanji = kanjis;
                this.showTrigger(rect);
            }
        } else {
            if (!this.state.isVisible) this.hideTrigger();
        }
    },

    getOrCreateTrigger() {
        let el = document.getElementById('ms-kanji-trigger');
        if (!el) {
            el = document.createElement('button');
            el.id = 'ms-kanji-trigger';
            // Use Aura primary color (indigo)
            el.className = 'fixed z-[10001] bg-indigo-600 text-white w-8 h-8 rounded-full shadow-lg flex items-center justify-center transition-all duration-200 hover:scale-110 active:scale-95';
            el.innerHTML = '<i class="fa-solid fa-magnifying-glass-char"></i>';
            el.onclick = (e) => {
                e.stopPropagation();
                this.lookup(this.state.activeKanji[0]);
            };
            document.body.appendChild(el);
        }
        return el;
    },

    showTrigger(rect) {
        const trigger = this.getOrCreateTrigger();
        this.state.triggerVisible = true;
        trigger.classList.remove('hidden');

        // Offset slightly to the right of the selection center 
        // to avoid overlapping with MsTranslator's "Dịch" button which centers itself
        const top = rect.top - 45;
        const left = rect.left + (rect.width / 2) + 30; // Shifted 30px to the right

        trigger.style.top = `${top > 0 ? top : rect.bottom + 10}px`;
        trigger.style.left = `${left}px`;
        trigger.style.transform = 'translateX(-50%)';
    },

    hideTrigger() {
        const trigger = document.getElementById('ms-kanji-trigger');
        if (trigger) trigger.classList.add('hidden');
        this.state.triggerVisible = false;
    },

    getOrCreatePopup() {
        let el = document.getElementById('ms-kanji-popup');
        if (!el) {
            el = document.createElement('div');
            el.id = 'ms-kanji-popup';
            el.className = 'ms-kanji-glass fixed z-[10002] rounded-3xl shadow-2xl border border-white/40 transition-all duration-300 overflow-hidden flex flex-col';
            el.style.width = '300px';
            document.body.appendChild(el);
        }
        return el;
    },

    async lookup(char) {
        this.hideTrigger();
        const popup = this.getOrCreatePopup();
        this.state.isVisible = true;
        popup.classList.remove('hidden');

        // Position intelligently
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const rect = selection.getRangeAt(0).getBoundingClientRect();
            // Above if space, otherwise below
            const topPos = rect.top - 180;
            popup.style.top = `${topPos > 20 ? topPos : rect.bottom + 15}px`;
            popup.style.left = `${Math.max(15, Math.min(window.innerWidth - 315, rect.left))}px`;
        }

        popup.innerHTML = `
            <div class="px-3 py-6 flex flex-col items-center justify-center space-y-3">
                <div class="w-12 h-12 rounded-2xl bg-slate-100/50 animate-pulse flex items-center justify-center">
                    <i class="fa-solid fa-spinner fa-spin text-indigo-400"></i>
                </div>
                <div class="h-2 bg-slate-100 rounded w-1/2 animate-pulse"></div>
            </div>
        `;

        try {
            const res = await fetch(`/api/kanji/${encodeURIComponent(char)}/details`);
            const data = await res.json();

            if (data.details) {
                this.renderDetails(char, data.details);
            } else {
                popup.innerHTML = '<div class="p-6 text-center text-slate-400 text-xs font-medium">Không tìm thấy dữ liệu cho chữ này.</div>';
            }
        } catch (e) {
            popup.innerHTML = '<div class="p-6 text-center text-rose-500 text-xs font-bold">Lỗi kết nối máy chủ.</div>';
        }
    },

    renderDetails(char, d) {
        const popup = document.getElementById('ms-kanji-popup');

        // Limit meanings for the quick popup
        const meanings = (d.meanings || []).slice(0, 3).join(', ');

        popup.innerHTML = `
            <div class="p-0 flex flex-col relative">
                <!-- Premium Gradient Header -->
                <div class="h-1.5 w-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500"></div>
                
                <div class="flex items-center justify-between px-4 py-3 bg-white/60 backdrop-blur-md border-b border-white/20">
                    <div class="flex items-center gap-2">
                        <div class="w-6 h-6 rounded-lg bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-200">
                             <i class="fa-solid fa-book-open-reader text-white text-[10px]"></i>
                        </div>
                        <span class="text-[10px] font-black text-slate-800 uppercase tracking-widest">Tra cứu Kanji</span>
                    </div>
                    <button onclick="MsKanjiLookup.hide()" class="w-7 h-7 flex items-center justify-center rounded-xl hover:bg-slate-100 text-slate-400 blur-none transition-colors">
                        <i class="fa-solid fa-xmark text-sm"></i>
                    </button>
                </div>
                
                <div class="p-5 flex gap-5 bg-white/20">
                    <div class="flex flex-col items-center space-y-2">
                        <div class="text-5xl font-bold text-slate-800 font-jp leading-none tracking-tighter">${char}</div>
                        <div class="px-2.5 py-1 bg-indigo-600 text-white text-[10px] font-black rounded-lg uppercase tracking-wider shadow-md shadow-indigo-100">${d.hanviet || '---'}</div>
                    </div>
                    
                    <div class="flex-1 flex flex-col justify-center min-w-0">
                        <div class="text-[10px] font-bold text-indigo-500/60 uppercase tracking-widest mb-1.5">Nghĩa Tiếng Việt</div>
                        <div class="text-base font-bold text-slate-800 leading-tight truncate-multiline">
                            ${meanings || 'Chưa có nghĩa'}
                        </div>
                    </div>
                </div>

                <div class="px-5 py-4 bg-indigo-50/30 border-t border-white/40 flex items-center justify-between">
                    <div class="flex gap-4">
                        <div class="flex flex-col">
                            <span class="text-[9px] text-slate-400 font-bold uppercase tracking-tighter">Số nét</span>
                            <span class="text-xs font-black text-slate-700">${d.strokes || '--'}</span>
                        </div>
                        <div class="flex flex-col">
                            <span class="text-[9px] text-slate-400 font-bold uppercase tracking-tighter">Cấp độ</span>
                            <span class="text-xs font-black text-slate-700">N${d.jlpt || '?'}</span>
                        </div>
                    </div>
                    <a href="/kanji/?q=${encodeURIComponent(char)}" class="h-9 px-4 bg-white border border-slate-200 text-indigo-600 text-[11px] font-black rounded-xl hover:bg-indigo-50 transition-all flex items-center shadow-sm">
                        CHI TIẾT <i class="fa-solid fa-arrow-right-long ml-2 opacity-60"></i>
                    </a>
                </div>
            </div>
        `;
    },

    hide() {
        const popup = document.getElementById('ms-kanji-popup');
        if (popup) popup.classList.add('hidden');
        this.hideTrigger();
        this.state.isVisible = false;
    }
};

document.addEventListener('DOMContentLoaded', () => MsKanjiLookup.init());
