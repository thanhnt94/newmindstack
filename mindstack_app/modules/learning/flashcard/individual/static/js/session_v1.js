const setVh = () => {
  if (window.flashcardViewport && typeof window.flashcardViewport.refresh === 'function') {
    window.flashcardViewport.refresh();
  }

  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
};

if (window.flashcardViewport && typeof window.flashcardViewport.refresh === 'function') {
  window.flashcardViewport.refresh();
}

let currentFlashcardBatch = [];
let currentFlashcardIndex = 0;
let previousCardStats = null;

let sessionScore = 0;
let currentUserTotalScore = window.FC.userTotalScore;

// End session button
const endSessionBtn = document.getElementById('end-session-btn');

// Helper function để sync nội dung giữa desktop và mobile (dùng shared classes)
function setFlashcardContent(html) {
  document.querySelectorAll('.js-flashcard-content').forEach(el => {
    el.innerHTML = html;
  });
}

// Helper function để lấy element hiển thị hiện tại (desktop hoặc mobile)
function getVisibleFlashcardContentDiv() {
  // Return first visible .js-flashcard-content element
  const allContentDivs = document.querySelectorAll('.js-flashcard-content');
  for (const div of allContentDivs) {
    if (div.offsetParent !== null) return div;
  }
  return allContentDivs[0] || null;
}

const currentCardStatsContainer = document.getElementById('current-card-stats');
const previousCardStatsContainer = document.getElementById('previous-card-stats');

const endSessionModal = document.getElementById('endSessionModal');
const confirmEndSessionBtn = document.getElementById('confirmEndSessionBtn');
const cancelEndSessionBtn = document.getElementById('cancelEndSessionBtn');

const statsModal = document.getElementById('statsModal');
const statsModalContent = document.getElementById('statsModalContent');
const closeStatsModalBtn = document.getElementById('closeStatsModalBtn');
const statsModalBody = document.getElementById('statsModalBody');

const getFlashcardBatchUrl = window.FC.urls.getFlashcardBatch;
const flashcardItemApiUrlTemplate = window.FC.urls.flashcardItemApi;
const submitAnswerUrl = window.FC.urls.submitAnswer;
const endSessionUrl = window.FC.urls.endSession;
const regenerateAudioUrl = window.FC.urls.regenerateAudio;
const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
const csrfToken = csrfTokenMeta ? csrfTokenMeta.getAttribute('content') : '';
const csrfHeaders = csrfToken ? { 'X-CSRFToken': csrfToken } : {};
const userButtonCount = window.FC.buttonCount;
const isAutoplaySession = window.FC.isAutoplay;
const autoplayMode = window.FC.autoplayMode;
let autoplayDelaySeconds = 2;
let currentAutoplayToken = 0;
let currentAutoplayTimeouts = [];
let currentCardElements = { card: null, actions: null, flipBtn: null };
let isMediaHidden = false;
let isAudioAutoplayEnabled = true;
let storedAudioAutoplay = null;

try {
  const storedImageVisibility = localStorage.getItem('flashcardHideImages');
  if (storedImageVisibility === 'true') {
    isMediaHidden = true;
  }
  storedAudioAutoplay = localStorage.getItem('flashcardAutoPlayAudio');
} catch (err) {
  console.warn('Không thể đọc trạng thái hiển thị ảnh:', err);
}

if (storedAudioAutoplay === 'false') {
  isAudioAutoplayEnabled = false;
}

if (isAutoplaySession) {
  try {
    const storedSettings = localStorage.getItem('flashcardAutoplaySettings');
    if (storedSettings) {
      const parsedSettings = JSON.parse(storedSettings);
      if (parsedSettings && typeof parsedSettings.delaySeconds === 'number' && parsedSettings.delaySeconds >= 0) {
        autoplayDelaySeconds = parsedSettings.delaySeconds;
      }
    }
  } catch (err) {
    console.warn('Không thể đọc cấu hình AutoPlay:', err);
  }
  document.body.classList.add('flashcard-autoplay-active');
}

const getNoteUrl = window.FC.urls.getNote;
const saveNoteUrl = window.FC.urls.saveNote;

function formatTextForHtml(text) {
  if (text == null) return '';
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML.replace(/\r?\n/g, '<br>');
}

function extractPlainText(text) {
  if (text == null) return '';
  if (typeof text !== 'string') {
    text = String(text);
  }
  const temp = document.createElement('div');
  temp.innerHTML = text;
  const plain = temp.textContent || temp.innerText || '';
  return plain.trim();
}

function applyMediaVisibility() {
  // Select từ cả desktop và mobile elements
  const mediaContainers = document.querySelectorAll('#flashcard-content .media-container, #flashcard-content-mobile .media-container');
  const cardContainers = document.querySelectorAll('#flashcard-content ._card-container, #flashcard-content-mobile ._card-container');

  mediaContainers.forEach(container => {
    container.classList.toggle('hidden', isMediaHidden);
  });

  cardContainers.forEach(container => {
    container.classList.toggle('media-hidden', isMediaHidden);
  });

  document.querySelectorAll('.image-toggle-btn').forEach(btn => {
    btn.classList.toggle('is-active', isMediaHidden);
    btn.setAttribute('aria-pressed', isMediaHidden ? 'true' : 'false');
    btn.title = isMediaHidden ? 'Bật ảnh' : 'Tắt ảnh';
    const icon = btn.querySelector('i');
    if (icon) {
      icon.className = `fas ${isMediaHidden ? 'fa-image-slash' : 'fa-image'}`;
    }
  });

  if (window.flashcardViewport && typeof window.flashcardViewport.refresh === 'function') {
    window.flashcardViewport.refresh();
  }

  setTimeout(adjustCardLayout, 0);
}

function setMediaHiddenState(hidden) {
  isMediaHidden = hidden;

  try {
    localStorage.setItem('flashcardHideImages', hidden ? 'true' : 'false');
  } catch (err) {
    console.warn('Không thể lưu trạng thái hiển thị ảnh:', err);
  }

  applyMediaVisibility();
}

function persistAudioAutoplayPreference(enabled) {
  try {
    localStorage.setItem('flashcardAutoPlayAudio', enabled ? 'true' : 'false');
  } catch (err) {
    console.warn('Không thể lưu cấu hình tự động phát audio:', err);
  }
}

function updateAudioAutoplayToggleButtons() {
  document.querySelectorAll('.audio-autoplay-toggle-btn').forEach((btn) => {
    btn.classList.toggle('is-active', isAudioAutoplayEnabled);
    btn.setAttribute('aria-pressed', isAudioAutoplayEnabled ? 'true' : 'false');
    btn.title = isAudioAutoplayEnabled ? 'Tắt tự động phát audio' : 'Bật tự động phát audio';
    const icon = btn.querySelector('i');
    if (icon) {
      icon.className = `fas ${isAudioAutoplayEnabled ? 'fa-volume-up' : 'fa-volume-mute'}`;
    }
  });
}

function setAudioAutoplayEnabled(enabled) {
  isAudioAutoplayEnabled = enabled;
  persistAudioAutoplayPreference(enabled);
  updateAudioAutoplayToggleButtons();
  if (!enabled) {
    stopAllFlashcardAudio();
  }
}

function closeAllSettingsMenus() {
  document.querySelectorAll('.toolbar-settings').forEach((menu) => {
    menu.classList.remove('is-open');
    const toggleBtn = menu.querySelector('.settings-toggle-btn');
    if (toggleBtn) {
      toggleBtn.setAttribute('aria-expanded', 'false');
    }
  });
}

function toggleSettingsMenu(menuEl) {
  if (!menuEl) return;
  const isOpen = menuEl.classList.contains('is-open');
  closeAllSettingsMenus();
  menuEl.classList.toggle('is-open', !isOpen);
  const toggleBtn = menuEl.querySelector('.settings-toggle-btn');
  if (toggleBtn) {
    toggleBtn.setAttribute('aria-expanded', (!isOpen).toString());
  }
}

document.addEventListener('click', (evt) => {
  const settingsToggle = evt.target.closest('.settings-toggle-btn');
  if (settingsToggle) {
    evt.stopPropagation();
    toggleSettingsMenu(settingsToggle.closest('.toolbar-settings'));
    return;
  }

  const autoplayToggle = evt.target.closest('.audio-autoplay-toggle-btn');
  if (autoplayToggle) {
    evt.stopPropagation();
    setAudioAutoplayEnabled(!isAudioAutoplayEnabled);
    return;
  }

  if (!evt.target.closest('.toolbar-settings')) {
    closeAllSettingsMenus();
  }
});

