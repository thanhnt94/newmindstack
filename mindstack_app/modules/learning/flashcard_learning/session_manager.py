# File: mindstack_app/modules/learning/flashcard_learning/session_manager.py
# Phiên bản: 3.5
# MỤC ĐÍCH: Nâng cấp để gửi kèm thống kê của thẻ hiện tại ra frontend.
# ĐÃ SỬA: Cập nhật hàm get_next_batch để lấy và gửi kèm initial_stats.

from flask import session, current_app, url_for
from flask_login import current_user
from ....models import db, LearningItem, FlashcardProgress, LearningGroup, User, LearningContainer
from .algorithms import (
    get_new_only_items,
    get_due_items,
    get_hard_items,
    get_mixed_items,
    get_all_review_items,
    get_all_items_for_autoplay,
    get_accessible_flashcard_set_ids,
    get_pronunciation_items,
    get_writing_items,
    get_quiz_items,
    get_essay_items,
    get_listening_items,
    get_speaking_items,
)
from .flashcard_logic import process_flashcard_answer
from .flashcard_stats_logic import get_flashcard_item_statistics
from .config import FlashcardLearningConfig
from sqlalchemy.sql import func
from sqlalchemy.orm.attributes import flag_modified
import random
import datetime
import os
import asyncio
from .audio_service import AudioService
from mindstack_app.modules.shared.utils.media_paths import get_media_folders, build_relative_media_path

audio_service = AudioService()


def _normalize_capability_flags(raw_flags):
    """Chuẩn hóa dữ liệu capability trong ai_settings thành tập hợp chuỗi."""
    normalized = set()
    if isinstance(raw_flags, (list, tuple, set)):
        for value in raw_flags:
            if isinstance(value, str) and value:
                normalized.add(value)
    elif isinstance(raw_flags, dict):
        for key, enabled in raw_flags.items():
            if enabled and isinstance(key, str) and key:
                normalized.add(key)
    elif isinstance(raw_flags, str) and raw_flags:
        normalized.add(raw_flags)
    return normalized

