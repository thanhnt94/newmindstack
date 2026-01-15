window.renderDesktopCardHtml = function (data, o) {
  // Override button logic (Always show rating buttons)
  const userButtonCount = window.FlashcardConfig.userButtonCount || 4;

  const buttonLogic = {
    3: [
      { class: 'rating-btn--again', value: 'quên', label: 'Quên', icon: 'fas fa-times' },
      { class: 'rating-btn--hard', value: 'mơ_hồ', label: 'Mơ hồ', icon: 'fas fa-question' },
      { class: 'rating-btn--easy', value: 'nhớ', label: 'Nhớ', icon: 'fas fa-check' }
    ],
    4: [
      { class: 'rating-btn--again', value: 'again', label: 'Học lại', icon: 'fas fa-undo' },
      { class: 'rating-btn--hard', value: 'hard', label: 'Khó', icon: 'fas fa-fire' },
      { class: 'rating-btn--good', value: 'good', label: 'Ổn', icon: 'fas fa-thumbs-up' },
      { class: 'rating-btn--easy', value: 'easy', label: 'Dễ', icon: 'fas fa-smile' }
    ],
    6: [
      { class: 'rating-btn--fail', value: 'fail', label: 'Rất khó', icon: 'fas fa-exclamation-circle' },
      { class: 'rating-btn--very-hard', value: 'very_hard', label: 'Khó', icon: 'fas fa-fire' },
      { class: 'rating-btn--hard', value: 'hard', label: 'TB', icon: 'fas fa-adjust' },
      { class: 'rating-btn--medium', value: 'medium', label: 'Dễ', icon: 'fas fa-leaf' },
      { class: 'rating-btn--good', value: 'good', label: 'Rất dễ', icon: 'fas fa-thumbs-up' },
      { class: 'rating-btn--very-easy', value: 'very_easy', label: 'Dễ dàng', icon: 'fas fa-star' }
    ]
  };

  const definitions = buttonLogic[userButtonCount] || buttonLogic[4];

  // Generate Rating Buttons HTML
  const ratingButtonsHtml = definitions.map(def => `
        <button class="btn rating-btn ${def.class}" data-answer="${def.value}">
            <span class="rating-btn__icon"><i class="${def.icon}"></i></span>
            <span class="rating-btn__title">${def.label}</span>
        </button>
    `).join('');

  // Generate Flip Button HTML (Now detached)
  // We add specific class usually expected but also new ones for styling
  const flipButtonHtml = `
        <button class="js-flip-card-btn flip-card-btn detached-flip-btn">
            <span class="btn-icon"><i class="fas fa-sync-alt"></i></span>
            <span class="btn-text">Lật thẻ / Xem đáp án</span>
        </button>
    `;


  // --- Toolbar Construction ---
  const menuButtonHtml = `<button class="icon-btn open-stats-modal-btn" title="Thống kê"><i class="fas fa-bars"></i></button>`;
  const aiButtonHtml = `<button class="icon-btn open-ai-modal-btn" data-item-id="${o.itemId}" title="AI Coach"><i class="fas fa-robot"></i></button>`;
  const noteButtonHtml = `<button class="icon-btn open-note-panel-btn" data-item-id="${o.itemId}" title="Ghi chú"><i class="fas fa-sticky-note"></i></button>`;
  const feedbackButtonHtml = `<button class="icon-btn open-feedback-modal-btn" data-item-id="${o.itemId}" title="Báo lỗi"><i class="fas fa-flag"></i></button>`;

  const editButtonHtml = o.canEditCurrentCard
    ? `<button class="icon-btn edit-card-btn" onclick="window.parent.openModal('${o.editUrl}')" title="Sửa thẻ"><i class="fas fa-pencil-alt"></i></button>`
    : '';

  const imageToggleButtonHtml = `<button class="icon-btn image-toggle-btn ${o.isMediaHidden ? 'is-active' : ''}" aria-pressed="${o.isMediaHidden}" title="${o.isMediaHidden ? 'Bật ảnh' : 'Tắt ảnh'}"><i class="fas ${o.isMediaHidden ? 'fa-image-slash' : 'fa-image'}"></i></button>`;
  const audioAutoplayToggleButtonHtml = `<button class="icon-btn audio-autoplay-toggle-btn ${o.isAudioAutoplayEnabled ? 'is-active' : ''}" aria-pressed="${o.isAudioAutoplayEnabled}" title="${o.isAudioAutoplayEnabled ? 'Tắt tự động phát audio' : 'Bật tự động phát audio'}"><i class="fas ${o.isAudioAutoplayEnabled ? 'fa-volume-up' : 'fa-volume-mute'}"></i></button>`;

  const audioButtonHtmlFront = `<button class="icon-btn play-audio-btn ${o.hasFrontAudio ? '' : 'is-disabled'}" data-audio-target="#front-audio-desktop" data-side="front" data-item-id="${o.itemId}" data-content-to-read="${o.frontAudioContent || ''}" title="Phát âm thanh" ${o.hasFrontAudio ? '' : 'disabled'}><i class="fas fa-volume-up"></i></button>`;
  const audioButtonHtmlBack = `<button class="icon-btn play-audio-btn ${o.hasBackAudio ? '' : 'is-disabled'}" data-audio-target="#back-audio-desktop" data-side="back" data-item-id="${o.itemId}" data-content-to-read="${o.backAudioContent || ''}" title="Phát âm thanh" ${o.hasBackAudio ? '' : 'disabled'}><i class="fas fa-volume-up"></i></button>`;


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

  let statsHtml = `
        <div class="desktop-stats-panel h-full flex flex-col bg-white border-l border-slate-200 shadow-sm">
            <div class="p-4 border-b border-slate-100">
                <h3 class="font-bold text-slate-700"><i class="fas fa-chart-line mr-2 text-emerald-500"></i>Thông tin thẻ</h3>
            </div>
            <div class="p-6 flex-1 overflow-y-auto">
                <div class="mb-6">
                    <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">Trạng thái</span>
                     <div class="flex items-center gap-2">
                        <span class="px-3 py-1 rounded-full bg-slate-100 text-slate-600 font-bold text-sm border border-slate-200">
                            ${data.user_status || 'New'}
                        </span>
                        ${data.ease_factor ? `<span class="px-3 py-1 rounded-full bg-blue-50 text-blue-600 font-bold text-sm border border-blue-100" title="Ease Factor">EF: ${data.ease_factor}</span>` : ''}
                    </div>
                </div>
                
                 <div class="mb-6">
                    <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">Lịch sử ôn tập</span>
                    ${data.review_history && data.review_history.length > 0 ?
      `<ul class="space-y-3">
                            ${data.review_history.slice(0, 5).map(h => `
                                <li class="flex items-center justify-between text-sm">
                                    <span class="text-slate-600">${h.date_str || 'N/A'}</span>
                                    <span class="font-bold ${h.rating >= 3 ? 'text-emerald-600' : 'text-amber-500'}">${h.rating_label || h.rating}</span>
                                </li>
                            `).join('')}
                        </ul>`
      : '<p class="text-sm text-slate-400 italic">Chưa có lịch sử ôn tập</p>'}
                </div>

                 <div class="p-4 bg-slate-50 rounded-lg border border-slate-100">
                    <p class="text-xs text-slate-500 leading-relaxed">
                        <i class="fas fa-info-circle mr-1 text-slate-400"></i>
                         Nhấn Space để lật thẻ, sau đó chọn mức độ nhớ để đánh giá và chuyển sang thẻ tiếp theo.
                    </p>
                </div>
            </div>
        </div>
    `;

  return `
    <div class="desktop-layout-grid w-full h-full flex flex-row overflow-hidden">
       
       <!-- Left Column: Flashcard & Actions -->
       <div class="main-column flex-1 flex flex-col relative min-w-0 bg-slate-50/50">
           
           <!-- Card Area -->
           <div class="card-display-area flex-1 flex items-center justify-center p-6 relative perspective-container">
                <div class="flashcard-card-container desktop-card-size">
                  <div class="js-flashcard-card flashcard-card ${o.cardCategory ? 'flashcard-card--' + o.cardCategory : ''}" data-card-category="${o.cardCategory || 'default'}">
                    
                    <div class="face front">
                      ${toolbarFront}
                      <div class="_card-container">
                        <div class="text-area"><div class="flashcard-content-text text-3xl">${o.fTxt}</div></div>
                        ${o.frontImg ? `<div class="media-container"><img src="${o.frontImg}" alt="Mặt trước" onerror="this.onerror=null;this.src='https://placehold.co/200x120?text=Image+not+found';"></div>` : ''}
                        <audio id="front-audio-desktop" class="hidden" src="${o.frontAudioUrl || ''}"></audio>
                      </div>
                      <!-- NO FLIP BUTTON INSIDE -->
                    </div>

                    <div class="face back">
                      ${toolbarBack}
                      <div class="_card-container">
                        <div class="text-area"><div class="flashcard-content-text">${o.bTxt}</div></div>
                        ${o.backImg ? `<div class="media-container"><img src="${o.backImg}" alt="Mặt sau" onerror="this.onerror=null;this.src='https://placehold.co/200x120?text=Image+not+found';"></div>` : ''}
                      </div>
                      <!-- NO RATING BUTTONS INSIDE -->
                      <audio id="back-audio-desktop" class="hidden" src="${o.backAudioUrl || ''}"></audio>
                    </div>

                  </div>
                </div>
           </div>

           <!-- Detached Action Bar -->
           <!-- Contains BOTH Flip Button AND Rating Buttons, toggled by CSS/JS -->
           <div class="desktop-action-bar h-24 bg-white border-t border-slate-200 flex items-center justify-center z-10 shrink-0 shadow-[0_-4px_20px_rgba(0,0,0,0.03)]">
                
                <!-- Flip Action Container -->
                <div class="action-group flip-action flex w-full justify-center">
                    ${flipButtonHtml}
                </div>

                <!-- Rating Action Container (Hidden initially) -->
                 <div class="actions js-internal-actions action-group rating-actions flex gap-4 w-full justify-center" 
                     data-button-count="${userButtonCount}"
                     style="display: none;">
                     ${ratingButtonsHtml}
                </div>
           </div>

       </div>

       <!-- Right Column: Stats Sidebar -->
       <div class="stats-sidebar w-[350px] shrink-0 h-full relative z-20">
            ${statsHtml}
       </div>

    </div>`;
};