function playAudioAfterLoad(audioPlayer, { restart = true, awaitCompletion = false } = {}) {
  return new Promise(resolve => {
    if (!audioPlayer) {
      resolve();
      return;
    }

    const cleanup = () => {
      audioPlayer.removeEventListener('canplay', onCanPlay);
      if (awaitCompletion) {
        audioPlayer.removeEventListener('ended', onEnded);
        audioPlayer.removeEventListener('error', onError);
      }
    };

    const onEnded = () => {
      cleanup();
      resolve();
    };

    const onError = () => {
      cleanup();
      resolve();
    };

    const onCanPlay = () => {
      audioPlayer.removeEventListener('canplay', onCanPlay);
      if (restart) {
        try {
          audioPlayer.pause();
          audioPlayer.currentTime = 0;
        } catch (err) {
          console.warn('Không thể đặt lại audio:', err);
        }
      }
      const playPromise = audioPlayer.play();
      if (!awaitCompletion) {
        cleanup();
        if (playPromise && typeof playPromise.catch === 'function') {
          playPromise.catch(() => { });
        }
        resolve();
      } else if (playPromise && typeof playPromise.catch === 'function') {
        playPromise.catch(() => {
          cleanup();
          resolve();
        });
      }
    };

    if (awaitCompletion) {
      audioPlayer.addEventListener('ended', onEnded, { once: true });
      audioPlayer.addEventListener('error', onError, { once: true });
    }

    if (audioPlayer.readyState >= 2) {
      onCanPlay();
    } else {
      audioPlayer.addEventListener('canplay', onCanPlay);
      try {
        audioPlayer.load();
      } catch (err) {
        cleanup();
        resolve();
      }
    }
  });
}

function stopAllFlashcardAudio(exceptAudio = null) {
  const audioElements = document.querySelectorAll('#flashcard-content audio');
  audioElements.forEach(audioEl => {
    if (exceptAudio && audioEl === exceptAudio) {
      return;
    }
    try {
      if (!audioEl.paused) {
        audioEl.pause();
      }
      audioEl.currentTime = 0;
    } catch (err) {
      console.warn('Không thể dừng audio:', err);
    }
  });
}

function playAudioForButton(button, options = {}) {
  if (!button) return Promise.resolve();
  const audioPlayer = document.querySelector(button.dataset.audioTarget);
  if (!audioPlayer || button.classList.contains('is-disabled')) {
    return Promise.resolve();
  }

  const awaitCompletion = options.await === true;
  const restart = options.restart !== false;
  const suppressLoadingUi = options.suppressLoadingUi === true;
  const hasAudioSource = audioPlayer.src && audioPlayer.src !== window.location.href;

  if (hasAudioSource) {
    stopAllFlashcardAudio(audioPlayer);
    return playAudioAfterLoad(audioPlayer, { restart, awaitCompletion });
  }

  stopAllFlashcardAudio(audioPlayer);
  return generateAndPlayAudio(button, audioPlayer, { awaitCompletion, suppressLoadingUi, restart });
}

function autoPlaySide(side) {
  if (!isAudioAutoplayEnabled) return;
  const button = document.querySelector(`.play-audio-btn[data-side="${side}"]`);
  if (!button) return;
  playAudioForButton(button, { suppressLoadingUi: true }).catch(() => { });
}

function autoPlayFrontSide() {
  autoPlaySide('front');
}

function autoPlayBackSide() {
  autoPlaySide('back');
}

function cancelAutoplaySequence() {
  currentAutoplayToken += 1;
  currentAutoplayTimeouts.forEach(timeoutId => clearTimeout(timeoutId));
  currentAutoplayTimeouts = [];
  stopAllFlashcardAudio();
}

function waitForAutoplayDelay(token) {
  return new Promise(resolve => {
    const delayMs = Math.max(0, autoplayDelaySeconds) * 1000;
    if (delayMs === 0) {
      resolve();
      return;
    }
    const timeoutId = setTimeout(() => {
      currentAutoplayTimeouts = currentAutoplayTimeouts.filter(id => id !== timeoutId);
      if (token === currentAutoplayToken) {
        resolve();
      }
    }, delayMs);
    currentAutoplayTimeouts.push(timeoutId);
  });
}

async function playAutoplayAudioForSide(side, token) {
  if (token !== currentAutoplayToken) return;
  const button = document.querySelector(`.play-audio-btn[data-side="${side}"]`);
  if (!button) return;
  try {
    await playAudioForButton(button, { await: true, suppressLoadingUi: true });
  } catch (err) {
    console.warn('Không thể phát audio tự động:', err);
  }
}

function revealBackSideForAutoplay(token) {
  if (token !== currentAutoplayToken) return;
  const { card, actions, flipBtn } = currentCardElements;
  if (!card) return;
  if (!card.classList.contains('flipped')) {
    stopAllFlashcardAudio();
    card.classList.add('flipped');
    actions?.classList.add('visible');
    if (flipBtn) {
      flipBtn.style.display = 'none';
    }
    setTimeout(adjustCardLayout, 0);
  } else if (actions) {
    actions.classList.add('visible');
  }
}

async function startAutoplaySequence() {
  cancelAutoplaySequence();
  const token = currentAutoplayToken;
  try {
    await playAutoplayAudioForSide('front', token);
    if (token !== currentAutoplayToken) return;
    await waitForAutoplayDelay(token);
    if (token !== currentAutoplayToken) return;
    revealBackSideForAutoplay(token);
    await playAutoplayAudioForSide('back', token);
    if (token !== currentAutoplayToken) return;
    await waitForAutoplayDelay(token);
    if (token !== currentAutoplayToken) return;
    getNextFlashcardBatch();
  } catch (err) {
    console.warn('AutoPlay gặp lỗi:', err);
  }
}

function shouldShowPreviewOnly(initialStats = {}) {
  const hasRealReviews = Boolean(initialStats.has_real_reviews);
  if (hasRealReviews) return false;

  const previewCount = initialStats.preview_count ?? 0;
  const hasPreviewHistory = Boolean(initialStats.has_preview_history);

  if (hasPreviewHistory && previewCount > 0) {
    return false;
  }

  return previewCount === 0;
}

function determineCardCategory(cardData) {
  if (!cardData) return '';

  const stats = cardData.initial_stats || {};
  const hasPreviewHistory = Boolean(stats.has_preview_history);
  const hasRealReviews = Boolean(stats.has_real_reviews);

  if (!hasPreviewHistory && !hasRealReviews) {
    return 'new';
  }

  if (stats.status === 'hard') {
    return 'hard';
  }

  if (stats.has_preview_only) {
    return 'due';
  }

  if (stats.next_review) {
    const dueDate = new Date(stats.next_review);
    if (!Number.isNaN(dueDate.getTime()) && dueDate <= new Date()) {
      return 'due';
    }
  }

  return '';
}

function getPreviewButtonHtml() {
  return '<button class="btn btn-continue" data-answer="continue"><i class="fas fa-arrow-right"></i>Tiếp tục</button>';
}

function updateSessionSummary() {
  const desktopTotalScore = document.querySelector('.statistics-card #total-score-display span');
  const desktopSessionScore = document.querySelector('.statistics-card #session-score-display');

  const mobileTotalScore = document.getElementById('total-score-display-mobile');
  const mobileSessionScore = document.getElementById('session-score-display-mobile');

  if (desktopTotalScore) desktopTotalScore.textContent = currentUserTotalScore;
  if (desktopSessionScore) desktopSessionScore.textContent = `+${sessionScore}`;

  if (mobileTotalScore) mobileTotalScore.textContent = currentUserTotalScore;
  if (mobileSessionScore) mobileSessionScore.textContent = `+${sessionScore}`;
}

/**
 * Tự động điều chỉnh kích thước font và căn chỉnh nội dung mặt sau thẻ.
 * Áp dụng căn giữa khi không có cuộn, và căn trên khi có cuộn.
 */
