/**
 * MindStack Speed Mode - SessionDriver Integration
 * Refactored to use SessionDriverClient for state management.
 */

import { SessionDriverClient } from '../../js/session_driver_client.js';

(function () {
    // Configuration from server
    const config = window.SpeedConfig || {};
    const CSRF_TOKEN = config.csrfToken;
    const DB_SESSION_ID = config.dbSessionId;
    const SET_ID = config.setId;
    const TIME_LIMIT = config.timeLimit || 5; // seconds
    const MAX_LIVES = config.lives; // '3', '5', 'inf'

    // Driver Client
    const client = new SessionDriverClient({
        csrfToken: CSRF_TOKEN,
        baseUrl: '/learn/session', // Standard Session Driver API
        driverId: 'vocabulary',    // Matches VocabularyDriver registry key
        mode: 'speed'
    });

    // State
    let lives = (MAX_LIVES === 'inf') ? 999 : parseInt(MAX_LIVES);
    let isGameOver = false;
    let timerInterval = null;
    let startTime = 0;

    // Stats for local UI tracking (Driver handles persistent stats)
    let sessionStartTimestamp = Date.now();
    let totalScore = 0;
    let correctCount = 0;
    let wrongCount = 0;
    let totalQuestionsHandled = 0;

    // UI Elements
    const ui = {
        livesContainer: document.getElementById('lives-display'),
        timerBar: document.getElementById('timer-bar'),
        qText: document.getElementById('q-text'),
        answersGrid: document.getElementById('answers-grid'),
        fbOverlay: document.getElementById('fb-overlay'),
        fbIcon: document.getElementById('fb-icon'),
        endModal: document.getElementById('end-modal'),
        currQ: document.getElementById('curr-q'),
        totalQ: document.getElementById('total-q'),
        scoreToast: window.showScoreToast // Global helper if available
    };

    // --- Initialization ---

    async function init() {
        initLives();

        try {
            // Start or Resume Session
            if (DB_SESSION_ID) {
                console.log(`Resuming Speed Session: ${DB_SESSION_ID}`);
                await client.startSession(DB_SESSION_ID);
            } else {
                // Should not happen if backend injects ID, but fallback just in case
                console.warn('No DB Session ID provided. Driver might not track progress correctly.');
            }

            // Load first item
            nextQuestion();

        } catch (err) {
            console.error("Failed to init session:", err);
            ui.qText.textContent = "Lỗi kết nối máy chủ.";
        }
    }

    function initLives() {
        ui.livesContainer.innerHTML = '';
        if (MAX_LIVES === 'inf') {
            ui.livesContainer.innerHTML = '<i class="fas fa-infinity life-heart active" style="color:#ef4444"></i>';
            return;
        }
        for (let i = 0; i < lives; i++) {
            const h = document.createElement('i');
            h.className = 'fas fa-heart life-heart active';
            ui.livesContainer.appendChild(h);
        }
    }

    function updateLivesUI() {
        if (MAX_LIVES === 'inf') return;
        const hearts = ui.livesContainer.querySelectorAll('.life-heart');
        hearts.forEach((h, i) => {
            if (i < lives) h.classList.add('active');
            else h.classList.remove('active');
        });
    }

    // --- Game Loop ---

    async function nextQuestion() {
        if (isGameOver) return;

        try {
            const item = await client.getNextItem();

            if (!item) {
                // Session Complete
                endGame(true);
                return;
            }

            // Map Data
            const qData = _mapSpeedData(item);
            renderQuestion(qData);

        } catch (err) {
            console.error("Error fetching next item:", err);
            ui.qText.textContent = "Lỗi tải câu hỏi.";
        }
    }

    function _mapSpeedData(driverItem) {
        // Driver returns { item_id, content: { question, options, ... }, meta: ... }
        // SpeedMode backend format_interaction ensures this structure.
        const content = driverItem.content || {};
        return {
            itemId: driverItem.item_id,
            question: content.question || "Câu hỏi lỗi",
            options: content.options || [],
            optionIds: content.option_ids || [], // Important for submission
            meta: driverItem.meta || {},
            // Use backend timeout if provided, else fallback to global config
            timeout: (content.meta?.settings?.timeout_ms || (TIME_LIMIT * 1000))
        };
    }

    function renderQuestion(qData) {
        totalQuestionsHandled++;
        ui.currQ.textContent = totalQuestionsHandled;
        // Total Q might be unknown in infinite mode, or fixed in backend config
        // ui.totalQ.textContent = ...; 

        ui.qText.textContent = qData.question;
        ui.answersGrid.innerHTML = '';

        qData.options.forEach((optText, idx) => {
            const btn = document.createElement('button');
            btn.className = 'answer-btn';
            btn.textContent = optText;

            // We need to pass the Option ID if available, or Index if legacy
            const optId = qData.optionIds[idx];
            btn.onclick = () => handleAnswer(qData, optId, idx);

            ui.answersGrid.appendChild(btn);
        });

        startTimer(qData.timeout);
        startTime = Date.now();

        // Store current question data for timeout handling
        ui.answersGrid.dataset.curentItemId = qData.itemId;
    }

    // --- Timer Logic ---

    function startTimer(durationMs) {
        clearInterval(timerInterval);
        const end = Date.now() + durationMs;

        // Reset Animation
        ui.timerBar.style.transition = 'none';
        ui.timerBar.style.width = '100%';
        void ui.timerBar.offsetWidth; // Force reflow

        // Start CSS transition
        ui.timerBar.style.transition = `width ${durationMs}ms linear`;
        ui.timerBar.style.width = '0%';

        timerInterval = setInterval(() => {
            if (Date.now() >= end) {
                clearInterval(timerInterval);
                handleTimeOut();
            }
        }, 100);
    }

    // --- Interaction ---

    async function handleAnswer(qData, selectedOptionId, btnIndex) {
        if (ui.answersGrid.classList.contains('locked')) return;

        clearInterval(timerInterval);
        ui.timerBar.style.transition = 'none';
        lockUI();

        const durationMs = Date.now() - startTime;
        const btns = ui.answersGrid.querySelectorAll('.answer-btn');
        const selectedBtn = btns[btnIndex];

        // Optimistic UI update? 
        // We don't know correct answer yet because backend validates securely.
        // Wait for server response.
        selectedBtn.classList.add('selected'); // Neutral state first

        try {
            // Submit to Driver
            const result = await client.submitAnswer(DB_SESSION_ID, {
                item_id: qData.itemId,
                selected_option_id: selectedOptionId,
                duration_ms: durationMs
            });

            // Process Result
            const isCorrect = result.evaluation.correct;
            const feedback = result.evaluation.feedback || {};

            if (isCorrect) {
                selectedBtn.classList.remove('selected');
                selectedBtn.classList.add('correct');
                scoreUpdate(true, result.evaluation.score_change);
                setTimeout(() => nextQuestion(), 500);
            } else {
                selectedBtn.classList.remove('selected');
                selectedBtn.classList.add('wrong');

                // Highlight correct one if server returned it
                const correctId = feedback.correct_id;
                if (correctId) {
                    // Find button with correct ID (if we mapped ids to buttons)
                    // Since we didn't store IDs on buttons specifically, rely on index if available
                    // or just show feedback. 
                    // Actually, backend might not return index if purely ID based.
                    // For now, if we have optionIds, we can find index.
                    const correctIdx = qData.optionIds.indexOf(parseInt(correctId));
                    if (correctIdx !== -1 && btns[correctIdx]) {
                        btns[correctIdx].classList.add('correct');
                    }
                }

                scoreUpdate(false);
                handleCreateLifeLoss();
            }

        } catch (err) {
            console.error("Submission error:", err);
            alert("Lỗi gửi đáp án.");
            nextQuestion(); // Try next anyway
        }
    }

    async function handleTimeOut() {
        if (ui.answersGrid.classList.contains('locked')) return;
        lockUI();

        try {
            // Submit Timeout (no selection)
            // We need the current item ID.
            const itemId = ui.answersGrid.dataset.curentItemId;
            if (!itemId) return;

            const result = await client.submitAnswer(DB_SESSION_ID, {
                item_id: itemId,
                selected_option_id: null,
                duration_ms: (config.timeLimit || 5) * 1000
            });

            // Show correct answer
            const feedback = result.evaluation.feedback || {};
            const correctId = feedback.correct_id;
            // We need to match this ID to the rendered buttons to show the user
            // Since we don't have the question data in scope easily without global state,
            // we might miss showing the "Correct" answer green highlight here unless we saved state.
            // Improvement: Save currentQData globally.

            // For now, just process life loss.
            scoreUpdate(false);
            handleCreateLifeLoss();

        } catch (err) {
            console.error("Timeout sub error", err);
            nextQuestion();
        }
    }

    function handleCreateLifeLoss() {
        if (MAX_LIVES !== 'inf') {
            lives--;
            updateLivesUI();
            if (lives <= 0) {
                endGame(false);
            } else {
                setTimeout(() => nextQuestion(), 1500);
            }
        } else {
            setTimeout(() => nextQuestion(), 1500);
        }
    }

    function lockUI() {
        ui.answersGrid.classList.add('locked');
        const btns = ui.answersGrid.querySelectorAll('.answer-btn');
        btns.forEach(b => b.disabled = true);
    }

    function scoreUpdate(isCorrect, points = 0) {
        if (isCorrect) {
            correctCount++;
            totalScore += points;
            if (ui.scoreToast) ui.scoreToast(points);
        } else {
            wrongCount++;
        }
    }

    function endGame(isWin) {
        isGameOver = true;
        ui.endModal.style.display = 'flex';
        ui.endModal.classList.add('active');

        const title = document.getElementById('end-title');
        const msg = document.getElementById('end-msg');

        // Calculate Stats
        const sessionDuration = Date.now() - sessionStartTimestamp;
        const totalQ = correctCount + wrongCount;
        const avgTime = totalQ > 0 ? (sessionDuration / totalQ / 1000).toFixed(1) : "0.0";

        // Update Modal UI
        if (document.getElementById('stat-avg')) document.getElementById('stat-avg').textContent = avgTime + 's';
        if (document.getElementById('stat-wrong')) document.getElementById('stat-wrong').textContent = wrongCount;
        if (document.getElementById('stat-score')) document.getElementById('stat-score').textContent = totalScore;

        if (isWin) {
            title.textContent = "Hoàn thành!";
            title.style.color = "var(--success)";
            msg.textContent = "Bạn đã hoàn thành bài ôn tập!";
        } else {
            title.textContent = "Hết mạng!";
            title.style.color = "var(--error)";
            msg.textContent = "Bạn đã hết số mạng cho phép.";
        }
    }

    // Start
    init();

})();
