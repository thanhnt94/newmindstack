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

  // --- Stats Panel Construction (Beautiful Design) ---
  // Calculate rating percentages for Bar Chart
  const totalRatings = o.stats?.times_reviewed || 0;
  const counts = o.stats?.rating_counts || { 1: 0, 2: 0, 3: 0, 4: 0 };
  const pTypically = totalRatings > 0 ? {
    1: (counts[1] / totalRatings) * 100,
    2: (counts[2] / totalRatings) * 100,
    3: (counts[3] / totalRatings) * 100,
    4: (counts[4] / totalRatings) * 100
  } : { 1: 0, 2: 0, 3: 0, 4: 0 };

  const reviewHistory = o.stats?.recent_reviews || [];

  let statsHtml = `
        <div class="desktop-stats-panel h-full flex flex-col bg-white border-l border-slate-200 shadow-[0_0_20px_rgba(0,0,0,0.02)] z-30">
            <!-- Header -->
            <div class="p-5 border-b border-slate-100 flex items-center justify-between">
                <h3 class="font-bold text-slate-800 flex items-center gap-2">
                    <span class="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center">
                        <i class="fas fa-chart-pie"></i>
                    </span>
                    Thông số thẻ
                </h3>
                <span class="px-2.5 py-1 rounded-md bg-slate-100 text-slate-500 text-xs font-bold uppercase tracking-wider">
                    ${data.user_status || 'New'}
                </span>
            </div>

            <div class="p-5 flex-1 overflow-y-auto space-y-6 scrollbar-thin scrollbar-thumb-slate-200 hover:scrollbar-thumb-slate-300">
                
                <!-- Primary Metrics Grid -->
                <div class="grid grid-cols-2 gap-3">
                    <div class="bg-slate-50 rounded-xl p-3 border border-slate-100 flex flex-col items-center justify-center text-center">
                        <span class="text-xs font-bold text-slate-400 uppercase mb-1">Đã học</span>
                        <span class="text-xl font-bold text-slate-700 js-hud-reviews">${totalRatings}</span>
                        <span class="text-[10px] text-slate-400">lần</span>
                    </div>
                    <div class="bg-slate-50 rounded-xl p-3 border border-slate-100 flex flex-col items-center justify-center text-center">
                        <span class="text-xs font-bold text-slate-400 uppercase mb-1">Chuỗi</span>
                         <span class="text-xl font-bold text-amber-500 js-hud-streak">${o.stats?.current_streak || 0}</span>
                        <span class="text-[10px] text-slate-400">liên tiếp</span>
                    </div>
                </div>

                <!-- Rating Distribution Bar -->
                <div>
                     <div class="flex items-center justify-between mb-2">
                        <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">Tỉ lệ đánh giá</span>
                        <span class="text-xs font-medium text-slate-500">${totalRatings} lượt</span>
                    </div>
                    <div class="h-4 w-full bg-slate-100 rounded-full overflow-hidden flex relative shadow-inner js-hud-rating-bar">
                         ${totalRatings > 0 ? `
                            <div class="h-full bg-rose-500" style="width: ${pTypically[1]}%" title="Quên: ${counts[1]}"></div>
                            <div class="h-full bg-amber-500" style="width: ${pTypically[2]}%" title="Khó: ${counts[2]}"></div>
                            <div class="h-full bg-emerald-500" style="width: ${pTypically[3]}%" title="Được: ${counts[3]}"></div>
                            <div class="h-full bg-blue-500" style="width: ${pTypically[4]}%" title="Dễ: ${counts[4]}"></div>
                         ` : '<div class="w-full h-full flex items-center justify-center text-[9px] text-slate-400 italic">Chưa có dữ liệu</div>'}
                    </div>
                    <!-- Legend -->
                    <div class="flex justify-between mt-2 px-1">
                        <div class="flex items-center gap-1"><div class="w-2 h-2 rounded-full bg-rose-500"></div><span class="text-[10px] text-slate-500">Q</span></div>
                        <div class="flex items-center gap-1"><div class="w-2 h-2 rounded-full bg-amber-500"></div><span class="text-[10px] text-slate-500">K</span></div>
                        <div class="flex items-center gap-1"><div class="w-2 h-2 rounded-full bg-emerald-500"></div><span class="text-[10px] text-slate-500">Đ</span></div>
                        <div class="flex items-center gap-1"><div class="w-2 h-2 rounded-full bg-blue-500"></div><span class="text-[10px] text-slate-500">D</span></div>
                    </div>
                </div>

                <!-- Next Review Info & Retention -->
                <div class="bg-blue-50/50 rounded-xl p-4 border border-blue-100">
                    <div class="flex items-center gap-3 mb-2">
                         <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
                            <i class="fas fa-calendar-alt text-sm"></i>
                        </div>
                        <div>
                            <span class="text-xs font-bold text-blue-400 uppercase block">Lần tới</span>
                            <span class="text-sm font-bold text-slate-700 js-hud-interval">
                                ${o.stats?.interval_minutes ? window.formatMinutesAsDuration(o.stats.interval_minutes) : (data.next_due_display || 'Ngay bây giờ')}
                            </span>
                        </div>
                    </div>
                    <!-- Retention Bar (Retrievability) -->
                    <div class="w-full bg-white rounded-lg h-1.5 overflow-hidden flex mb-1">
                        <div class="bg-blue-500 h-full rounded-full js-hud-retention-bar" style="width: ${Math.round((o.stats?.retrievability !== undefined ? o.stats.retrievability : 1) * 100)}%"></div>
                    </div>
                     <div class="flex justify-between items-center">
                        <span class="text-[10px] text-slate-400">Khả năng nhớ</span> <!-- Was Độ ổn định -->
                        <div class="text-right">
                             <span class="text-[10px] font-bold text-blue-600 js-hud-retention-text">${Math.round((o.stats?.retrievability !== undefined ? o.stats.retrievability : 1) * 100)}%</span>
                             <span class="text-[9px] text-slate-400 ml-1 js-hud-stability">(${o.stats?.stability || 0}d)</span>
                        </div>
                    </div>
                </div>

                <!-- Review History Timeline -->
                <div>
                     <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-3">Lịch sử gần đây</span>
                     <div class="relative pl-4 border-l-2 border-slate-100 space-y-4 js-hud-history">
                        ${reviewHistory.length > 0 ? reviewHistory.slice().reverse().slice(0, 5).map(h => `
                            <div class="relative">
                                <div class="absolute -left-[21px] top-0 w-3 h-3 rounded-full border-2 border-white shadow-sm ${h.user_answer_quality >= 3 ? 'bg-emerald-500' : (h.user_answer_quality === 2 ? 'bg-amber-500' : 'bg-rose-500')}"></div>
                                <div class="flex justify-between items-start">
                                    <div class="flex flex-col">
                                        <span class="text-xs font-bold text-slate-700">
                                            ${h.user_answer_quality === 1 ? 'Quên' : (h.user_answer_quality === 2 ? 'Khó' : (h.user_answer_quality === 3 ? 'Được' : 'Dễ'))}
                                        </span>
                                        <span class="text-[10px] text-slate-400">${window.formatDateTime ? window.formatDateTime(h.timestamp) : h.timestamp}</span>
                                    </div>
                                    ${h.result === 'correct' ? '<i class="fas fa-check text-xs text-emerald-500"></i>' : ''}
                                </div>
                            </div>
                        `).join('') : '<p class="text-xs text-slate-400 italic">Chưa có lịch sử</p>'}
                     </div>
                </div>

            </div>
             
             <!-- Footer Tip -->
            <div class="p-4 bg-slate-50 border-t border-slate-100">
                <p class="text-[11px] text-slate-500 leading-relaxed text-center">
                    Cố gắng duy trì chuỗi để nhận thêm điểm thưởng!
                </p>
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
           <div class="desktop-action-bar h-24 bg-white border-t border-slate-200 flex items-center justify-center z-10 shrink-0 shadow-[0_-4px_20px_rgba(0,0,0,0.03)]">
                <div class="action-group flip-action flex w-full justify-center">
                    ${flipButtonHtml}
                </div>
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

// --- NEW Update Function for HUD ---
window.updateCardHudStats = function (stats) {
  if (!stats) return;

  // Update Reviews
  const revEl = document.querySelector('.js-hud-reviews');
  if (revEl) revEl.textContent = stats.times_reviewed || 0;

  // Update Streak
  const streakEl = document.querySelector('.js-hud-streak');
  if (streakEl) streakEl.textContent = stats.current_streak || 0;

  // Update Rating Bar
  const barContainer = document.querySelector('.js-hud-rating-bar');
  if (barContainer) {
    const total = stats.times_reviewed || 0;
    const counts = stats.rating_counts || { 1: 0, 2: 0, 3: 0, 4: 0 };
    if (total > 0) {
      const p1 = (counts[1] / total) * 100;
      const p2 = (counts[2] / total) * 100;
      const p3 = (counts[3] / total) * 100;
      const p4 = (counts[4] / total) * 100;

      barContainer.innerHTML = `
                <div class="h-full bg-rose-500" style="width: ${p1}%" title="Quên: ${counts[1]}"></div>
                <div class="h-full bg-amber-500" style="width: ${p2}%" title="Khó: ${counts[2]}"></div>
                <div class="h-full bg-emerald-500" style="width: ${p3}%" title="Được: ${counts[3]}"></div>
                <div class="h-full bg-blue-500" style="width: ${p4}%" title="Dễ: ${counts[4]}"></div>
            `;
    } else {
      barContainer.innerHTML = '<div class="w-full h-full flex items-center justify-center text-[9px] text-slate-400 italic">Chưa có dữ liệu</div>';
    }
  }

  // Update Retention/Stability
  const intEl = document.querySelector('.js-hud-interval');
  if (intEl) {
    if (stats.interval_minutes) {
      intEl.textContent = window.formatMinutesAsDuration ? window.formatMinutesAsDuration(stats.interval_minutes) : stats.interval_minutes + 'm';
    } else {
      intEl.textContent = stats.next_review ? window.formatDateTime(stats.next_review) : 'Chưa có';
    }
  }

  // Update Retention Bar & Text
  const retBar = document.querySelector('.js-hud-retention-bar');
  if (retBar) retBar.style.width = (stats.retrievability || 100) + '%';

  const retText = document.querySelector('.js-hud-retention-text');
  if (retText) retText.textContent = (stats.retrievability || 100) + '%';

  const stabEl = document.querySelector('.js-hud-stability');
  if (stabEl) stabEl.textContent = '(' + (stats.stability || 0).toFixed(1) + 'd)';

  // Update History
  const histContainer = document.querySelector('.js-hud-history');
  if (histContainer && stats.recent_reviews) {
    const hist = stats.recent_reviews.slice().reverse().slice(0, 5);
    if (hist.length > 0) {
      histContainer.innerHTML = hist.map(h => `
                <div class="relative">
                    <div class="absolute -left-[21px] top-0 w-3 h-3 rounded-full border-2 border-white shadow-sm ${h.user_answer_quality >= 3 ? 'bg-emerald-500' : (h.user_answer_quality === 2 ? 'bg-amber-500' : 'bg-rose-500')}"></div>
                    <div class="flex justify-between items-start">
                        <div class="flex flex-col">
                            <span class="text-xs font-bold text-slate-700">
                                ${h.user_answer_quality === 1 ? 'Quên' : (h.user_answer_quality === 2 ? 'Khó' : (h.user_answer_quality === 3 ? 'Được' : 'Dễ'))}
                            </span>
                            <span class="text-[10px] text-slate-400">${window.formatDateTime ? window.formatDateTime(h.timestamp) : h.timestamp}</span>
                        </div>
                        ${h.result === 'correct' ? '<i class="fas fa-check text-xs text-emerald-500"></i>' : ''}
                    </div>
                </div>
             `).join('');
    } else {
      histContainer.innerHTML = '<p class="text-xs text-slate-400 italic">Chưa có lịch sử</p>';
    }
  }
};
