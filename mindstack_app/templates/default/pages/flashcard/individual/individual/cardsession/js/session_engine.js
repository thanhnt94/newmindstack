// Session Engine and API interaction logic

function syncSettingsToServer() {
    if (!saveSettingsUrl) return;
    const payload = {
        visual_settings: {
            autoplay: isAudioAutoplayEnabled,
            show_image: !isMediaHidden,
            show_stats: showStats
        }
    };
    fetch(saveSettingsUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...csrfHeaders },
        body: JSON.stringify(payload)
    }).catch(err => console.warn('[SYNC SETTINGS] Failed:', err));
}

function stopAllFlashcardAudio(exceptAudio = null) {
    FlashcardAudioController.stopAllAudio({
        exceptAudio,
        selector: '.js-flashcard-content audio, audio'
    });
}

function playAudioForButton(button, options = {}) {
    if (!button) return Promise.resolve();
    const audioSelector = button.dataset.audioTarget;
    const card = button.closest('.js-flashcard-card');
    const audioPlayer = card ? card.querySelector(audioSelector) : document.querySelector(audioSelector);

    if (!audioPlayer || button.classList.contains('is-disabled')) return Promise.resolve();

    const awaitCompletion = options.await === true;
    const restart = options.restart !== false;
    const suppressLoadingUi = options.suppressLoadingUi === true;
    const hasAudioSource = audioPlayer.src && audioPlayer.src !== window.location.href;

    if (hasAudioSource) {
        stopAllFlashcardAudio(audioPlayer);
        return FlashcardAudioController.playAudioAfterLoad(audioPlayer, { restart, awaitCompletion });
    }
    stopAllFlashcardAudio(audioPlayer);
    return generateAndPlayAudio(button, audioPlayer, { awaitCompletion, suppressLoadingUi, restart });
}

async function generateAndPlayAudio(button, audioPlayer, options = {}) {
    return FlashcardAudioController.generateAndPlayAudio(button, audioPlayer, {
        url: regenerateAudioUrl,
        csrfHeaders: csrfHeaders,
        ...options
    });
}

function autoPlaySide(side) {
    if (!isAudioAutoplayEnabled) return;
    const visibleContainer = getVisibleFlashcardContentDiv();
    const button = visibleContainer ? visibleContainer.querySelector(`.play-audio-btn[data-side="${side}"]`) : document.querySelector(`.play-audio-btn[data-side="${side}"]`);
    if (!button) return;
    playAudioForButton(button, { suppressLoadingUi: true }).catch(() => { });
}

function autoPlayFrontSide() { autoPlaySide('front'); }
function autoPlayBackSide() { autoPlaySide('back'); }

function cancelAutoplaySequence() { FlashcardAudioController.cancelAutoplay(); }
function waitForAutoplayDelay(token) { return FlashcardAudioController.waitForDelay(token); }

async function playAutoplayAudioForSide(side, token) {
    if (token !== FlashcardAudioController.getCurrentToken()) return;
    const visibleContainer = getVisibleFlashcardContentDiv();
    const button = visibleContainer ? visibleContainer.querySelector(`.play-audio-btn[data-side="${side}"]`) : document.querySelector(`.play-audio-btn[data-side="${side}"]`);
    if (!button) return;
    try {
        await playAudioForButton(button, { await: true, suppressLoadingUi: true });
    } catch (err) { }
}

async function startAutoplaySequence() {
    const token = FlashcardAudioController.cancelAutoplay();
    try {
        await playAutoplayAudioForSide('front', token);
        if (token !== FlashcardAudioController.getCurrentToken()) return;
        await waitForAutoplayDelay(token);
        if (token !== FlashcardAudioController.getCurrentToken()) return;
        revealBackSideForAutoplay(token);
        await playAutoplayAudioForSide('back', token);
        if (token !== FlashcardAudioController.getCurrentToken()) return;
        await waitForAutoplayDelay(token);
        if (token !== FlashcardAudioController.getCurrentToken()) return;
        getNextFlashcardBatch();
    } catch (err) { }
}

function revealBackSideForAutoplay(token) {
    if (token !== FlashcardAudioController.getCurrentToken()) return;
    const { card, actions, flipBtn } = currentCardElements;
    if (!card) return;
    if (!card.classList.contains('flipped')) {
        stopAllFlashcardAudio();
        card.classList.add('flipped');
        actions?.classList.add('visible');
        if (flipBtn) flipBtn.style.display = 'none';
        setTimeout(adjustCardLayout, 0);
    } else if (actions) {
        actions.classList.add('visible');
    }
}

