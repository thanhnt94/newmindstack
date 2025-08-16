# File: mindstack_app/modules/learning/quiz_learning/session_manager.py
# Phiên bản: 1.21
# Mục đích: Quản lý trạng thái của phiên học Quiz hiện tại cho người dùng.
# ĐÃ SỬA: Khắc phục triệt để lỗi đường dẫn media bằng cách loại bỏ hoàn toàn logic nối với thư mục con và sửa các lời gọi hàm.

from flask import session, current_app, url_for
from flask_login import current_user
from ....models import db, LearningItem, UserProgress, LearningGroup, User
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

    def __init__(self, user_id, set_id, mode, batch_size, all_item_ids, 
                 current_batch_start_index, total_items_in_session, 
                 correct_answers, incorrect_answers, start_time, common_pre_question_text_global):
        """
        Khởi tạo một phiên QuizSessionManager.
        """
        self.user_id = user_id
        self.set_id = set_id
        self.mode = mode
        self.batch_size = batch_size
        self.all_item_ids = all_item_ids
        self.current_batch_start_index = current_batch_start_index
        self.total_items_in_session = total_items_in_session
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
            all_item_ids=session_dict['all_item_ids'],
            current_batch_start_index=session_dict['current_batch_start_index'],
            total_items_in_session=session_dict['total_items_in_session'],
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
            'all_item_ids': self.all_item_ids,
            'current_batch_start_index': self.current_batch_start_index,
            'total_items_in_session': self.total_items_in_session,
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
        all_items_for_session_objects = [] # Danh sách TẤT CẢ các đối tượng LearningItem cho phiên

        # Lấy hàm thuật toán tương ứng từ cấu hình
        mode_config = next((m for m in QuizLearningConfig.QUIZ_MODES if m['id'] == mode), None)
        if not mode_config:
            print(f">>> SESSION_MANAGER: LỖI - Chế độ học không hợp lệ hoặc không được định nghĩa: {mode} <<<")
            current_app.logger.error(f"SessionManager: Chế độ học không hợp lệ hoặc không được định nghĩa: {mode}")
            return False
        
        algorithm_func_name = mode_config['algorithm_func_name']
        
        # Lấy hàm từ algorithms.py dựa trên tên
        if algorithm_func_name == 'get_new_only_items':
            all_items_for_session_objects = get_new_only_items(user_id, set_id, None)
        elif algorithm_func_name == 'get_reviewed_items':
            all_items_for_session_objects = get_reviewed_items(user_id, set_id, None)
        elif algorithm_func_name == 'get_hard_items':
            all_items_for_session_objects = get_hard_items(user_id, set_id, None)
        else:
            print(f">>> SESSION_MANAGER: LỖI - Không tìm thấy hàm thuật toán cho chế độ: {algorithm_func_name} <<<")
            current_app.logger.error(f"SessionManager: Không tìm thấy hàm thuật toán cho chế độ: {algorithm_func_name}")
            return False

        print(f">>> SESSION_MANAGER: Chế độ '{mode}' tìm thấy {len(all_items_for_session_objects)} câu hỏi tổng cộng. <<<")
        current_app.logger.debug(f"SessionManager: Chế độ '{mode}' tìm thấy {len(all_items_for_session_objects)} câu hỏi tổng cộng.")

        if not all_items_for_session_objects:
            cls.end_quiz_session() # Sử dụng cls.end_quiz_session
            print(">>> SESSION_MANAGER: Không có câu hỏi nào được tìm thấy cho phiên học mới. <<<")
            current_app.logger.warning("SessionManager: Không có câu hỏi nào được tìm thấy cho phiên học mới.")
            return False
        
        # Trộn ngẫu nhiên tất cả các câu hỏi để đảm bảo tính ngẫu nhiên cho phiên học
        random.shuffle(all_items_for_session_objects) 

        # Xác định common_pre_question_text_global cho toàn bộ phiên học
        global_pre_texts = [item.content.get('pre_question_text') for item in all_items_for_session_objects if item.content.get('pre_question_text')]
        common_pre_question_text_global = None
        if global_pre_texts and all(p == global_pre_texts[0] for p in global_pre_texts):
            common_pre_question_text_global = global_pre_texts[0]
            print(f">>> SESSION_MANAGER: Phát hiện common_pre_question_text_global: '{common_pre_question_text_global}' <<<")

        # Tạo instance của QuizSessionManager và lưu vào session
        new_session_manager = cls(
            user_id=user_id,
            set_id=set_id,
            mode=mode,
            batch_size=batch_size,
            all_item_ids=[item.item_id for item in all_items_for_session_objects],
            current_batch_start_index=0,
            total_items_in_session=len(all_items_for_session_objects),
            correct_answers=0,
            incorrect_answers=0,
            start_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            common_pre_question_text_global=common_pre_question_text_global
        )
        session[cls.SESSION_KEY] = new_session_manager.to_dict() # Lưu dictionary của instance vào session
        session.modified = True # Đảm bảo session được đánh dấu là đã thay đổi để lưu

        # SỬA LỖI: Thay thế all_item_ids bằng all_items_for_session_objects
        print(f">>> SESSION_MANAGER: Phiên học mới đã được khởi tạo với {len(all_items_for_session_objects)} câu hỏi. Batch size: {batch_size} <<<")
        current_app.logger.debug(f"SessionManager: Phiên học mới đã được khởi tạo với {len(all_items_for_session_objects)} câu hỏi. Batch size: {batch_size}")
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
        
        # ĐÃ SỬA: Loại bỏ logic nối đường dẫn media_type + 's' và chỉ sử dụng tên file
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
        Lấy dữ liệu của nhóm câu hỏi tiếp theo trong phiên, có xử lý nhóm câu hỏi phức hợp.
        Sẽ lấy N câu hỏi đơn hoặc N nhóm câu hỏi (nếu câu đầu tiên là nhóm).

        Args:
            requested_batch_size (int): Kích thước nhóm câu hỏi yêu cầu.

        Returns:
            dict/None: Dữ liệu nhóm câu hỏi nếu có, None nếu phiên không hợp lệ hoặc hết câu.
        """
        print(f">>> SESSION_MANAGER: Lấy nhóm câu hỏi: current_batch_start_index={self.current_batch_start_index}, total_items_in_session={self.total_items_in_session}, requested_batch_size={requested_batch_size} <<<")
        current_app.logger.debug(f"SessionManager: Lấy nhóm câu hỏi: current_batch_start_index={self.current_batch_start_index}, total_items_in_session={self.total_items_in_session}, requested_batch_size={requested_batch_size}")

        if self.current_batch_start_index >= self.total_items_in_session:
            print(">>> SESSION_MANAGER: Hết nhóm câu hỏi trong phiên. <<<")
            current_app.logger.debug("SessionManager: Hết nhóm câu hỏi trong phiên.")
            return None # Hết câu hỏi

        items_data = []
        
        # Danh sách các group_id đã được xử lý trong batch này để tránh trùng lặp
        processed_group_ids = set() 
        
        # Lặp để thu thập đủ số lượng "main entries" (câu hỏi đơn hoặc nhóm câu hỏi)
        # hoặc cho đến khi hết câu hỏi trong phiên
        current_collected_entries = 0
        current_scan_index = self.current_batch_start_index

        while current_collected_entries < requested_batch_size and current_scan_index < self.total_items_in_session:
            item_id_to_check = self.all_item_ids[current_scan_index]
            item_to_check = LearningItem.query.get(item_id_to_check)

            if not item_to_check:
                print(f">>> SESSION_MANAGER: LỖI - Không tìm thấy LearningItem với ID: {item_id_to_check} khi quét. Bỏ qua. <<<")
                current_app.logger.error(f"SessionManager: Không tìm thấy LearningItem với ID: {item_id_to_check} khi quét. Bỏ qua.")
                current_scan_index += 1 # Bỏ qua item lỗi
                continue

            if item_to_check.group_id:
                # Nếu item thuộc một nhóm và nhóm đó chưa được xử lý trong batch này
                if item_to_check.group_id not in processed_group_ids:
                    group = LearningGroup.query.get(item_to_check.group_id)
                    if group:
                        print(f">>> SESSION_MANAGER: Phát hiện nhóm câu hỏi (Group ID: {group.group_id}). Lấy tất cả item trong nhóm. <<<")
                        
                        # Lấy tất cả các item thuộc nhóm này VÀ CŨNG NẰM TRONG all_item_ids của phiên
                        # Đảm bảo thứ tự theo order_in_container
                        items_in_group_query = LearningItem.query.filter(
                            LearningItem.group_id == group.group_id,
                            LearningItem.item_type == 'QUIZ_MCQ',
                            LearningItem.item_id.in_(self.all_item_ids) # Đảm bảo chỉ lấy các item có trong phiên hiện tại
                        ).order_by(LearningItem.order_in_container).all()

                        # Xử lý URL media cho group_details
                        group_content = group.content.copy() # Tạo bản sao để sửa đổi
                        if group_content.get('question_image_file'):
                            group_content['question_image_file'] = self._get_media_absolute_url(group_content['question_image_file'])
                        if group_content.get('question_audio_file'):
                            group_content['question_audio_file'] = self._get_media_absolute_url(group_content['question_audio_file'])

                        for item in items_in_group_query:
                            item_dict = {
                                'item_id': item.item_id,
                                'content': item.content,
                                'ai_explanation': item.ai_explanation,
                                'group_id': item.group_id,
                                'group_details': group_content # Gắn group_content đã xử lý URL
                            }
                            # Xử lý URL media cho từng item con
                            if item_dict['content'].get('question_image_file'):
                                item_dict['content']['question_image_file'] = self._get_media_absolute_url(item_dict['content']['question_image_file'])
                            if item_dict['content'].get('question_audio_file'):
                                item_dict['content']['question_audio_file'] = self._get_media_absolute_url(item_dict['content']['question_audio_file'])

                            items_data.append(item_dict)
                        processed_group_ids.add(item_to_check.group_id)
                        current_collected_entries += 1 # Đếm nhóm này là 1 entry
                        print(f">>> SESSION_MANAGER: Nhóm câu hỏi có {len(items_data)} item. Tổng entries đã thu thập: {current_collected_entries} <<<")
                    else:
                        print(f">>> SESSION_MANAGER: LỖI - Không tìm thấy LearningGroup với ID: {item_id_to_check.group_id}. Xử lý như câu đơn. <<<")
                        # Fallback: nếu không tìm thấy group, xử lý như câu đơn
                        item_dict = {
                            'item_id': item_to_check.item_id,
                            'content': item_to_check.content,
                            'ai_explanation': item_to_check.ai_explanation,
                            'group_id': item_to_check.group_id, # Sẽ là None
                            'group_details': None # Không có group_details
                        }
                        # Xử lý URL media cho item
                        if item_dict['content'].get('question_image_file'):
                            item_dict['content']['question_image_file'] = self._get_media_absolute_url(item_dict['content']['question_image_file'])
                        if item_dict['content'].get('question_audio_file'):
                            item_dict['content']['question_audio_file'] = self._get_media_absolute_url(item_dict['content']['question_audio_file'])
                        items_data.append(item_dict)
                        current_collected_entries += 1
                else:
                    # Nếu nhóm đã được xử lý trong batch này, bỏ qua item này
                    print(f">>> SESSION_MANAGER: Item {item_id_to_check} thuộc nhóm đã xử lý. Bỏ qua. <<<")
            else:
                # Câu hỏi đơn lẻ
                item_dict = {
                    'item_id': item_to_check.item_id,
                    'content': item_to_check.content,
                    'ai_explanation': item_to_check.ai_explanation,
                    'group_id': item_to_check.group_id, # Sẽ là None
                    'group_details': None # Không có group_details
                }
                # Xử lý URL media cho item
                if item_dict['content'].get('question_image_file'):
                    item_dict['content']['question_image_file'] = self._get_media_absolute_url(item_dict['content']['question_image_file'])
                if item_dict['content'].get('question_audio_file'):
                    item_dict['content']['question_audio_file'] = self._get_media_absolute_url(item_dict['content']['question_audio_file'])
                items_data.append(item_dict)
                current_collected_entries += 1 # Đếm câu đơn là 1 entry
                print(f">>> SESSION_MANAGER: Thêm câu hỏi đơn lẻ {item_id_to_check}. Tổng entries đã thu thập: {current_collected_entries} <<<")
            
            current_scan_index += 1 # Di chuyển đến item tiếp theo trong all_item_ids

        # Sau khi vòng lặp kết thúc, items_data chứa các câu hỏi cho batch hiện tại
        # current_batch_start_index sẽ được cập nhật trong process_answer_batch
        
        if not items_data:
            print(">>> SESSION_MANAGER: Nhóm câu hỏi trống hoặc không tìm thấy item nào sau khi quét. <<<")
            return None

        return {
            'items': items_data,
            'common_pre_question_text_global': self.common_pre_question_text_global, # Văn bản pre-question chung toàn phiên
            'start_index': self.current_batch_start_index,
            'total_items_in_session': self.total_items_in_session,
            'actual_batch_item_count': len(items_data) # Số lượng item thực tế trong batch này
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
        actual_items_processed_in_batch = 0 # Số lượng item thực tế được xử lý trong batch này

        # Lấy tổng điểm hiện tại của người dùng một lần duy nhất
        current_user_obj = User.query.get(self.user_id)
        current_user_total_score = current_user_obj.total_score if current_user_obj else 0

        for answer in answers:
            item_id = answer.get('item_id')
            user_answer_text = answer.get('user_answer')

            # GỌI HÀM TỪ QUIZ_LOGIC ĐỂ XỬ LÝ
            score_change, updated_total_score, is_correct, correct_option_char, explanation = process_quiz_answer(
                user_id=self.user_id,
                item_id=item_id,
                user_answer_text=user_answer_text,
                current_user_total_score=current_user_total_score # Truyền tổng điểm hiện tại
            )
            current_user_total_score = updated_total_score # Cập nhật tổng điểm cho các câu tiếp theo trong batch

            # Lấy thống kê cho câu hỏi vừa trả lời
            item_stats = get_quiz_item_statistics(self.user_id, item_id)
            
            if is_correct:
                self.correct_answers += 1 # Cập nhật thuộc tính của instance
                print(f">>> SESSION_MANAGER: Câu trả lời đúng. Điểm thay đổi: {score_change} <<<")
            else:
                self.incorrect_answers += 1 # Cập nhật thuộc tính của instance
                print(f">>> SESSION_MANAGER: Câu trả lời sai. Điểm thay đổi: {score_change} <<<")
            
            results.append({
                'item_id': item_id,
                'is_correct': is_correct,
                'correct_answer': correct_option_char, # TRẢ VỀ KÝ TỰ ĐÁP ÁN ĐÚNG CHO FRONTEND
                'explanation': explanation,
                'statistics': item_stats, # THÊM THỐNG KÊ VÀO KẾT QUẢ
                'score_change': score_change, # THÊM score_change VÀO KẾT QUẢ
            })
            actual_items_processed_in_batch += 1 # Đếm số item đã xử lý

        # Tăng current_batch_start_index sau khi xử lý toàn bộ nhóm
        self.current_batch_start_index += actual_items_processed_in_batch # Tăng theo số lượng câu hỏi thực tế trong batch
        session[self.SESSION_KEY] = self.to_dict() # Lưu lại trạng thái cập nhật vào session
        session.modified = True 
        print(f">>> SESSION_MANAGER: Nhóm đáp án đã xử lý. current_batch_start_index: {self.current_batch_start_index} <<<")

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