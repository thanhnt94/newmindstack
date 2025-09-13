# File: mindstack_app/modules/learning/flashcard_learning/session_manager.py
# Phiên bản: 3.1
# MỤC ĐÍCH: Sửa lỗi "Không tìm thấy hàm thuật toán cho chế độ: mixed_srs".
# ĐÃ SỬA: Thêm logic để xử lý chế độ học mới 'mixed_srs' và gọi hàm thuật toán tương ứng.
# ĐÃ SỬA: Import thêm hàm get_mixed_items.

from flask import session, current_app, url_for
from flask_login import current_user
from ....models import db, LearningItem, FlashcardProgress, LearningGroup, User
from .algorithms import get_new_only_items, get_due_items, get_hard_items, get_mixed_items
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

# Khởi tạo một instance của AudioService
audio_service = AudioService()

class FlashcardSessionManager:
    """
    Mô tả: Quản lý phiên học Flashcard cho một người dùng.
           Sử dụng Flask session để lưu trữ trạng thái.
    """
    SESSION_KEY = 'flashcard_session'

    def __init__(self, user_id, set_id, mode,
                 total_items_in_session, processed_item_ids,
                 correct_answers, incorrect_answers, vague_answers, start_time):
        """
        Mô tả: Khởi tạo một phiên FlashcardSessionManager.
        """
        self.user_id = user_id
        self.set_id = set_id
        self.mode = mode
        self.total_items_in_session = total_items_in_session
        self.processed_item_ids = processed_item_ids
        self.correct_answers = correct_answers
        self.incorrect_answers = incorrect_answers
        self.vague_answers = vague_answers
        self.start_time = start_time
        current_app.logger.debug(f"FlashcardSessionManager: Instance được khởi tạo/tải. User: {self.user_id}, Set: {self.set_id}, Mode: {self.mode}")

    @classmethod
    def from_dict(cls, session_dict):
        """
        Mô tả: Tạo một instance FlashcardSessionManager từ một dictionary (thường từ Flask session).
        """
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
        """
        Mô tả: Chuyển đổi instance FlashcardSessionManager thành một dictionary để lưu vào Flask session.
        """
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
        """
        Mô tả: Khởi tạo một phiên học Flashcard mới.
        """
        print(f">>> SESSION_MANAGER: Bắt đầu start_new_flashcard_session cho set_id={set_id}, mode={mode} <<<")
        current_app.logger.debug(f"SessionManager: Bắt đầu start_new_flashcard_session cho set_id={set_id}, mode={mode}")
        user_id = current_user.user_id
        
        cls.end_flashcard_session()

        mode_config = next((m for m in FlashcardLearningConfig.FLASHCARD_MODES if m['id'] == mode), None)
        if not mode_config:
            print(f">>> SESSION_MANAGER: LỖI - Chế độ học không hợp lệ hoặc không được định nghĩa: {mode} <<<")
            current_app.logger.error(f"SessionManager: Chế độ học không hợp lệ hoặc không được định nghĩa: {mode}")
            return False
        
        algorithm_func = None
        if mode == 'new_only':
            algorithm_func = get_new_only_items
        elif mode == 'due_only':
            algorithm_func = get_due_items
        elif mode == 'hard_only':
            algorithm_func = get_hard_items
        # THAY ĐỔI: Thêm chế độ mixed_srs vào đây
        elif mode == 'mixed_srs':
            algorithm_func = get_mixed_items
        
        if not algorithm_func:
            print(f">>> SESSION_MANAGER: LỖI - Không tìm thấy hàm thuật toán cho chế độ: {mode} <<<")
            current_app.logger.error(f"SessionManager: Không tìm thấy hàm thuật toán cho chế độ: {mode}")
            return False
        
        # LẤY TỔNG SỐ CÂU HỎI CỦA PHIÊN MÀ KHÔNG LƯU CẢ DANH SÁCH ID
        # SỬA LỖI: Sử dụng .count() trên đối tượng truy vấn để lấy tổng số câu hỏi một cách chính xác
        total_items_in_session_query = algorithm_func(user_id, set_id, None)
        total_items_in_session = total_items_in_session_query.count()

        if total_items_in_session == 0:
            cls.end_flashcard_session()
            print(">>> SESSION_MANAGER: Không có thẻ nào được tìm thấy cho phiên học mới. <<<")
            current_app.logger.warning("SessionManager: Không có thẻ nào được tìm thấy cho phiên học mới.")
            return False

        new_session_manager = cls(
            user_id=user_id,
            set_id=set_id,
            mode=mode,
            total_items_in_session=total_items_in_session,
            processed_item_ids=[],
            correct_answers=0,
            incorrect_answers=0,
            vague_answers=0,
            start_time=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
        session[cls.SESSION_KEY] = new_session_manager.to_dict()
        session.modified = True

        print(f">>> SESSION_MANAGER: Phiên học mới đã được khởi tạo với {total_items_in_session} thẻ. Batch size: 1 <<<")
        current_app.logger.debug(f"SessionManager: Phiên học mới đã được khởi tạo với {total_items_in_session} thẻ. Batch size: 1")
        return True

    def _get_media_absolute_url(self, file_path):
        """
        Mô tả: Chuyển đổi đường dẫn file media tương đối thành URL tuyệt đối.
               Đã sửa để xử lý đúng các trường hợp đường dẫn có và không có dấu '/'.
        """
        if not file_path:
            return None
        
        try:
            if file_path.startswith('/'):
                file_path = file_path.lstrip('/')
            
            full_url = url_for('static', filename=file_path)
            current_app.logger.debug(f"Media URL - Gốc: '{file_path}', URL: '{full_url}'")
            return full_url
        except Exception as e:
            current_app.logger.error(f"Lỗi khi tạo URL cho media '{file_path}': {e}")
            return None

    def get_next_batch(self):
        """
        Mô tả: Lấy dữ liệu của một thẻ tiếp theo trong phiên học.
        Returns:
            dict/None: Dữ liệu thẻ nếu có, None nếu phiên không hợp lệ hoặc hết thẻ.
        """
        requested_batch_size = 1
        current_app.logger.debug(f"SessionManager: Lấy thẻ tiếp theo: Đã xử lý {len(self.processed_item_ids)}/{self.total_items_in_session}")
        
        if len(self.processed_item_ids) >= self.total_items_in_session:
            current_app.logger.debug("SessionManager: Hết thẻ trong phiên. Đã hiển thị đủ số lượng.")
            return None

        mode_config = next((m for m in FlashcardLearningConfig.FLASHCARD_MODES if m['id'] == self.mode), None)
        if not mode_config:
            current_app.logger.error(f"Chế độ học không hợp lệ: {self.mode}")
            return None
        
        algorithm_func = None
        if self.mode == 'new_only':
            algorithm_func = get_new_only_items
        elif self.mode == 'due_only':
            algorithm_func = get_due_items
        elif self.mode == 'hard_only':
            algorithm_func = get_hard_items
        elif self.mode == 'mixed_srs':
            algorithm_func = get_mixed_items
        
        if not algorithm_func:
            current_app.logger.error(f"Không tìm thấy hàm thuật toán cho chế độ: {self.mode}")
            return None

        unprocessed_items_query = algorithm_func(self.user_id, self.set_id, None).filter(
            LearningItem.item_id.notin_(self.processed_item_ids)
        )
        
        new_items_to_add_to_session = unprocessed_items_query.order_by(func.random()).limit(requested_batch_size).all()
        
        if not new_items_to_add_to_session:
            current_app.logger.debug("Không còn thẻ mới nào để lấy.")
            return None

        items_data = []
        newly_processed_item_ids = []

        for item in new_items_to_add_to_session:
            item_dict = {
                'item_id': item.item_id,
                'content': {
                    'front': item.content.get('front', ''),
                    'back': item.content.get('back', ''),
                    'front_audio_content': item.content.get('front_audio_content', ''),
                    'front_audio_url': item.content.get('front_audio_url', ''),
                    'back_audio_content': item.content.get('back_audio_content', ''),
                    'back_audio_url': item.content.get('back_audio_url', ''),
                    'front_img': item.content.get('front_img', ''),
                    'back_img': item.content.get('back_img', ''),
                },
                'ai_explanation': item.ai_explanation
            }
            
            if item_dict['content'].get('front_audio_url'):
                item_dict['content']['front_audio_url'] = self._get_media_absolute_url(item_dict['content']['front_audio_url'])
            if item_dict['content'].get('back_audio_url'):
                item_dict['content']['back_audio_url'] = self._get_media_absolute_url(item_dict['content']['back_audio_url'])
            if item_dict['content'].get('front_img'):
                item_dict['content']['front_img'] = self._get_media_absolute_url(item_dict['content']['front_img'])
            if item_dict['content'].get('back_img'):
                item_dict['content']['back_img'] = self._get_media_absolute_url(item_dict['content']['back_img'])

            items_data.append(item_dict)
            newly_processed_item_ids.append(item.item_id)
        
        self.processed_item_ids.extend(newly_processed_item_ids)
        session[self.SESSION_KEY] = self.to_dict()
        session.modified = True

        return {
            'items': items_data,
            'start_index': len(self.processed_item_ids) - len(items_data),
            'total_items_in_session': self.total_items_in_session,
            'session_correct_answers': self.correct_answers,
            'session_incorrect_answers': self.incorrect_answers,
            'session_vague_answers': self.vague_answers,
            'session_total_answered': self.correct_answers + self.incorrect_answers + self.vague_answers
        }

    def process_flashcard_answer(self, item_id, user_answer_quality):
        """
        Mô tả: Xử lý một câu trả lời của người dùng cho một thẻ flashcard.
               Hàm này giờ đây nhận trực tiếp điểm chất lượng (dạng số) đã được xử lý.
        """
        print(f">>> SESSION_MANAGER: Bắt đầu process_flashcard_answer cho item_id={item_id}, user_answer_quality={user_answer_quality} <<<")
        current_app.logger.debug(f"SessionManager: Bắt đầu process_flashcard_answer cho item_id={item_id}, user_answer_quality={user_answer_quality}")

        try:
            current_user_obj = User.query.get(self.user_id)
            current_user_total_score = current_user_obj.total_score if current_user_obj else 0

            # SỬA LỖI: Loại bỏ hoàn toàn logic tra cứu quality_map ở đây.
            # Giá trị user_answer_quality nhận vào đã là dạng số (integer).
            
            score_change, updated_total_score, is_correct, new_progress_status, item_stats = process_flashcard_answer(
                user_id=self.user_id,
                item_id=item_id,
                user_answer_quality=user_answer_quality, # Truyền thẳng giá trị số đã nhận
                current_user_total_score=current_user_total_score
            )
            
            # Cập nhật số liệu thống kê của phiên học
            if is_correct:
                self.correct_answers += 1
            elif user_answer_quality == 2: # Trường hợp "mơ hồ"
                self.vague_answers += 1
            else: # Các trường hợp còn lại là "sai"
                self.incorrect_answers += 1

            session[self.SESSION_KEY] = self.to_dict()
            session.modified = True 
            
            print(f">>> SESSION_MANAGER: Thẻ đã xử lý. Quality: {user_answer_quality}, Điểm thay đổi: {score_change} <<<")
            return {
                'success': True,
                'score_change': score_change,
                'updated_total_score': updated_total_score,
                'is_correct': is_correct,
                'new_progress_status': new_progress_status,
                'statistics': item_stats,
                'session_correct_answers': self.correct_answers,
                'session_incorrect_answers': self.incorrect_answers,
                'session_vague_answers': self.vague_answers,
                'session_total_answered': self.correct_answers + self.incorrect_answers + self.vague_answers
            }

        except Exception as e:
            current_app.logger.error(f"Lỗi khi xử lý câu trả lời flashcard: {e}", exc_info=True)
            return {'error': f'Lỗi khi xử lý câu trả lời: {str(e)}'}

    @classmethod
    def end_flashcard_session(cls):
        """
        Mô tả: Kết thúc phiên học Flashcard hiện tại và xóa dữ liệu khỏi session.
        """
        if cls.SESSION_KEY in session:
            session.pop(cls.SESSION_KEY, None)
            print(">>> SESSION_MANAGER: Phiên học đã kết thúc và xóa khỏi session. <<<")
            current_app.logger.debug("SessionManager: Phiên học đã kết thúc và xóa khỏi session.")
        return {'message': 'Phiên học đã kết thúc.'}

    @classmethod
    def get_session_status(cls):
        """
        Mô tả: Lấy trạng thái hiện tại của phiên học.
        """
        status = session.get(cls.SESSION_KEY)
        print(f">>> SESSION_MANAGER: Lấy trạng thái session: {status} <<<")
        current_app.logger.debug(f"SessionManager: Lấy trạng thái session: {status}")
        return status