function adjustCardLayout() {
  // Điều chỉnh layout cho tất cả card elements (cả desktop và mobile)
  document.querySelectorAll('.js-flashcard-card').forEach(card => {
    if (!card) return;

    const textAreas = card.querySelectorAll('.text-area');

    textAreas.forEach(scrollArea => {
      const txt = scrollArea.querySelector('.flashcard-content-text');
      if (!txt) return;

      // Reset style
      txt.style.fontSize = '';
      scrollArea.classList.remove('has-scroll');
      scrollArea.parentElement?.classList?.remove('has-scroll');

      // Đợi DOM render xong rồi đo
      setTimeout(() => {
        const hasScroll = scrollArea.scrollHeight > scrollArea.clientHeight;

        if (hasScroll) {
          // Ghim lên trên: set class cho cả text-area và container
          scrollArea.classList.add('has-scroll');
          scrollArea.parentElement?.classList?.add('has-scroll');

          // Đảm bảo nhìn thấy từ đầu nội dung
          scrollArea.scrollTop = 0;
        }

        // Thu nhỏ font nếu vẫn tràn
        let current = parseFloat(getComputedStyle(txt).fontSize) || 22;
        const min = 18;
        while (scrollArea.scrollHeight > scrollArea.clientHeight && current > min) {
          current -= 1;
          txt.style.fontSize = current + 'px';
        }
      }, 0);
    });
  });
}

function shouldShowPreviewOnly(initialStats = {}) {
  const hasRealReviews = Boolean(initialStats.has_real_reviews);
  if (hasRealReviews) return false;

  const previewCount = initialStats.preview_count ?? 0;
  const hasPreviewHistory = Boolean(initialStats.has_preview_history);

  if (hasPreviewHistory && previewCount > 0) {
    return false;
  }

  return previewCount === 0;
}

function determineCardCategory(cardData) {
  if (!cardData) return '';

  const stats = cardData.initial_stats || {};
  const hasPreviewHistory = Boolean(stats.has_preview_history);
  const hasRealReviews = Boolean(stats.has_real_reviews);

  if (!hasPreviewHistory && !hasRealReviews) {
    return 'new';
  }

  if (stats.status === 'hard') {
    return 'hard';
  }

  if (stats.has_preview_only) {
    return 'due';
  }

  if (stats.next_review) {
    const dueDate = new Date(stats.next_review);
    if (!Number.isNaN(dueDate.getTime()) && dueDate <= new Date()) {
      return 'due';
    }
  }

  return '';
}

function getPreviewButtonHtml() {
  return '<button class="btn btn-continue" data-answer="continue"><i class="fas fa-arrow-right"></i>Tiếp tục</button>';
}

function generateDynamicButtons(buttonCount) {
  const buttonSets = {
    3: [
      { variant: 'again', value: 'quên', title: 'Quên', icon: 'fas fa-redo-alt' },
      { variant: 'hard', value: 'mơ_hồ', title: 'Mơ hồ', icon: 'fas fa-question-circle' },
      { variant: 'easy', value: 'nhớ', title: 'Nhớ', icon: 'fas fa-check-circle' }
    ],
    4: [
      { variant: 'again', value: 'again', title: 'Học lại', icon: 'fas fa-undo' },
      { variant: 'very-hard', value: 'hard', title: 'Khó', icon: 'fas fa-fire' },
      { variant: 'good', value: 'good', title: 'Bình thường', icon: 'fas fa-thumbs-up' },
      { variant: 'easy', value: 'easy', title: 'Dễ', icon: 'fas fa-smile' }
    ],
    6: [
      { variant: 'fail', value: 'fail', title: 'Rất khó', icon: 'fas fa-exclamation-circle' },
      { variant: 'very-hard', value: 'very_hard', title: 'Khó', icon: 'fas fa-fire' },
      { variant: 'hard', value: 'hard', title: 'Trung bình', icon: 'fas fa-adjust' },
      { variant: 'medium', value: 'medium', title: 'Dễ', icon: 'fas fa-leaf' },
      { variant: 'good', value: 'good', title: 'Rất dễ', icon: 'fas fa-thumbs-up' },
      { variant: 'very-easy', value: 'very_easy', title: 'Dễ dàng', icon: 'fas fa-star' }
    ]
  };
  const buttons = buttonSets[buttonCount] || buttonSets[3];
  return buttons.map(btn => {
    const iconHtml = btn.icon ? `<span class="rating-btn__icon"><i class="${btn.icon}"></i></span>` : '';
    return `<button class="btn rating-btn rating-btn--${btn.variant}" data-answer="${btn.value}">${iconHtml}<span class="rating-btn__title">${btn.title}</span></button>`;
  }).join('');
}