function getPreviewButtonHtml() {
    return '<button class="btn btn-continue" data-answer="continue"><i class="fas fa-arrow-right"></i>Tiếp tục</button>';
}

function generateDynamicButtons(buttonCount) {
    const buttonSets = {
        3: [{ variant: 'again', value: 'quên', title: 'Quên', icon: 'fas fa-redo-alt' }, { variant: 'hard', value: 'mơ_hồ', title: 'Mơ hồ', icon: 'fas fa-question-circle' }, { variant: 'easy', value: 'nhớ', title: 'Nhớ', icon: 'fas fa-check-circle' }],
        4: [{ variant: 'again', value: 'again', title: 'Học lại', icon: 'fas fa-undo' }, { variant: 'very-hard', value: 'hard', title: 'Khó', icon: 'fas fa-fire' }, { variant: 'good', value: 'good', title: 'Bình thường', icon: 'fas fa-thumbs-up' }, { variant: 'easy', value: 'easy', title: 'Dễ', icon: 'fas fa-smile' }],
        6: [{ variant: 'fail', value: 'fail', title: 'Rất khó', icon: 'fas fa-exclamation-circle' }, { variant: 'very-hard', value: 'very_hard', title: 'Khó', icon: 'fas fa-fire' }, { variant: 'hard', value: 'hard', title: 'Trung bình', icon: 'fas fa-adjust' }, { variant: 'medium', value: 'medium', title: 'Dễ', icon: 'fas fa-leaf' }, { variant: 'good', value: 'good', title: 'Rất dễ', icon: 'fas fa-thumbs-up' }, { variant: 'very-easy', value: 'very_easy', title: 'Dễ dàng', icon: 'fas fa-star' }]
    };
    const buttons = buttonSets[buttonCount] || buttonSets[3];
    return buttons.map(btn => `<button class="btn rating-btn rating-btn--${btn.variant}" data-answer="${btn.value}"><span class="rating-btn__icon"><i class="${btn.icon}"></i></span><span class="rating-btn__title">${btn.title}</span></button>`).join('');
}

