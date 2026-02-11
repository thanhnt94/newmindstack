/**
 * Typing Mode Frontend Logic
 * Uses SessionDriverClient for all interactions.
 */

(function () {
    // Check dependencies
    if (typeof SessionDriverClient === 'undefined') {
        console.error("SessionDriverClient is missing!");
        return;
    }

    // Config from Window (set in index.html)
    const config = window.TypingConfig || {};
    const csrfToken = config.csrfToken || '';
    const setId = config.setId;
    const itemsCount = config.count || 10;

    // Initial Session ID might be passed from backend if created eagerly
    let dbSessionId = config.dbSessionId || null;

    // Setup Client
    const client = new SessionDriverClient({
        csrfToken: csrfToken
    });

    // State
    let currentItem = null;
    let currentIndex = 0; // for display only
    let isAnswered = false;
    let startTime = 0;
    let sessionPoints = 0;
    let scoreCorrect = 0;
    let scoreWrong = 0;

    // UI Elements
    const els = {
        prompt: document.getElementById('prompt'),
        input: document.getElementById('answer-input'),
        feedback: document.getElementById('feedback'),
        submitBtn: document.getElementById('submit-btn'),
        hintBtn: document.getElementById('hint-btn'),
        progressNum: document.getElementById('current-q-num'),
        totalNum: document.getElementById('total-q-num'),
        liveCorrect: document.getElementById('live-correct'),
        liveWrong: document.getElementById('live-wrong'),
        liveScore: document.getElementById('live-session-score'),
        totalScore: document.getElementById('mcq-total-score-val'),

        // Modals
        exitModal: document.getElementById('exit-confirm-modal'),
        exitPanel: document.getElementById('exit-modal-panel'),
        completeModal: document.getElementById('complete-modal'),

        // Final Stats
        finalCorrect: document.getElementById('final-correct'),
        finalWrong: document.getElementById('final-wrong'),
        finalTotal: document.getElementById('final-total')
    };

    // ── Initialization ──────────────────────────────────────────────

    async function init() {
        try {
            if (!dbSessionId) {
                console.log('Starting new session via client...');
                const sessionData = await client.startSession(setId, 'typing', {
                    count: itemsCount,
                    // mode_config_id: 'standard' // default
                });
                dbSessionId = sessionData.session_id;
            } else {
                console.log('Resuming session:', dbSessionId);
            }

            // Expose ID for other tools if needed
            if (window.setDriverSessionId) {
                window.setDriverSessionId(dbSessionId);
            }

            if (els.totalNum) els.totalNum.textContent = itemsCount;

            nextQuestion();
        } catch (err) {
            console.error("[Typing] Init failed:", err);
            if (els.prompt) els.prompt.textContent = "Lỗi khởi tạo phiên học: " + (err.message || "Unknown error");
        }
    }

    // ── Core Flow ───────────────────────────────────────────────────

    async function nextQuestion() {
        if (!dbSessionId) return;

        try {
            // Loading State
            if (els.submitBtn) els.submitBtn.disabled = true;

            const rawData = await client.getNextItem(dbSessionId);
            console.log('📦 Driver Data:', rawData);

            if (rawData.finished) {
                showResult();
            } else {
                currentItem = _mapTypingData(rawData);
                console.log('✨ Mapped Item:', currentItem);
                currentIndex++;
                renderItem();
            }
        } catch (err) {
            console.error("[Typing] Next failed:", err);
            if (els.prompt) els.prompt.textContent = "Lỗi tải từ vựng.";
        } finally {
            if (els.submitBtn) els.submitBtn.disabled = false;
            // Auto focus
            setTimeout(() => {
                if (els.input) {
                    els.input.focus();
                    els.input.scrollIntoView({ behavior: "smooth", block: "center" });
                }
            }, 100);
        }
    }

    /**
     * Map Driver Payload to UI format.
     */
    function _mapTypingData(payload) {
        // Handle nested 'data' or flat payload
        const core = payload.data || payload;
        const content = payload.content || core.content || {};

        // TypingMode backend returns: question, hint, length
        return {
            item_id: payload.item_id || core.item_id,
            prompt: core.question || core.front || content.front || "...",
            hint: core.hint || "",
            length: core.length || 0,
            // Pass entire object for stats/debug
            raw: core
        };
    }

    function renderItem() {
        if (!currentItem) return;

        isAnswered = false;

        // Update UI
        if (els.progressNum) els.progressNum.textContent = currentIndex;
        if (els.prompt) els.prompt.textContent = currentItem.prompt;

        // Reset Input
        if (els.input) {
            els.input.value = '';
            els.input.className = 'typing-input';
            els.input.disabled = false;
            els.input.focus();
        }

        if (els.feedback) els.feedback.innerHTML = '';

        // Reset Buttons
        if (els.submitBtn) {
            els.submitBtn.innerHTML = 'Kiểm tra <i class="fas fa-check ms-2"></i>';
            els.submitBtn.classList.remove('bg-emerald-500', 'bg-rose-500');
            els.submitBtn.disabled = false;
        }

        // Hint Logic
        if (els.hintBtn) {
            els.hintBtn.classList.add('hidden');
            els.hintBtn.style.display = 'none';
            els.hintBtn.onclick = () => {
                if (window.openVocabularyItemStats && currentItem.item_id) {
                    window.openVocabularyItemStats(currentItem.item_id);
                }
            };
        }

        startTime = Date.now();
    }

    async function checkAnswer() {
        if (isAnswered) return;

        const userText = els.input ? els.input.value.trim() : '';
        if (!userText) return; // Prevent empty submit

        isAnswered = true;
        if (els.input) els.input.disabled = true;

        const durationMs = Date.now() - startTime;

        try {
            const result = await client.submitAnswer(dbSessionId, {
                item_id: currentItem.item_id,
                text: userText,
                duration_ms: durationMs
            });

            console.log('✅ Submit Result:', result);

            // UI Feedback
            if (result.is_correct) {
                if (els.input) els.input.classList.add('correct');
                if (els.feedback) els.feedback.innerHTML = '<div class="feedback-msg success"><i class="fas fa-check-circle"></i> Chính xác!</div>';
                scoreCorrect++;
            } else {
                if (els.input) els.input.classList.add('wrong');

                // Show Correct Answer
                const corr = result.feedback?.display_answer || result.feedback?.correct_answer || "Unknown";

                // Show Diff if available (Backend TODO)
                let msg = `Đáp án: <b>${corr}</b>`;
                if (result.feedback?.diff) {
                    msg += `<br><span class="text-sm text-gray-500">${result.feedback.diff}</span>`;
                }

                if (els.feedback) els.feedback.innerHTML = `<div class="feedback-msg error"><i class="fas fa-times-circle"></i> ${msg}</div>`;
                scoreWrong++;
            }

            // Gamification
            if (result.score_change > 0) {
                sessionPoints += result.score_change;
                if (window.showScoreToast) window.showScoreToast(result.score_change);
            }
            if (result.new_total_score && els.totalScore) {
                els.totalScore.textContent = result.new_total_score.toLocaleString();
            }

            updateStats();

            // Reveal Hint/Stats
            if (els.hintBtn) {
                els.hintBtn.classList.remove('hidden');
                els.hintBtn.style.display = 'flex';
            }

            // Change Button to Next
            if (els.submitBtn) els.submitBtn.innerHTML = 'Tiếp theo <i class="fas fa-arrow-right ms-2"></i>';

        } catch (err) {
            console.error("Submit error:", err);
            alert("Lỗi khi gửi đáp án.");
            isAnswered = false;
            if (els.input) els.input.disabled = false;
        }
    }

    function updateStats() {
        if (els.liveCorrect) els.liveCorrect.textContent = scoreCorrect;
        if (els.liveWrong) els.liveWrong.textContent = scoreWrong;
        if (els.liveScore) els.liveScore.textContent = sessionPoints;
    }

    function showResult() {
        if (els.finalCorrect) els.finalCorrect.textContent = scoreCorrect;
        if (els.finalWrong) els.finalWrong.textContent = scoreWrong;
        if (els.finalTotal) els.finalTotal.textContent = scoreCorrect + scoreWrong;

        if (els.completeModal) els.completeModal.classList.add('active');
    }


    // ── Global Interface (Window) ───────────────────────────────────

    // Back/Exit Logic
    window.endTypingSession = function () {
        if (els.exitModal) {
            els.exitModal.style.display = 'flex';
            setTimeout(() => {
                els.exitModal.classList.remove('opacity-0', 'hidden');
                if (els.exitPanel) {
                    els.exitPanel.classList.remove('scale-95');
                    els.exitPanel.classList.add('scale-100');
                }
            }, 10);
        }
    };

    window.closeExitModal = function () {
        if (els.exitModal) {
            els.exitModal.classList.add('opacity-0');
            if (els.exitPanel) {
                els.exitPanel.classList.remove('scale-100');
                els.exitPanel.classList.add('scale-95');
            }
            setTimeout(() => {
                els.exitModal.classList.add('hidden');
                els.exitModal.style.display = 'none';
            }, 300);
        }
    };

    window.confirmExit = function () {
        window.goToSummary();
    };

    window.goToSummary = function () {
        if (dbSessionId) {
            window.location.href = `/learn/session/${dbSessionId}/summary`;
        } else {
            // Fallback
            window.location.href = "/dashboard";
        }
    };

    // Events
    if (els.submitBtn) {
        els.submitBtn.onclick = () => {
            if (!isAnswered) checkAnswer();
            else nextQuestion();
        };
    }

    if (els.input) {
        els.input.onkeypress = (e) => {
            if (e.key === 'Enter') {
                if (!isAnswered) checkAnswer();
                else nextQuestion();
            }
        };
    }

    // Start
    init();

})();