// Hàm renderCard đã được làm mới để sử dụng logic tách biệt
function renderCard(data) {
  if (isAutoplaySession) {
    cancelAutoplaySequence();
  }
  const c = data.content;
  const itemId = data.item_id;
  const setId = data.container_id;
  const fTxt = formatTextForHtml(c.front || '');
  const bTxt = formatTextForHtml(c.back || '');
  const initialStats = data.initial_stats || {};
  const cardCategory = determineCardCategory(data);
  const showPreviewOnly = shouldShowPreviewOnly(initialStats);
  const shouldRenderButtons = !isAutoplaySession && !showPreviewOnly;
  const buttonsHtml = showPreviewOnly ? getPreviewButtonHtml() : (shouldRenderButtons ? generateDynamicButtons(userButtonCount) : '');
  const buttonCount = showPreviewOnly ? 1 : (shouldRenderButtons ? userButtonCount : 0);

  // Check view mode
  const isMobile = window.innerWidth < 1024;

  // Prepare options common for both views
  const hasFrontAudio = c.front_audio_url || c.front_audio_content;
  const hasBackAudio = c.back_audio_url || c.back_audio_content;
  const canEditCurrentCard = Boolean(data.can_edit);

  // Construct Edit URL
  let editUrl = "";
  if (canEditCurrentCard) {
    const urlTemplate = "{{ url_for('content_management.content_management_flashcards.edit_flashcard_item', set_id=0, item_id=0) }}";
    editUrl = urlTemplate.replace('/0', '/' + setId).replace('/0', '/' + itemId);
  }

  const renderOptions = {
    itemId, setId, fTxt, bTxt, cardCategory,
    isMediaHidden, isAudioAutoplayEnabled,
    hasFrontAudio, hasBackAudio,
    buttonsHtml, buttonCount,
    frontImg: c.front_img,
    backImg: c.back_img,
    frontAudioUrl: c.front_audio_url,
    backAudioUrl: c.back_audio_url,
    frontAudioContent: c.front_audio_content,
    backAudioContent: c.back_audio_content,
    canEditCurrentCard,
    editUrl
  };

  let html = "";
  if (isMobile && window.renderMobileCardHtml) {
    html = window.renderMobileCardHtml(data, renderOptions);
  } else if (!isMobile && window.renderDesktopCardHtml) {
    html = window.renderDesktopCardHtml(data, renderOptions);
  } else {
    // Fallback if partials not loaded for some reason (should not happen)
    console.error("Render functions not found!");
    return;
  }

  setFlashcardContent(html);
  updateAudioAutoplayToggleButtons();
  closeAllSettingsMenus();

  if (Array.isArray(currentFlashcardBatch) && currentFlashcardBatch[currentFlashcardIndex]) {
    currentFlashcardBatch[currentFlashcardIndex].card_category = cardCategory;
  }

  // Tìm elements dùng shared .js- classes
  const visibleContainer = getVisibleFlashcardContentDiv();
  const card = visibleContainer ? visibleContainer.querySelector('.js-flashcard-card') : document.querySelector('.js-flashcard-card');
  const actions = visibleContainer ? visibleContainer.querySelector('.js-internal-actions') : document.querySelector('.js-internal-actions');
  const flipBtn = visibleContainer ? visibleContainer.querySelector('.js-flip-card-btn') : document.querySelector('.js-flip-card-btn');
  currentCardElements = { card, actions, flipBtn };

  if (window.flashcardViewport && typeof window.flashcardViewport.refresh === 'function') {
    window.flashcardViewport.refresh();
  }

  // --- Xử lý tự động tái tạo audio khi lỗi ---
  async function handleAudioError(audioEl, itemId, side, contentToRead) {
    if (!audioEl || audioEl.dataset.retried === 'true') return;
    if (!contentToRead) return;

    console.log(`[AudioRecovery] Phát hiện lỗi ở ${side} audio. Đang thử tái tạo...`);
    audioEl.dataset.retried = 'true';

    try {
      const response = await fetch(regenerateAudioUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...csrfHeaders },
        body: JSON.stringify({ item_id: itemId, side: side, content_to_read: contentToRead })
      });
      const result = await response.json();

      if (result.success && result.audio_url) {
        console.log(`[AudioRecovery] Tái tạo thành công. URL mới: ${result.audio_url}`);
        audioEl.src = `${result.audio_url}?t=${new Date().getTime()}`;
      } else {
        console.warn(`[AudioRecovery] Tái tạo thất bại: ${result.message}`);
      }
    } catch (err) {
      console.error(`[AudioRecovery] Lỗi kết nối API:`, err);
    }
  }

  function setupAudioErrorHandler(itemId, frontContent, backContent) {
    const frontAudio = document.getElementById('front-audio');
    const backAudio = document.getElementById('back-audio');
    if (frontAudio) {
      frontAudio.addEventListener('error', () => handleAudioError(frontAudio, itemId, 'front', frontContent));
    }
    if (backAudio) {
      backAudio.addEventListener('error', () => handleAudioError(backAudio, itemId, 'back', backContent));
    }
  }

  if (card) {
    card.dataset.cardCategory = cardCategory || 'default';
  }

  setupAudioErrorHandler(itemId, c.front_audio_content || '', c.back_audio_content || '');

  const flipToBack = () => {
    stopAllFlashcardAudio();
    card.classList.add('flipped');
    actions?.classList.add('visible');
    if (flipBtn) {
      flipBtn.style.display = 'none';
    }
    setTimeout(adjustCardLayout, 0);
    if (!isAutoplaySession) {
      autoPlayBackSide();
    }
  };

  const flipToFront = () => {
    stopAllFlashcardAudio();
    card.classList.remove('flipped');
    actions?.classList.remove('visible');
    if (flipBtn) {
      flipBtn.style.display = '';
    }
    setTimeout(adjustCardLayout, 0);
  };

  if (flipBtn) {
    flipBtn.addEventListener('click', (ev) => {
      ev.stopPropagation();
      flipToBack();
    });
  }

  const frontLabel = card?.querySelector('.front .card-toolbar .label');
  const backLabel = card?.querySelector('.back .card-toolbar .label');

  if (frontLabel) frontLabel.addEventListener('click', (ev) => { ev.stopPropagation(); flipToBack(); });
  if (backLabel) backLabel.addEventListener('click', (ev) => { ev.stopPropagation(); flipToFront(); });

  document.querySelectorAll('.card-toolbar .icon-btn').forEach(btn => {
    btn.addEventListener('click', ev => {
      if (btn.classList.contains('settings-toggle-btn') || btn.classList.contains('audio-autoplay-toggle-btn')) {
        return;
      }
      ev.stopPropagation();
    });
  });

  document.querySelectorAll('.image-toggle-btn').forEach(btn => {
    btn.addEventListener('click', ev => {
      ev.stopPropagation();
      setMediaHiddenState(!isMediaHidden);
    });
  });

  if (!isAutoplaySession) {
    document.querySelectorAll('.actions .btn').forEach(b => b.addEventListener('click', ev => {
      ev.stopPropagation();
      submitFlashcardAnswer(data.item_id, b.dataset.answer);
    }));
  }

  document.querySelectorAll('.play-audio-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const audioPlayer = document.querySelector(btn.dataset.audioTarget);
      if (!audioPlayer || btn.classList.contains('is-disabled')) return;
      if (!audioPlayer.paused && audioPlayer.currentTime > 0) {
        audioPlayer.pause();
        audioPlayer.currentTime = 0;
        return;
      }
      playAudioForButton(btn).catch(() => { });
    });
  });

  document.querySelectorAll('.open-stats-modal-btn').forEach(btn => btn.addEventListener('click', () => toggleStatsModal(true)));

  document.querySelectorAll('.open-ai-modal-btn').forEach(btn => btn.addEventListener('click', () => {
    const currentCard = currentFlashcardBatch[currentFlashcardIndex];
    window.openAiModal(currentCard.item_id, currentCard.content.front);
  }));

  document.querySelectorAll('.open-note-panel-btn').forEach(btn => btn.addEventListener('click', () => {
    openNotePanel(btn.dataset.itemId);
  }));

  document.querySelectorAll('.open-feedback-modal-btn').forEach(btn => btn.addEventListener('click', () => {
    const currentCard = currentFlashcardBatch[currentFlashcardIndex];
    openFeedbackModal(currentCard.item_id, currentCard.content.front);
  }));

  applyMediaVisibility();
  setTimeout(adjustCardLayout, 0);

  if (isAutoplaySession) {
    startAutoplaySequence();
  } else {
    autoPlayFrontSide();
  }
}

async function generateAndPlayAudio(button, audioPlayer, options = {}) {
  const itemId = button.dataset.itemId;
  const side = button.dataset.side;
  const contentToRead = button.dataset.contentToRead;
  const awaitCompletion = options.awaitCompletion === true;
  const suppressLoadingUi = options.suppressLoadingUi === true;
  const restart = options.restart !== false;

  const originalHtml = button.dataset.originalHtml || button.innerHTML;
  if (!button.dataset.originalHtml) {
    button.dataset.originalHtml = originalHtml;
  }

  if (!suppressLoadingUi) {
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  }

  button.classList.add('is-disabled');
  let playbackPromise = Promise.resolve();

  try {
    const response = await fetch(regenerateAudioUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...csrfHeaders },
      body: JSON.stringify({ item_id: itemId, side: side, content_to_read: contentToRead })
    });
    const result = await response.json();
    if (result.success && result.audio_url) {
      audioPlayer.src = result.audio_url;
      playbackPromise = playAudioAfterLoad(audioPlayer, { restart, awaitCompletion });
      if (awaitCompletion) {
        await playbackPromise;
      }
    } else {
      showCustomAlert(result.message || 'Lỗi khi tạo audio.');
    }
  } catch (error) {
    console.error('Lỗi khi tạo audio:', error);
    showCustomAlert('Không thể kết nối đến máy chủ để tạo audio.');
  } finally {
    button.classList.remove('is-disabled');
    if (!suppressLoadingUi) {
      button.innerHTML = button.dataset.originalHtml || '<i class="fas fa-volume-up"></i>';
    }
  }

  return playbackPromise;
}

function formatMinutesAsDuration(minutes) {
  if (minutes <= 0) return 'Dưới 1 phút';
  const M_IN_H = 60, M_IN_D = 1440, M_IN_W = 10080, M_IN_MO = 43200;
  let result = [], remainingMinutes = minutes;
  if (remainingMinutes >= M_IN_MO) { const m = Math.floor(remainingMinutes / M_IN_MO); result.push(`${m} tháng`); remainingMinutes %= M_IN_MO; }
  if (remainingMinutes >= M_IN_W) { const w = Math.floor(remainingMinutes / M_IN_W); result.push(`${w} tuần`); remainingMinutes %= M_IN_W; }
  if (remainingMinutes >= M_IN_D) { const d = Math.floor(remainingMinutes / M_IN_D); result.push(`${d} ngày`); remainingMinutes %= M_IN_D; }
  if (remainingMinutes >= M_IN_H) { const h = Math.floor(remainingMinutes / M_IN_H); result.push(`${h} giờ`); remainingMinutes %= M_IN_H; }
  if (remainingMinutes > 0) result.push(`${remainingMinutes} phút`);
  return result.join(' ');
}

function formatDateTime(value, fallback = 'Chưa có') {
  if (!value) return fallback;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return fallback;
  }
  try {
    return date.toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short' });
  } catch (err) {
    return fallback;
  }
}

