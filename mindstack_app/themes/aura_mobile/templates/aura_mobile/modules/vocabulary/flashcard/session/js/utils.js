/**
 * Utility functions for Flashcard Session
 */

function formatTextForHtml(text) {
    if (text == null) return '';
    // Don't escape HTML tags (like <br>), just convert newlines
    return String(text).replace(/\r?\n/g, '<br>');
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

function formatRecentTimestamp(value) {
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
}

// Export functions to global scope
window.formatTextForHtml = formatTextForHtml;
window.extractPlainText = extractPlainText;
window.formatMinutesAsDuration = formatMinutesAsDuration;
window.formatDateTime = formatDateTime;
window.formatRecentTimestamp = formatRecentTimestamp;
