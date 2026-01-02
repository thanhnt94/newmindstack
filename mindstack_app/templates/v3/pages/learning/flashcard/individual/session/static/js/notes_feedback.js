// Notes and Feedback Logic

let currentAiItemId = null;
let currentNoteItemId = null;
let lastLoadedNoteContent = '';

function setNoteMode(mode) {
    const noteViewSection = document.getElementById('note-view-section');
    const noteEditSection = document.getElementById('note-edit-section');
    const editNoteBtn = document.getElementById('edit-note-btn');
    const noteTextarea = document.getElementById('note-textarea');

    if (mode === 'view') {
        noteViewSection?.classList.remove('hidden');
        noteEditSection?.classList.add('hidden');
        editNoteBtn?.classList.remove('hidden');
    } else {
        noteViewSection?.classList.add('hidden');
        noteEditSection?.classList.remove('hidden');
        editNoteBtn?.classList.add('hidden');
        noteTextarea?.focus();
    }
}

function updateNoteView(content) {
    const noteDisplay = document.getElementById('note-display');
    const noteTextarea = document.getElementById('note-textarea');
    lastLoadedNoteContent = content || '';
    const hasContent = lastLoadedNoteContent.trim().length > 0;

    if (noteDisplay) noteDisplay.innerHTML = hasContent ? formatTextForHtml(lastLoadedNoteContent) : '<span class="italic text-gray-500">Chưa có ghi chú.</span>';
    if (noteTextarea) noteTextarea.value = lastLoadedNoteContent;

    setNoteMode(hasContent ? 'view' : 'edit');
}

async function openNotePanel(itemId) {
    const notePanel = document.getElementById('note-panel');
    const noteTextarea = document.getElementById('note-textarea');
    const editNoteBtn = document.getElementById('edit-note-btn');
    if (!itemId) return;
    currentNoteItemId = itemId;
    notePanel?.classList.add('open');

    if (noteTextarea) {
        noteTextarea.value = 'Đang tải ghi chú...';
        noteTextarea.disabled = true;
    }
    if (editNoteBtn) editNoteBtn.classList.add('hidden');

    try {
        const response = await fetch(getNoteUrl.replace('/0', `/${itemId}`));
        const result = await response.json();
        updateNoteView(result.success ? result.content : '');
    } catch (error) {
        console.error('Lỗi khi tải ghi chú:', error);
        updateNoteView('');
    } finally {
        if (noteTextarea) noteTextarea.disabled = false;
    }
}

function closeNotePanel() {
    const notePanel = document.getElementById('note-panel');
    const noteTextarea = document.getElementById('note-textarea');
    const editNoteBtn = document.getElementById('edit-note-btn');
    notePanel?.classList.remove('open');
    currentNoteItemId = null;
    lastLoadedNoteContent = '';
    if (noteTextarea) noteTextarea.value = '';
    if (editNoteBtn) editNoteBtn.classList.add('hidden');
}

async function saveNote() {
    const saveNoteBtn = document.getElementById('save-note-btn');
    const noteTextarea = document.getElementById('note-textarea');
    if (!currentNoteItemId || !saveNoteBtn || !noteTextarea) return;

    const content = noteTextarea.value;
    saveNoteBtn.disabled = true;
    saveNoteBtn.textContent = 'Đang lưu...';

    try {
        const response = await fetch(saveNoteUrl.replace('/0', `/${currentNoteItemId}`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...csrfHeaders },
            body: JSON.stringify({ content: content })
        });
        const result = await response.json();
        if (result.success) {
            window.showFlashMessage?.(result.message, 'success');
            updateNoteView(content);
        } else {
            window.showFlashMessage?.(result.message || 'Lỗi khi lưu.', 'danger');
        }
    } catch (error) {
        console.error('Save note error:', error);
    } finally {
        saveNoteBtn.disabled = false;
        saveNoteBtn.textContent = 'Lưu Ghi chú';
    }
}

function handleCancelNote() {
    if (lastLoadedNoteContent.trim()) setNoteMode('view'); else closeNotePanel();
}

// AI Modal override
window.openAiModal = function (itemId, termContent) {
    const aiModal = document.getElementById('ai-modal');
    const aiModalTerm = document.getElementById('ai-modal-term');
    if (aiModal?.classList.contains('open')) return;

    currentAiItemId = itemId;
    if (aiModalTerm) aiModalTerm.textContent = termContent;
    aiModal?.classList.add('open');
    if (typeof fetchAiResponse === 'function') fetchAiResponse();
};

window.closeAiModal = function () {
    const aiModal = document.getElementById('ai-modal');
    const aiResponseContainer = document.getElementById('ai-response-container');
    aiModal?.classList.remove('open');
    currentAiItemId = null;
    if (aiResponseContainer) aiResponseContainer.innerHTML = `<div class="text-gray-500">Câu trả lời của AI sẽ xuất hiện ở đây.</div>`;
};