function renderCardStatsHtml(stats, scoreChange = 0, cardContent = {}, isInitial = false) {
  if (!stats) {
    return `<div class="empty-state"><i class="fas fa-info-circle"></i> ${isInitial ? 'Đây là thẻ mới.' : 'Không có dữ liệu thống kê.'}</div>`;
  }

  const totalReviews = Number(stats.times_reviewed) || 0;
  const correctCount = Number(stats.correct_count) || 0;
  const incorrectCount = Number(stats.incorrect_count) || 0;
  const vagueCount = Number(stats.vague_count) || 0;
  const previewCount = Number(stats.preview_count) || 0;
  const correctWidth = totalReviews > 0 ? (correctCount / totalReviews) * 100 : 0;
  const vagueWidth = totalReviews > 0 ? (vagueCount / totalReviews) * 100 : 0;
  const incorrectWidth = totalReviews > 0 ? (incorrectCount / totalReviews) * 100 : 0;
  const correctPercentDisplay = Math.round(correctWidth);
  const vaguePercentDisplay = Math.round(vagueWidth);
  const incorrectPercentDisplay = Math.round(incorrectWidth);
  const dueTime = formatDateTime(stats.next_review, 'Chưa có');
  const lastReviewed = formatDateTime(stats.last_reviewed, totalReviews > 0 ? 'Chưa có' : 'Chưa ôn');
  const firstSeen = formatDateTime(stats.first_seen, 'Chưa mở');
  const formattedIntervalDisplay = formatMinutesAsDuration(stats.interval);
  const scoreChangeSign = scoreChange > 0 ? '+' : '';
  const scoreChangeClass = scoreChange > 0 ? 'positive' : (scoreChange < 0 ? 'negative' : '');
  const isBrandNew = !stats.has_preview_history && !stats.has_real_reviews;
  const isPreviewStage = stats.has_preview_history && !stats.has_real_reviews;
  const statusKeyRaw = (stats.status || 'new').toString();
  const statusKey = statusKeyRaw.toLowerCase().replace(/\s+/g, '-');
  const statusLabelMap = {
    'new': 'Mới',
    'learning': 'Đang học',
    'review': 'Ôn tập',
    'relearning': 'Ôn lại',
    'hard': 'Khó',
    'easy': 'Dễ',
    'suspended': 'Tạm dừng'
  };
  const statusLabel = statusLabelMap[statusKeyRaw.toLowerCase()] || statusKeyRaw;
  const correctRateDisplay = typeof stats.correct_rate === 'number' ? Math.round(stats.correct_rate) : correctPercentDisplay;
  const repetitions = Number(stats.repetitions) || 0;
  const easinessFactor = typeof stats.easiness_factor === 'number' ? Number(stats.easiness_factor).toFixed(2) : '—';
  const currentStreak = Number(stats.current_streak) || 0;
  const longestStreak = Number(stats.longest_streak) || 0;
  const formatRecentTimestamp = (value) => {
    if (!value) return 'Không rõ';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Không rõ';
    try {
      const timePart = date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
      const datePart = date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
      return `${timePart} · ${datePart}`;
    } catch (err) {
      return 'Không rõ';
    }
  };
  const recentReviews = Array.isArray(stats.recent_reviews) ? [...stats.recent_reviews].slice(-10).reverse() : [];
  const recentReviewConfig = {
    'correct': { label: 'Nhớ', icon: 'fas fa-check-circle' },
    'vague': { label: 'Mơ hồ', icon: 'fas fa-adjust' },
    'incorrect': { label: 'Quên', icon: 'fas fa-times-circle' },
    'preview': { label: 'Xem trước', icon: 'fas fa-eye' }
  };
  const introNotice = isBrandNew
    ? `<div class="insight-banner"><i class="fas fa-seedling"></i><span>Thẻ mới - khám phá nội dung trước khi chấm điểm.</span></div>`
    : (isPreviewStage
      ? `<div class="insight-banner"><i class="fas fa-hourglass-half"></i><span>Thẻ đang ở giai đoạn giới thiệu. Nhấn "Tiếp tục" để bước vào phần đánh giá.</span></div>`
      : '');

  const hasHistoricData = totalReviews > 0 || previewCount > 0;
  const progressSection = hasHistoricData
    ? `
                <div class="stats-section stats-section--performance">
                    <div class="stats-section__header">
                        <div class="icon-bubble"><i class="fas fa-chart-line"></i></div>
                        <div>
                            <h4>Hiệu suất trả lời</h4>
                            <p>Tỷ lệ ghi nhớ dựa trên toàn bộ lịch sử của thẻ.</p>
                        </div>
                    </div>
                    <div class="progress-stack">
                        <div class="progress-bar-group">
                            <div class="progress-bar-label">
                                <span class="label-title"><span class="progress-dot"></span> Nhớ</span>
                                <span class="progress-bar-stat">${correctCount} lượt · ${correctPercentDisplay}%</span>
                            </div>
                            <div class="progress-bar-container"><div class="progress-bar-fill progress-bar-fill-correct" style="--progress:${correctWidth}%;"></div></div>
                        </div>
                        <div class="progress-bar-group">
                            <div class="progress-bar-label">
                                <span class="label-title"><span class="progress-dot vague"></span> Mơ hồ</span>
                                <span class="progress-bar-stat">${vagueCount} lượt · ${vaguePercentDisplay}%</span>
                            </div>
                            <div class="progress-bar-container"><div class="progress-bar-fill progress-bar-fill-vague" style="--progress:${vagueWidth}%;"></div></div>
                        </div>
                        <div class="progress-bar-group">
                            <div class="progress-bar-label">
                                <span class="label-title"><span class="progress-dot incorrect"></span> Quên</span>
                                <span class="progress-bar-stat">${incorrectCount} lượt · ${incorrectPercentDisplay}%</span>
                            </div>
                            <div class="progress-bar-container"><div class="progress-bar-fill progress-bar-fill-incorrect" style="--progress:${incorrectWidth}%;"></div></div>
                        </div>
                    </div>
                </div>
            `
    : `
                <div class="stats-section stats-section--performance">
                    <div class="stats-section__header">
                        <div class="icon-bubble"><i class="fas fa-chart-line"></i></div>
                        <div>
                            <h4>Hiệu suất trả lời</h4>
                            <p>Thống kê sẽ xuất hiện sau khi bạn chấm điểm thẻ này.</p>
                        </div>
                    </div>
                    <div class="empty-state"><i class="fas fa-info-circle"></i> Bắt đầu trả lời để mở khóa biểu đồ hiệu suất.</div>
                </div>
            `;

  const insightSection = `
            <div class="stats-section stats-section--insight">
                <div class="stats-section__header">
                    <div class="icon-bubble"><i class="fas fa-bullseye"></i></div>
                    <div>
                        <h4>Chỉ số ghi nhớ</h4>
                        <p>Tổng hợp theo thuật toán SM-2.</p>
                    </div>
                </div>
                <div class="insight-grid">
                    ${!isInitial ? `<div class="insight-card insight-card--highlight"><span class="insight-card__label">Điểm phiên này</span><span class="insight-card__value ${scoreChangeClass}">${scoreChangeSign}${scoreChange}</span><span class="insight-card__muted">Sau lượt trả lời vừa rồi</span></div>` : ''}
                    <div class="insight-card">
                        <span class="insight-card__label">Trạng thái</span>
                        <span class="status-chip status-${statusKey}"><i class="fas fa-circle"></i> ${statusLabel}</span>
                        <span class="insight-card__muted">Theo tiến trình hiện tại</span>
                    </div>
                    <div class="insight-card">
                        <span class="insight-card__label">Tỷ lệ chính xác</span>
                        <span class="insight-card__value">${correctRateDisplay}%</span>
                        <span class="insight-card__muted">${totalReviews > 0 ? `${correctCount} đúng · ${incorrectCount} sai` : 'Chưa có lượt ôn'}</span>
                    </div>
                    <div class="insight-card">
                        <span class="insight-card__label">Lượt ôn</span>
                        <span class="insight-card__value">${totalReviews}</span>
                        <span class="insight-card__muted">${previewCount > 0 ? `${previewCount} lần xem thử` : 'Chưa xem trước'}</span>
                    </div>
                    <div class="insight-card">
                        <span class="insight-card__label">Chuỗi hiện tại</span>
                        <span class="insight-card__value">${currentStreak}</span>
                        <span class="insight-card__muted">${currentStreak > 0 ? 'Lượt đúng liên tiếp' : 'Chưa có chuỗi'}</span>
                    </div>
                    <div class="insight-card">
                        <span class="insight-card__label">Chuỗi dài nhất</span>
                        <span class="insight-card__value">${longestStreak}</span>
                        <span class="insight-card__muted">${longestStreak > 0 ? 'Kỷ lục ghi nhớ' : 'Chưa xác định'}</span>
                    </div>
                    <div class="insight-card">
                        <span class="insight-card__label">Hệ số dễ (EF)</span>
                        <span class="insight-card__value">${easinessFactor}</span>
                        <span class="insight-card__muted">Điều chỉnh sau mỗi lần ôn</span>
                    </div>
                    <div class="insight-card">
                        <span class="insight-card__label">Lặp lại (n)</span>
                        <span class="insight-card__value">${repetitions}</span>
                        <span class="insight-card__muted">Số lần đã ghi nhớ</span>
                    </div>
                    <div class="insight-card">
                        <span class="insight-card__label">Khoảng cách (I)</span>
                        <span class="insight-card__value">${formattedIntervalDisplay || 'Chưa có'}</span>
                        <span class="insight-card__muted">Thời gian đến lần ôn tiếp theo</span>
                    </div>
                </div>
            </div>
        `;

  const recentSection = recentReviews.length
    ? `
                <div class="stats-section stats-section--recent">
                    <div class="stats-section__header">
                        <div class="icon-bubble"><i class="fas fa-history"></i></div>
                        <div>
                            <h4>Lượt trả lời gần đây</h4>
                            <p>Theo dõi tối đa 10 lượt mới nhất bằng biểu tượng màu sắc.</p>
                        </div>
                    </div>
                    <div class="recent-answers-track" role="list">
                        ${recentReviews.map(entry => {
      const resultKey = (entry.result || '').toLowerCase();
      const config = recentReviewConfig[resultKey] || recentReviewConfig.preview;
      const timestampDisplay = formatRecentTimestamp(entry.timestamp);
      const qualityScore = typeof entry.user_answer_quality === 'number' ? entry.user_answer_quality : '—';
      const tooltip = `${config.label} · ${timestampDisplay} · Điểm: ${qualityScore}`;
      return `
                                <div class="recent-answer-dot recent-answer-dot--${resultKey || 'preview'}" role="listitem" title="${tooltip}">
                                    <i class="${config.icon}" aria-hidden="true"></i>
                                    <span class="sr-only">${tooltip}</span>
                                </div>
                            `;
    }).join('')}
                    </div>
                </div>
            `
    : '';

  const timelineSection = `
            <div class="stats-section stats-section--timeline">
                <div class="stats-section__header">
                    <div class="icon-bubble"><i class="fas fa-route"></i></div>
                    <div>
                        <h4>Mốc thời gian học</h4>
                        <p>Quản lý lịch sử ôn tập của riêng bạn.</p>
                    </div>
                </div>
                <div class="timeline-card">
                    <div class="timeline-item">
                        <div class="timeline-icon"><i class="fas fa-flag"></i></div>
                        <div>
                            <div class="timeline-label">Lần đầu gặp</div>
                            <div class="timeline-value">${firstSeen}</div>
                            <div class="timeline-subtle">Thời điểm bạn mở thẻ lần đầu</div>
                        </div>
                    </div>
                    <div class="timeline-item">
                        <div class="timeline-icon"><i class="fas fa-redo"></i></div>
                        <div>
                            <div class="timeline-label">Ôn gần nhất</div>
                            <div class="timeline-value">${lastReviewed}</div>
                            <div class="timeline-subtle">${totalReviews > 0 ? `${totalReviews} lượt đã ghi nhận` : 'Chưa có lượt ôn thực tế'}</div>
                        </div>
                    </div>
                    <div class="timeline-item">
                        <div class="timeline-icon"><i class="fas fa-calendar-check"></i></div>
                        <div>
                            <div class="timeline-label">Lịch ôn tiếp theo</div>
                            <div class="timeline-value">${dueTime}</div>
                            <div class="timeline-subtle">${stats.has_real_reviews ? 'Theo lịch SM-2 cá nhân hóa' : 'Cần trả lời để tạo lịch ôn'}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;

  const cardDetails = cardContent.front ? `
            <div class="card-info-section">
                <div class="card-info-title collapsed" data-toggle="card-details-content">
                    <i class="fas fa-caret-right"></i><span>Chi tiết thẻ</span>
                </div>
                <div class="card-info-content">
                    <p><span class="label">Mặt trước</span>${formatTextForHtml(cardContent.front)}</p>
                    <p><span class="label">Mặt sau</span>${formatTextForHtml(cardContent.back)}</p>
                </div>
            </div>
        `.trim() : '';

  return [
    cardDetails,
    introNotice,
    progressSection,
    insightSection,
    recentSection,
    timelineSection
  ].join('');
}

function renderMobileCardStatsHtml(stats, scoreChange = 0, cardContent = {}, isInitial = false) {
  if (!stats) return '<div class="p-4 text-center text-slate-400">Chưa có dữ liệu</div>';

  const totalReviews = Number(stats.times_reviewed) || 0;
  const correctCount = Number(stats.correct_count) || 0;
  const incorrectCount = Number(stats.incorrect_count) || 0;
  const correctRate = totalReviews > 0 ? Math.round((correctCount / totalReviews) * 100) : 0;
  const nextReview = formatDateTime(stats.next_review, 'Sẵn sàng');
  const statusLabel = (stats.status || 'New').toString().toUpperCase();
  const streak = stats.current_streak || 0;
  const ef = Number(stats.easiness_factor || 2.5).toFixed(2);

  // Status Colors
  const statusColors = {
    'new': 'bg-blue-100 text-blue-700',
    'learning': 'bg-orange-100 text-orange-700',
    'review': 'bg-emerald-100 text-emerald-700',
    'relearning': 'bg-purple-100 text-purple-700',
    'hard': 'bg-red-100 text-red-700'
  };
  const statusClass = statusColors[String(stats.status).toLowerCase()] || 'bg-slate-100 text-slate-700';

  return `
        <div class="mobile-stats-content">
            <!-- Top Row: Status & Next Review -->
            <div class="flex items-center justify-between mb-5">
                <span class="px-3 py-1 rounded-full text-xs font-bold ${statusClass}">${statusLabel}</span>
                <div class="text-right">
                    <div class="text-[10px] text-slate-400 uppercase font-bold">Lần ôn tới</div>
                    <div class="text-xs font-semibold text-slate-700">${nextReview}</div>
                </div>
            </div>

            <!-- Accuracy Bar -->
            <div class="mb-6 bg-white border border-slate-100 p-4 rounded-2xl shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
                <div class="flex justify-between items-end mb-2">
                    <span class="text-sm font-bold text-slate-700">Độ chính xác</span>
                    <span class="text-2xl font-black text-slate-800">${correctRate}%</span>
                </div>
                <div class="h-3 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div class="h-full bg-gradient-to-r from-blue-500 to-emerald-400" style="width: ${correctRate}%"></div>
                </div>
                <div class="mt-2 flex justify-between text-xs font-medium text-slate-400">
                    <span>${correctCount} đúng</span>
                    <span>${incorrectCount} sai</span>
                </div>
            </div>

            <!-- Metrics Grid -->
            <div class="grid grid-cols-3 gap-3 mb-6">
                <div class="bg-slate-50 p-3 rounded-2xl flex flex-col items-center justify-center text-center">
                    <span class="text-[10px] uppercase font-bold text-slate-400 mb-1">Chuỗi</span>
                    <span class="text-lg font-black text-slate-700">${streak}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-2xl flex flex-col items-center justify-center text-center">
                    <span class="text-[10px] uppercase font-bold text-slate-400 mb-1">Lượt ôn</span>
                    <span class="text-lg font-black text-slate-700">${totalReviews}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-2xl flex flex-col items-center justify-center text-center">
                    <span class="text-[10px] uppercase font-bold text-slate-400 mb-1">Độ khó</span>
                    <span class="text-lg font-black text-slate-700">${ef}</span>
                </div>
            </div>

            <!-- Card Info Toggle (App style) -->
            <div class="bg-white border border-slate-200 rounded-2xl overflow-hidden">
                <button class="w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100 transition-colors" onclick="this.nextElementSibling.classList.toggle('hidden'); this.querySelector('.fa-chevron-down').classList.toggle('rotate-180')">
                    <span class="text-sm font-bold text-slate-700">Chi tiết nội dung thẻ</span>
                    <i class="fas fa-chevron-down text-slate-400 transition-transform"></i>
                </button>
                <div class="hidden p-4 border-t border-slate-200 space-y-3 bg-white">
                    <div>
                        <span class="text-[10px] uppercase font-bold text-slate-400">Mặt trước</span>
                        <div class="text-sm text-slate-700 mt-1">${formatTextForHtml(cardContent.front)}</div>
                    </div>
                    <div class="pt-3 border-t border-slate-100">
                        <span class="text-[10px] uppercase font-bold text-slate-400">Mặt sau</span>
                        <div class="text-sm text-slate-700 mt-1">${formatTextForHtml(cardContent.back)}</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function initializeStatsToggleListeners(rootElement) {
  if (!rootElement) return;

  rootElement.querySelectorAll('[data-toggle]').forEach(toggleBtn => {
    if (toggleBtn.dataset.toggleListenerAttached === 'true') return;

    toggleBtn.addEventListener('click', function () {
      const content = this.nextElementSibling;
      this.classList.toggle('collapsed');

      if (!content) return;

      content.classList.toggle('open');

      if (content.classList.contains('open')) {
        content.style.maxHeight = content.scrollHeight + 'px';
      } else {
        content.style.maxHeight = null;
      }
    });

    toggleBtn.dataset.toggleListenerAttached = 'true';
  });
}

function displayCardStats(container, html) {
  container.innerHTML = html;
  initializeStatsToggleListeners(container);
}

window.updateFlashcardCard = async function (itemId, setId) {
  const numericItemId = Number(itemId);
  const numericSetId = Number(setId);

  if (!Number.isInteger(numericItemId) || numericItemId <= 0) {
    const message = 'Không thể xác định thẻ cần cập nhật.';
    if (window.showFlashMessage) {
      window.showFlashMessage(message, 'warning');
    }
    throw new Error(message);
  }

  const apiUrl = flashcardItemApiUrlTemplate.replace('/0', `/${numericItemId}`);

  try {
    const response = await fetch(apiUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    let payload = null;

    try {
      payload = await response.json();
    } catch (parseError) {
      payload = null;
    }

    if (!response.ok || !payload || !payload.success || !payload.item) {
      const errorMessage = (payload && payload.message) ? payload.message : 'Không thể tải lại thẻ sau khi chỉnh sửa.';
      throw new Error(errorMessage);
    }

    const updatedItem = payload.item;

    if (Number.isInteger(numericSetId) && updatedItem.container_id !== numericSetId) {
      const message = 'Thẻ vừa chỉnh sửa không thuộc bộ hiện tại.';
      if (window.showFlashMessage) {
        window.showFlashMessage(message, 'warning');
      }
      return updatedItem;
    }

    const targetIndex = currentFlashcardBatch.findIndex(card => Number(card.item_id) === Number(updatedItem.item_id));

    if (targetIndex === -1) {
      const message = 'Không tìm thấy thẻ đang hiển thị trong phiên để cập nhật.';
      if (window.showFlashMessage) {
        window.showFlashMessage(message, 'info');
      }
      return updatedItem;
    }

    currentFlashcardBatch[targetIndex] = updatedItem;

    if (targetIndex === currentFlashcardIndex) {
      stopAllFlashcardAudio();
      renderCard(updatedItem);
      const initialStatsHtml = renderCardStatsHtml(updatedItem.initial_stats, 0, updatedItem.content, true);
      displayCardStats(currentCardStatsContainer, initialStatsHtml);
    }

    return updatedItem;
  } catch (error) {
    console.error('Không thể tải lại thẻ sau khi chỉnh sửa:', error);
    if (window.showFlashMessage) {
      window.showFlashMessage(error.message || 'Không thể tải lại thẻ sau khi chỉnh sửa.', 'danger');
    }
    throw error;
  }
};

async function getNextFlashcardBatch() {
  stopAllFlashcardAudio();
  setFlashcardContent(`<div class="flex flex-col items-center justify-center h-full text-blue-500 min-h-[300px]"><i class="fas fa-spinner fa-spin text-4xl mb-3"></i><p>Đang tải thẻ...</p></div>`);
  try {
    const res = await fetch(getFlashcardBatchUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    if (!res.ok) {
      if (res.status === 404) {
        const end = await res.json();
        if (isAutoplaySession) {
          cancelAutoplaySequence();
        }
        setFlashcardContent(`<div class="text-center py-12 text-gray-600"><i class="fas fa-check-circle text-5xl text-green-500 mb-4"></i><h3 class="text-xl font-semibold text-gray-700 mb-2">Hoàn thành phiên học!</h3><p class="text-gray-500">${formatTextForHtml(end.message)}</p><button id="return-to-dashboard-btn" class="mt-6 px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 shadow-sm"><i class="fas fa-home mr-2"></i> Quay lại Dashboard</button></div>`);
        document.getElementById('return-to-dashboard-btn').addEventListener('click', () => { window.location.href = "{{ url_for('learning.flashcard.dashboard') }}"; });
        return;
      }
      throw new Error('HTTP ' + res.status);
    }
    const batch = await res.json();
    currentFlashcardBatch = batch.items;
    currentFlashcardIndex = 0;
    const currentCardData = currentFlashcardBatch[currentFlashcardIndex];

    const initialStatsHtml = renderCardStatsHtml(currentCardData.initial_stats, 0, currentCardData.content, true);
    displayCardStats(currentCardStatsContainer, initialStatsHtml);

    const mobileCurrent = document.getElementById('current-card-stats-mobile');
    if (mobileCurrent) {
      const mobileHtml = renderMobileCardStatsHtml(currentCardData.initial_stats, 0, currentCardData.content, true);
      mobileCurrent.innerHTML = mobileHtml;
    }

    renderCard(currentCardData);
    updateSessionSummary();

  } catch (e) {
    console.error('Lỗi khi tải nhóm thẻ:', e);
    setFlashcardContent(`<p class='text-red-500 text-center'>Không thể tải thẻ. Vui lòng thử lại.</p>`);
  }
}

async function submitFlashcardAnswer(itemId, answer) {
  stopAllFlashcardAudio();
  try {
    const res = await fetch(submitAnswerUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...csrfHeaders },
      body: JSON.stringify({ item_id: itemId, user_answer: answer })
    });
    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`HTTP error! status: ${res.status}, body: ${errorText}`);
    }
    const data = await res.json();

    sessionScore += data.score_change;
    currentUserTotalScore = data.updated_total_score;

    const previousCardContent = currentFlashcardBatch[currentFlashcardIndex].content;
    previousCardStats = {
      stats: data.statistics,
      scoreChange: data.score_change,
      cardContent: previousCardContent
    };
    const previousStatsHtml = renderCardStatsHtml(data.statistics, data.score_change, previousCardContent, false);
    displayCardStats(previousCardStatsContainer, previousStatsHtml);

    const mobilePrev = document.getElementById('previous-card-stats-mobile');
    if (mobilePrev) {
      const mobileHtml = renderMobileCardStatsHtml(data.statistics, data.score_change, previousCardContent, false);
      mobilePrev.innerHTML = mobileHtml;
    }

    const prevTabButton = document.querySelector('.stats-tab-button[data-target="previous-card-stats-pane"]');
    if (prevTabButton) {
      prevTabButton.click();
    }

    currentFlashcardIndex++;
    getNextFlashcardBatch();
  } catch (e) {
    console.error('Lỗi khi gửi đáp án:', e);
    showCustomAlert('Có lỗi khi gửi đáp án. Vui lòng thử lại.');
  }
}