class FlashcardSessionManager:
    """
    Mô tả: Quản lý phiên học Flashcard cho một người dùng.
    """
    SESSION_KEY = 'flashcard_session'

    def __init__(self, user_id, set_id, mode,
                 total_items_in_session, processed_item_ids,
                 correct_answers, incorrect_answers, vague_answers, start_time):
        self.user_id = user_id
        self.set_id = set_id
        self.mode = mode
        self.total_items_in_session = total_items_in_session
        self.processed_item_ids = processed_item_ids
        self.correct_answers = correct_answers
        self.incorrect_answers = incorrect_answers
        self.vague_answers = vague_answers
        self.start_time = start_time
        self._media_folders_cache = None

    @classmethod
    def from_dict(cls, session_dict):
        instance = cls(
            user_id=session_dict['user_id'],
            set_id=session_dict['set_id'],
            mode=session_dict['mode'],
            total_items_in_session=session_dict['total_items_in_session'],
            processed_item_ids=session_dict.get('processed_item_ids', []),
            correct_answers=session_dict['correct_answers'],
            incorrect_answers=session_dict['incorrect_answers'],
            vague_answers=session_dict['vague_answers'],
            start_time=session_dict['start_time']
        )
        instance._media_folders_cache = None
        return instance

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'set_id': self.set_id,
            'mode': self.mode,
            'total_items_in_session': self.total_items_in_session,
            'processed_item_ids': self.processed_item_ids,
            'current_batch_start_index': len(self.processed_item_ids),
            'correct_answers': self.correct_answers,
            'incorrect_answers': self.incorrect_answers,
            'vague_answers': self.vague_answers,
            'start_time': self.start_time
        }

    @classmethod
    def start_new_flashcard_session(cls, set_id, mode):
        user_id = current_user.user_id
        cls.end_flashcard_session()
        mode_config = next((m for m in FlashcardLearningConfig.FLASHCARD_MODES if m['id'] == mode), None)
        if not mode_config and mode in ('autoplay_all', 'autoplay_learned'):
            mode_config = {'id': mode}
        if not mode_config:
            return False

        algorithm_func = {
            'new_only': get_new_only_items,
            'due_only': get_due_items,
            'hard_only': get_hard_items,
            'mixed_srs': get_mixed_items,
            'all_review': get_all_review_items,
            'pronunciation_practice': get_pronunciation_items,
            'writing_practice': get_writing_items,
            'quiz_practice': get_quiz_items,
            'essay_practice': get_essay_items,
            'listening_practice': get_listening_items,
            'speaking_practice': get_speaking_items,
            'autoplay_all': get_all_items_for_autoplay,
            'autoplay_learned': get_all_review_items,
        }.get(mode)
        if not algorithm_func: return False

        accessible_ids = set(get_accessible_flashcard_set_ids(user_id))
        normalized_set_id = set_id

        if set_id == 'all':
            if not accessible_ids:
                current_app.logger.info(
                    "FlashcardSessionManager: Người dùng không có bộ thẻ nào khả dụng cho chế độ 'all'."
                )
                return False
        elif isinstance(set_id, list):
            filtered_ids = []
            for set_value in set_id:
                try:
                    set_int = int(set_value)
                except (TypeError, ValueError):
                    continue
                if set_int in accessible_ids:
                    filtered_ids.append(set_int)

            if not filtered_ids:
                current_app.logger.info(
                    "FlashcardSessionManager: Không có bộ thẻ nào khả dụng sau khi lọc chế độ multi-selection."
                )
                return False

            normalized_set_id = filtered_ids
        else:
            try:
                set_id_int = int(set_id)
            except (TypeError, ValueError):
                current_app.logger.warning(
                    "FlashcardSessionManager: ID bộ thẻ không hợp lệ khi khởi tạo phiên học."
                )
                return False

            if set_id_int not in accessible_ids:
                current_app.logger.info(
                    "FlashcardSessionManager: Người dùng không có quyền truy cập bộ thẻ đã chọn."
                )
                return False

            normalized_set_id = set_id_int

        total_items_in_session = algorithm_func(user_id, normalized_set_id, None).count()
        if total_items_in_session == 0: return False

        new_session_manager = cls(
            user_id=user_id, set_id=normalized_set_id, mode=mode,
            total_items_in_session=total_items_in_session,
            processed_item_ids=[], correct_answers=0,
            incorrect_answers=0, vague_answers=0,
            start_time=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
        session[cls.SESSION_KEY] = new_session_manager.to_dict()
        session.modified = True
        return True

    def _get_media_folders(self):
        if self._media_folders_cache is None:
            container = LearningContainer.query.get(self.set_id)
            if container:
                folders = getattr(container, 'media_folders', {}) or {}
                if not folders:
                    settings_payload = container.ai_settings or {}
                    if isinstance(settings_payload, dict):
                        folders = get_media_folders(settings_payload)
                self._media_folders_cache = dict(folders)
            else:
                self._media_folders_cache = {}
        return self._media_folders_cache

    def _get_media_absolute_url(self, file_path, media_type=None):
        if not file_path:
            return None
        try:
            folders = self._get_media_folders()
            relative_path = build_relative_media_path(file_path, folders.get(media_type) if media_type else None)
            if not relative_path:
                return None
            if relative_path.startswith(('http://', 'https://')):
                return relative_path
            if relative_path.startswith('/'):
                return url_for('static', filename=relative_path.lstrip('/'))
            return url_for('static', filename=relative_path)
        except Exception:
            return None

    def get_next_batch(self):
        next_item = None
        exclusion_condition = None
        if self.processed_item_ids:
            exclusion_condition = LearningItem.item_id.notin_(self.processed_item_ids)

        def apply_exclusion(query):
            if exclusion_condition is not None:
                return query.filter(exclusion_condition)
            return query

        if self.mode == 'new_only':
            query = apply_exclusion(
                get_new_only_items(self.user_id, self.set_id, None)
            ).order_by(LearningItem.order_in_container.asc())
            next_item = query.first()
        elif self.mode == 'due_only':
            query = apply_exclusion(
                get_due_items(self.user_id, self.set_id, None)
            ).order_by(FlashcardProgress.due_time.asc())
            next_item = query.first()
        elif self.mode == 'hard_only':
            query = apply_exclusion(
                get_hard_items(self.user_id, self.set_id, None)
            ).order_by(FlashcardProgress.due_time.asc(), LearningItem.item_id.asc())
            next_item = query.first()
        elif self.mode == 'all_review':
            query = apply_exclusion(
                get_all_review_items(self.user_id, self.set_id, None)
            ).order_by(FlashcardProgress.due_time.asc(), LearningItem.item_id.asc())
            next_item = query.first()
        elif self.mode == 'autoplay_learned':
            query = apply_exclusion(
                get_all_review_items(self.user_id, self.set_id, None)
            ).order_by(LearningItem.order_in_container.asc(), LearningItem.item_id.asc())
            next_item = query.first()
        elif self.mode == 'autoplay_all':
            query = apply_exclusion(
                get_all_items_for_autoplay(self.user_id, self.set_id, None)
            ).order_by(LearningItem.order_in_container.asc(), LearningItem.item_id.asc())
            next_item = query.first()
        elif self.mode == 'pronunciation_practice':
            query = apply_exclusion(
                get_pronunciation_items(self.user_id, self.set_id, None)
            ).order_by(LearningItem.order_in_container.asc(), LearningItem.item_id.asc())
            next_item = query.first()
        elif self.mode == 'writing_practice':
            query = apply_exclusion(
                get_writing_items(self.user_id, self.set_id, None)
            ).order_by(LearningItem.order_in_container.asc(), LearningItem.item_id.asc())
            next_item = query.first()
        elif self.mode == 'quiz_practice':
            query = apply_exclusion(
                get_quiz_items(self.user_id, self.set_id, None)
            ).order_by(LearningItem.order_in_container.asc(), LearningItem.item_id.asc())
            next_item = query.first()
        else:
            due_query = apply_exclusion(
                get_due_items(self.user_id, self.set_id, None)
            ).order_by(FlashcardProgress.due_time.asc())
            next_item = due_query.first()
            if not next_item:
                new_query = apply_exclusion(
                    get_new_only_items(self.user_id, self.set_id, None)
                ).order_by(LearningItem.order_in_container.asc())
                next_item = new_query.first()

        if not next_item:
            return None

        # ĐÃ THÊM: Lấy thống kê ban đầu cho thẻ sắp hiển thị
        initial_stats = get_flashcard_item_statistics(self.user_id, next_item.item_id)

        container_capabilities = set()
        try:
            container = LearningContainer.query.get(next_item.container_id)
            if container:
                if hasattr(container, 'capability_flags'):
                    container_capabilities = container.capability_flags()
                else:
                    settings_payload = container.ai_settings if hasattr(container, 'ai_settings') else None
                    if isinstance(settings_payload, dict):
                        container_capabilities = _normalize_capability_flags(
                            settings_payload.get('capabilities')
                        )
        except Exception:
            container_capabilities = set()

        item_dict = {
            'item_id': next_item.item_id,
            'container_id': next_item.container_id,
            'content': {
                'front': next_item.content.get('front', ''),
                'back': next_item.content.get('back', ''),
                'front_audio_content': next_item.content.get('front_audio_content', ''),
                'front_audio_url': self._get_media_absolute_url(next_item.content.get('front_audio_url'), 'audio'),
                'back_audio_content': next_item.content.get('back_audio_content', ''),
                'back_audio_url': self._get_media_absolute_url(next_item.content.get('back_audio_url'), 'audio'),
                'front_img': self._get_media_absolute_url(next_item.content.get('front_img'), 'image'),
                'back_img': self._get_media_absolute_url(next_item.content.get('back_img'), 'image'),
                'supports_pronunciation': bool(next_item.content.get('supports_pronunciation')) or (
                    'supports_pronunciation' in container_capabilities
                ),
                'supports_writing': bool(next_item.content.get('supports_writing')) or (
                    'supports_writing' in container_capabilities
                ),
                'supports_quiz': bool(next_item.content.get('supports_quiz')) or (
                    'supports_quiz' in container_capabilities
                ),
                'supports_essay': bool(next_item.content.get('supports_essay')) or (
                    'supports_essay' in container_capabilities
                ),
                'supports_listening': bool(next_item.content.get('supports_listening')) or (
                    'supports_listening' in container_capabilities
                ),
                'supports_speaking': bool(next_item.content.get('supports_speaking')) or (
                    'supports_speaking' in container_capabilities
                ),
            },
            'ai_explanation': next_item.ai_explanation,
            'initial_stats': initial_stats  # Gửi kèm thống kê
        }
        
        self.processed_item_ids.append(next_item.item_id)
        session[self.SESSION_KEY] = self.to_dict()
        session.modified = True

        return {
            'items': [item_dict],
            'start_index': len(self.processed_item_ids) - 1,
            'total_items_in_session': self.total_items_in_session,
            'session_correct_answers': self.correct_answers,
            'session_incorrect_answers': self.incorrect_answers,
            'session_vague_answers': self.vague_answers,
            'session_total_answered': self.correct_answers + self.incorrect_answers + self.vague_answers
        }

    def process_flashcard_answer(self, item_id, user_answer_quality):
        try:
            current_user_obj = User.query.get(self.user_id)
            current_user_total_score = current_user_obj.total_score if current_user_obj else 0

            score_change, updated_total_score, answer_result_type, new_progress_status, item_stats = process_flashcard_answer(
                user_id=self.user_id,
                item_id=item_id,
                user_answer_quality=user_answer_quality,
                current_user_total_score=current_user_total_score,
                mode=self.mode
            )
            
            if answer_result_type == 'correct':
                self.correct_answers += 1
            elif answer_result_type == 'vague':
                self.vague_answers += 1
            elif answer_result_type == 'incorrect':
                self.incorrect_answers += 1
            elif answer_result_type == 'preview':
                if item_id in self.processed_item_ids:
                    self.processed_item_ids.remove(item_id)

            session[self.SESSION_KEY] = self.to_dict()
            session.modified = True
            
            return {
                'success': True,
                'score_change': score_change,
                'updated_total_score': updated_total_score,
                'answer_result_type': answer_result_type,
                'new_progress_status': new_progress_status,
                'statistics': item_stats
            }
        except Exception as e:
            current_app.logger.error(f"Lỗi khi xử lý câu trả lời flashcard: {e}", exc_info=True)
            return {'error': f'Lỗi khi xử lý câu trả lời: {str(e)}'}

    @classmethod
    def end_flashcard_session(cls):
        if cls.SESSION_KEY in session:
            session.pop(cls.SESSION_KEY, None)
        return {'message': 'Phiên học đã kết thúc.'}

    @classmethod
    def get_session_status(cls):
        return session.get(cls.SESSION_KEY)