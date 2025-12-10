// Auto-Generate JavaScript for AI Coach Admin Panel
// This file handles the auto-generation UI and API calls

(function () {
    'use strict';

    let currentContentType = 'quiz';
    let isGenerating = false;
    let isInitialized = false;

    // Initialize when autogen tab is shown
    function initializeAutogen() {
        console.log('[Autogen] initializeAutogen called, isInitialized:', isInitialized);
        if (!isInitialized) {
            console.log('[Autogen] Loading quiz sets...');
            loadSets('quiz');
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
            const url = '/admin/api-keys/autogen/get-sets/' + type;
            console.log('[Autogen] Fetching from URL:', url);
            const response = await fetch(url, {
                credentials: 'same-origin'
            });
            console.log('[Autogen] Response status:', response.status);
            const data = await response.json();
            console.log('[Autogen] Response data:', data);

            if (data.success) {
                const selectId = type === 'quiz' ? 'quiz-set-select' : 'flashcard-set-select';
                const select = document.getElementById(selectId);

                if (!select) {
                    console.error('[Autogen] Select element not found:', selectId);
                    return;
                }

                console.log('[Autogen] Found', data.sets.length, 'sets');
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

                select.onchange = function () {
                    updateSetInfo(type);
                };

                console.log('[Autogen] Successfully populated select with', data.sets.length, 'options');
            } else {
                console.error('[Autogen] API returned error:', data.message);
                addLog('error', 'Lỗi: ' + (data.message || 'Không thể tải danh sách'));
            }
        } catch (e) {
            console.error('[Autogen] Error loading sets:', e);
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

            const delay = parseInt(document.getElementById('api-delay-slider').value);
            const maxItems = parseInt(document.getElementById('max-items-select').value);
            const itemsToProcess = maxItems > 0 ? Math.min(maxItems, toGenerate) : toGenerate;
            const estimatedSeconds = itemsToProcess * ((delay * 60) + 2);  // delay is in minutes, convert to seconds
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

        const type = currentContentType;
        const selectId = type === 'quiz' ? 'quiz-set-select' : 'flashcard-set-select';
        const select = document.getElementById(selectId);
        if (select.value) {
            updateSetInfo(type);
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

        if (!confirm('Bắt đầu tạo nội dung AI? Quá trình này có thể mất vài phút.')) {
            return;
        }

        isGenerating = true;

        document.getElementById('btn-start-generation').disabled = true;
        document.getElementById('btn-stop-generation').disabled = false;
        updateStatus('running', 'Đang chạy...');

        document.getElementById('activity-log').innerHTML = '';

        const setId = select.value;
        const apiDelayMinutes = parseInt(document.getElementById('api-delay-slider').value);
        const apiDelaySeconds = apiDelayMinutes * 60;  // Convert minutes to seconds
        const maxItems = parseInt(document.getElementById('max-items-select').value);

        addLog('info', 'Bắt đầu tạo ' + currentContentType + ' cho set #' + setId);
        addLog('info', 'Delay: ' + apiDelayMinutes + ' phút (' + apiDelaySeconds + 's), Max items: ' + (maxItems === -1 ? 'Unlimited' : maxItems));

        try {
            const response = await fetch('/admin/api-keys/autogen/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    content_type: currentContentType,
                    set_id: setId,
                    api_delay: apiDelaySeconds,
                    max_items: maxItems
                })
            });

            const data = await response.json();

            if (data.success) {
                const results = data.results;

                document.getElementById('progress-current').textContent = results.total_processed;
                document.getElementById('progress-total').textContent = results.total_processed;
                document.getElementById('progress-bar').style.width = '100%';
                document.getElementById('progress-percent').textContent = '100';

                addLog('success', '✅ Hoàn thành! Tổng: ' + results.total_processed + ', Thành công: ' + results.success_count + ', Lỗi: ' + results.error_count);

                if (results.items) {
                    results.items.forEach(function (item) {
                        if (item.status === 'success') {
                            addLog('success', '#' + item.id + ': ' + (item.content || 'Generated successfully'));
                        } else {
                            addLog('error', '#' + item.id + ': ' + item.error);
                        }
                    });
                }

                updateStatus('completed', 'Hoàn thành');
                loadSets(currentContentType);
            } else {
                addLog('error', 'Lỗi: ' + data.message);
                updateStatus('error', 'Lỗi');
            }

        } catch (e) {
            addLog('error', 'Lỗi kết nối: ' + e.message);
            updateStatus('error', 'Lỗi');
        } finally {
            isGenerating = false;
            document.getElementById('btn-start-generation').disabled = false;
            document.getElementById('btn-stop-generation').disabled = true;
        }
    };

    // Stop Generation
    window.stopGeneration = function () {
        if (!isGenerating) return;

        if (confirm('Dừng quá trình tạo? (Chức năng này chưa được implement)')) {
            addLog('warning', 'Đã yêu cầu dừng (chức năng đang phát triển)');
        }
    };

    // Update Status
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

    // Add Log
    function addLog(type, message) {
        const log = document.getElementById('activity-log');
        const entry = document.createElement('div');
        entry.className = 'flex items-start gap-2 p-2 rounded text-sm';

        const timestamp = new Date().toLocaleTimeString('vi-VN');

        if (type === 'success') {
            entry.className += ' bg-emerald-50 text-emerald-700';
            entry.innerHTML = '<i class="fas fa-check-circle mt-0.5"></i><div class="flex-grow"><span class="text-xs text-emerald-500">' + timestamp + '</span> ' + message + '</div>';
        } else if (type === 'error') {
            entry.className += ' bg-rose-50 text-rose-700';
            entry.innerHTML = '<i class="fas fa-times-circle mt-0.5"></i><div class="flex-grow"><span class="text-xs text-rose-500">' + timestamp + '</span> ' + message + '</div>';
        } else if (type === 'warning') {
            entry.className += ' bg-amber-50 text-amber-700';
            entry.innerHTML = '<i class="fas fa-exclamation-triangle mt-0.5"></i><div class="flex-grow"><span class="text-xs text-amber-500">' + timestamp + '</span> ' + message + '</div>';
        } else {
            entry.className += ' bg-slate-50 text-slate-700';
            entry.innerHTML = '<i class="fas fa-info-circle mt-0.5"></i><div class="flex-grow"><span class="text-xs text-slate-500">' + timestamp + '</span> ' + message + '</div>';
        }

        log.appendChild(entry);
        log.scrollTop = log.scrollHeight;
    }

    // Clear Log
    window.clearLog = function () {
        document.getElementById('activity-log').innerHTML = '<div class="text-center text-slate-400 italic py-8">Chưa có hoạt động nào</div>';
    };

})();
