# File: mindstack_app/modules/learning/flashcard_learning/session_manager.py
# Phiên bản: 3.5
# MỤC ĐÍCH: Nâng cấp để gửi kèm thống kê của thẻ hiện tại ra frontend.
# ĐÃ SỬA: Cập nhật hàm get_next_batch để lấy và gửi kèm initial_stats.

from flask import session, current_app, url_for
from flask_login import current_user
from ....models import db, LearningItem, FlashcardProgress, LearningGroup, User
from .algorithms import (
    get_new_only_items,
    get_due_items,
    get_hard_items,
    get_mixed_items,
    get_accessible_flashcard_set_ids,
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

audio_service = AudioService()

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

    @classmethod
    def from_dict(cls, session_dict):
        return cls(
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
        if not mode_config: return False

        algorithm_func = {'new_only': get_new_only_items, 'due_only': get_due_items, 'hard_only': get_hard_items, 'mixed_srs': get_mixed_items}.get(mode)
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

    def _get_media_absolute_url(self, file_path):
        if not file_path: return None
        try:
            if file_path.startswith('/'): file_path = file_path.lstrip('/')
            return url_for('static', filename=file_path)
        except Exception: return None

    def get_next_batch(self):
        next_item = None
        due_item = get_due_items(self.user_id, self.set_id, None).filter(
            LearningItem.item_id.notin_(self.processed_item_ids)
        ).order_by(FlashcardProgress.due_time.asc()).first()
        
        if due_item:
            next_item = due_item
        else:
            new_item = get_new_only_items(self.user_id, self.set_id, None).filter(
                LearningItem.item_id.notin_(self.processed_item_ids)
            ).order_by(LearningItem.order_in_container.asc()).first()
            if new_item: next_item = new_item

        if not next_item: return None

        # ĐÃ THÊM: Lấy thống kê ban đầu cho thẻ sắp hiển thị
        initial_stats = get_flashcard_item_statistics(self.user_id, next_item.item_id)

        item_dict = {
            'item_id': next_item.item_id,
            'container_id': next_item.container_id,
            'content': {
                'front': next_item.content.get('front', ''),
                'back': next_item.content.get('back', ''),
                'front_audio_content': next_item.content.get('front_audio_content', ''),
                'front_audio_url': self._get_media_absolute_url(next_item.content.get('front_audio_url')),
                'back_audio_content': next_item.content.get('back_audio_content', ''),
                'back_audio_url': self._get_media_absolute_url(next_item.content.get('back_audio_url')),
                'front_img': self._get_media_absolute_url(next_item.content.get('front_img')),
                'back_img': self._get_media_absolute_url(next_item.content.get('back_img')),
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
                current_user_total_score=current_user_total_score
            )
            
            if answer_result_type == 'correct': self.correct_answers += 1
            elif answer_result_type == 'vague': self.vague_answers += 1
            elif answer_result_type == 'incorrect': self.incorrect_answers += 1

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