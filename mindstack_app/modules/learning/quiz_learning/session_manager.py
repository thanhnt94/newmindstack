# File: mindstack_app/modules/learning/quiz_learning/session_manager.py
# Phiên bản: 1.9
# Mục đích: Quản lý trạng thái của phiên học Quiz hiện tại cho người dùng.
# ĐÃ SỬA: Hỗ trợ làm bài theo nhóm câu hỏi.
# ĐÃ SỬA: Phương thức get_current_question_data trả về một nhóm câu hỏi.
# ĐÃ SỬA: Phương thức process_answer nhận và xử lý nhiều đáp án.
# ĐÃ THÊM: Logic xử lý câu hỏi phức hợp (LearningGroup).
# ĐÃ SỬA: Sử dụng batch_size động từ người dùng thay vì hằng số cố định.
# ĐÃ SỬA: Logic gộp pre_question_text nếu giống nhau trong một nhóm.
# ĐÃ THÊM: Xác định và lưu common_pre_question_text ở cấp độ TOÀN BỘ PHIÊN HỌC.
# ĐÃ SỬA: Gắn group_content trực tiếp vào từng LearningItem trong batchData.items.
# ĐÃ SỬA: Khắc phục lỗi AttributeError: 'item_to_check' is not defined.

from flask import session, current_app
from flask_login import current_user
from ....models import db, LearningItem, UserProgress, LearningGroup
from .algorithms import get_new_only_items, get_reviewed_items, get_hard_items
from sqlalchemy.sql import func
import random
import datetime

