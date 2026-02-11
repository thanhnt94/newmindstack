/**
 * MindStack Matching Mode - SessionDriver Integration
 * Refactored to use SessionDriverClient for the game board.
 */

import { SessionDriverClient } from '../../js/session_driver_client.js';

(function () {
    // Configuration
    const config = window.MatchingConfig || {};
    const CSRF_TOKEN = config.csrfToken;
    const DB_SESSION_ID = config.dbSessionId;
    const SET_ID = config.setId;

    // Driver Client
    const client = new SessionDriverClient({
        csrfToken: CSRF_TOKEN,
        baseUrl: '/learn/session',
        driverId: 'vocabulary',
        mode: 'matching'
    });

    // State
    let isSessionActive = false;
    let currentBoard = null;
    let selectedLeft = null;
    let selectedRight = null;
    let boardMatches = 0;
    let mistakeCount = 0;
    let startTime = 0;
    let sessionScore = 0;

    // UI Elements
    const ui = {
        leftCol: document.getElementById('left-col'),
        rightCol: document.getElementById('right-col'),
        scoreEl: document.getElementById('score'),
        completeModal: document.getElementById('complete-modal'),
        finalScore: document.getElementById('final-score'),
        exitModal: document.getElementById('exit-confirm-modal'),
        exitPanel: document.getElementById('exit-modal-panel')
    };

    // --- Initialization ---

    async function init() {
        try {
            if (DB_SESSION_ID) {
                console.log(`Starting Matching Session: ${DB_SESSION_ID}`);
                await client.startSession(DB_SESSION_ID);
                isSessionActive = true;
                nextBoard();
            } else {
                alert("Lỗi phiên học (Missing ID)");
            }
        } catch (err) {
            console.error("Init Error:", err);
            alert("Không thể kết nối máy chủ");
        }
    }

    // --- Game Logic ---

    async function nextBoard() {
        if (!isSessionActive) return;

        try {
            const item = await client.getNextItem();

            if (!item) {
                endGame();
                return;
            }

            // item.data contains the board pairs from MatchingMode.format_interaction
            renderBoard(item.data);
            startTime = Date.now();
            mistakeCount = 0;
            boardMatches = 0;

        } catch (err) {
            console.error("Next Board Error:", err);
        }
    }

    function renderBoard(boardData) {
        currentBoard = boardData;
        const pairs = boardData.pairs || [];

        ui.leftCol.innerHTML = '';
        ui.rightCol.innerHTML = '';
        ui.scoreEl.textContent = '0';

        // Split and Shuffle for columns
        const leftSide = [...pairs].sort(() => Math.random() - 0.5);
        const rightSide = [...pairs].sort(() => Math.random() - 0.5);

        leftSide.forEach(pair => {
            const card = createCard(pair, 'left');
            ui.leftCol.appendChild(card);
        });

        rightSide.forEach(pair => {
            const card = createCard(pair, 'right');
            ui.rightCol.appendChild(card);
        });
    }

    function createCard(pair, side) {
        const card = document.createElement('div');
        card.className = 'match-card';
        card.dataset.side = side;
        card.dataset.id = pair.id;
        card.textContent = side === 'left' ? pair.front : pair.back;

        card.onclick = () => handleCardClick(card);
        return card;
    }

    function handleCardClick(card) {
        if (card.classList.contains('matched')) return;

        const side = card.dataset.side;
        if (side === 'left') {
            if (selectedLeft) selectedLeft.classList.remove('selected');
            selectedLeft = card;
            card.classList.add('selected');
        } else {
            if (selectedRight) selectedRight.classList.remove('selected');
            selectedRight = card;
            card.classList.add('selected');
        }

        if (selectedLeft && selectedRight) {
            checkMatch();
        }
    }

    async function checkMatch() {
        const leftId = selectedLeft.dataset.id;
        const rightId = selectedRight.dataset.id;

        if (leftId === rightId) {
            // Success
            selectedLeft.classList.replace('selected', 'matched');
            selectedRight.classList.replace('selected', 'matched');

            boardMatches++;
            ui.scoreEl.textContent = boardMatches;

            selectedLeft = null;
            selectedRight = null;

            if (boardMatches === currentBoard.pairs.length) {
                // Board Cleared -> Submit
                submitBoardResult();
            }
        } else {
            // Fail
            mistakeCount++;
            selectedLeft.classList.add('wrong');
            selectedRight.classList.add('wrong');

            const l = selectedLeft;
            const r = selectedRight;
            selectedLeft = null;
            selectedRight = null;

            setTimeout(() => {
                l.classList.remove('wrong', 'selected');
                r.classList.remove('wrong', 'selected');
            }, 500);
        }
    }

    async function submitBoardResult() {
        if (!currentBoard) return;

        const durationMs = Date.now() - startTime;

        try {
            const result = await client.submitAnswer(DB_SESSION_ID, {
                item_id: currentBoard.anchor_id,
                mistakes: mistakeCount,
                duration_ms: durationMs
            });

            // If correct (quality matches), proceed to next board after a small delay
            console.log("Board Submitted:", result);

            if (window.showScoreToast && result.evaluation.score_change > 0) {
                window.showScoreToast(result.evaluation.score_change);
            }

            setTimeout(() => {
                nextBoard();
            }, 1000);

        } catch (err) {
            console.error("Board Submit Error:", err);
            alert("Lỗi lưu kết quả bảng.");
        }
    }

    function endGame() {
        ui.finalScore.textContent = correctCount || 0; // Or some global count
        ui.completeModal.style.display = 'flex';
        isSessionActive = false;
    }

    // --- Modal & Navigation ---

    window.endMatchingSession = function () {
        if (ui.exitModal) {
            ui.exitModal.style.display = 'flex';
            setTimeout(() => {
                ui.exitModal.classList.remove('opacity-0', 'hidden');
                ui.exitPanel.classList.remove('scale-95');
                ui.exitPanel.classList.add('scale-100');
            }, 10);
        }
    };

    window.closeExitModal = function () {
        if (ui.exitModal) {
            ui.exitModal.classList.add('opacity-0');
            ui.exitPanel.classList.remove('scale-100');
            ui.exitPanel.classList.add('scale-95');
            setTimeout(() => {
                ui.exitModal.classList.add('hidden');
                ui.exitModal.style.display = 'none';
            }, 300);
        }
    };

    window.confirmExit = async function () {
        const btn = document.querySelector('button[onclick="confirmExit()"]');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Xử lý...';
            btn.disabled = true;
        }

        try {
            await client.completeSession(DB_SESSION_ID);
            window.location.href = `/learn/session/${DB_SESSION_ID}/summary`;
        } catch (err) {
            console.error(err);
            window.location.href = "/learn/session/history";
        }
    };

    window.goToSummary = function () {
        if (DB_SESSION_ID) {
            window.location.href = `/learn/session/${DB_SESSION_ID}/summary`;
        } else {
            window.location.href = "/learn/vocabulary/matching/setup/" + SET_ID;
        }
    };

    // --- Start ---
    init();

})();
