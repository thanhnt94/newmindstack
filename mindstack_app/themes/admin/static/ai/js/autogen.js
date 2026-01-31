// Auto-Generate JavaScript for AI Coach Admin Panel
// This file handles the auto-generation UI and API calls

(function () {
    'use strict';

    let currentContentType = 'quiz';
    let isGenerating = false;
    let isInitialized = false;
    let pollInterval = null;

    // Initialize when autogen tab is shown
    function initializeAutogen() {
        console.log('[Autogen] initializeAutogen called, isInitialized:', isInitialized);
        if (!isInitialized) {
            console.log('[Autogen] Loading quiz sets...');
            loadSets('quiz');
            // Check if task is already running
            checkStatus();
            loadLogs(); // Load existing logs from DB
            isInitialized = true;
        } else {
            console.log('[Autogen] Already initialized, skipping');
        }
    }

    // Expose initialization function globally
    window.initializeAutogen = initializeAutogen;

    // Content Type Selection
    window.selectContentType = function (type) {
        currentContentType = type;

        const quizBtn = document.getElementById('content-type-quiz');
        const flashcardBtn = document.getElementById('content-type-flashcard');

        if (type === 'quiz') {
            quizBtn.classList.add('active', 'border-indigo-500', 'bg-indigo-50');
            quizBtn.classList.remove('border-slate-200', 'bg-white');
            flashcardBtn.classList.remove('active', 'border-purple-500', 'bg-purple-50');
            flashcardBtn.classList.add('border-slate-200', 'bg-white');

            document.getElementById('quiz-set-selector').classList.remove('hidden');
            document.getElementById('flashcard-set-selector').classList.add('hidden');
        } else {
            flashcardBtn.classList.add('active', 'border-purple-500', 'bg-purple-50');
            flashcardBtn.classList.remove('border-slate-200', 'bg-white');
            quizBtn.classList.remove('active', 'border-indigo-500', 'bg-indigo-50');
            quizBtn.classList.add('border-slate-200', 'bg-white');

            document.getElementById('quiz-set-selector').classList.add('hidden');
            document.getElementById('flashcard-set-selector').classList.remove('hidden');
        }

        loadSets(type);
    };

    // Load Sets
    async function loadSets(type) {
        console.log('[Autogen] loadSets called with type:', type);
        try {
            const url = '/admin/ai/autogen/get-sets/' + type;
            const response = await fetch(url, { credentials: 'same-origin' });
            const data = await response.json();

            if (data.success) {
                const selectId = type === 'quiz' ? 'quiz-set-select' : 'flashcard-set-select';
                const select = document.getElementById(selectId);
                if (!select) return;

                select.innerHTML = '<option value="">-- Chọn bộ ' + (type === 'quiz' ? 'quiz' : 'flashcard') + ' --</option>';

                data.sets.forEach(function (set) {
                    const option = document.createElement('option');
                    option.value = set.id;
                    option.textContent = set.name + ' (' + set.missing + '/' + set.total + ' cần tạo)';
                    option.dataset.total = set.total;
                    option.dataset.missing = set.missing;
                    option.dataset.toGenerate = set.to_generate;
                    select.appendChild(option);
                });
                
                select.onchange = function () { updateSetInfo(type); };
            } else {
                addLog('error', 'Lỗi: ' + (data.message || 'Không thể tải danh sách'));
            }
        } catch (e) {
            addLog('error', 'Lỗi tải danh sách: ' + e.message);
        }
    }

    // Update Set Info
    function updateSetInfo(type) {
        const selectId = type === 'quiz' ? 'quiz-set-select' : 'flashcard-set-select';
        const infoId = type === 'quiz' ? 'quiz-set-info' : 'flashcard-set-info';
        const select = document.getElementById(selectId);
        const info = document.getElementById(infoId);

        if (select.value) {
            const option = select.options[select.selectedIndex];
            const total = option.dataset.total;
            const missing = option.dataset.missing;
            const toGenerate = option.dataset.toGenerate;

            document.getElementById(type + '-total').textContent = total;
            document.getElementById(type + '-missing').textContent = missing;
            document.getElementById(type + '-to-generate').textContent = toGenerate;

            info.classList.remove('hidden');
            
            // Recalculate estimated time
            const delay = parseInt(document.getElementById('api-delay-slider').value);
            const maxItems = parseInt(document.getElementById('max-items-select').value);
            const itemsToProcess = maxItems > 0 ? Math.min(maxItems, toGenerate) : toGenerate;
            const estimatedSeconds = itemsToProcess * ((delay * 60) + 2);
            const estimatedMinutes = Math.ceil(estimatedSeconds / 60);

            document.getElementById('estimated-time').textContent = '~' + estimatedMinutes + ' phút';
        } else {
            info.classList.add('hidden');
            document.getElementById('estimated-time').textContent = '--';
        }
    }

    // Update Delay Display
    window.updateDelayDisplay = function (value) {
        document.getElementById('api-delay-value').textContent = value;
        if (document.getElementById(currentContentType === 'quiz' ? 'quiz-set-select' : 'flashcard-set-select').value) {
            updateSetInfo(currentContentType);
        }
    };

    // Start Generation
    window.startGeneration = async function () {
        if (isGenerating) return;

        const selectId = currentContentType === 'quiz' ? 'quiz-set-select' : 'flashcard-set-select';
        const select = document.getElementById(selectId);

        if (!select.value) {
            alert('Vui lòng chọn bộ câu hỏi/thẻ trước!');
            return;
        }

        if (!confirm('Bắt đầu tạo nội dung AI? Tác vụ sẽ chạy ngầm.')) {
            return;
        }

        const setId = select.value;
        const apiDelayMinutes = parseInt(document.getElementById('api-delay-slider').value);
        const apiDelaySeconds = apiDelayMinutes * 60;
        const maxItems = parseInt(document.getElementById('max-items-select').value);
        const csrfToken = document.querySelector('input[name="csrf_token"]').value;

        addLog('info', 'Đang gửi yêu cầu...');

        try {
            const response = await fetch('/admin/ai/autogen/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    content_type: currentContentType,
                    set_id: setId,
                    api_delay: apiDelaySeconds,
                    max_items: maxItems
                })
            });

            const data = await response.json();

            if (data.success) {
                addLog('success', 'Task started! ID: ' + data.task_id);
                isGenerating = true;
                startPolling();
            } else {
                addLog('error', 'Không thể bắt đầu: ' + data.message);
            }
        } catch (e) {
            addLog('error', 'Lỗi kết nối: ' + e.message);
        }
    };

    // Stop Generation
    window.stopGeneration = async function () {
        if (!isGenerating) return;
        
        const csrfToken = document.querySelector('input[name="csrf_token"]').value;
        
        if (confirm('Bạn có chắc chắn muốn dừng tác vụ?')) {
            try {
                const response = await fetch('/admin/ai/autogen/stop', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    }
                });
                const data = await response.json();
                if (data.success) {
                    addLog('warning', 'Đã gửi yêu cầu dừng.');
                } else {
                    addLog('error', 'Lỗi: ' + data.message);
                }
            } catch (e) {
                addLog('error', 'Lỗi kết nối: ' + e.message);
            }
        }
    };

    function startPolling() {
        if (pollInterval) clearInterval(pollInterval);
        
        updateButtons(true);
        updateStatus('running', 'Đang xử lý...');

        pollInterval = setInterval(async () => {
            await checkStatus();
            await loadLogs();
        }, 2000);
    }
    
    async function loadLogs() {
        try {
            const response = await fetch('/admin/ai/autogen/logs');
            const data = await response.json();
            
            if (data.success && data.logs) {
                const logContainer = document.getElementById('activity-log');
                logContainer.innerHTML = ''; 
                
                if (data.logs.length === 0) {
                     logContainer.innerHTML = '<div class="text-center text-slate-400 italic py-8">Chưa có hoạt động nào</div>';
                     return;
                }

                data.logs.forEach(log => {
                    let type = 'info';
                    if (log.status === 'error' || (log.message && log.message.includes('Error'))) type = 'error';
                    else if (log.status === 'completed') type = 'success';
                    else if (log.status === 'cancelled') type = 'warning';
                    
                    addLogEntry(type, log.message, log.timestamp);
                });
                
                logContainer.scrollTop = logContainer.scrollHeight;
            }
        } catch (e) {
            console.error('Error loading logs:', e);
        }
    }

    async function checkStatus() {
        try {
            const response = await fetch('/admin/ai/autogen/status');
            const data = await response.json();
            
            if (!data.active) {
                if (isGenerating) {
                    isGenerating = false;
                    clearInterval(pollInterval);
                    updateButtons(false);
                }
                return;
            }
            
            document.getElementById('progress-current').textContent = data.progress;
            document.getElementById('progress-total').textContent = data.total;
            
            const percent = data.total > 0 ? Math.round((data.progress / data.total) * 100) : 0;
            document.getElementById('progress-bar').style.width = percent + '%';
            document.getElementById('progress-percent').textContent = percent;
            
            const statusBadge = document.getElementById('generation-status');
            
            if (data.status === 'running' || data.status === 'pending') {
                isGenerating = true;
                updateButtons(true);
                updateStatus('running', data.message);
            } else {
                isGenerating = false;
                if (pollInterval) clearInterval(pollInterval);
                updateButtons(false);
                
                if (data.status === 'completed') {
                    updateStatus('completed', data.message);
                    loadSets(currentContentType); 
                } else if (data.status === 'error') {
                    updateStatus('error', data.message);
                } else if (data.status === 'cancelled') {
                    updateStatus('error', 'Đã hủy');
                }
                loadLogs();
            }
            
        } catch (e) {
            console.error('Polling error:', e);
        }
    }
    
    function updateButtons(running) {
        document.getElementById('btn-start-generation').disabled = running;
        document.getElementById('btn-stop-generation').disabled = !running;
    }

    function updateStatus(status, text) {
        const badge = document.getElementById('generation-status');
        badge.className = 'px-3 py-1 rounded-full text-xs font-bold';

        if (status === 'running') {
            badge.className += ' bg-blue-100 text-blue-600';
            badge.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> ' + text;
        } else if (status === 'completed') {
            badge.className += ' bg-emerald-100 text-emerald-600';
            badge.innerHTML = '<i class="fas fa-check-circle mr-1"></i> ' + text;
        } else if (status === 'error') {
            badge.className += ' bg-rose-100 text-rose-600';
            badge.innerHTML = '<i class="fas fa-exclamation-circle mr-1"></i> ' + text;
        } else {
            badge.className += ' bg-slate-100 text-slate-600';
            badge.innerHTML = '<i class="fas fa-circle mr-1"></i> ' + text;
        }
    }

    function addLogEntry(type, message, timestamp) {
        const log = document.getElementById('activity-log');
        const entry = document.createElement('div');
        entry.className = 'flex items-start gap-2 p-2 rounded text-sm';
        
        let timeStr;
        const timeZone = window.USER_TIMEZONE || 'UTC';
        
        if (timestamp) {
            // Parse ISO string from server and convert to user's preferred timezone
            try {
                timeStr = new Date(timestamp).toLocaleTimeString('vi-VN', { timeZone: timeZone });
            } catch (e) {
                timeStr = timestamp; // Fallback if parsing/timezone fails
            }
        } else {
            // For client-side generated logs (immediate feedback), use current time
            // but try to respect the timezone if possible, though new Date() is system time.
            // To be strictly correct, we should format new Date() with the target timezone.
            timeStr = new Date().toLocaleTimeString('vi-VN', { timeZone: timeZone });
        }

        if (type === 'success') {
            entry.className += ' bg-emerald-50 text-emerald-700';
            entry.innerHTML = '<i class="fas fa-check-circle mt-0.5"></i><div class="flex-grow"><span class="text-xs text-emerald-500">' + timeStr + '</span> ' + message + '</div>';
        } else if (type === 'error') {
            entry.className += ' bg-rose-50 text-rose-700';
            entry.innerHTML = '<i class="fas fa-times-circle mt-0.5"></i><div class="flex-grow"><span class="text-xs text-rose-500">' + timeStr + '</span> ' + message + '</div>';
        } else if (type === 'warning') {
            entry.className += ' bg-amber-50 text-amber-700';
            entry.innerHTML = '<i class="fas fa-exclamation-triangle mt-0.5"></i><div class="flex-grow"><span class="text-xs text-amber-500">' + timeStr + '</span> ' + message + '</div>';
        } else {
            entry.className += ' bg-slate-50 text-slate-700';
            entry.innerHTML = '<i class="fas fa-info-circle mt-0.5"></i><div class="flex-grow"><span class="text-xs text-slate-500">' + timeStr + '</span> ' + message + '</div>';
        }

        log.appendChild(entry);
    }
    
    function addLog(type, message) {
        addLogEntry(type, message);
        const log = document.getElementById('activity-log');
        log.scrollTop = log.scrollHeight;
    }

    window.clearLog = function () {
        document.getElementById('activity-log').innerHTML = '<div class="text-center text-slate-400 italic py-8">Chưa có hoạt động nào</div>';
    };

})();