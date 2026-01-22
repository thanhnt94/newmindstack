window.renderMobileCardHtml = function (data, o) {
  // o = options
  // Xây dựng toolbar cho mobile
  const menuButtonHtml = `<button class="icon-btn open-stats-modal-btn"><i class="fas fa-bars"></i></button>`;
  const aiButtonHtml = `<button class="icon-btn open-ai-modal-btn" data-item-id="${o.itemId}"><i class="fas fa-robot"></i></button>`;
  const noteButtonHtml = `<button class="icon-btn open-note-panel-btn" data-item-id="${o.itemId}"><i class="fas fa-sticky-note"></i></button>`;
  const feedbackButtonHtml = `<button class="icon-btn open-feedback-modal-btn" data-item-id="${o.itemId}"><i class="fas fa-flag"></i></button>`;

  const editButtonHtml = o.canEditCurrentCard
    ? `<button class="icon-btn edit-card-btn" onclick="window.parent.openModal('${o.editUrl}')"><i class="fas fa-pencil-alt"></i></button>`
    : '';

  const imageToggleButtonHtml = `<button class="icon-btn image-toggle-btn ${o.isMediaHidden ? 'is-active' : ''}" aria-pressed="${o.isMediaHidden}" title="${o.isMediaHidden ? 'Bật ảnh' : 'Tắt ảnh'}"><i class="fas ${o.isMediaHidden ? 'fa-image-slash' : 'fa-image'}"></i></button>`;
  const audioAutoplayToggleButtonHtml = `<button class="icon-btn audio-autoplay-toggle-btn ${o.isAudioAutoplayEnabled ? 'is-active' : ''}" aria-pressed="${o.isAudioAutoplayEnabled}" title="${o.isAudioAutoplayEnabled ? 'Tắt tự động phát audio' : 'Bật tự động phát audio'}"><i class="fas ${o.isAudioAutoplayEnabled ? 'fa-volume-up' : 'fa-volume-mute'}"></i></button>`;

  const audioButtonHtmlFront = `<button class="icon-btn play-audio-btn ${o.hasFrontAudio ? '' : 'is-disabled'}" data-audio-target="#front-audio-mobile" data-side="front" data-item-id="${o.itemId}" data-content-to-read="${o.frontAudioContent || ''}" ${o.hasFrontAudio ? '' : 'disabled'}><i class="fas fa-volume-up"></i></button>`;
  const audioButtonHtmlBack = `<button class="icon-btn play-audio-btn ${o.hasBackAudio ? '' : 'is-disabled'}" data-audio-target="#back-audio-mobile" data-side="back" data-item-id="${o.itemId}" data-content-to-read="${o.backAudioContent || ''}" ${o.hasBackAudio ? '' : 'disabled'}><i class="fas fa-volume-up"></i></button>`;

  const flipButtonHtml = `<button class="js-flip-card-btn flip-card-btn"><i class="fas fa-sync-alt mr-2"></i>Lật thẻ</button>`;

  const leftToolbarContent = `${menuButtonHtml}${aiButtonHtml}${noteButtonHtml}`;

  const settingsMenuHtml = `
        <div class="toolbar-settings">
          <div class="settings-panel">
            ${feedbackButtonHtml}${editButtonHtml}${imageToggleButtonHtml}${audioAutoplayToggleButtonHtml}
          </div>
          <button type="button" class="icon-btn settings-toggle-btn" aria-expanded="false" title="Mở cài đặt"><i class="fas fa-ellipsis-v"></i></button>
        </div>
      `;

  const toolbarFront = `<div class="card-toolbar"><div class="toolbar-left">${leftToolbarContent}</div><span class="label">MẶT TRƯỚC</span><div class="toolbar-right">${audioButtonHtmlFront}${settingsMenuHtml}</div></div>`;
  const toolbarBack = `<div class="card-toolbar"><div class="toolbar-left">${leftToolbarContent}</div><span class="label">MẶT SAU</span><div class="toolbar-right">${audioButtonHtmlBack}${settingsMenuHtml}</div></div>`;

  // [NEW] Get display settings from config
  const displaySettings = window.FlashcardConfig?.displaySettings || {};
  const frontAlignClass = displaySettings.front_align === 'center' ? 'display-center' : '';
  const backAlignClass = displaySettings.back_align === 'center' ? 'display-center' : '';
  const frontBoldClass = displaySettings.force_bold_front ? 'force-bold-override' : '';
  const backBoldClass = displaySettings.force_bold_back ? 'force-bold-override' : '';

  // Mobile structure
  return `
    <div class="flashcard-card-container">
      <div class="js-flashcard-card flashcard-card ${o.cardCategory ? 'flashcard-card--' + o.cardCategory : ''}" data-card-category="${o.cardCategory || 'default'}">
        <div class="face front ${frontAlignClass} ${frontBoldClass}">
          ${toolbarFront}
          <div class="_card-container">
            <div class="text-area"><div class="flashcard-content-text">${o.fTxt}</div></div>
            ${o.frontImg ? `<div class="media-container"><img src="${o.frontImg}" alt="Mặt trước" onerror="this.onerror=null;this.src='https://placehold.co/200x120?text=Image+not+found';"></div>` : ''}
            <audio id="front-audio-mobile" class="hidden" src="${o.frontAudioUrl || ''}"></audio>
          </div>
          <div class="flip-btn-container">
            ${flipButtonHtml}
          </div>
        </div>
        <div class="face back ${backAlignClass} ${backBoldClass}">
          ${toolbarBack}
          <div class="_card-container">
            <div class="text-area"><div class="flashcard-content-text">${o.bTxt}</div></div>
            ${o.backImg ? `<div class="media-container"><img src="${o.backImg}" alt="Mặt sau" onerror="this.onerror=null;this.src='https://placehold.co/200x120?text=Image+not+found';"></div>` : ''}
          </div>
          <div class="actions js-internal-actions" data-button-count="${o.buttonCount}">${o.buttonsHtml}</div>
          <audio id="back-audio-mobile" class="hidden" src="${o.backAudioUrl || ''}"></audio>
        </div>
      </div>
    </div>`;
};
