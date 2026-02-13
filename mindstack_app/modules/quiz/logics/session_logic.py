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
    Note,
    ContainerContributor,
    UserItemMarker,
    db,
)
# REFAC: Remove ItemMemoryState import
from mindstack_app.modules.fsrs.interface import FSRSInterface
from .algorithms import (
    get_new_only_items,
    get_reviewed_items,
    get_hard_items,
    get_accessible_quiz_set_ids,
)
from .stats_logic import get_quiz_item_statistics
from ..engine.core import QuizEngine
from ..config import QuizLearningConfig
from sqlalchemy.sql import func
import random
import datetime
from mindstack_app.utils.content_renderer import render_content_dict, render_text_field
import os

from mindstack_app.utils.media_paths import build_relative_media_path

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
                 processed_question_count=0, group_numbering=None, group_sub_counters=None, 
                 custom_pairs=None, batch_options_mappings=None, batch_correct_answers=None, 
                 current_batch_cache=None, db_session_id=None):
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
        self.custom_pairs = custom_pairs or []
        self.batch_options_mappings = batch_options_mappings or {} 
        self.batch_correct_answers = batch_correct_answers or {}
        self.current_batch_cache = current_batch_cache
        self.db_session_id = db_session_id
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
            batch_correct_answers=session_dict.get('batch_correct_answers') or {},
            current_batch_cache=session_dict.get('current_batch_cache'),
            db_session_id=session_dict.get('db_session_id')
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
            'batch_correct_answers': self.batch_correct_answers,
            'current_batch_cache': self.current_batch_cache,
            'db_session_id': self.db_session_id
        }

    @classmethod
    def start_new_quiz_session(cls, set_id, mode, session_size, batch_size=1, custom_pairs=None):
        """
        Khởi tạo một phiên học Quiz mới.
        Lấy danh sách câu hỏi dựa trên chế độ và số lượng yêu cầu.
        """
        current_app.logger.debug(f"SessionManager: Bắt đầu start_new_quiz_session cho set_id={set_id}, mode={mode}, session_size={session_size}, turn_size={batch_size}")
        user_id = current_user.user_id
        
        # [UPDATED] Smart Session Cleanup (Session Isolation)
        # If switching to a DIFFERENT set, just clear Flask session (keep DB session active for resume).
        # If restarting SAME set, complete the old session.
        if cls.SESSION_KEY in session:
            current_session_data = session.get(cls.SESSION_KEY)
            current_set_id = current_session_data.get('set_id')
            
            # Helper to normalize for comparison
            # Handle potential list vs int mismatch if applicable, though set_id usually int/list matches logic
            is_same_set = str(current_set_id) == str(set_id)
            
            if is_same_set:
                cls.end_quiz_session() # Restarting same set -> Complete old one
            else:
                session.pop(cls.SESSION_KEY, None) # Switching sets -> Detach, keep active in DB
        
        # OLD: cls.end_quiz_session()

        mode_config = next((m for m in QuizLearningConfig.QUIZ_MODES if m['id'] == mode), None)
        if not mode_config:
            current_app.logger.error(f"SessionManager: Chế độ học không hợp lệ hoặc không được định nghĩa: {mode}")
            return False, 'Chế độ học không hợp lệ.', None
        
        algorithm_func = None
        if mode == 'new_only':
            algorithm_func = get_new_only_items
        elif mode == 'due_only':
            algorithm_func = get_reviewed_items
        elif mode == 'hard_only':
            algorithm_func = get_hard_items
        elif mode in ['custom', 'mixed', 'front_back', 'back_front']:
            # Use get_reviewed_items to only include learned items (FSRS state != 0)
            algorithm_func = get_reviewed_items
        
        if not algorithm_func:
            current_app.logger.error(f"SessionManager: Không tìm thấy hàm thuật toán cho chế độ: {mode}")
            return False, 'Lỗi hệ thống: Không tìm thấy thuật toán.', None
        
        accessible_ids = set(get_accessible_quiz_set_ids(user_id))
        normalized_set_id = set_id

        if set_id == 'all':
            if not accessible_ids:
                current_app.logger.info(
                    "QuizSessionManager: Người dùng không có bộ quiz nào khả dụng cho chế độ 'all'."
                )
                return False, 'Không có bộ quiz nào khả dụng.', None
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
                return False, 'Không có bộ quiz nào khả dụng.', None

            normalized_set_id = filtered_ids
        else:
            try:
                set_id_int = int(set_id)
            except (TypeError, ValueError):
                current_app.logger.warning(
                    "QuizSessionManager: ID bộ quiz không hợp lệ khi khởi tạo phiên học."
                )
                return False, 'ID bộ quiz không hợp lệ.', None

            if set_id_int not in accessible_ids:
                current_app.logger.info(
                    "QuizSessionManager: Người dùng không có quyền truy cập bộ quiz đã chọn."
                )
                return False, 'Bạn không có quyền truy cập bộ quiz này.', None

            normalized_set_id = set_id_int

        total_items_in_session_query = algorithm_func(user_id, normalized_set_id, None)
        total_items_in_session = min(total_items_in_session_query.count(), session_size)

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
            current_app.logger.warning("SessionManager: Không có câu hỏi nào được tìm thấy cho phiên học mới.")
            return False, 'Không có câu hỏi nào cho chế độ này.', None

        sample_size = min(total_items_in_session, 50)
        
        if total_items_in_session > 0:
            sample_items = total_items_in_session_query.order_by(func.random()).limit(sample_size).all()
            global_pre_texts = [item.content.get('pre_question_text') for item in sample_items if item.content.get('pre_question_text')]
            common_pre_question_text_global = None
            if global_pre_texts and all(p == global_pre_texts[0] for p in global_pre_texts):
                common_pre_question_text_global = global_pre_texts[0]
                current_app.logger.debug(f"SessionManager: Phát hiện common_pre_question_text_global: '{common_pre_question_text_global}'")
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
            batch_correct_answers={},
            current_batch_cache=None,
            db_session_id=None
        )

        # [NEW] Create session in database
        from mindstack_app.modules.session.interface import SessionInterface
        db_session = SessionInterface.create_session(
            user_id=user_id,
            learning_mode='quiz',
            mode_config_id=mode,
            set_id_data=normalized_set_id,
            total_items=total_items_in_session
        )
        if db_session:
            new_session_manager.db_session_id = db_session.session_id

        session[cls.SESSION_KEY] = new_session_manager.to_dict()
        session.modified = True

        current_app.logger.debug(f"SessionManager: Phiên học mới đã được khởi tạo với {total_items_in_session} câu hỏi. Batch size: {batch_size}")
        return True, 'Khởi tạo thành công.', new_session_manager.db_session_id

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
            # THAY ĐỔI: Dùng media_uploads cho file người dùng tải lên thay vì static
            static_path = relative_path.lstrip('/')
            full_url = url_for('media_uploads', filename=static_path)
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


    def get_next_batch(self, requested_batch_size, force_next=False):
        """
        Lấy dữ liệu của nhóm câu hỏi tiếp theo trong phiên học.
        If force_next=False and cache exists, return cached batch (Reload support).
        """
        current_app.logger.debug(f"SessionManager: Lấy nhóm câu hỏi: Đã xử lý {len(self.processed_item_ids)}/{self.total_items_in_session}, size={requested_batch_size}, force={force_next}")
        
        if not force_next and self.current_batch_cache:
            current_app.logger.debug("SessionManager: Returning cached batch (Reload Detected).")
            return self.current_batch_cache

        if len(self.processed_item_ids) >= self.total_items_in_session:
            self.current_batch_cache = None # Clear cache provided end
            session[self.SESSION_KEY] = self.to_dict()
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
            # Use get_reviewed_items for learned items only
            algorithm_func = get_reviewed_items
        
        if not algorithm_func:
            current_app.logger.error(f"Không tìm thấy hàm thuật toán cho chế độ: {self.mode}")
            return None

        unprocessed_items_query = algorithm_func(self.user_id, self.set_id, None).filter(
            LearningItem.item_id.notin_(self.processed_item_ids)
        )
        
        # [NEW] Exclude items marked as 'ignored' by this user
        ignored_subquery = db.session.query(UserItemMarker.item_id).filter(
            UserItemMarker.user_id == self.user_id,
            UserItemMarker.marker_type == 'ignored'
        )
        unprocessed_items_query = unprocessed_items_query.filter(LearningItem.item_id.notin_(ignored_subquery))
        
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

        # [REFACTORED] Bulk fetch items via ContentInterface
        from mindstack_app.modules.content_management.interface import ContentInterface
        new_item_ids = [i.item_id for i in new_items_to_add_to_session]
        content_map = ContentInterface.get_items_content(new_item_ids)

        items_data = []
        newly_processed_item_ids = []
        next_main_number = self.processed_question_count + 1
        group_sub_counters = dict(self.group_sub_counters or {})
        group_numbering = dict(self.group_numbering or {})
        main_numbers_in_batch: list[int] = []
        
        # Reset mappings for new batch
        self.batch_options_mappings = {}
        self.batch_correct_answers = {}

        for item in new_items_to_add_to_session:
            # Lấy ghi chú cho câu hỏi này
            note = Note.query.filter_by(user_id=self.user_id, reference_type='item', reference_id=item.item_id).first()
            
            # std_content from interface (contains absolute media URLs)
            std_content = content_map.get(item.item_id) or {}
            
            # Reconstruct content expected by frontend/logic
            # Start with std_content
            content_copy = dict(std_content)
            
            # Normalize keys to what this module expects (legacy compat)
            if 'image' in content_copy: content_copy['question_image_file'] = content_copy.pop('image')
            if 'audio' in content_copy: content_copy['question_audio_file'] = content_copy.pop('audio')

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

            raw_options = content_copy.get('options') or {}
            
            # [FIX] Logic to ensure options are found even if flat structure
            if not raw_options:
                for key, field in [('A', 'option_a'), ('B', 'option_b'), ('C', 'option_c'), ('D', 'option_d')]:
                    val = content_copy.get(field)
                    if val not in (None, ''):
                        raw_options[key] = val

            # Filter out empty options (e.g. for questions with only 2 or 3 answers)
            content_copy['options'] = {
                k: v for k, v in raw_options.items() 
                if k in ('A', 'B', 'C', 'D') and v not in (None, '')
            }

            item_dict = {
                'item_id': item.item_id,
                'container_id': item.container_id,
                'content': render_content_dict(content_copy),  # BBCode rendering
                'ai_explanation': render_text_field(item.ai_explanation),
                'note_content': render_text_field(note.content if note else ''),
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
                # Keep direct query for distractors for now as they are internal logic
                distractor_items = LearningItem.query.filter_by(
                    container_id=item.container_id, 
                    item_type='FLASHCARD'
                ).limit(200).all()
                
                for d_item in distractor_items:
                    d_content = d_item.content or {}
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
                
                # Format current item using std_content from interface (mapped back)
                # Need raw values for QuizEngine? std_content has absolute URLs but text fields should be fine.
                # However, Flashcard needs 'front'/'back'.
                # Interface returns 'front', 'back' for FLASHCARD type.
                current_item_dict = next((i for i in all_items_pool if i['item_id'] == item.item_id), None)
                if not current_item_dict:
                    # If not in limited pool, use std_content
                    current_item_dict = {
                        'item_id': item.item_id,
                        'prompt': std_content.get('front'),
                        'answers': [std_content.get('back')],
                        'content': std_content # Use std_content for extended fields
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
                    'correct_answer': generated_question['correct_answer'], 
                })
                if generated_question.get('audio_url'):
                     item_dict['content']['question_audio_file'] = generated_question['audio_url']

            # Capture options mapping for validation
            if item_dict['content'].get('options'):
                self.batch_options_mappings[str(item.item_id)] = item_dict['content']['options']
            
            # Capture dynamic correct answer (especially for Flashcards)
            if item_dict['content'].get('correct_answer'):
                 self.batch_correct_answers[str(item.item_id)] = item_dict['content']['correct_answer']

            # NO MORE MANUAL MEDIA RESOLUTION NEEDED (handled by Interface + mapping above)
            
            # [NEW] Fetch markers for this item
            try:
                markers = db.session.query(UserItemMarker.marker_type).filter_by(
                    user_id=self.user_id,
                    item_id=item.item_id
                ).all()
                item_dict['markers'] = [m[0] for m in markers]
            except Exception:
                item_dict['markers'] = []

            # Calculate User Stats for this question
            state_record = FSRSInterface.get_item_state(self.user_id, item.item_id)
                
            if state_record:
                correct_count = state_record.times_correct or 0
                incorrect_count = state_record.times_incorrect or 0
                times_answered = correct_count + incorrect_count
                accuracy = round((correct_count / times_answered * 100), 1) if times_answered > 0 else 0
                    
                recent_history = [] 
                    
                last_reviewed_str = state_record.last_review.strftime("%d/%m %H:%M") if state_record.last_review else "--"

                item_dict['user_stats'] = {
                    'has_data': True,
                    'times_answered': times_answered,
                    'correct_count': correct_count,
                    'incorrect_count': incorrect_count,
                    'accuracy': accuracy,
                    'streak': state_record.streak or 0,
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
        
        result_batch = {
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
        
        self.current_batch_cache = result_batch
        session[self.SESSION_KEY] = self.to_dict()
        session.modified = True
        return result_batch

    def process_answer_batch(self, answers):
        """
        Xử lý một danh sách các câu trả lời của người dùng cho một nhóm câu hỏi.
        """
        current_app.logger.debug(f"SessionManager: Bắt đầu process_answer_batch với {len(answers)} đáp án.")
        
        results = []
        
        current_user_obj = User.query.get(self.user_id)
        current_user_total_score = current_user_obj.total_score if current_user_obj else 0

        # [REFACTORED] Bulk fetch content for answers
        from mindstack_app.modules.content_management.interface import ContentInterface
        answer_item_ids = [a.get('item_id') for a in answers if a.get('item_id')]
        content_map = ContentInterface.get_items_content(answer_item_ids)

        for answer in answers:
            item_id = answer.get('item_id')
            user_answer_text = answer.get('user_answer')
            duration_ms = answer.get('duration_ms', 0)

            # Get raw item for container_id context (needed for stats/permissions)
            item = LearningItem.query.get(item_id)
            std_content = content_map.get(item_id) or {}
            
            explanation = ""
            correct_option_char = "" 
            
            if item:
                # Need explanation
                explanation = std_content.get('explanation') or item.ai_explanation or ""
                
                # Resolve User Answer Text from Key (A/B/C/D) via batch_options_mappings
                options_mapping = self.batch_options_mappings.get(str(item_id)) or {}
                # Also check content directly if not in mapping (fallback)
                if not options_mapping and std_content.get('options'):
                     options_mapping = std_content.get('options')

                user_answer_val = options_mapping.get(user_answer_text) 
                check_val = user_answer_val if user_answer_val else user_answer_text
                
                result = QuizEngine.check_answer(
                    item_id=item_id,
                    user_answer=check_val, 
                    user_id=self.user_id,
                    duration_ms=duration_ms,
                    user_answer_key=user_answer_text,
                    session_id=getattr(self, 'db_session_id', None),
                    container_id=item.container_id if item else None,
                    mode=self.mode,
                    correct_answer_override=self.batch_correct_answers.get(str(item_id)),
                    streak_position=0 
                )
                
            is_correct = result.get('correct', False)
            score_change = result.get('score_change', 0)
            correct_option_char = None
            
            if item:
                # Need explanation (again?) - already got it above
                pass
                
                # Resolve User Answer Text from Key (A/B/C/D) via batch_options_mappings
                # (Already got mapping above)

                # Find correct option char
                correct_text = result.get('correct_answer') # Text from Engine
                if correct_text and options_mapping:
                    c_text_normalized = str(correct_text).strip().lower()
                    for k, v in options_mapping.items():
                        if str(v).strip().lower() == c_text_normalized:
                            correct_option_char = k
                            break
                
                if not correct_option_char:
                    # Fallback: Return the text itself if we can't map it to A/B/C/D
                    # This prevents "null" from showing in UI
                    correct_option_char = correct_text
                    
                    if not correct_option_char:
                        # If even correct_text is empty, try to get from content directly
                        correct_option_char = std_content.get('correct_answer') or std_content.get('correct_answer_text') or "N/A"

            item_stats = get_quiz_item_statistics(self.user_id, item_id)
            
            if is_correct:
                self.correct_answers += 1
            else:
                self.incorrect_answers += 1
            
            # Build result result dictionary with all fields from QuizEngine
            res_dict = {
                'item_id': item_id,
                'is_correct': is_correct,
                'correct_answer': correct_option_char,
                'explanation': explanation,
                'statistics': item_stats,
                'score_change': score_change,
                'user_answer': check_val, # Add user answer for state restoration
                'user_answer_key': user_answer_text # Add original key if needed
            }
            # Add SRS fields if available
            for field in ['mastery_delta', 'new_mastery_pct', 'points_breakdown', 'srs_result']:
                if field in result:
                    res_dict[field] = result[field]
                    
            results.append(res_dict)
        
        session[self.SESSION_KEY] = self.to_dict()
        session.modified = True 
        
        # [NEW] Update database session progress
        if getattr(self, 'db_session_id', None):
            try:
                from mindstack_app.modules.session.interface import SessionInterface
                
                # Assume item_id is stored in the question object. 
                # If not, we might need to adjust generate_mcq_question, 
                # but typically MCQ questions retain item_id reference.
                # NOTE: results list contains dicts with item_id. 
                # We need to loop results to update session for each?
                # The original code wasn't shown fully here, assuming it loops or batches.
                # Wait, SessionService doesn't have batch update?
                # We should update per item.
                
                for res in results:
                     SessionInterface.update_progress(
                        session_id=self.db_session_id,
                        item_id=res['item_id'],
                        result_type='correct' if res['is_correct'] else 'incorrect',
                        points=res.get('score_change', 0)
                    )
                
                # Check completion? 
                # Logic usually checks if processed >= total.
                # If so:
                if len(self.processed_item_ids) >= self.total_items_in_session:
                     SessionInterface.complete_session(self.db_session_id)

            except Exception as e:
                current_app.logger.error(f"Error updating DB session history: {e}")
            # The original code imported LearningSessionService again here.
            # We will use SessionInterface if we needed service methods, but checking lines 831-840 it uses `db` directly to update `LearningSession`.
            # So we can remove the Service import if it's not used for anything else in this block.
            # Wait, line 827 in original was importing LearningSessionService.
            
            # The original code:
            # db_sess = db.session.get(LearningSession, self.db_session_id)
            
            # It seems `LearningSessionService` wasn't even used in the following block (lines 831-840)! 
            # It just does direct DB operations.
            # I will remove the unused import.
            # We use process_answer_batch for the whole batch
            # We'll update the session metadata (counts) 
            # and processed_item_ids in bulk via a custom service method or manual update
            from mindstack_app.models import LearningSession, db
            try:
                db_sess = db.session.get(LearningSession, self.db_session_id)
                if db_sess:
                    db_sess.correct_count = self.correct_answers
                    db_sess.incorrect_count = self.incorrect_answers
                    db_sess.processed_item_ids = list(self.processed_item_ids) # Sync full list
                    db.session.add(db_sess)
                    from mindstack_app.utils.db_session import safe_commit
                    safe_commit(db.session)
            except Exception as e:
                current_app.logger.error(f"Error syncing quiz session to DB: {e}")

        print(f">>> SESSION_MANAGER: Nhóm đáp án đã xử lý. Đã xử lý tổng cộng: {len(self.processed_item_ids)} câu. <<<")

        if self.current_batch_cache:
            self.current_batch_cache['submitted_results'] = results
            # Update session with new cache state
            session[self.SESSION_KEY] = self.to_dict()
            session.modified = True
            
        return results

    @classmethod
    def end_quiz_session(cls):
        """
        Kết thúc phiên học Quiz hiện tại và xóa dữ liệu khỏi session.
        """
        result = {'message': 'Phiên học đã kết thúc.', 'stats': {}}
        
        if cls.SESSION_KEY in session:
            session_data = session.get(cls.SESSION_KEY)
            db_session_id = session_data.get('db_session_id')
            
            # Gather stats
            stats = {
                'total_items': session_data.get('total_items_in_session', 0),
                'processed_count': len(session_data.get('processed_item_ids', [])),
                'correct_count': session_data.get('correct_answers', 0),
                'incorrect_count': session_data.get('incorrect_answers', 0),
            }
            result['stats'] = stats

            if db_session_id:
                from mindstack_app.modules.session.interface import SessionInterface
                # Always mark as completed if user explicitly ends it, 
                # or just use complete_session which sets status='completed'
                SessionInterface.complete_session(db_session_id)

            session.pop(cls.SESSION_KEY, None)
            
        return result

    @classmethod
    def get_session_status(cls):
        """
        Lấy trạng thái hiện tại của phiên học.
        """
        status = session.get(cls.SESSION_KEY)
        print(f">>> SESSION_MANAGER: Lấy trạng thái session: {status} <<<")
        current_app.logger.debug(f"SessionManager: Lấy trạng thái session: {status}")
        return status