endSessionBtn.addEventListener('click', () => endSessionModal.style.display = 'flex');
confirmEndSessionBtn.addEventListener('click', async () => {
  if (isAutoplaySession) {
    cancelAutoplaySequence();
  }
  try {
    const res = await fetch(endSessionUrl, { method: 'POST', headers: csrfHeaders });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const r = await res.json();
    window.showFlashMessage(r.message || 'Đã kết thúc phiên.', 'info');
    window.location.href = "{{ url_for('learning.flashcard.dashboard') }}";
  } catch (e) {
    window.showFlashMessage('Có lỗi xảy ra khi kết thúc phiên.', 'danger');
  } finally {
    endSessionModal.style.display = 'none';
  }
});
cancelEndSessionBtn.addEventListener('click', () => endSessionModal.style.display = 'none');

function showCustomAlert(message) {
  const modalHtml = `<div id="custom-alert-modal" class="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50"><div class="bg-white p-6 rounded-lg shadow-xl max-w-sm w-full text-center"><p class="text-lg font-semibold text-gray-800 mb-4">${formatTextForHtml(message)}</p><button id="custom-alert-ok-btn" class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">OK</button></div></div>`;
  document.body.insertAdjacentHTML('beforeend', modalHtml);
  document.getElementById('custom-alert-ok-btn').addEventListener('click', () => document.getElementById('custom-alert-modal').remove());
}

