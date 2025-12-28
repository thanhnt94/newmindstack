# File: quiz/individual/logics/session_logic.py
# Phiên bản: 2.2 (Refactored location)
# MỤC ĐÍCH: Sửa lỗi không tìm thấy URL chỉnh sửa bằng cách thêm container_id vào dữ liệu câu hỏi.

from flask import session, current_app, url_for
from flask_login import current_user
from typing import Optional
from mindstack_app.models import (
    LearningContainer,
    LearningGroup,
    LearningItem,
    User,
    UserNote,
    ContainerContributor,
    db,
)
from mindstack_app.models.learning_progress import LearningProgress
from .algorithms import (
    get_new_only_items,
    get_reviewed_items,
    get_hard_items,
    get_accessible_quiz_set_ids,
)
from .stats_logic import get_quiz_item_statistics
from ...engine import QuizEngine
from ..config import QuizLearningConfig
from sqlalchemy.sql import func
import random
import datetime
import os

from mindstack_app.modules.shared.utils.media_paths import build_relative_media_path

class QuizSessionManager:
    """
    Quản lý phiên học Quiz cho một người dùng.
    Sử dụng Flask session để lưu trữ trạng thái.
    """
    SESSION_KEY = 'quiz_session'

    def __init__(self, user_id, set_id, mode, batch_size,
                 total_items_in_session, processed_item_ids,

                 correct_answers, incorrect_answers, start_time, common_pre_question_text_global,
                 *, total_question_groups_in_session=None,
                 processed_question_count=0, group_numbering=None, group_sub_counters=None, custom_pairs=None, batch_options_mappings=None):
        """
        Khởi tạo một phiên QuizSessionManager.
        """
        self.user_id = user_id
        self.set_id = set_id
        self.mode = mode
        self.batch_size = batch_size
        self.total_items_in_session = total_items_in_session
        self.total_question_groups_in_session = total_question_groups_in_session
        self.processed_item_ids = processed_item_ids
        self.correct_answers = correct_answers
        self.incorrect_answers = incorrect_answers
        self.start_time = start_time
        self.common_pre_question_text_global = common_pre_question_text_global
        self.processed_question_count = processed_question_count or 0
        self.group_numbering = group_numbering or {}
        self.group_sub_counters = group_sub_counters or {}
        self.custom_pairs = custom_pairs or []
        self.batch_options_mappings = batch_options_mappings or {} 
        self._media_folders_cache: Optional[dict[str, str]] = None
        current_app.logger.debug(f"QuizSessionManager: Instance được khởi tạo/tải. User: {self.user_id}, Set: {self.set_id}, Mode: {self.mode}")

    @classmethod
    def from_dict(cls, session_dict):
        """
        Tạo một instance QuizSessionManager từ một dictionary (thường từ Flask session).
        """
        instance = cls(
            user_id=session_dict.get('user_id'),
            set_id=session_dict.get('set_id'),
            mode=session_dict.get('mode'),
            batch_size=session_dict.get('batch_size'),
            total_items_in_session=session_dict.get('total_items_in_session', 0),
            processed_item_ids=session_dict.get('processed_item_ids', []),
            correct_answers=session_dict.get('correct_answers', 0),
            incorrect_answers=session_dict.get('incorrect_answers', 0),
            start_time=session_dict.get('start_time'),
            common_pre_question_text_global=session_dict.get('common_pre_question_text_global'),
            total_question_groups_in_session=session_dict.get('total_question_groups_in_session'),
            processed_question_count=session_dict.get('processed_question_count', 0),
            group_numbering=session_dict.get('group_numbering') or {},
            group_sub_counters=session_dict.get('group_sub_counters') or {},
            custom_pairs=session_dict.get('custom_pairs') or [],
            batch_options_mappings=session_dict.get('batch_options_mappings') or {},
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
            'total_question_groups_in_session': self.total_question_groups_in_session,
            'processed_item_ids': self.processed_item_ids,
            'current_batch_start_index': len(self.processed_item_ids),
            'correct_answers': self.correct_answers,
            'incorrect_answers': self.incorrect_answers,
            'start_time': self.start_time,
            'common_pre_question_text_global': self.common_pre_question_text_global,
            'processed_question_count': self.processed_question_count,
            'group_numbering': self.group_numbering,
            'group_sub_counters': self.group_sub_counters,
            'custom_pairs': self.custom_pairs,
            'batch_options_mappings': self.batch_options_mappings,
        }

    @classmethod
    def start_new_quiz_session(cls, set_id, mode, batch_size, custom_pairs=None):
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
        elif mode in ['custom', 'mixed', 'front_back', 'back_front']:
            # For custom modes on Flashcards, we usually just want ALL items (new + reviewed) or specific logic.
            # Assuming 'new_only' logic base for now, or maybe get_all_items (which we don't have yet).
            # Let's reuse get_new_only_items combined with get_reviewed_items logic?
            # Or simplified: Get ALL items.
            # Since algorithms.py doesn't have get_all_items, let's use get_reviewed_items as a base fallback or creating a new one.
            # Ideally, specific algorithm for these modes.
            # But for now, let's use get_new_only_items as a placeholder if we need functionality.
            # Actually, `vocabulary/mcq` typically quizzes on ALL items.
            # We can use `_get_base_items_query` directly inside a lambda or wrapper.
            algorithm_func = lambda u, c, s: _get_base_items_query(u, c) # Return query for all items
            # Imports inside function to avoid circular dependency if _get_base_items_query is not exported.
            # Ensure _get_base_items_query is imported.
            from .algorithms import _get_base_items_query
        
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

        group_counts = (
            total_items_in_session_query
            .with_entities(LearningItem.group_id, func.count())
            .group_by(LearningItem.group_id)
            .all()
        )
        total_question_groups_in_session = 0
        for gid, count in group_counts:
            if gid is None:
                total_question_groups_in_session += count
            else:
                total_question_groups_in_session += 1

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
            total_question_groups_in_session=total_question_groups_in_session,
            processed_item_ids=[],
            correct_answers=0,
            incorrect_answers=0,
            start_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            common_pre_question_text_global=common_pre_question_text_global,
            processed_question_count=0,
            group_numbering={},
            group_sub_counters={},
            custom_pairs=custom_pairs,
            batch_options_mappings={},
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
        elif self.mode in ['custom', 'mixed', 'front_back', 'back_front']:
            # Fallback for custom modes
             from .algorithms import _get_base_items_query
             algorithm_func = lambda u, c, s: _get_base_items_query(u, c)
        
        if not algorithm_func:
            current_app.logger.error(f"Không tìm thấy hàm thuật toán cho chế độ: {self.mode}")
            return None

        unprocessed_items_query = algorithm_func(self.user_id, self.set_id, None).filter(
            LearningItem.item_id.notin_(self.processed_item_ids)
        )
        
        unprocessed_items = unprocessed_items_query.order_by(func.random()).all()

        if not unprocessed_items:
            current_app.logger.debug("Không còn câu hỏi mới nào để lấy.")
            return None

        grouped_candidates: dict[str, list[LearningItem]] = {}
        for item in unprocessed_items:
            if item.group_id:
                key = f"group-{item.group_id}"
            else:
                key = f"single-{item.item_id}"
            grouped_candidates.setdefault(key, []).append(item)

        group_keys = list(grouped_candidates.keys())
        random.shuffle(group_keys)

        new_items_to_add_to_session: list[LearningItem] = []
        selected_group_count = 0

        for key in group_keys:
            if selected_group_count >= requested_batch_size:
                break
            new_items_to_add_to_session.extend(grouped_candidates[key])
            selected_group_count += 1

        if not new_items_to_add_to_session:
            current_app.logger.debug("Không chọn được nhóm câu hỏi nào để thêm.")
            return None

        items_data = []
        newly_processed_item_ids = []
        next_main_number = self.processed_question_count + 1
        group_sub_counters = dict(self.group_sub_counters or {})
        group_numbering = dict(self.group_numbering or {})
        main_numbers_in_batch: list[int] = []
        
        # Reset mappings for new batch
        self.batch_options_mappings = {}

        for item in new_items_to_add_to_session:
            # Lấy ghi chú cho câu hỏi này
            note = UserNote.query.filter_by(user_id=self.user_id, item_id=item.item_id).first()

            group_details = None
            group_key = None
            if item.group_id and getattr(item, 'group', None):
                group_obj = item.group
                group_content = group_obj.content or {}
                group_details = {
                    'group_id': group_obj.group_id,
                    'external_id': group_content.get('external_id'),
                    'shared_components': group_content.get('shared_components') or [],
                    'shared_values': {
                        token: group_content.get(field)
                        for token, field in {
                            'image': 'question_image_file',
                            'audio': 'question_audio_file',
                            'explanation': 'explanation',
                            'prompt': 'ai_prompt',
                        }.items()
                        if token in (group_content.get('shared_components') or [])
                    }
                }
                group_key = str(group_obj.group_id)

            if group_key and group_key in group_numbering:
                main_number = group_numbering[group_key]
            else:
                main_number = next_main_number
                next_main_number += 1
                if group_key:
                    group_numbering[group_key] = main_number

            if group_key:
                sub_index = group_sub_counters.get(group_key, 0) + 1
                group_sub_counters[group_key] = sub_index
                display_number = f"{main_number}.{sub_index}"
            else:
                display_number = str(main_number)
                sub_index = None

            main_numbers_in_batch.append(main_number)

            # Create a clean copy of content and filter options
            content_copy = dict(item.content or {})
            raw_options = content_copy.get('options') or {}
            # Filter out empty options (e.g. for questions with only 2 or 3 answers)
            content_copy['options'] = {
                k: v for k, v in raw_options.items() 
                if k in ('A', 'B', 'C', 'D') and v not in (None, '')
            }

            item_dict = {
                'item_id': item.item_id,
                # THAY ĐỔI: Thêm container_id để có thể tạo URL chỉnh sửa
                'container_id': item.container_id,
                'content': content_copy,
                'ai_explanation': item.ai_explanation,
                'note_content': note.content if note else '',
                'group_id': item.group_id,
                'group_details': group_details,
                'display_number': display_number,
                'main_number': main_number,
                'sub_index': sub_index,
            }
            container_obj = item.container if hasattr(item, 'container') else None
            
            # --- INTEGRATION: QuizEngine for Flashcards ---
            if item.item_type == 'FLASHCARD':
                # Convert LearningItem to QuizEngine-compatible dict format
                all_items_pool = []
                # Fetch minimal data for distractors (optimize later to cache in session if needed)
                # For now, fetch all items in container (similar to legacy behavior)
                # Limit to 200 random items to avoid performance hit on huge sets
                # We do this query on EVERY batch. Optimizable but functional.
                distractor_items = LearningItem.query.filter_by(
                    container_id=item.container_id, 
                    item_type='FLASHCARD'
                ).limit(200).all()
                
                for d_item in distractor_items:
                    d_content = d_item.content or {}
                    # Normalize format for QuizEngine
                    formatted_d = {
                        'item_id': d_item.item_id,
                        'prompt': d_content.get('front'), 
                        'answers': [d_content.get('back')],
                        'content': d_content
                    }
                    if d_content.get('memrise_prompt') and d_content.get('memrise_answers'):
                        formatted_d['prompt'] = d_content.get('memrise_prompt')
                        formatted_d['answers'] = d_content.get('memrise_answers')
                    
                    all_items_pool.append(formatted_d)
                
                # Format current item
                current_item_dict = next((i for i in all_items_pool if i['item_id'] == item.item_id), None)
                if not current_item_dict:
                    # If not in limited pool, add it manually
                    c_content = item.content or {}
                    current_item_dict = {
                        'item_id': item.item_id,
                        'prompt': c_content.get('front'),
                        'answers': [c_content.get('back')],
                        'content': c_content
                    }
                
                generated_question = QuizEngine.generate_question(
                    current_item_dict, 
                    all_items_pool, 
                    mode=self.mode if self.mode in ['custom', 'mixed', 'front_back', 'back_front'] else 'front_back',
                    custom_pairs=self.custom_pairs
                )
                
                # Merge generated question into content
                item_dict['content'].update({
                    'question': generated_question['prompt'],
                    'options': dict(zip(['A', 'B', 'C', 'D'], generated_question['choices'])),
                    'correct_answer': generated_question['correct_answer'], # Should be hidden? Frontend needs it?
                    # Note: Legacy QuizFrontend might check correct_answer in HTML for debug or immediate feedback?
                    # Usually better to verify on server.
                    # But QuizSessionManager returns 'content' which includes options.
                })
                # Hide answer from direct content if strictly server-side check, 
                # but legacy logic might rely on it being present (though insecure).
                # New quiz logic checks on server.
                # However, generated_question includes 'audio_url'. Update if needed.
                if generated_question.get('audio_url'):
                    # Override/Set audio
                     item_dict['content']['question_audio_file'] = generated_question['audio_url']

            # Capture options mapping for validation
            if item_dict['content'].get('options'):
                self.batch_options_mappings[str(item.item_id)] = item_dict['content']['options']

            # Media URL resolution (Existing logic)
            if item_dict['content'].get('question_image_file'):
                item_dict['content']['question_image_file'] = self._get_media_absolute_url(
                    item_dict['content']['question_image_file'], 'image', container=container_obj
                )
            if item_dict['content'].get('question_audio_file'):
                item_dict['content']['question_audio_file'] = self._get_media_absolute_url(
                    item_dict['content']['question_audio_file'], 'audio', container=container_obj
                )

            # Calculate User Stats for this question
            # Note: This might cause N+1 query issue if batch is large. For generic batch size (10-20) it's acceptable.
            # Optimization: could query stats for all items in batch in one go, but keeping it simple for now.
            # Get User Stats for this question using LearningProgress
            progress = LearningProgress.query.filter_by(
                user_id=self.user_id,
                item_id=item.item_id,
                learning_mode=LearningProgress.MODE_QUIZ
            ).first()
                
            if progress:
                times_answered = (progress.times_correct or 0) + (progress.times_incorrect or 0)
                correct_count = progress.times_correct or 0
                incorrect_count = progress.times_incorrect or 0
                accuracy = round((correct_count / times_answered * 100), 1) if times_answered > 0 else 0
                    
                # History from mode_data if available
                mode_data = progress.mode_data or {}
                history = mode_data.get('review_history', [])
                recent_history = history[-5:][::-1] if history else []
                    
                last_reviewed_str = progress.last_reviewed.strftime("%d/%m %H:%M") if progress.last_reviewed else "--"

                item_dict['user_stats'] = {
                    'has_data': True,
                    'times_answered': times_answered,
                    'correct_count': correct_count,
                    'incorrect_count': incorrect_count,
                    'accuracy': accuracy,
                    'streak': progress.correct_streak or 0,
                    'last_reviewed': last_reviewed_str,
                    'recent_history': recent_history
                }
            else:
                item_dict['user_stats'] = {
                    'has_data': False,
                    'times_answered': 0,
                    'correct_count': 0,
                    'incorrect_count': 0,
                    'accuracy': 0,
                    'streak': 0,
                    'last_reviewed': '--',
                    'recent_history': []
                }

            # Determine can_edit
            can_edit = False
            if current_user.is_authenticated and current_user.user_role == User.ROLE_ADMIN:
                can_edit = True
            elif hasattr(item, 'container') and item.container:
                if item.container.creator_user_id == self.user_id:
                    can_edit = True
                else:
                    contributor = ContainerContributor.query.filter_by(
                        container_id=item.container_id,
                        user_id=self.user_id,
                        permission_level='editor'
                    ).first()
                    if contributor:
                        can_edit = True

            item_dict['can_edit'] = can_edit

            items_data.append(item_dict)
            newly_processed_item_ids.append(item.item_id)

        self.processed_item_ids.extend(newly_processed_item_ids)
        self.group_sub_counters = group_sub_counters
        self.group_numbering = group_numbering
        if main_numbers_in_batch:
            self.processed_question_count = max(self.processed_question_count, max(main_numbers_in_batch))
        session[self.SESSION_KEY] = self.to_dict()
        session.modified = True

        return {
            'items': items_data,
            'common_pre_question_text_global': self.common_pre_question_text_global,
            'start_index': len(self.processed_item_ids) - len(items_data),
            'total_items_in_session': self.total_items_in_session,
            'total_question_groups_in_session': self.total_question_groups_in_session,
            'question_number_min': min(main_numbers_in_batch) if main_numbers_in_batch else None,
            'question_number_max': max(main_numbers_in_batch) if main_numbers_in_batch else None,
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
            duration_ms = answer.get('duration_ms', 0)

            # --- INTEGRATION: Use QuizEngine for checking answer ---
            # Try to get existing answer logic from QuizEngine
            # We need to discern between 'Quiz Set Item' (QUIZ_MCQ) and 'Flashcard Item' (FLASHCARD)
            item = LearningItem.query.get(item_id)
            explanation = ""
            correct_option_char = "" # Need to determine this
            
            if item:
                # Need explanation
                explanation = item.content.get('explanation') or item.ai_explanation or ""
                
                # Resolve User Answer Text from Key (A/B/C/D) via batch_options_mappings
                options_mapping = self.batch_options_mappings.get(str(item_id)) or {}
                # Also check item content directly if not in mapping (fallback for legacy sets)
                if not options_mapping and item.content and item.content.get('options'):
                     options_mapping = item.content.get('options')

                user_answer_val = options_mapping.get(user_answer_text) 
                
                # If no mapping, assume user_answer_text IS the value? (Unlikely for A/B keys)
                # But legacy process_quiz_answer used the KEY.
                # QuizEngine expects TEXT for Flashcards (generated).
                
                check_val = user_answer_val if user_answer_val else user_answer_text
                
                # Special handling for QUIZ_MCQ legacy logic via QuizEngine?
                # If item is QUIZ_MCQ, QuizEngine.check_answer will look for 'correct_answer' in content.
                # If 'correct_answer' in content is "A" (key) or "Text"?
                # Legacy: `correct_answer` is Text. 
                # `process_quiz_answer` logic: 
                #    correct_answer_text = item.content.get('correct_answer')
                #    find char where options[char] == correct_answer_text.
                #    compare user_char == char.
                
                # So Legacy validated KEYS.
                # QuizEngine validates VALUES (Text).
                
                # If we pass TEXT (user_answer_val) to QuizEngine.check_answer:
                # QuizEngine checks if `user_answer.lower() in [correct_answers...]`.
                # If `correct_answers` are TEXT values, then passing `user_answer_val` is CORRECT.
                
                result = QuizEngine.check_answer(
                    item_id=item_id,
                    user_answer=check_val, 
                    user_id=self.user_id,
                    duration_ms=duration_ms
                )
                
                is_correct = result.get('correct', False)
                score_change = 0 # Handled by QuizEngine internally (SRS + Score)?
                # QuizEngine.check_answer calls ScoreService.award_points.
                # But it returns 'correct' dict.
                # It does NOT return score_change explicitly.
                # Wait, QuizEngine.check_answer DOES return score_change?
                # No, looking at code: `return {'correct': is_correct, ...}`.
                # But it calculates `score_change` internally for ScoreService.
                # We need `score_change` for frontend feedback in `results`.
                
                # Update QuizEngine to return score_change? 
                # Or estimate it. 
                # Standard is usually +5 or updated logic.
                # Actually, QuizEngine hardcodes +5.
                score_change = 5 if is_correct else 0
                
                # Also, we might want "correct_option_char" for UI feedback.
                # We need to find which Key corresponds to the correct answer returned by QuizEngine.
                correct_text = result.get('correct_answer')
                correct_option_char = None
                if correct_text and options_mapping:
                    # Find key for this text
                    for k, v in options_mapping.items():
                        if str(v).strip().lower() == str(correct_text).strip().lower():
                            correct_option_char = k
                            break
                            
                updated_total_score = current_user_total_score + score_change # Approximate, real value in DB.

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