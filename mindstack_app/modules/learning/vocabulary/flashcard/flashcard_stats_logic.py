# File: mindstack_app/modules/learning/flashcard_learning/flashcard_stats_logic.py
# Phiên bản: 2.1
# MỤC ĐÍCH: Cập nhật logic thống kê để phản ánh đầy đủ các chỉ số của SM-2.
# ĐÃ SỬA: Thay đổi cách tính correct_rate, hard_count và thêm các chỉ số SM-2.

import datetime

from .....models import FlashcardProgress


def get_flashcard_item_statistics(user_id, item_id):
    """
    Truy vấn và tính toán các thống kê chi tiết cho một flashcard cụ thể của người dùng.

    Args:
        user_id (int): ID của người dùng.
        item_id (int): ID của flashcard.

    Returns:
        dict: Một dictionary chứa các thống kê của flashcard.
    """
    progress = FlashcardProgress.query.filter_by(user_id=user_id, item_id=item_id).first()

    base_stats = {
        'times_reviewed': 0,
        'correct_count': 0,
        'incorrect_count': 0,
        'vague_count': 0,
        'correct_rate': 0.0,
        'current_streak': 0,
        'longest_streak': 0,
        'first_seen': None,
        'last_reviewed': None,
        'next_review': None,
        'easiness_factor': 2.5,
        'repetitions': 0,
        'interval': 0,
        'status': 'new',
        'preview_count': 0,
        'has_real_reviews': False,
        'has_preview_history': False,
        'has_preview_only': False,
        'recent_reviews': [],
    }

    if not progress:
        return base_stats

    stats = base_stats.copy()
    stats.update({
        'first_seen': progress.first_seen_timestamp.isoformat() if progress.first_seen_timestamp else None,
        'last_reviewed': progress.last_reviewed.isoformat() if progress.last_reviewed else None,
        'next_review': progress.due_time.isoformat() if progress.due_time else None,
        'easiness_factor': round(progress.easiness_factor, 2),
        'repetitions': progress.repetitions,
        'interval': progress.interval,
        'status': progress.status,
    })

    history = progress.review_history or []
    if not history:
        return stats

    preview_entries = []
    review_qualities = []
    normalized_review_entries = []

    def _normalize_timestamp(value):
        if isinstance(value, datetime.datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=datetime.timezone.utc)
            return value.isoformat()
        if isinstance(value, str):
            try:
                parsed = datetime.datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=datetime.timezone.utc)
                return parsed.isoformat()
            except ValueError:
                return value
        return None

    for entry in history:
        if not isinstance(entry, dict):
            continue

        quality = entry.get('user_answer_quality')
        timestamp = _normalize_timestamp(entry.get('timestamp'))
        entry_type = entry.get('type')

        normalized_entry = {
            'timestamp': timestamp,
            'type': entry_type or ('preview' if quality is None else 'review'),
        }

        if quality is None:
            preview_entries.append(normalized_entry)
            continue

        try:
            quality_value = int(float(quality))
        except (TypeError, ValueError):
            quality_value = None

        if quality_value is None:
            continue

        normalized_entry.update({
            'user_answer_quality': quality_value,
            'result': 'correct' if quality_value >= 4 else ('vague' if quality_value >= 2 else 'incorrect')
        })

        review_qualities.append(quality_value)
        normalized_review_entries.append(normalized_entry)

    stats['preview_count'] = len(preview_entries)
    stats['has_preview_history'] = stats['preview_count'] > 0

    if not review_qualities:
        stats['has_preview_only'] = stats['has_preview_history']
        stats['recent_reviews'] = []
        return stats

    total_reviews = len(review_qualities)
    correct_count = 0
    incorrect_count = 0
    vague_count = 0
    current_streak = 0
    longest_streak = 0

    for quality in review_qualities:
        if quality >= 3:
            correct_count += 1
            current_streak += 1
        else:
            incorrect_count += 1
            if current_streak > longest_streak:
                longest_streak = current_streak
            current_streak = 0

        if quality == 2:
            vague_count += 1

    if current_streak > longest_streak:
        longest_streak = current_streak

    correct_rate = (correct_count / total_reviews) * 100 if total_reviews > 0 else 0.0

    stats.update({
        'times_reviewed': total_reviews,
        'correct_count': correct_count,
        'incorrect_count': incorrect_count,
        'vague_count': vague_count,
        'correct_rate': round(correct_rate, 2),
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'has_real_reviews': True,
        'has_preview_only': stats['has_preview_history'] and total_reviews == 0,
        'recent_reviews': [entry.copy() for entry in normalized_review_entries[-10:]],
    })

    return stats