function toggleStatsModal(show) {
  if (show) {
    statsModal.classList.add('open');
    statsModalContent.classList.add('open');
    document.body.style.overflow = 'hidden';

    // Load content from template if not already loaded
    if (!statsModalContent.querySelector('.mobile-stats-container')) {
      const template = document.getElementById('mobile-stats-template');
      if (template) {
        statsModalContent.innerHTML = '';
        statsModalContent.appendChild(template.content.cloneNode(true));

        // Bind Events
        document.getElementById('close-stats-mobile-btn')?.addEventListener('click', () => toggleStatsModal(false));
        document.getElementById('end-session-mobile-btn')?.addEventListener('click', () => endSessionBtn.click());

        document.querySelectorAll('.stats-mobile-tab').forEach(btn => {
          btn.addEventListener('click', (e) => {
            const targetId = e.currentTarget.dataset.target;
            document.querySelectorAll('.stats-mobile-tab').forEach(t => t.classList.toggle('active', t === e.currentTarget));
            document.querySelectorAll('.stats-mobile-pane').forEach(p => p.classList.toggle('hidden', p.id !== targetId));
          });
        });
      }
    }

    // Sync Data
    updateSessionSummary();

    const currentCardData = currentFlashcardBatch.length > 0 ? currentFlashcardBatch[currentFlashcardIndex] : null;
    const mobileCurrentContainer = document.getElementById('current-card-stats-mobile');

    if (mobileCurrentContainer) {
      if (currentCardData && currentCardData.initial_stats) {
        // Use Mobile Render Function
        const html = renderMobileCardStatsHtml(currentCardData.initial_stats, 0, currentCardData.content, true);
        mobileCurrentContainer.innerHTML = html;
      } else {
        mobileCurrentContainer.innerHTML = '<div class="flex flex-col items-center justify-center h-40 text-slate-400"><p>Chưa có dữ liệu.</p></div>';
      }
    }

    const mobilePrevContainer = document.getElementById('previous-card-stats-mobile');
    if (mobilePrevContainer && previousCardStats) {
      // Use Mobile Render Function
      const html = renderMobileCardStatsHtml(previousCardStats.stats, previousCardStats.scoreChange, previousCardStats.cardContent, false);
      mobilePrevContainer.innerHTML = html;
    }

  } else {
    statsModal.classList.remove('open');
    statsModalContent.classList.remove('open');
    document.body.style.overflow = '';
  }
}