function renderCard(data) {
    if (isAutoplaySession) cancelAutoplaySequence();
    const c = data.content, itemId = data.item_id, setId = data.container_id;
    const fTxt = formatTextForHtml(c.front || ''), bTxt = formatTextForHtml(c.back || '');
    const initialStats = data.initial_stats || {};
    const cardCategory = determineCardCategory(data);
    const showPreviewOnly = shouldShowPreviewOnly(initialStats);
    const shouldRenderButtons = !isAutoplaySession && !showPreviewOnly;
    const buttonsHtml = showPreviewOnly ? getPreviewButtonHtml() : (shouldRenderButtons ? generateDynamicButtons(userButtonCount) : '');
    const buttonCount = showPreviewOnly ? 1 : (shouldRenderButtons ? userButtonCount : 0);
    const hasFrontAudio = c.front_audio_url || c.front_audio_content, hasBackAudio = c.back_audio_url || c.back_audio_content;
    const canEditCurrentCard = Boolean(data.can_edit);
    let editUrl = canEditCurrentCard ? editUrlTemplate.replace('/EDIT_SET_ID/', '/' + setId).replace('/EDIT_ITEM_ID/', '/' + itemId) : "";

    const renderOptions = {
        itemId, setId, fTxt, bTxt, cardCategory, isMediaHidden, isAudioAutoplayEnabled,
        hasFrontAudio, hasBackAudio, buttonsHtml, buttonCount, frontImg: c.front_img, backImg: c.back_img,
        frontAudioUrl: c.front_audio_url, backAudioUrl: c.back_audio_url, frontAudioContent: c.front_audio_content,
        backAudioContent: c.back_audio_content, canEditCurrentCard, editUrl
    };

    let desktopHtml = window.renderDesktopCardHtml ? window.renderDesktopCardHtml(data, renderOptions) : "";
    let mobileHtml = window.renderMobileCardHtml ? window.renderMobileCardHtml(data, renderOptions) : "";

    if (!desktopHtml && !mobileHtml) return;
    setFlashcardContent(desktopHtml, mobileHtml);
    updateAudioAutoplayToggleButtons();
    closeAllSettingsMenus();

    if (Array.isArray(currentFlashcardBatch) && currentFlashcardBatch[currentFlashcardIndex]) {
        currentFlashcardBatch[currentFlashcardIndex].card_category = cardCategory;
    }

    const visibleContainer = getVisibleFlashcardContentDiv();
    const card = visibleContainer ? visibleContainer.querySelector('.js-flashcard-card') : document.querySelector('.js-flashcard-card');
    const actions = visibleContainer ? visibleContainer.querySelector('.js-internal-actions') : document.querySelector('.js-internal-actions');
    const flipBtn = visibleContainer ? visibleContainer.querySelector('.js-flip-card-btn') : document.querySelector('.js-flip-card-btn');
    currentCardElements = { card, actions, flipBtn };

    if (window.flashcardViewport && typeof window.flashcardViewport.refresh === 'function') window.flashcardViewport.refresh();
    setupAudioErrorHandler(itemId, c.front_audio_content || '', c.back_audio_content || '');
    if (card) card.dataset.cardCategory = cardCategory || 'default';

    const flipToBack = () => {
        stopAllFlashcardAudio();
        card.classList.add('flipped');
        actions?.classList.add('visible');
        if (flipBtn) flipBtn.style.display = 'none';
        setTimeout(adjustCardLayout, 0);
        if (!isAutoplaySession) setTimeout(autoPlayBackSide, 50);
    };

    const flipToFront = () => {
        stopAllFlashcardAudio();
        card.classList.remove('flipped');
        actions?.classList.remove('visible');
        if (flipBtn) flipBtn.style.display = '';
        setTimeout(adjustCardLayout, 0);
        if (!isAutoplaySession) setTimeout(autoPlayFrontSide, 50);
    };

    if (flipBtn) flipBtn.addEventListener('click', (ev) => { ev.stopPropagation(); flipToBack(); });
    const frontLabel = card?.querySelector('.front .card-toolbar .label'), backLabel = card?.querySelector('.back .card-toolbar .label');
    if (frontLabel) frontLabel.addEventListener('click', (ev) => { ev.stopPropagation(); flipToBack(); });
    if (backLabel) backLabel.addEventListener('click', (ev) => { ev.stopPropagation(); flipToFront(); });

    document.querySelectorAll('.card-toolbar .icon-btn').forEach(btn => {
        btn.addEventListener('click', ev => {
            if (btn.classList.contains('settings-toggle-btn') || btn.classList.contains('audio-autoplay-toggle-btn')) return;
            ev.stopPropagation();
        });
    });

    document.querySelectorAll('.image-toggle-btn').forEach(btn => { btn.addEventListener('click', ev => { ev.stopPropagation(); setMediaHiddenState(!isMediaHidden); }); });
    if (!isAutoplaySession) {
        document.querySelectorAll('.actions .btn').forEach(b => b.addEventListener('click', ev => { ev.stopPropagation(); submitFlashcardAnswer(data.item_id, b.dataset.answer); }));
    }

    document.querySelectorAll('.play-audio-btn').forEach(btn => {
        btn.addEventListener('click', (ev) => {
            ev.stopPropagation();
            const audioSelector = btn.dataset.audioTarget;
            const cardEl = btn.closest('.js-flashcard-card');
            const audioPlayer = cardEl ? cardEl.querySelector(audioSelector) : document.querySelector(audioSelector);
            if (!audioPlayer || btn.classList.contains('is-disabled')) return;
            if (!audioPlayer.paused && audioPlayer.currentTime > 0) { audioPlayer.pause(); audioPlayer.currentTime = 0; return; }
            playAudioForButton(btn).catch(() => { });
        });
    });

    document.querySelectorAll('.open-stats-modal-btn').forEach(btn => btn.addEventListener('click', () => toggleStatsModal(true)));
    document.querySelectorAll('.open-ai-modal-btn').forEach(btn => btn.addEventListener('click', () => {
        const currentCard = currentFlashcardBatch[currentFlashcardIndex];
        window.openAiModal(currentCard.item_id, currentCard.content.front);
    }));
    document.querySelectorAll('.open-note-panel-btn').forEach(btn => btn.addEventListener('click', () => { openNotePanel(btn.dataset.itemId); }));
    document.querySelectorAll('.open-feedback-modal-btn').forEach(btn => btn.addEventListener('click', () => {
        const currentCard = currentFlashcardBatch[currentFlashcardIndex];
        openFeedbackModal(currentCard.item_id, currentCard.content.front);
    }));

    applyMediaVisibility();
    setTimeout(adjustCardLayout, 0);
    if (isAutoplaySession) startAutoplaySequence(); else autoPlayFrontSide();
}

