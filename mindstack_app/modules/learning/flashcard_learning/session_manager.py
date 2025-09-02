# File: mindstack_app/modules/learning/flashcard_learning/session_manager.py
# Phiên bản: 1.7
# Mục đích: Quản lý trạng thái của phiên học Flashcard hiện tại cho người dùng.
# ĐÃ SỬA: Sửa lỗi TypeError bằng cách gọi hàm process_flashcard_answer trong flashcard_logic.py với tham số user_answer.
# ĐÃ THÊM: Cập nhật logic xử lý câu trả lời để hỗ trợ các hệ thống nút đánh giá khác nhau.

from flask import session, current_app, url_for
from flask_login import current_user
from ....models import db, LearningItem, UserProgress, LearningGroup, User
from .algorithms import get_new_only_items, get_due_items, get_hard_items
from .flashcard_logic import process_flashcard_answer
from .flashcard_stats_logic import get_flashcard_item_statistics
from .config import FlashcardLearningConfig
from sqlalchemy.sql import func
import random
import datetime
import os

class FlashcardSessionManager:
    """
    Quản lý phiên học Flashcard cho một người dùng.
    Sử dụng Flask session để lưu trữ trạng thái.
    """
    SESSION_KEY = 'flashcard_session'

    def __init__(self, user_id, set_id, mode, 
                 total_items_in_session, processed_item_ids, 
                 correct_answers, incorrect_answers, vague_answers, start_time):
        """
        Khởi tạo một phiên FlashcardSessionManager.
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
        Tạo một instance FlashcardSessionManager từ một dictionary (thường từ Flask session).
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
        Chuyển đổi instance FlashcardSessionManager thành một dictionary để lưu vào Flask session.
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
        Khởi tạo một phiên học Flashcard mới.
        Lấy danh sách thẻ dựa trên chế độ.

        Args:
            set_id (int/str): ID của bộ Flashcard hoặc 'all'.
            mode (str): Chế độ học ('new_only', 'due_only', 'hard_only', ...).
        
        Returns:
            bool: True nếu phiên được khởi tạo thành công, False nếu không có thẻ.
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
        
        if not algorithm_func:
            print(f">>> SESSION_MANAGER: LỖI - Không tìm thấy hàm thuật toán cho chế độ: {mode} <<<")
            current_app.logger.error(f"SessionManager: Không tìm thấy hàm thuật toán cho chế độ: {mode}")
            return False
        
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
        Chuyển đổi đường dẫn file media tương đối thành URL tuyệt đối.
        
        Hàm này đã được cập nhật để xử lý các đường dẫn không nhất quán,
        loại bỏ tiền tố 'media/flashcard/' không cần thiết.
        """
        if not file_path:
            return None
        
        # Sửa lỗi: Nếu đường dẫn chứa tiền tố không cần thiết, hãy loại bỏ nó
        # Dựa trên lỗi 404, đường dẫn có thể bị trùng lặp như /uploads/media/flashcard/...
        cleaned_file_path = file_path.replace('media/flashcard/', '')
        
        try:
            full_url = url_for('static', filename=cleaned_file_path)
            current_app.logger.debug(f"Media URL - Gốc: '{file_path}', Đã dọn dẹp: '{cleaned_file_path}', URL: '{full_url}'")
            return full_url
        except Exception as e:
            current_app.logger.error(f"Lỗi khi tạo URL cho media '{file_path}': {e}")
            return None


    def get_next_batch(self):
        """
        Lấy dữ liệu của một thẻ tiếp theo trong phiên học.

        Returns:
            dict/None: Dữ liệu thẻ nếu có, None nếu phiên không hợp lệ hoặc hết thẻ.
        """
        requested_batch_size = 1 # Flashcard luôn lấy từng thẻ một
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
            # Xử lý URL media
            if item_dict['content'].get('front_img'):
                item_dict['content']['front_img'] = self._get_media_absolute_url(item_dict['content']['front_img'])
            if item_dict['content'].get('back_img'):
                item_dict['content']['back_img'] = self._get_media_absolute_url(item_dict['content']['back_img'])
            if item_dict['content'].get('front_audio_url'):
                item_dict['content']['front_audio_url'] = self._get_media_absolute_url(item_dict['content']['front_audio_url'])
            if item_dict['content'].get('back_audio_url'):
                item_dict['content']['back_audio_url'] = self._get_media_absolute_url(item_dict['content']['back_audio_url'])

            items_data.append(item_dict)
            newly_processed_item_ids.append(item.item_id)
        
        self.processed_item_ids.extend(newly_processed_item_ids)
        session[self.SESSION_KEY] = self.to_dict()
        session.modified = True

        # Trả về một dictionary duy nhất cho thẻ hiện tại
        return {
            'items': items_data,
            'start_index': len(self.processed_item_ids) - len(items_data),
            'total_items_in_session': self.total_items_in_session,
            'session_correct_answers': self.correct_answers,
            'session_incorrect_answers': self.incorrect_answers,
            'session_vague_answers': self.vague_answers,
            'session_total_answered': self.correct_answers + self.incorrect_answers + self.vague_answers
        }

    def process_flashcard_answer(self, item_id, user_answer):
        """
        Xử lý một câu trả lời của người dùng cho một thẻ flashcard.
        Args:
            item_id (int): ID của thẻ.
            user_answer (str): Chuỗi đại diện cho nút mà người dùng đã bấm.
        """
        print(f">>> SESSION_MANAGER: Bắt đầu process_flashcard_answer cho item_id={item_id}, user_answer={user_answer} <<<")
        current_app.logger.debug(f"SessionManager: Bắt đầu process_flashcard_answer cho item_id={item_id}, user_answer={user_answer}")

        try:
            current_user_obj = User.query.get(self.user_id)
            current_user_total_score = current_user_obj.total_score if current_user_obj else 0

            # THAY ĐỔI: Chuyển logic ánh xạ từ route sang đây để dễ quản lý hơn.
            # Dựa trên số nút mà người dùng đã chọn
            user_button_count = current_user.flashcard_button_count or 3
            quality_map = {}
            if user_button_count == 3:
                quality_map = {'nhớ': 4, 'mơ_hồ': 2, 'quên': 1}
            elif user_button_count == 4:
                quality_map = {'again': 1, 'hard': 3, 'good': 4, 'easy': 5}
            elif user_button_count == 6:
                quality_map = {'fail': 0, 'very_hard': 1, 'hard': 2, 'good': 3, 'easy': 4, 'very_easy': 5}
            
            user_answer_quality = quality_map.get(user_answer, 0)
            
            score_change, updated_total_score, is_correct, new_progress_status, item_stats = process_flashcard_answer(
                user_id=self.user_id,
                item_id=item_id,
                user_answer_quality=user_answer_quality,
                current_user_total_score=current_user_total_score
            )
            
            if is_correct:
                self.correct_answers += 1
            elif user_answer_quality == 2:
                self.vague_answers += 1
            else:
                self.incorrect_answers += 1

            session[self.SESSION_KEY] = self.to_dict()
            session.modified = True 
            
            print(f">>> SESSION_MANAGER: Thẻ đã xử lý. Đáp án: {user_answer}, Điểm thay đổi: {score_change} <<<")
            return {
                'success': True,
                'score_change': score_change,
                'updated_total_score': updated_total_score,
                'is_correct': is_correct,
                'new_progress_status': new_progress_status,
                'statistics': item_stats,
                # THÊM MỚI: Trả về số liệu thống kê phiên học để cập nhật giao diện
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
        Kết thúc phiên học Flashcard hiện tại và xóa dữ liệu khỏi session.
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