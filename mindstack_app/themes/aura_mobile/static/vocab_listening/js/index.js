/**
 * MindStack Listening Mode - SessionDriver Integration
 * Refactored to use SessionDriverClient and robust audio handling.
 */

import { SessionDriverClient } from '../../js/session_driver_client.js';

(function () {
    // Configuration
    const config = window.ListeningConfig || {};
    const CSRF_TOKEN = config.csrfToken;
    const DB_SESSION_ID = config.dbSessionId;
    const SET_ID = config.setId;

    // Driver Client
    const client = new SessionDriverClient({
        csrfToken: CSRF_TOKEN,
        baseUrl: '/learn/session',
        driverId: 'vocabulary',
        mode: 'listening'
    });

    // State
    let isSessionActive = false;
    let currentItem = null; // Store current item explicitly
    let startTime = 0;

    // Stats tracking
    let sessionScore = 0;
    let totalQuestions = 0; // Learned from driver progress or count
    let correctCount = 0;
    let wrongCount = 0;

    // UI Elements
    const ui = {
        centerAudioBtn: document.getElementById('center-audio-btn'),
        audioPlayer: document.getElementById('audio-player'),
        inputEl: document.getElementById('answer-input'),
        feedbackEl: document.getElementById('feedback'),
        submitBtn: document.getElementById('submit-btn'),
        hintBtn: document.getElementById('hint-btn'),
        progressEl: document.querySelector('.js-fc-progress'),
        learnedEl: document.querySelector('.js-fc-learned'),
        relearnEl: document.querySelector('.js-fc-relearn'),
        // scoreDisplay: document.getElementById('total-score-display'),
        completeModal: document.getElementById('complete-modal'),
        finalScore: document.getElementById('final-score'),
        finalTotal: document.getElementById('final-total'),
        scoreToast: window.showScoreToast,
        memoryFeedback: window.showMemoryPowerFeedback
    };

    // --- Initialization ---

    async function init() {
        try {
            if (DB_SESSION_ID) {
                console.log(`Starting Listening Session: ${DB_SESSION_ID}`);
                await client.startSession(DB_SESSION_ID);
                isSessionActive = true;
                nextQuestion();
            } else {
                ui.feedbackEl.innerHTML = '<div class="feedback-msg error">Lỗi phiên học (Missing ID)</div>';
            }
        } catch (err) {
            console.error("Init Error:", err);
            ui.feedbackEl.innerHTML = '<div class="feedback-msg error">Không thể kết nối máy chủ</div>';
        }
    }

    // --- Game Loop ---

    async function nextQuestion() {
        if (!isSessionActive) return;

        try {
            // Reset UI
            resetUI();

            const item = await client.getNextItem();

            if (!item) {
                endGame();
                return;
            }

            // Map Data
            const qData = _mapListeningData(item);
            currentItem = qData;

            // Update Progress UI
            if (item.progress) {
                ui.progressEl.textContent = `${item.progress.current}/${item.progress.total}`;
                totalQuestions = item.progress.total;
            }

            // Play Audio
            playItemAudio(qData);

            startTime = Date.now();

        } catch (err) {
            console.error("Next Item Error:", err);
            alert("Lỗi tải câu hỏi tiếp theo.");
        }
    }

    function _mapListeningData(driverItem) {
        const content = driverItem.content || {}; // From format_interaction
        return {
            itemId: driverItem.item_id,
            audioUrl: content.audio_url,
            audioText: content.audio_text,
            hint: content.hint,
            answerLength: content.answer_length || 0,
            originalItem: content // Backup
        };
    }

    function resetUI() {
        ui.inputEl.value = '';
        ui.inputEl.className = 'listening-input';
        ui.inputEl.disabled = false;
        ui.inputEl.focus();
        ui.feedbackEl.innerHTML = '';

        ui.submitBtn.innerHTML = 'Kiểm tra <i class="fas fa-check ms-2"></i>';
        ui.submitBtn.classList.remove('!bg-slate-500');
        ui.submitBtn.disabled = false;
        ui.submitBtn.onclick = handleCheck; // Bind check action

        // Hide hint initially
        if (ui.hintBtn) {
            ui.hintBtn.classList.add('hidden');
            ui.hintBtn.style.display = 'none';
        }
    }

    // --- Audio Logic ---

    function playItemAudio(qData) {
        console.log(`Playing audio for item ${qData.itemId}`);
        ui.centerAudioBtn.classList.add('playing');

        if (qData.audioUrl) {
            // Use Backend URL
            ui.audioPlayer.src = qData.audioUrl;
            ui.audioPlayer.play()
                .catch(e => {
                    console.warn("Autoplay blocked:", e);
                    ui.centerAudioBtn.classList.remove('playing');
                });

            ui.audioPlayer.onended = () => ui.centerAudioBtn.classList.remove('playing');
            ui.audioPlayer.onerror = () => {
                console.warn("Audio load error, falling back to TTS");
                playTTS(qData.audioText);
            };

        } else if (qData.audioText) {
            // Fallback to TTS
            playTTS(qData.audioText);
        } else {
            // No audio source?
            console.error("No audio source available");
            ui.centerAudioBtn.classList.remove('playing');
            ui.feedbackEl.innerHTML = '<div class="text-red-500">Lỗi: Không có âm thanh</div>';
        }
    }

    function playTTS(text) {
        if (!text) return;

        // Browser Speech Synthesis Fallback
        if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(text);
            // Attempt to detect language or default to English/Vietnamese based on text?
            // Assuming Vocabulary is English learning for now
            utterance.lang = 'en-US';
            utterance.onend = () => ui.centerAudioBtn.classList.remove('playing');
            utterance.onerror = () => ui.centerAudioBtn.classList.remove('playing');

            window.speechSynthesis.cancel(); // Stop previous
            window.speechSynthesis.speak(utterance);
        } else {
            alert("Trình duyệt không hỗ trợ đọc văn bản.");
            ui.centerAudioBtn.classList.remove('playing');
        }
    }

    // Bind Global Audio Controls
    ui.centerAudioBtn.onclick = () => {
        if (currentItem) playItemAudio(currentItem);
        ui.inputEl.focus();
    };

    // Keyboard Shortcuts
    ui.inputEl.onkeydown = (e) => {
        if (e.key === 'Enter') {
            if (!ui.submitBtn.disabled) ui.submitBtn.click();
        }
        if (e.code === 'Space' && e.ctrlKey) {
            e.preventDefault();
            if (currentItem) playItemAudio(currentItem);
        }
    };

    // --- Interaction ---

    async function handleCheck() {
        if (!currentItem) return;

        const userInput = ui.inputEl.value.trim();
        if (!userInput) return; // Prevent empty submit

        // Lock UI
        ui.inputEl.disabled = true;
        ui.submitBtn.disabled = true;

        const durationMs = Date.now() - startTime;

        try {
            // Submit to Driver
            const result = await client.submitAnswer(DB_SESSION_ID, {
                text: userInput,
                duration_ms: durationMs
            });

            // Process Result
            const isCorrect = result.evaluation.correct;
            const feedback = result.evaluation.feedback || {};
            const correctText = feedback.correct_answer || "???";

            // Visual Feedback
            if (isCorrect) {
                correctCount++;
                sessionScore += (result.evaluation.score_change || 0);

                ui.inputEl.classList.add('correct');
                ui.feedbackEl.innerHTML = `<div class="feedback-msg success"><i class="fas fa-check"></i> Chính xác!</div>`;

                if (ui.scoreToast) ui.scoreToast(result.evaluation.score_change);

            } else {
                wrongCount++;
                ui.inputEl.classList.add('wrong');
                ui.feedbackEl.innerHTML = `<div class="feedback-msg error">
                    <i class="fas fa-times"></i> Đáp án: <strong>${correctText}</strong>
                </div>`;
            }

            // Gamification / Memory Feedback (if available in SessionDriver result?)
            // Driver response usually has `srs_update`. 
            // We can add memory feedback if `result.submission.srs_update` exists.

            updateStatsUI();

            // Setup Next Button
            ui.submitBtn.innerHTML = 'Tiếp theo <i class="fas fa-arrow-right ms-2"></i>';
            ui.submitBtn.classList.add('!bg-slate-500');
            ui.submitBtn.disabled = false;
            ui.submitBtn.onclick = () => nextQuestion();

            // Show Hint Button (Logic from legacy)
            if (ui.hintBtn) {
                ui.hintBtn.classList.remove('hidden');
                ui.hintBtn.style.display = 'flex';
                ui.hintBtn.onclick = () => {
                    // Open Item Stats if available
                    if (window.openVocabularyItemStats) window.openVocabularyItemStats(currentItem.itemId);
                };
            }

            ui.submitBtn.focus();

        } catch (err) {
            console.error("Submission Error:", err);
            alert("Lỗi gửi câu trả lời.");
            ui.inputEl.disabled = false;
            ui.submitBtn.disabled = false; // Re-enable to retry
        }
    }

    function updateStatsUI() {
        ui.learnedEl.textContent = correctCount;
        ui.relearnEl.textContent = wrongCount;
    }

    function endGame() {
        ui.finalScore.textContent = correctCount;
        ui.finalTotal.textContent = totalQuestions || (correctCount + wrongCount);
        ui.completeModal.classList.add('active');
        isSessionActive = false;
    }

    // --- Start ---
    init();

})();