async function updateFlashcardCard(itemId, setId) {
    const apiUrl = flashcardItemApiUrlTemplate.replace('/0', `/${itemId}`);
    try {
        const response = await fetch(apiUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        const payload = await response.json();
        if (!response.ok || !payload.success) throw new Error(payload.message || 'Error');
        const updatedItem = payload.item;
        const targetIndex = currentFlashcardBatch.findIndex(card => Number(card.item_id) === Number(updatedItem.item_id));
        if (targetIndex !== -1) {
            currentFlashcardBatch[targetIndex] = updatedItem;
            if (targetIndex === currentFlashcardIndex) {
                stopAllFlashcardAudio();
                renderCard(updatedItem);
                displayCardStats(currentCardStatsContainer, renderCardStatsHtml(updatedItem.initial_stats, 0, updatedItem.content, true));
            }
        }
        return updatedItem;
    } catch (error) { console.error(error); throw error; }
}
window.updateFlashcardCard = updateFlashcardCard;

async function getNextFlashcardBatch() {
    stopAllFlashcardAudio();
    setFlashcardContent(`<div class="flex flex-col items-center justify-center h-full text-blue-500 min-h-[300px]"><i class="fas fa-spinner fa-spin text-4xl mb-3"></i><p>Đang tải thẻ...</p></div>`);
    try {
        const res = await fetch(getFlashcardBatchUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        if (!res.ok) {
            if (res.status === 404) {
                const end = await res.json();
                if (isAutoplaySession) cancelAutoplaySequence();
                setFlashcardContent(`<div class="text-center py-12 text-gray-600"><i class="fas fa-check-circle text-5xl text-green-500 mb-4"></i><h3 class="text-xl font-semibold text-gray-700 mb-2">Hoàn thành phiên học!</h3><p class="text-gray-500">${formatTextForHtml(end.message)}</p><button id="return-to-dashboard-btn" class="mt-6 px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 shadow-sm"><i class="fas fa-home mr-2"></i> Quay lại Dashboard</button></div>`);
                document.getElementById('return-to-dashboard-btn').addEventListener('click', () => { window.location.href = dashboardUrl; });
                return;
            }
            throw new Error('HTTP ' + res.status);
        }
        const batch = await res.json();
        currentFlashcardBatch = batch.items;
        currentFlashcardIndex = 0;
        const currentCardData = currentFlashcardBatch[currentFlashcardIndex];
        displayCardStats(currentCardStatsContainer, renderCardStatsHtml(currentCardData.initial_stats, 0, currentCardData.content, true));
        const mobileCurrent = document.getElementById('current-card-stats-mobile');
        if (mobileCurrent) mobileCurrent.innerHTML = renderMobileCardStatsHtml(currentCardData.initial_stats, 0, currentCardData.content, true);
        renderCard(currentCardData);
        updateSessionSummary();
        sessionStatsLocal.processed = batch.session_processed_count || 1;
        sessionStatsLocal.total = batch.session_total_items || batch.total_items_in_session || 0;
        sessionStatsLocal.correct = batch.session_correct_answers || 0;
        sessionStatsLocal.incorrect = batch.session_incorrect_answers || 0;
        sessionStatsLocal.vague = batch.session_vague_answers || 0;
        if (batch.container_name) document.querySelectorAll('.js-fc-title').forEach(el => { el.textContent = batch.container_name; });
        window.flashcardSessionStats = { progress: sessionStatsLocal.processed + '/' + sessionStatsLocal.total, ...sessionStatsLocal };
        document.dispatchEvent(new CustomEvent('flashcardStatsUpdated', { detail: window.flashcardSessionStats }));
    } catch (e) { console.error(e); setFlashcardContent(`<p class='text-red-500 text-center'>Không thể tải thẻ. Vui lòng thử lại.</p>`); }
}

async function submitFlashcardAnswer(itemId, answer) {
    stopAllFlashcardAudio();
    try {
        const res = await fetch(submitAnswerUrl, { method: 'POST', headers: { 'Content-Type': 'application/json', ...csrfHeaders }, body: JSON.stringify({ item_id: itemId, user_answer: answer }) });
        const data = await res.json();
        if (!res.ok) throw new Error(data.message || 'Error');
        sessionScore += data.score_change;
        currentUserTotalScore = data.updated_total_score;
        const previousCardContent = currentFlashcardBatch[currentFlashcardIndex].content;
        sessionAnswerHistory.push({ front: previousCardContent.front, back: previousCardContent.back, answer, scoreChange: data.score_change, stats: data.statistics, timestamp: Date.now() });
        displayCardStats(previousCardStatsContainer, renderCardStatsHtml(data.statistics, data.score_change, previousCardContent, false));
        const mobilePrev = document.getElementById('previous-card-stats-mobile');
        if (mobilePrev) mobilePrev.innerHTML = renderMobileCardStatsHtml(data.statistics, data.score_change, previousCardContent, false);
        const prevTabButton = document.querySelector('.stats-tab-button[data-target="previous-card-stats-pane"]');
        if (prevTabButton) prevTabButton.click();
        const answerResult = data.answer_result || answer;
        if (['good', 'easy', 'very_easy', 'nhớ', 'medium'].includes(answerResult)) sessionStatsLocal.correct++;
        else if (['fail', 'again', 'quên'].includes(answerResult)) sessionStatsLocal.incorrect++;
        else sessionStatsLocal.vague++;
        sessionStatsLocal.processed++;
        window.flashcardSessionStats = { progress: sessionStatsLocal.processed + '/' + sessionStatsLocal.total, ...sessionStatsLocal };
        document.dispatchEvent(new CustomEvent('flashcardStatsUpdated', { detail: window.flashcardSessionStats }));
        currentFlashcardIndex++;
        getNextFlashcardBatch();
    } catch (e) { console.error(e); }
}
window.submitFlashcardAnswer = submitFlashcardAnswer;

function toggleStatsModal(show) {
    if (show) {
        statsModal.classList.add('open');
        statsModalContent.classList.add('open');
        document.body.style.overflow = 'hidden';
        if (!statsModalContent.querySelector('.mobile-stats-container')) {
            const template = document.getElementById('mobile-stats-template');
            if (template) {
                statsModalContent.innerHTML = '';
                statsModalContent.appendChild(template.content.cloneNode(true));
                document.getElementById('close-stats-mobile-btn')?.addEventListener('click', () => toggleStatsModal(false));
                document.getElementById('end-session-mobile-btn')?.addEventListener('click', () => endSessionBtn.click());
                document.querySelectorAll('.stats-mobile-tab').forEach(btn => btn.addEventListener('click', (e) => {
                    const targetId = e.currentTarget.dataset.target;
                    document.querySelectorAll('.stats-mobile-tab').forEach(t => t.classList.toggle('active', t === e.currentTarget));
                    document.querySelectorAll('.stats-mobile-pane').forEach(p => p.classList.toggle('hidden', p.id !== targetId));
                }));
            }
        }
        updateSessionSummary();
        const currentCardData = currentFlashcardBatch[currentFlashcardIndex];
        const mobileCurrent = document.getElementById('current-card-stats-mobile');
        if (mobileCurrent) mobileCurrent.innerHTML = currentCardData ? renderMobileCardStatsHtml(currentCardData.initial_stats, 0, currentCardData.content, true) : '';
        const mobilePrev = document.getElementById('previous-card-stats-mobile');
        if (mobilePrev && previousCardStats) mobilePrev.innerHTML = renderMobileCardStatsHtml(previousCardStats.stats, previousCardStats.scoreChange, previousCardStats.cardContent, false);
    } else {
        statsModal.classList.remove('open');
        statsModalContent.classList.remove('open');
        document.body.style.overflow = '';
    }
}

function handleTabClick(event) {
    const button = event.currentTarget || event.target.closest('.stats-tab-button');
    if (!button) return;
    const targetPaneId = button.dataset.target;
    const parentContainer = button.closest('.statistics-card');
    if (!parentContainer) return;
    parentContainer.querySelectorAll('.stats-tab-button').forEach(btn => btn.classList.remove('active'));
    button.classList.add('active');
    parentContainer.querySelectorAll('.stats-tab-pane').forEach(pane => pane.classList.toggle('active', pane.id === targetPaneId));
    initializeStatsToggleListeners(parentContainer);
}

function determineCardCategory(cardData) {
    if (!cardData) return '';
    const stats = cardData.initial_stats || {};
    if (!stats.has_preview_history && !stats.has_real_reviews) return 'new';
    if (stats.status === 'hard') return 'hard';
    if (stats.has_preview_only) return 'due';
    if (stats.next_review) {
        const dueDate = new Date(stats.next_review);
        if (!Number.isNaN(dueDate.getTime()) && dueDate <= new Date()) return 'due';
    }
    return '';
}

function shouldShowPreviewOnly(initialStats = {}) {
    if (initialStats.has_real_reviews) return false;
    if (initialStats.has_preview_history && (initialStats.preview_count ?? 0) > 0) return false;
    return (initialStats.preview_count ?? 0) === 0;
}
