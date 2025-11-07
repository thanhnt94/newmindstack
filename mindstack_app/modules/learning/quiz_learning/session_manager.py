# File: mindstack_app/modules/learning/quiz_learning/session_manager.py
# Phiên bản: 2.2
# MỤC ĐÍCH: Sửa lỗi không tìm thấy URL chỉnh sửa bằng cách thêm container_id vào dữ liệu câu hỏi.

from flask import session, current_app, url_for
from flask_login import current_user
from typing import Optional
from ....models import db, LearningItem, QuizProgress, LearningGroup, User, UserNote, LearningContainer
from .algorithms import (
    get_new_only_items,
    get_reviewed_items,
    get_hard_items,
    get_accessible_quiz_set_ids,
)
from .quiz_logic import process_quiz_answer
from .quiz_stats_logic import get_quiz_item_statistics
from .config import QuizLearningConfig
from sqlalchemy.sql import func
import random
import datetime
import os

from mindstack_app.modules.shared.utils.media_paths import (
    get_media_folders,
    build_relative_media_path,
)

class QuizSessionManager:
    """
    Quản lý phiên học Quiz cho một người dùng.
    Sử dụng Flask session để lưu trữ trạng thái.
    """
    SESSION_KEY = 'quiz_session'

    def __init__(self, user_id, set_id, mode, batch_size,
                 total_items_in_session, processed_item_ids,
                 correct_answers, incorrect_answers, start_time, common_pre_question_text_global):
        """
        Khởi tạo một phiên QuizSessionManager.
        """
        self.user_id = user_id
        self.set_id = set_id
        self.mode = mode
        self.batch_size = batch_size
        self.total_items_in_session = total_items_in_session
        self.processed_item_ids = processed_item_ids
        self.correct_answers = correct_answers
        self.incorrect_answers = incorrect_answers
        self.start_time = start_time
        self.common_pre_question_text_global = common_pre_question_text_global
        self._media_folders_cache: Optional[dict[str, str]] = None
        current_app.logger.debug(f"QuizSessionManager: Instance được khởi tạo/tải. User: {self.user_id}, Set: {self.set_id}, Mode: {self.mode}")

    @classmethod
    def from_dict(cls, session_dict):
        """
        Tạo một instance QuizSessionManager từ một dictionary (thường từ Flask session).
        """
        instance = cls(
            user_id=session_dict['user_id'],
            set_id=session_dict['set_id'],
            mode=session_dict['mode'],
            batch_size=session_dict['batch_size'],
            total_items_in_session=session_dict['total_items_in_session'],
            processed_item_ids=session_dict.get('processed_item_ids', []),
            correct_answers=session_dict['correct_answers'],
            incorrect_answers=session_dict['incorrect_answers'],
            start_time=session_dict['start_time'],
            common_pre_question_text_global=session_dict['common_pre_question_text_global']
        )
        instance._media_folders_cache = None
        return instance

    def to_dict(self):
        """
        Chuyển đổi instance QuizSessionManager thành một dictionary để lưu vào Flask session.
        """
        return {
            'user_id': self.user_id,
            'set_id': self.set_id,
            'mode': self.mode,
            'batch_size': self.batch_size,
            'total_items_in_session': self.total_items_in_session,
            'processed_item_ids': self.processed_item_ids,
            'current_batch_start_index': len(self.processed_item_ids),
            'correct_answers': self.correct_answers,
            'incorrect_answers': self.incorrect_answers,
            'start_time': self.start_time,
            'common_pre_question_text_global': self.common_pre_question_text_global
        }

    @classmethod
    def start_new_quiz_session(cls, set_id, mode, batch_size):
        """
        Khởi tạo một phiên học Quiz mới.
        Lấy danh sách câu hỏi dựa trên chế độ và số lượng yêu cầu.
        """
        print(f">>> SESSION_MANAGER: Bắt đầu start_new_quiz_session cho set_id={set_id}, mode={mode}, batch_size={batch_size} <<<")
        current_app.logger.debug(f"SessionManager: Bắt đầu start_new_quiz_session cho set_id={set_id}, mode={mode}, batch_size={batch_size}")
        user_id = current_user.user_id
        
        cls.end_quiz_session()

        mode_config = next((m for m in QuizLearningConfig.QUIZ_MODES if m['id'] == mode), None)
        if not mode_config:
            print(f">>> SESSION_MANAGER: LỖI - Chế độ học không hợp lệ hoặc không được định nghĩa: {mode} <<<")
            current_app.logger.error(f"SessionManager: Chế độ học không hợp lệ hoặc không được định nghĩa: {mode}")
            return False
        
        algorithm_func = None
        if mode == 'new_only':
            algorithm_func = get_new_only_items
        elif mode == 'due_only':
            algorithm_func = get_reviewed_items
        elif mode == 'hard_only':
            algorithm_func = get_hard_items
        
        if not algorithm_func:
            print(f">>> SESSION_MANAGER: LỖI - Không tìm thấy hàm thuật toán cho chế độ: {mode} <<<")
            current_app.logger.error(f"SessionManager: Không tìm thấy hàm thuật toán cho chế độ: {mode}")
            return False
        
        accessible_ids = set(get_accessible_quiz_set_ids(user_id))
        normalized_set_id = set_id

        if set_id == 'all':
            if not accessible_ids:
                current_app.logger.info(
                    "QuizSessionManager: Người dùng không có bộ quiz nào khả dụng cho chế độ 'all'."
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
                    "QuizSessionManager: Không có bộ quiz nào khả dụng sau khi lọc chế độ multi-selection."
                )
                return False

            normalized_set_id = filtered_ids
        else:
            try:
                set_id_int = int(set_id)
            except (TypeError, ValueError):
                current_app.logger.warning(
                    "QuizSessionManager: ID bộ quiz không hợp lệ khi khởi tạo phiên học."
                )
                return False

            if set_id_int not in accessible_ids:
                current_app.logger.info(
                    "QuizSessionManager: Người dùng không có quyền truy cập bộ quiz đã chọn."
                )
                return False

            normalized_set_id = set_id_int

        total_items_in_session_query = algorithm_func(user_id, normalized_set_id, None)
        total_items_in_session = total_items_in_session_query.count()

        if total_items_in_session == 0:
            cls.end_quiz_session()
            print(">>> SESSION_MANAGER: Không có câu hỏi nào được tìm thấy cho phiên học mới. <<<")
            current_app.logger.warning("SessionManager: Không có câu hỏi nào được tìm thấy cho phiên học mới.")
            return False

        sample_size = min(total_items_in_session, 50)
        
        if total_items_in_session > 0:
            sample_items = total_items_in_session_query.order_by(func.random()).limit(sample_size).all()
            global_pre_texts = [item.content.get('pre_question_text') for item in sample_items if item.content.get('pre_question_text')]
            common_pre_question_text_global = None
            if global_pre_texts and all(p == global_pre_texts[0] for p in global_pre_texts):
                common_pre_question_text_global = global_pre_texts[0]
                print(f">>> SESSION_MANAGER: Phát hiện common_pre_question_text_global: '{common_pre_question_text_global}' <<<")
        else:
            common_pre_question_text_global = None

        new_session_manager = cls(
            user_id=user_id,
            set_id=normalized_set_id,
            mode=mode,
            batch_size=batch_size,
            total_items_in_session=total_items_in_session,
            processed_item_ids=[],
            correct_answers=0,
            incorrect_answers=0,
            start_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            common_pre_question_text_global=common_pre_question_text_global
        )
        session[cls.SESSION_KEY] = new_session_manager.to_dict()
        session.modified = True

        print(f">>> SESSION_MANAGER: Phiên học mới đã được khởi tạo với {total_items_in_session} câu hỏi. Batch size: {batch_size} <<<")
        current_app.logger.debug(f"SessionManager: Phiên học mới đã được khởi tạo với {total_items_in_session} câu hỏi. Batch size: {batch_size}")
        return True

    def _get_media_absolute_url(self, file_path, media_type: Optional[str] = None, *, container: Optional[LearningContainer] = None):
        """
        Chuyển đổi đường dẫn file media tương đối thành URL tuyệt đối.
        """
        if not file_path:
            return None

        try:
            if container:
                folders = self._get_container_media_folders(container)
            else:
                folders = self._get_media_folders()
            relative_path = build_relative_media_path(file_path, folders.get(media_type) if media_type else None)
            if not relative_path:
                return None
            if relative_path.startswith(('http://', 'https://')):
                return relative_path
            static_path = relative_path.lstrip('/')
            full_url = url_for('static', filename=static_path)
            current_app.logger.debug(f"Media URL - Gốc: '{file_path}', URL: '{full_url}'")
            return full_url
        except Exception as e:
            current_app.logger.error(f"Lỗi khi tạo URL cho media '{file_path}': {e}")
            return None

    def _get_media_folders(self):
        if self._media_folders_cache is None:
            container = LearningContainer.query.get(self.set_id)
            if container:
                self._media_folders_cache = self._get_container_media_folders(container)
            else:
                self._media_folders_cache = {}
        return self._media_folders_cache

    @staticmethod
    def _get_container_media_folders(container: Optional[LearningContainer]) -> dict[str, str]:
        if not container:
            return {}
        folders = getattr(container, 'media_folders', {}) or {}
        if folders:
            return dict(folders)
        settings_payload = container.ai_settings or {}
        if isinstance(settings_payload, dict):
            return get_media_folders(settings_payload)
        return {}


    def get_next_batch(self, requested_batch_size):
        """
        Lấy dữ liệu của nhóm câu hỏi tiếp theo trong phiên học.
        """
        current_app.logger.debug(f"SessionManager: Lấy nhóm câu hỏi: Đã xử lý {len(self.processed_item_ids)}/{self.total_items_in_session}, requested_batch_size={requested_batch_size}")
        
        if len(self.processed_item_ids) >= self.total_items_in_session:
            current_app.logger.debug("SessionManager: Hết câu hỏi trong phiên. Đã hiển thị đủ số lượng.")
            return None

        mode_config = next((m for m in QuizLearningConfig.QUIZ_MODES if m['id'] == self.mode), None)
        if not mode_config:
            current_app.logger.error(f"Chế độ học không hợp lệ: {self.mode}")
            return None
        
        algorithm_func = None
        if self.mode == 'new_only':
            algorithm_func = get_new_only_items
        elif self.mode == 'due_only':
            algorithm_func = get_reviewed_items
        elif self.mode == 'hard_only':
            algorithm_func = get_hard_items
        
        if not algorithm_func:
            current_app.logger.error(f"Không tìm thấy hàm thuật toán cho chế độ: {self.mode}")
            return None

        unprocessed_items_query = algorithm_func(self.user_id, self.set_id, None).filter(
            LearningItem.item_id.notin_(self.processed_item_ids)
        )
        
        new_items_to_add_to_session = unprocessed_items_query.order_by(func.random()).limit(requested_batch_size).all()
        
        if not new_items_to_add_to_session:
            current_app.logger.debug("Không còn câu hỏi mới nào để lấy.")
            return None

        items_data = []
        newly_processed_item_ids = []

        for item in new_items_to_add_to_session:
            # Lấy ghi chú cho câu hỏi này
            note = UserNote.query.filter_by(user_id=self.user_id, item_id=item.item_id).first()

            item_dict = {
                'item_id': item.item_id,
                # THAY ĐỔI: Thêm container_id để có thể tạo URL chỉnh sửa
                'container_id': item.container_id,
                'content': item.content,
                'ai_explanation': item.ai_explanation,
                'note_content': note.content if note else '',
                'group_id': item.group_id,
                'group_details': None
            }
            container_obj = item.container if hasattr(item, 'container') else None
            if item_dict['content'].get('question_image_file'):
                item_dict['content']['question_image_file'] = self._get_media_absolute_url(
                    item_dict['content']['question_image_file'], 'image', container=container_obj
                )
            if item_dict['content'].get('question_audio_file'):
                item_dict['content']['question_audio_file'] = self._get_media_absolute_url(
                    item_dict['content']['question_audio_file'], 'audio', container=container_obj
                )

            items_data.append(item_dict)
            newly_processed_item_ids.append(item.item_id)
        
        self.processed_item_ids.extend(newly_processed_item_ids)
        session[self.SESSION_KEY] = self.to_dict()
        session.modified = True

        return {
            'items': items_data,
            'common_pre_question_text_global': self.common_pre_question_text_global,
            'start_index': len(self.processed_item_ids) - len(items_data),
            'total_items_in_session': self.total_items_in_session,
            'session_correct_answers': self.correct_answers,
            'session_total_answered': self.correct_answers + self.incorrect_answers
        }

    def process_answer_batch(self, answers):
        """
        Xử lý một danh sách các câu trả lời của người dùng cho một nhóm câu hỏi.
        """
        print(f">>> SESSION_MANAGER: Bắt đầu process_answer_batch với {len(answers)} đáp án. <<<")
        current_app.logger.debug(f"SessionManager: Bắt đầu process_answer_batch với {len(answers)} đáp án.")
        
        results = []
        
        current_user_obj = User.query.get(self.user_id)
        current_user_total_score = current_user_obj.total_score if current_user_obj else 0

        for answer in answers:
            item_id = answer.get('item_id')
            user_answer_text = answer.get('user_answer')

            score_change, updated_total_score, is_correct, correct_option_char, explanation = process_quiz_answer(
                user_id=self.user_id,
                item_id=item_id,
                user_answer_text=user_answer_text,
                current_user_total_score=current_user_total_score
            )
            current_user_total_score = updated_total_score

            item_stats = get_quiz_item_statistics(self.user_id, item_id)
            
            if is_correct:
                self.correct_answers += 1
                print(f">>> SESSION_MANAGER: Câu trả lời đúng. Điểm thay đổi: {score_change} <<<")
            else:
                self.incorrect_answers += 1
                print(f">>> SESSION_MANAGER: Câu trả lời sai. Điểm thay đổi: {score_change} <<<")
            
            results.append({
                'item_id': item_id,
                'is_correct': is_correct,
                'correct_answer': correct_option_char,
                'explanation': explanation,
                'statistics': item_stats,
                'score_change': score_change,
            })
        
        session[self.SESSION_KEY] = self.to_dict()
        session.modified = True 
        print(f">>> SESSION_MANAGER: Nhóm đáp án đã xử lý. Đã xử lý tổng cộng: {len(self.processed_item_ids)} câu. <<<")

        return results

    @classmethod
    def end_quiz_session(cls):
        """
        Kết thúc phiên học Quiz hiện tại và xóa dữ liệu khỏi session.
        """
        if cls.SESSION_KEY in session:
            session.pop(cls.SESSION_KEY, None)
            print(">>> SESSION_MANAGER: Phiên học đã kết thúc và xóa khỏi session. <<<")
            current_app.logger.debug("SessionManager: Phiên học đã kết thúc và xóa khỏi session.")
        return {'message': 'Phiên học đã kết thúc.'}

    @classmethod
    def get_session_status(cls):
        """
        Lấy trạng thái hiện tại của phiên học.
        """
        status = session.get(cls.SESSION_KEY)
        print(f">>> SESSION_MANAGER: Lấy trạng thái session: {status} <<<")
        current_app.logger.debug(f"SessionManager: Lấy trạng thái session: {status}")
        return status