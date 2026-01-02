/**
 * Render Engine for Flashcard Session
 * Handles HTML generation, Stats rendering, and Card layout adjustments.
 */
window.RenderEngine = (function () {

  // Formatting Utilities
  function formatTextForHtml(text) {
    if (text == null) return '';
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML.replace(/\r?\n/g, '<br>');
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
    if (Number.isNaN(date.getTime())) return fallback;
    try {
      return date.toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short' });
    } catch (err) {
      return fallback;
    }
  }

  // Stats Rendering
  function renderCardStatsHtml(stats, scoreChange = 0, cardContent = {}, isInitial = false) {
    if (!stats) return `<div class="empty-state"><i class="fas fa-info-circle"></i> ${isInitial ? 'Đây là thẻ mới.' : 'Không có dữ liệu thống kê.'}</div>`;

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
      'new': 'Mới', 'learning': 'Đang học', 'review': 'Ôn tập',
      'relearning': 'Ôn lại', 'hard': 'Khó', 'easy': 'Dễ', 'suspended': 'Tạm dừng'
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
      } catch (err) { return 'Không rõ'; }
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
      ? `<div class="stats-section stats-section--performance"><div class="stats-section__header"><div class="icon-bubble"><i class="fas fa-chart-line"></i></div><div><h4>Hiệu suất trả lời</h4><p>Tỷ lệ ghi nhớ dựa trên toàn bộ lịch sử của thẻ.</p></div></div><div class="progress-stack"><div class="progress-bar-group"><div class="progress-bar-label"><span class="label-title"><span class="progress-dot"></span> Nhớ</span><span class="progress-bar-stat">${correctCount} lượt · ${correctPercentDisplay}%</span></div><div class="progress-bar-container"><div class="progress-bar-fill progress-bar-fill-correct" style="--progress:${correctWidth}%;"></div></div></div><div class="progress-bar-group"><div class="progress-bar-label"><span class="label-title"><span class="progress-dot vague"></span> Mơ hồ</span><span class="progress-bar-stat">${vagueCount} lượt · ${vaguePercentDisplay}%</span></div><div class="progress-bar-container"><div class="progress-bar-fill progress-bar-fill-vague" style="--progress:${vagueWidth}%;"></div></div></div><div class="progress-bar-group"><div class="progress-bar-label"><span class="label-title"><span class="progress-dot incorrect"></span> Quên</span><span class="progress-bar-stat">${incorrectCount} lượt · ${incorrectPercentDisplay}%</span></div><div class="progress-bar-container"><div class="progress-bar-fill progress-bar-fill-incorrect" style="--progress:${incorrectWidth}%;"></div></div></div></div></div>`
      : `<div class="stats-section stats-section--performance"><div class="stats-section__header"><div class="icon-bubble"><i class="fas fa-chart-line"></i></div><div><h4>Hiệu suất trả lời</h4><p>Thống kê sẽ xuất hiện sau khi bạn chấm điểm thẻ này.</p></div></div><div class="empty-state"><i class="fas fa-info-circle"></i> Bắt đầu trả lời để mở khóa biểu đồ hiệu suất.</div></div>`;

    const insightSection = `<div class="stats-section stats-section--insight"><div class="stats-section__header"><div class="icon-bubble"><i class="fas fa-bullseye"></i></div><div><h4>Chỉ số ghi nhớ</h4><p>Tổng hợp theo thuật toán SM-2.</p></div></div><div class="insight-grid">${!isInitial ? `<div class="insight-card insight-card--highlight"><span class="insight-card__label">Điểm phiên này</span><span class="insight-card__value ${scoreChangeClass}">${scoreChangeSign}${scoreChange}</span><span class="insight-card__muted">Sau lượt trả lời vừa rồi</span></div>` : ''}<div class="insight-card"><span class="insight-card__label">Trạng thái</span><span class="status-chip status-${statusKey}"><i class="fas fa-circle"></i> ${statusLabel}</span><span class="insight-card__muted">Theo tiến trình hiện tại</span></div><div class="insight-card"><span class="insight-card__label">Tỷ lệ chính xác</span><span class="insight-card__value">${correctRateDisplay}%</span><span class="insight-card__muted">${totalReviews > 0 ? `${correctCount} đúng · ${incorrectCount} sai` : 'Chưa có lượt ôn'}</span></div><div class="insight-card"><span class="insight-card__label">Lượt ôn</span><span class="insight-card__value">${totalReviews}</span><span class="insight-card__muted">${previewCount > 0 ? `${previewCount} lần xem thử` : 'Chưa xem trước'}</span></div><div class="insight-card"><span class="insight-card__label">Chuỗi hiện tại</span><span class="insight-card__value">${currentStreak}</span><span class="insight-card__muted">${currentStreak > 0 ? 'Lượt đúng liên tiếp' : 'Chưa có chuỗi'}</span></div><div class="insight-card"><span class="insight-card__label">Chuỗi dài nhất</span><span class="insight-card__value">${longestStreak}</span><span class="insight-card__muted">${longestStreak > 0 ? 'Kỷ lục ghi nhớ' : 'Chưa xác định'}</span></div><div class="insight-card"><span class="insight-card__label">Hệ số dễ (EF)</span><span class="insight-card__value">${easinessFactor}</span><span class="insight-card__muted">Điều chỉnh sau mỗi lần ôn</span></div><div class="insight-card"><span class="insight-card__label">Lặp lại (n)</span><span class="insight-card__value">${repetitions}</span><span class="insight-card__muted">Số lần đã ghi nhớ</span></div><div class="insight-card"><span class="insight-card__label">Khoảng cách (I)</span><span class="insight-card__value">${formattedIntervalDisplay || 'Chưa có'}</span><span class="insight-card__muted">Thời gian đến lần ôn tiếp theo</span></div></div></div>`;

    const recentSection = recentReviews.length
      ? `<div class="stats-section stats-section--recent"><div class="stats-section__header"><div class="icon-bubble"><i class="fas fa-history"></i></div><div><h4>Lượt trả lời gần đây</h4><p>Theo dõi tối đa 10 lượt mới nhất bằng biểu tượng màu sắc.</p></div></div><div class="recent-answers-track" role="list">${recentReviews.map(entry => {
        const resultKey = (entry.result || '').toLowerCase();
        const config = recentReviewConfig[resultKey] || recentReviewConfig.preview;
        const tooltip = `${config.label} · ${formatRecentTimestamp(entry.timestamp)}`;
        return `<div class="recent-answer-dot recent-answer-dot--${resultKey || 'preview'}" role="listitem" title="${tooltip}"><i class="${config.icon}" aria-hidden="true"></i></div>`;
      }).join('')}</div></div>`
      : '';

    const timelineSection = `<div class="stats-section stats-section--timeline"><div class="stats-section__header"><div class="icon-bubble"><i class="fas fa-route"></i></div><div><h4>Mốc thời gian học</h4><p>Quản lý lịch sử ôn tập của riêng bạn.</p></div></div><div class="timeline-card"><div class="timeline-item"><div class="timeline-icon"><i class="fas fa-flag"></i></div><div><div class="timeline-label">Lần đầu gặp</div><div class="timeline-value">${firstSeen}</div></div></div><div class="timeline-item"><div class="timeline-icon"><i class="fas fa-redo"></i></div><div><div class="timeline-label">Ôn gần nhất</div><div class="timeline-value">${lastReviewed}</div></div></div><div class="timeline-item"><div class="timeline-icon"><i class="fas fa-calendar-check"></i></div><div><div class="timeline-label">Lịch ôn tiếp theo</div><div class="timeline-value">${dueTime}</div></div></div></div></div>`;

    const cardDetails = cardContent.front ? `<div class="card-info-section"><div class="card-info-title collapsed" data-toggle="card-details-content"><i class="fas fa-caret-right"></i><span>Chi tiết thẻ</span></div><div class="card-info-content"><p><span class="label">Mặt trước</span>${formatTextForHtml(cardContent.front)}</p><p><span class="label">Mặt sau</span>${formatTextForHtml(cardContent.back)}</p></div></div>` : '';

    return [cardDetails, introNotice, progressSection, insightSection, recentSection, timelineSection].join('');
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

    const statusColors = { 'new': 'bg-blue-100 text-blue-700', 'learning': 'bg-orange-100 text-orange-700', 'review': 'bg-emerald-100 text-emerald-700', 'relearning': 'bg-purple-100 text-purple-700', 'hard': 'bg-red-100 text-red-700' };
    const statusClass = statusColors[String(stats.status).toLowerCase()] || 'bg-slate-100 text-slate-700';

    let historyHtml = '';
    if (stats.recent_reviews && stats.recent_reviews.length > 0) {
      const icons = stats.recent_reviews.slice().reverse().map((review) => {
        const isCorrect = review.result === 'correct';
        const isWrong = review.result === 'incorrect';
        const colorClass = isCorrect ? 'bg-emerald-500' : (isWrong ? 'bg-rose-500' : 'bg-slate-400');
        const icon = isCorrect ? 'fa-check' : (isWrong ? 'fa-times' : 'fa-minus');
        return `<span class="w-6 h-6 rounded-full ${colorClass} flex items-center justify-center ring-1 ring-white shadow-sm"><i class="fas ${icon} text-white text-[10px]"></i></span>`;
      }).join('');
      historyHtml = `<div class="mb-3 bg-white border border-slate-100 p-3 rounded-2xl shadow-[0_2px_8px_rgba(0,0,0,0.04)]"><div class="flex items-center gap-2 mb-2"><i class="fas fa-history text-xs text-slate-400"></i><span class="text-xs uppercase font-bold text-slate-400">Lịch sử thẻ này</span></div><div class="flex flex-wrap gap-1.5">${icons}</div></div>`;
    }

    return `<div class="mobile-stats-content"><div class="flex items-center justify-between mb-5"><span class="px-3 py-1 rounded-full text-xs font-bold ${statusClass}">${statusLabel}</span><div class="text-right"><div class="text-[10px] text-slate-400 uppercase font-bold">Lần ôn tới</div><div class="text-xs font-semibold text-slate-700">${nextReview}</div></div></div><div class="mb-6 bg-white border border-slate-100 p-4 rounded-2xl shadow-[0_2px_8px_rgba(0,0,0,0.04)]"><div class="flex justify-between items-end mb-2"><span class="text-sm font-bold text-slate-700">Độ chính xác</span><span class="text-2xl font-black text-slate-800">${correctRate}%</span></div><div class="h-3 w-full bg-slate-100 rounded-full overflow-hidden"><div class="h-full bg-gradient-to-r from-blue-500 to-emerald-400" style="width: ${correctRate}%"></div></div><div class="mt-2 flex justify-between text-xs font-medium text-slate-400"><span>${correctCount} đúng</span><span>${incorrectCount} sai</span></div></div><div class="grid grid-cols-3 gap-3 mb-6"><div class="bg-slate-50 p-3 rounded-2xl flex flex-col items-center text-center"><span class="text-[10px] uppercase font-bold text-slate-400 mb-1">Chuỗi</span><span class="text-lg font-black text-slate-700">${streak}</span></div><div class="bg-slate-50 p-3 rounded-2xl flex flex-col items-center text-center"><span class="text-[10px] uppercase font-bold text-slate-400 mb-1">Lượt ôn</span><span class="text-lg font-black text-slate-700">${totalReviews}</span></div><div class="bg-slate-50 p-3 rounded-2xl flex flex-col items-center text-center"><span class="text-[10px] uppercase font-bold text-slate-400 mb-1">Độ khó</span><span class="text-lg font-black text-slate-700">${ef}</span></div></div>${historyHtml}</div>`;
  }

  // Card Rendering (Desktop & Mobile)
  function renderDesktopCardHtml(data, o) {
    // o = options { itemId, canEditCurrentCard, editUrl, isMediaHidden, isAudioAutoplayEnabled, ... }

    const aiButtonHtml = `<button class="icon-btn open-ai-modal-btn" data-item-id="${o.itemId}"><i class="fas fa-robot"></i></button>`;
    const noteButtonHtml = `<button class="icon-btn open-note-panel-btn" data-item-id="${o.itemId}"><i class="fas fa-sticky-note"></i></button>`;
    const feedbackButtonHtml = `<button class="icon-btn open-feedback-modal-btn" data-item-id="${o.itemId}"><i class="fas fa-flag"></i></button>`;

    const editButtonHtml = o.canEditCurrentCard
      ? `<button class="icon-btn edit-card-btn" onclick="window.parent.openModal('${o.editUrl}')"><i class="fas fa-pencil-alt"></i></button>`
      : '';

    const imageToggleButtonHtml = `<button class="icon-btn image-toggle-btn ${o.isMediaHidden ? 'is-active' : ''}" aria-pressed="${o.isMediaHidden}" title="${o.isMediaHidden ? 'Bật ảnh' : 'Tắt ảnh'}"><i class="fas ${o.isMediaHidden ? 'fa-image-slash' : 'fa-image'}"></i></button>`;
    const audioAutoplayToggleButtonHtml = `<button class="icon-btn audio-autoplay-toggle-btn ${o.isAudioAutoplayEnabled ? 'is-active' : ''}" aria-pressed="${o.isAudioAutoplayEnabled}" title="${o.isAudioAutoplayEnabled ? 'Tắt tự động phát audio' : 'Bật tự động phát audio'}"><i class="fas ${o.isAudioAutoplayEnabled ? 'fa-volume-up' : 'fa-volume-mute'}"></i></button>`;

    const audioButtonHtmlFront = `<button class="icon-btn play-audio-btn ${o.hasFrontAudio ? '' : 'is-disabled'}" data-audio-target="#front-audio-desktop" data-side="front" data-item-id="${o.itemId}" data-content-to-read="${o.frontAudioContent || ''}" ${o.hasFrontAudio ? '' : 'disabled'}><i class="fas fa-volume-up"></i></button>`;
    const audioButtonHtmlBack = `<button class="icon-btn play-audio-btn ${o.hasBackAudio ? '' : 'is-disabled'}" data-audio-target="#back-audio-desktop" data-side="back" data-item-id="${o.itemId}" data-content-to-read="${o.backAudioContent || ''}" ${o.hasBackAudio ? '' : 'disabled'}><i class="fas fa-volume-up"></i></button>`;

    const flipButtonHtml = `<button class="js-flip-card-btn flip-card-btn"><i class="fas fa-sync-alt mr-2"></i>Lật thẻ</button>`;

    const leftToolbarContent = `${aiButtonHtml}${noteButtonHtml}`;

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

    return `
  <div class="flashcard-card-container">
    <div class="js-flashcard-card flashcard-card ${o.cardCategory ? 'flashcard-card--' + o.cardCategory : ''}" data-card-category="${o.cardCategory || 'default'}">
      <div class="face front">
        ${toolbarFront}
        <div class="_card-container">
          <div class="text-area"><div class="flashcard-content-text">${o.fTxt}</div></div>
          ${o.frontImg ? `<div class="media-container"><img src="${o.frontImg}" alt="Mặt trước" onerror="this.onerror=null;this.src='https://placehold.co/200x120?text=Loi+anh';"></div>` : ''}
          <audio id="front-audio-desktop" class="hidden" src="${o.frontAudioUrl || ''}"></audio>
        </div>
        <div class="flip-btn-container">
          ${flipButtonHtml}
        </div>
      </div>
      <div class="face back">
        ${toolbarBack}
        <div class="_card-container">
          <div class="text-area"><div class="flashcard-content-text">${o.bTxt}</div></div>
          ${o.backImg ? `<div class="media-container"><img src="${o.backImg}" alt="Mặt sau" onerror="this.onerror=null;this.src='https://placehold.co/200x120?text=Loi+anh';"></div>` : ''}
        </div>
        <div class="actions js-internal-actions" data-button-count="${o.buttonCount}">${o.buttonsHtml}</div>
        <audio id="back-audio-desktop" class="hidden" src="${o.backAudioUrl || ''}"></audio>
      </div>
    </div>
  </div>`;
  }

  function renderMobileCardHtml(data, o) {
    // o = options
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

    return `
      <div class="flashcard-card-container">
        <div class="js-flashcard-card flashcard-card ${o.cardCategory ? 'flashcard-card--' + o.cardCategory : ''}" data-card-category="${o.cardCategory || 'default'}">
          <div class="face front">
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
          <div class="face back">
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
  }

  // New API: Adjust layout after render
  function adjustCardLayout() {
    document.querySelectorAll('.js-flashcard-card').forEach(card => {
      if (!card) return;
      const textAreas = card.querySelectorAll('.text-area');
      textAreas.forEach(scrollArea => {
        const txt = scrollArea.querySelector('.flashcard-content-text');
        if (!txt) return;

        txt.style.fontSize = '';
        scrollArea.classList.remove('has-scroll');
        scrollArea.parentElement?.classList?.remove('has-scroll');

        setTimeout(() => {
          const hasScroll = scrollArea.scrollHeight > scrollArea.clientHeight;
          if (hasScroll) {
            scrollArea.classList.add('has-scroll');
            scrollArea.parentElement?.classList?.add('has-scroll');
            scrollArea.scrollTop = 0;
          }
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

  return {
    formatTextForHtml,
    formatDateTime,
    renderCardStatsHtml,
    renderMobileCardStatsHtml,
    renderDesktopCardHtml,
    renderMobileCardHtml,
    adjustCardLayout
  };
})();
