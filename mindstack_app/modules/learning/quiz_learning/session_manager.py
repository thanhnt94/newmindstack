# File: mindstack_app/modules/learning/quiz_learning/session_manager.py
# Phiên bản: 2.0
# MỤC ĐÍCH: Cập nhật logic để sử dụng model QuizProgress mới thay cho UserProgress.
# ĐÃ SỬA: Thay thế import UserProgress bằng QuizProgress.
# ĐÃ SỬA: Cập nhật các hàm khởi tạo, lấy câu hỏi, xử lý đáp án để tương tác với bảng mới.

from flask import session, current_app, url_for
from flask_login import current_user
from ....models import db, LearningItem, QuizProgress, LearningGroup, User
from .algorithms import get_new_only_items, get_reviewed_items, get_hard_items
from .quiz_logic import process_quiz_answer
from .quiz_stats_logic import get_quiz_item_statistics
from .config import QuizLearningConfig
from sqlalchemy.sql import func
import random
import datetime
import os

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
        current_app.logger.debug(f"QuizSessionManager: Instance được khởi tạo/tải. User: {self.user_id}, Set: {self.set_id}, Mode: {self.mode}")

    @classmethod
    def from_dict(cls, session_dict):
        """
        Tạo một instance QuizSessionManager từ một dictionary (thường từ Flask session).
        """
        return cls(
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

        Args:
            set_id (int/str): ID của bộ Quiz hoặc 'all'.
            mode (str): Chế độ học ('new_only', 'due_only', 'hard_only', ...).
            batch_size (int): Số lượng câu hỏi trong mỗi nhóm.
        
        Returns:
            bool: True nếu phiên được khởi tạo thành công, False nếu không có câu hỏi.
        """
        print(f">>> SESSION_MANAGER: Bắt đầu start_new_quiz_session cho set_id={set_id}, mode={mode}, batch_size={batch_size} <<<")
        current_app.logger.debug(f"SessionManager: Bắt đầu start_new_quiz_session cho set_id={set_id}, mode={mode}, batch_size={batch_size}")
        user_id = current_user.user_id
        
        # BƯỚC SỬA LỖI: Xóa phiên học cũ trước khi bắt đầu phiên mới
        cls.end_quiz_session()

        # Lấy hàm thuật toán tương ứng từ cấu hình
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
        
        # LẤY TỔNG SỐ CÂU HỎI CỦA PHIÊN MÀ KHÔNG LƯU CẢ DANH SÁCH ID
        # SỬA LỖI: Sử dụng .count() trên đối tượng truy vấn để lấy tổng số câu hỏi một cách chính xác
        total_items_in_session_query = algorithm_func(user_id, set_id, None)
        total_items_in_session = total_items_in_session_query.count()

        if total_items_in_session == 0:
            cls.end_quiz_session()
            print(">>> SESSION_MANAGER: Không có câu hỏi nào được tìm thấy cho phiên học mới. <<<")
            current_app.logger.warning("SessionManager: Không có câu hỏi nào được tìm thấy cho phiên học mới.")
            return False

        # Xác định common_pre_question_text_global cho toàn bộ phiên học
        # Cần lấy ngẫu nhiên một vài câu để kiểm tra, không lấy toàn bộ
        sample_size = min(total_items_in_session, 50) # Lấy mẫu 50 câu hoặc ít hơn
        
        # Nếu tổng số câu hỏi nhỏ hơn sample_size, ta lấy toàn bộ
        if total_items_in_session > 0:
            sample_items = total_items_in_session_query.order_by(func.random()).limit(sample_size).all()
            global_pre_texts = [item.content.get('pre_question_text') for item in sample_items if item.content.get('pre_question_text')]
            common_pre_question_text_global = None
            if global_pre_texts and all(p == global_pre_texts[0] for p in global_pre_texts):
                common_pre_question_text_global = global_pre_texts[0]
                print(f">>> SESSION_MANAGER: Phát hiện common_pre_question_text_global: '{common_pre_question_text_global}' <<<")
        else:
            common_pre_question_text_global = None

        # Tạo instance của QuizSessionManager và lưu vào session
        new_session_manager = cls(
            user_id=user_id,
            set_id=set_id,
            mode=mode,
            batch_size=batch_size,
            total_items_in_session=total_items_in_session,
            processed_item_ids=[], # Khởi tạo danh sách các ID đã xử lý
            correct_answers=0,
            incorrect_answers=0,
            start_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            common_pre_question_text_global=common_pre_question_text_global
        )
        session[cls.SESSION_KEY] = new_session_manager.to_dict() # Lưu dictionary của instance vào session
        session.modified = True # Đảm bảo session được đánh dấu là đã thay đổi để lưu

        print(f">>> SESSION_MANAGER: Phiên học mới đã được khởi tạo với {total_items_in_session} câu hỏi. Batch size: {batch_size} <<<")
        current_app.logger.debug(f"SessionManager: Phiên học mới đã được khởi tạo với {total_items_in_session} câu hỏi. Batch size: {batch_size}")
        return True

    def _get_media_absolute_url(self, file_path):
        """
        Chuyển đổi đường dẫn file media tương đối thành URL tuyệt đối.
        
        Args:
            file_path (str): Đường dẫn tương đối của file media.
        
        Returns:
            str: URL tuyệt đối của file media.
        """
        if not file_path:
            return None
        
        # Flask đã được cấu hình để phục vụ file từ thư mục 'uploads'
        try:
            full_url = url_for('static', filename=file_path)
            current_app.logger.debug(f"Media URL - Gốc: '{file_path}', URL: '{full_url}'")
            return full_url
        except Exception as e:
            current_app.logger.error(f"Lỗi khi tạo URL cho media '{file_path}': {e}")
            return None


    def get_next_batch(self, requested_batch_size):
        """
        Lấy dữ liệu của nhóm câu hỏi tiếp theo trong phiên học.
        Hàm này sẽ lấy ngẫu nhiên các câu hỏi từ CSDL và loại bỏ các câu hỏi đã được hiển thị.

        Args:
            requested_batch_size (int): Kích thước nhóm câu hỏi yêu cầu.

        Returns:
            dict/None: Dữ liệu nhóm câu hỏi nếu có, None nếu phiên không hợp lệ hoặc hết câu.
        """
        current_app.logger.debug(f"SessionManager: Lấy nhóm câu hỏi: Đã xử lý {len(self.processed_item_ids)}/{self.total_items_in_session}, requested_batch_size={requested_batch_size}")
        
        if len(self.processed_item_ids) >= self.total_items_in_session:
            current_app.logger.debug("SessionManager: Hết câu hỏi trong phiên. Đã hiển thị đủ số lượng.")
            return None

        # Lấy hàm thuật toán tương ứng từ cấu hình
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

        # Lấy danh sách ID các câu hỏi chưa được hiển thị
        unprocessed_items_query = algorithm_func(self.user_id, self.set_id, None).filter(
            LearningItem.item_id.notin_(self.processed_item_ids)
        )
        
        # Lấy một số lượng câu hỏi ngẫu nhiên bằng với requested_batch_size
        new_items_to_add_to_session = unprocessed_items_query.order_by(func.random()).limit(requested_batch_size).all()
        
        if not new_items_to_add_to_session:
            current_app.logger.debug("Không còn câu hỏi mới nào để lấy.")
            return None

        items_data = []
        newly_processed_item_ids = []

        for item in new_items_to_add_to_session:
            item_dict = {
                'item_id': item.item_id,
                'content': item.content,
                'ai_explanation': item.ai_explanation,
                'group_id': item.group_id,
                'group_details': None
            }
            if item_dict['content'].get('question_image_file'):
                item_dict['content']['question_image_file'] = self._get_media_absolute_url(item_dict['content']['question_image_file'])
            if item_dict['content'].get('question_audio_file'):
                item_dict['content']['question_audio_file'] = self._get_media_absolute_url(item_dict['content']['question_audio_file'])

            items_data.append(item_dict)
            newly_processed_item_ids.append(item.item_id)
        
        # CẬP NHẬT DANH SÁCH CÁC ID ĐÃ XỬ LÝ
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
        Xử lý một danh sách các câu trả lời của người dùng cho một nhóm câu hỏi,
        cập nhật tiến độ và session.

        Args:
            answers (list): Danh sách các dict, mỗi dict chứa {'item_id': int, 'user_answer': str}.

        Returns:
            list: Danh sách các dict kết quả xử lý cho từng câu hỏi.
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

            # SỬA: Lấy thống kê từ hàm mới đã được cập nhật để truy vấn bảng QuizProgress
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