class QuizSessionManager:
    """
    Quản lý phiên học Quiz cho một người dùng.
    Sử dụng Flask session để lưu trữ trạng thái.
    """
    SESSION_KEY = 'quiz_session'

    @staticmethod
    def start_new_quiz_session(set_id, mode, batch_size):
        """
        Khởi tạo một phiên học Quiz mới.
        Lấy danh sách câu hỏi dựa trên chế độ và số lượng yêu cầu.

        Args:
            set_id (int/str): ID của bộ Quiz hoặc 'all'.
            mode (str): Chế độ học ('new_only', 'due_only', 'hard_only').
            batch_size (int): Số lượng câu hỏi trong mỗi nhóm.
        
        Returns:
            bool: True nếu phiên được khởi tạo thành công, False nếu không có câu hỏi.
        """
        print(f">>> SESSION_MANAGER: Bắt đầu start_new_quiz_session cho set_id={set_id}, mode={mode}, batch_size={batch_size} <<<")
        current_app.logger.debug(f"SessionManager: Bắt đầu start_new_quiz_session cho set_id={set_id}, mode={mode}, batch_size={batch_size}")
        user_id = current_user.user_id
        all_items_for_session_objects = [] # Danh sách TẤT CẢ các đối tượng LearningItem cho phiên

        # Lấy tất cả các câu hỏi phù hợp với chế độ (None để lấy tất cả)
        if mode == 'new_only':
            all_items_for_session_objects = get_new_only_items(user_id, set_id, None)
        elif mode == 'due_only':
            all_items_for_session_objects = get_reviewed_items(user_id, set_id, None)
        elif mode == 'hard_only':
            all_items_for_session_objects = get_hard_items(user_id, set_id, None)
        else:
            print(f">>> SESSION_MANAGER: LỖI - Chế độ học không hợp lệ: {mode} <<<")
            current_app.logger.error(f"SessionManager: Chế độ học không hợp lệ: {mode}")
            return False

        print(f">>> SESSION_MANAGER: Chế độ '{mode}' tìm thấy {len(all_items_for_session_objects)} câu hỏi tổng cộng. <<<")
        current_app.logger.debug(f"SessionManager: Chế độ '{mode}' tìm thấy {len(all_items_for_session_objects)} câu hỏi tổng cộng.")

        if not all_items_for_session_objects:
            QuizSessionManager.end_quiz_session()
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

        session[QuizSessionManager.SESSION_KEY] = {
            'set_id': set_id,
            'mode': mode,
            'batch_size': batch_size, # Lưu batch_size vào session (số câu hiển thị mỗi lần)
            'all_item_ids': [item.item_id for item in all_items_for_session_objects], # Tất cả ID câu hỏi của phiên
            'current_batch_start_index': 0, # Index bắt đầu của nhóm câu hỏi hiện tại
            'total_items_in_session': len(all_items_for_session_objects), # Tổng số câu thực tế trong phiên
            'correct_answers': 0,
            'incorrect_answers': 0,
            'start_time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'common_pre_question_text_global': common_pre_question_text_global # Lưu vào session
        }
        print(f">>> SESSION_MANAGER: Phiên học mới đã được khởi tạo với {len(all_items_for_session_objects)} câu hỏi. Batch size: {batch_size} <<<")
        current_app.logger.debug(f"SessionManager: Phiên học mới đã được khởi tạo với {len(all_items_for_session_objects)} câu hỏi. Batch size: {batch_size}")
        return True

    @staticmethod
    def get_current_question_batch():
        """
        Lấy dữ liệu của nhóm câu hỏi hiện tại trong phiên, có xử lý nhóm câu hỏi phức hợp.
        Sẽ lấy N câu hỏi đơn hoặc N nhóm câu hỏi (nếu câu đầu tiên là nhóm).

        Returns:
            dict/None: Dữ liệu nhóm câu hỏi nếu có, None nếu phiên không hợp lệ hoặc hết câu.
        """
        quiz_session = session.get(QuizSessionManager.SESSION_KEY)
        if not quiz_session:
            print(">>> SESSION_MANAGER: Không tìm thấy phiên học trong session khi lấy nhóm câu hỏi. <<<")
            current_app.logger.debug("SessionManager: Không tìm thấy phiên học trong session.")
            return None

        current_batch_start_index = quiz_session.get('current_batch_start_index', 0)
        all_item_ids = quiz_session.get('all_item_ids', [])
        total_items_in_session = quiz_session.get('total_items_in_session', 0)
        requested_batch_size = quiz_session.get('batch_size', 10) # Lấy batch_size từ session
        common_pre_question_text_global = quiz_session.get('common_pre_question_text_global', None) # Lấy global pre-text
        
        print(f">>> SESSION_MANAGER: Lấy nhóm câu hỏi: current_batch_start_index={current_batch_start_index}, total_items_in_session={total_items_in_session}, requested_batch_size={requested_batch_size} <<<")
        current_app.logger.debug(f"SessionManager: Lấy nhóm câu hỏi: current_batch_start_index={current_batch_start_index}, total_items_in_session={total_items_in_session}, requested_batch_size={requested_batch_size}")

        if current_batch_start_index >= total_items_in_session:
            print(">>> SESSION_MANAGER: Hết nhóm câu hỏi trong phiên. <<<")
            current_app.logger.debug("SessionManager: Hết nhóm câu hỏi trong phiên.")
            return None # Hết câu hỏi

        items_data = []
        
        # Danh sách các group_id đã được xử lý trong batch này để tránh trùng lặp
        processed_group_ids = set() 
        
        # Lặp để thu thập đủ số lượng "main entries" (câu hỏi đơn hoặc nhóm câu hỏi)
        # hoặc cho đến khi hết câu hỏi trong phiên
        current_collected_entries = 0
        current_scan_index = current_batch_start_index

        while current_collected_entries < requested_batch_size and current_scan_index < total_items_in_session:
            item_id_to_check = all_item_ids[current_scan_index]
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
                            LearningItem.item_id.in_(all_item_ids) # Đảm bảo chỉ lấy các item có trong phiên hiện tại
                        ).order_by(LearningItem.order_in_container).all()

                        for item in items_in_group_query:
                            item_dict = {
                                'item_id': item.item_id,
                                'content': item.content,
                                'ai_explanation': item.ai_explanation,
                                'group_id': item.group_id,
                                'group_details': group.content # Gắn group_content trực tiếp vào item
                            }
                            items_data.append(item_dict)
                        processed_group_ids.add(item_to_check.group_id)
                        current_collected_entries += 1 # Đếm nhóm này là 1 entry
                        print(f">>> SESSION_MANAGER: Nhóm câu hỏi có {len(items_data)} item. Tổng entries đã thu thập: {current_collected_entries} <<<")
                    else:
                        print(f">>> SESSION_MANAGER: LỖI - Không tìm thấy LearningGroup với ID: {item_to_check.group_id}. Xử lý như câu đơn. <<<")
                        # Fallback: nếu không tìm thấy group, xử lý như câu đơn
                        items_data.append({
                            'item_id': item_to_check.item_id,
                            'content': item_to_check.content,
                            'ai_explanation': item_to_check.ai_explanation,
                            'group_id': item_to_check.group_id,
                            'group_details': None # Không có group_details
                        })
                        current_collected_entries += 1
                else:
                    # Nếu nhóm đã được xử lý trong batch này, bỏ qua item này
                    print(f">>> SESSION_MANAGER: Item {item_id_to_check} thuộc nhóm đã xử lý. Bỏ qua. <<<")
            else:
                # Câu hỏi đơn lẻ
                # SỬA LỖI: Đổi item_to_to_check thành item_to_check
                items_data.append({
                    'item_id': item_to_check.item_id,
                    'content': item_to_check.content,
                    'ai_explanation': item_to_check.ai_explanation,
                    'group_id': item_to_check.group_id, # Sẽ là None
                    'group_details': None # Không có group_details
                })
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
            # 'group_content': group_content, # Không còn cần thiết ở đây, đã chuyển vào từng item
            'common_pre_question_text_global': common_pre_question_text_global, # Văn bản pre-question chung toàn phiên
            'start_index': current_batch_start_index,
            'total_items_in_session': total_items_in_session,
            'actual_batch_item_count': len(items_data) # Số lượng item thực tế trong batch này
        }

    @staticmethod
    def process_answer_batch(answers):
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
        quiz_session = session.get(QuizSessionManager.SESSION_KEY)
        if not quiz_session:
            print(">>> SESSION_MANAGER: LỖI - Phiên không hợp lệ khi xử lý nhóm đáp án. <<<")
            return [{'error': 'Invalid session'}]

        results = []
        actual_items_processed_in_batch = 0 # Số lượng item thực tế được xử lý trong batch này

        for answer in answers:
            item_id = answer.get('item_id')
            user_answer = answer.get('user_answer')

            item = LearningItem.query.get(item_id)
            if not item:
                print(f">>> SESSION_MANAGER: LỖI - LearningItem không tìm thấy khi xử lý đáp án nhóm: {item_id} <<<")
                results.append({'item_id': item_id, 'error': 'Question not found'})
                continue

            correct_answer = item.content.get('correct_answer')
            is_correct = (user_answer == correct_answer)
            explanation = item.content.get('explanation') or item.ai_explanation # Ưu tiên giải thích thủ công

            # Cập nhật UserProgress
            progress = UserProgress.query.filter_by(user_id=current_user.user_id, item_id=item_id).first()
            if not progress:
                print(f">>> SESSION_MANAGER: Tạo UserProgress mới cho user {current_user.user_id}, item {item_id} <<<")
                progress = UserProgress(user_id=current_user.user_id, item_id=item_id)
                db.session.add(progress)
                progress.first_seen_timestamp = func.now()

            if is_correct:
                progress.correct_streak = (progress.correct_streak or 0) + 1
                progress.incorrect_streak = 0
                progress.times_correct = (progress.times_correct or 0) + 1
                print(f">>> SESSION_MANAGER: Câu trả lời đúng. Correct streak: {progress.correct_streak} <<<")
            else:
                progress.correct_streak = 0
                progress.incorrect_streak = (progress.incorrect_streak or 0) + 1
                progress.times_incorrect = (progress.times_incorrect or 0) + 1
                print(f">>> SESSION_MANAGER: Câu trả lời sai. Incorrect streak: {progress.incorrect_streak} <<<")
            
            if is_correct:
                progress.memory_score = min(1.0, (progress.memory_score or 0) + 0.1)
                progress.due_time = func.now() + func.interval(f'{progress.correct_streak * 24} hour') 
            else:
                progress.memory_score = max(0.0, (progress.memory_score or 0) - 0.2)
                progress.due_time = func.now() 

            progress.last_reviewed = func.now()
            progress.status = 'learning' 
            db.session.commit()
            print(f">>> SESSION_MANAGER: UserProgress cập nhật cho item {item_id}. Correct: {is_correct}, Memory Score: {progress.memory_score} <<<")

            # Cập nhật session tổng
            if is_correct:
                quiz_session['correct_answers'] += 1
            else:
                quiz_session['incorrect_answers'] += 1
            
            results.append({
                'item_id': item_id,
                'is_correct': is_correct,
                'correct_answer': correct_answer,
                'explanation': explanation
            })
            actual_items_processed_in_batch += 1 # Đếm số item đã xử lý

        # Tăng current_batch_start_index sau khi xử lý toàn bộ nhóm
        quiz_session['current_batch_start_index'] += actual_items_processed_in_batch # Tăng theo số lượng câu hỏi thực tế trong batch
        session.modified = True 
        print(f">>> SESSION_MANAGER: Nhóm đáp án đã xử lý. current_batch_start_index: {quiz_session['current_batch_start_index']} <<<")

        return results

    @staticmethod
    def end_quiz_session():
        """
        Kết thúc phiên học Quiz hiện tại và xóa dữ liệu khỏi session.
        """
        if QuizSessionManager.SESSION_KEY in session:
            session.pop(QuizSessionManager.SESSION_KEY, None)
            print(">>> SESSION_MANAGER: Phiên học đã kết thúc và xóa khỏi session. <<<")
            current_app.logger.debug("SessionManager: Phiên học đã kết thúc và xóa khỏi session.")
        return {'message': 'Phiên học đã kết thúc.'}

    @staticmethod
    def get_session_status():
        """
        Lấy trạng thái hiện tại của phiên học.
        """
        status = session.get(QuizSessionManager.SESSION_KEY)
        print(f">>> SESSION_MANAGER: Lấy trạng thái session: {status} <<<")
        current_app.logger.debug(f"SessionManager: Lấy trạng thái session: {status}")
        return status