closeStatsModalBtn.addEventListener('click', () => toggleStatsModal(false));
function handleTabClick(event) {
  const button = event.currentTarget || event.target.closest('.stats-tab-button');
  if (!button) return;

  const targetPaneId = button.dataset.target;
  if (!targetPaneId) return;

  const parentContainer = button.closest('.statistics-card');
  if (!parentContainer) return;

  parentContainer.querySelectorAll('.stats-tab-button').forEach(btn => btn.classList.remove('active'));
  button.classList.add('active');
  parentContainer.querySelectorAll('.stats-tab-pane').forEach(pane => {
    pane.classList.toggle('active', pane.id === targetPaneId);
  });

  initializeStatsToggleListeners(parentContainer);
}

// ==============================================================================
// LOGIC CHO AI MODAL (ĐÃ SỬA LỖI LOGIC)
// ==============================================================================

// Ghi đè hàm openAiModal và closeAiModal được định nghĩa trong _ai_modal.html
window.openAiModal = function (itemId, termContent) {
  const aiModal = document.getElementById('ai-modal');
  if (aiModal && aiModal.classList.contains('open')) {
    console.warn("AI modal đã được mở, bỏ qua lệnh gọi.");
    return;
  }

  const aiModalTerm = document.getElementById('ai-modal-term');
  const aiResponseContainer = document.getElementById('ai-response-container');

  currentAiItemId = itemId;
  aiModalTerm.textContent = termContent;
  aiModal.classList.add('open');

  fetchAiResponse();
};

window.closeAiModal = function () {
  const aiModal = document.getElementById('ai-modal');
  const aiResponseContainer = document.getElementById('ai-response-container');

  aiModal.classList.remove('open');
  currentAiItemId = null;
  aiResponseContainer.innerHTML = `<div class="text-gray-500">Câu trả lời của AI sẽ xuất hiện ở đây.</div>`;
};

// Các listeners trong _ai_modal.html sẽ gọi các hàm global trên

// ==============================================================================
// LOGIC CHO NOTE PANEL
// ==============================================================================
const notePanel = document.getElementById('note-panel');
const noteTextarea = document.getElementById('note-textarea');
const saveNoteBtn = document.getElementById('save-note-btn');
const cancelNoteBtn = document.getElementById('cancel-note-btn');
const noteDisplay = document.getElementById('note-display');
const editNoteBtn = document.getElementById('edit-note-btn');
const noteViewSection = document.getElementById('note-view-section');
const noteEditSection = document.getElementById('note-edit-section');
const closeNoteBtn = document.getElementById('close-note-btn');
let currentNoteItemId = null;
let lastLoadedNoteContent = '';

function setNoteMode(mode) {
  if (mode === 'view') {
    noteViewSection.classList.remove('hidden');
    noteEditSection.classList.add('hidden');
    // Show edit button in view mode
    if (editNoteBtn) editNoteBtn.classList.remove('hidden');
  } else {
    noteViewSection.classList.add('hidden');
    noteEditSection.classList.remove('hidden');
    // Hide edit button in edit mode
    if (editNoteBtn) editNoteBtn.classList.add('hidden');
    noteTextarea.focus();
  }
}

function updateNoteView(content) {
  lastLoadedNoteContent = content || '';
  const hasContent = lastLoadedNoteContent.trim().length > 0;

  // Use formatTextForHtml for display
  noteDisplay.innerHTML = hasContent ? formatTextForHtml(lastLoadedNoteContent) : '<span class="italic text-gray-500">Chưa có ghi chú.</span>';
  noteTextarea.value = lastLoadedNoteContent;

  // If content exists, default to view mode. If empty, default to edit mode.
  setNoteMode(hasContent ? 'view' : 'edit');
}

async function openNotePanel(itemId) {
  if (!itemId) return;
  currentNoteItemId = itemId;
  notePanel.classList.add('open');

  noteTextarea.value = 'Đang tải ghi chú...';
  noteTextarea.disabled = true;
  // Hide edit button while loading
  if (editNoteBtn) editNoteBtn.classList.add('hidden');

  try {
    const response = await fetch(getNoteUrl.replace('/0', `/${itemId}`));
    const result = await response.json();
    if (response.ok && result.success) {
      updateNoteView(result.content || '');
    } else {
      updateNoteView('');
    }
  } catch (error) {
    console.error('Lỗi khi tải ghi chú:', error);
    updateNoteView('');
  } finally {
    noteTextarea.disabled = false;
  }
}

function closeNotePanel() {
  notePanel.classList.remove('open');
  currentNoteItemId = null;
  lastLoadedNoteContent = '';
  noteTextarea.value = '';
  // Reset to default state
  if (editNoteBtn) editNoteBtn.classList.add('hidden');
}

async function saveNote() {
  if (!currentNoteItemId) return;

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
    if (response.ok && result.success) {
      window.showFlashMessage(result.message, 'success');
      updateNoteView(content);
    } else {
      window.showFlashMessage(result.message || 'Lỗi khi lưu ghi chú.', 'danger');
    }
  } catch (error) {
    console.error('Lỗi khi lưu ghi chú:', error);
    window.showFlashMessage('Lỗi kết nối khi lưu ghi chú.', 'danger');
  } finally {
    saveNoteBtn.disabled = false;
    saveNoteBtn.textContent = 'Lưu Ghi chú';
  }
}

function handleCancelNote() {
  if (lastLoadedNoteContent.trim()) {
    setNoteMode('view');
  } else {
    closeNotePanel();
  }
}

if (saveNoteBtn) saveNoteBtn.addEventListener('click', saveNote);
if (cancelNoteBtn) cancelNoteBtn.addEventListener('click', handleCancelNote);
if (editNoteBtn) editNoteBtn.addEventListener('click', () => setNoteMode('edit'));
if (closeNoteBtn) closeNoteBtn.addEventListener('click', closeNotePanel);
if (notePanel) notePanel.addEventListener('click', (event) => {
  if (event.target === notePanel) {
    closeNotePanel();
  }
});


document.addEventListener('DOMContentLoaded', () => {
  setVh();
  document.body.classList.add('flashcard-session-active');

  document.querySelectorAll('.statistics-card .stats-tab-button').forEach(btn => btn.addEventListener('click', handleTabClick));
  updateSessionSummary();
  getNextFlashcardBatch();
});

window.addEventListener('resize', () => {
  setVh();
  setTimeout(adjustCardLayout, 0);
});

