# File: mindstack_app/modules/learning/flashcard/engine/session_manager.py
# Phiên bản: 4.0 (Engine refactor)
# MỤC ĐÍCH: Core flashcard session management - pure engine module.
# Engine này được gọi từ nhiều entry points: vocabulary, practice, collab.

from flask import session, current_app, url_for
from flask_login import current_user
from mindstack_app.models import (
    db,
    LearningItem,
    LearningGroup,
    User,
    LearningContainer,
    ContainerContributor,
    UserItemMarker,
)
from mindstack_app.models.learning_progress import LearningProgress
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
from .core import FlashcardEngine
from .config import FlashcardLearningConfig
from sqlalchemy.sql import func
from sqlalchemy.orm.attributes import flag_modified
import random
import datetime
import os
import asyncio
from mindstack_app.modules.learning.sub_modules.flashcard.services.audio_service import AudioService
from mindstack_app.modules.learning.sub_modules.flashcard.services.session_service import LearningSessionService

# [NEW] Imports for Preview Simulation
from mindstack_app.modules.learning.logics.memory_engine import MemoryEngine, ProgressState
from mindstack_app.modules.learning.logics.scoring_engine import ScoringEngine

from mindstack_app.utils.media_paths import build_relative_media_path
from mindstack_app.utils.content_renderer import render_text_field

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
                 correct_answers, incorrect_answers, vague_answers, start_time,
                 session_points=0, db_session_id=None):
        self.user_id = user_id
        self.set_id = set_id
        self.mode = mode
        self.total_items_in_session = total_items_in_session
        self.processed_item_ids = processed_item_ids
        self.correct_answers = correct_answers
        self.incorrect_answers = incorrect_answers
        self.vague_answers = vague_answers
        self.start_time = start_time
        self.session_points = session_points  # Track points earned in this session
        self.db_session_id = db_session_id # NEW: Link to database session
        self._media_folders_cache = None
        self._edit_permission_cache = {}

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
            start_time=session_dict['start_time'],
            session_points=session_dict.get('session_points', 0),
            db_session_id=session_dict.get('db_session_id')
        )
        instance._media_folders_cache = None
        instance._edit_permission_cache = {}
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
            'start_time': self.start_time,
            'session_points': self.session_points,
            'db_session_id': self.db_session_id
        }

    @classmethod
    def start_new_flashcard_session(cls, set_id, mode):
        user_id = current_user.user_id
        
        # [UPDATED] Smart Session Cleanup
        # If switching to a DIFFERENT set, just clear Flask session (keep DB session active for resume).
        # If restarting SAME set, complete the old session.
        if cls.SESSION_KEY in session:
            current_session_data = session.get(cls.SESSION_KEY)
            current_set_id = current_session_data.get('set_id')
            
            # Helper to normalize for comparison (handle list vs int cases if needed, though exact match is safer)
            is_same_set = str(current_set_id) == str(set_id) 
            
            if is_same_set:
                 cls.end_flashcard_session() # Complete old session for SAME set
            else:
                 session.pop(cls.SESSION_KEY, None) # Just detach, leave active in DB
        
        # [FIX] Legacy Mode Mapping
        if mode == 'review_due': mode = 'due_only'
        if mode == 'hard_items': mode = 'hard_only'
        if mode == 'random_all': mode = 'mixed_srs'
        if mode == 'review_hard': mode = 'hard_only'

        mode_config = next((m for m in FlashcardLearningConfig.FLASHCARD_MODES if m['id'] == mode), None)
        if not mode_config and mode in ('autoplay_all', 'autoplay_learned'):
            mode_config = {'id': mode}
        if not mode_config:
            return False, "Chế độ học không hợp lệ."

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
        if not algorithm_func: return False, "Không tìm thấy thuật toán cho chế độ này."

        accessible_ids = set(get_accessible_flashcard_set_ids(user_id))
        normalized_set_id = set_id

        if set_id == 'all':
            if not accessible_ids:
                return False, "Bạn chưa có bộ thẻ nào khả dụng."
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
                return False, "Không có bộ thẻ nào khả dụng trong danh sách đã chọn."

            normalized_set_id = filtered_ids
        else:
            try:
                set_id_int = int(set_id)
            except (TypeError, ValueError):
                return False, "ID bộ thẻ không hợp lệ."

            if set_id_int not in accessible_ids:
                return False, "Bạn không có quyền truy cập bộ thẻ này."

            normalized_set_id = set_id_int

        total_items_in_session = algorithm_func(user_id, normalized_set_id, None).count()
        if total_items_in_session == 0:
            if mode == 'due_only':
                return False, "Không có thẻ nào đến hạn ôn tập."
            elif mode == 'hard_only':
                return False, "Không có thẻ nào được đánh dấu là khó."
            elif mode == 'new_only':
                return False, "Không còn thẻ mới nào để học."
            else:
                return False, "Không tìm thấy thẻ nào phù hợp cho chế độ này."

        new_session_manager = cls(
            user_id=user_id, set_id=normalized_set_id, mode=mode,
            total_items_in_session=total_items_in_session,
            processed_item_ids=[], correct_answers=0,
            incorrect_answers=0, vague_answers=0,
            start_time=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )

        # Create DB session for persistence
        db_session = LearningSessionService.create_session(
            user_id=user_id,
            learning_mode='flashcard',
            mode_config_id=mode,
            set_id_data=normalized_set_id,
            total_items=total_items_in_session
        )
        if db_session:
            new_session_manager.db_session_id = db_session.session_id

        session[cls.SESSION_KEY] = new_session_manager.to_dict()
        session.modified = True
        return True, "Bắt đầu phiên học thành công."

    def _get_media_folders(self):
        if self._media_folders_cache is None:
            container = LearningContainer.query.get(self.set_id)
            if container:
                folders = getattr(container, 'media_folders', {}) or {}
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

    def _can_edit_container(self, container_id):
        """Check if the session user can edit items inside the container."""

        if container_id in self._edit_permission_cache:
            return self._edit_permission_cache[container_id]

        try:
            user = User.query.get(self.user_id)
            if not user:
                self._edit_permission_cache[container_id] = False
                return False

            if user.user_role == User.ROLE_ADMIN:
                self._edit_permission_cache[container_id] = True
                return True

            container = LearningContainer.query.get(container_id)
            if container and container.creator_user_id == user.user_id:
                self._edit_permission_cache[container_id] = True
                return True

            has_permission = ContainerContributor.query.filter_by(
                container_id=container_id,
                user_id=user.user_id,
                permission_level="editor",
            ).first() is not None
            self._edit_permission_cache[container_id] = has_permission
            return has_permission
        except Exception:
            self._edit_permission_cache[container_id] = False
            return False

    def get_next_batch(self):
        next_item = None
        exclusion_condition = None
        if self.processed_item_ids:
            exclusion_condition = LearningItem.item_id.notin_(self.processed_item_ids)

        # [NEW] Exclude items marked as 'ignored' by this user
        ignored_subquery = db.session.query(UserItemMarker.item_id).filter(
            UserItemMarker.user_id == self.user_id,
            UserItemMarker.marker_type == 'ignored'
        )

        def apply_exclusion(query):
            # 1. Exclude processed
            if exclusion_condition is not None:
                query = query.filter(exclusion_condition)
            # 2. Exclude ignored
            query = query.filter(LearningItem.item_id.notin_(ignored_subquery))
            return query

        if self.mode == 'new_only':
            query = apply_exclusion(
                get_new_only_items(self.user_id, self.set_id, None)
            ).order_by(LearningItem.order_in_container.asc())
            next_item = query.first()
        elif self.mode == 'due_only':
            query = apply_exclusion(
                get_due_items(self.user_id, self.set_id, None)
            ).order_by(LearningProgress.due_time.asc())
            next_item = query.first()
        elif self.mode == 'hard_only':
            query = apply_exclusion(
                get_hard_items(self.user_id, self.set_id, None)
            ).order_by(LearningProgress.due_time.asc(), LearningItem.item_id.asc())
            next_item = query.first()
        elif self.mode == 'all_review':
            query = apply_exclusion(
                get_all_review_items(self.user_id, self.set_id, None)
            ).order_by(LearningProgress.due_time.asc(), LearningItem.item_id.asc())
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
            ).order_by(LearningProgress.due_time.asc())
            next_item = due_query.first()
            if not next_item:
                new_query = apply_exclusion(
                    get_new_only_items(self.user_id, self.set_id, None)
                ).order_by(LearningItem.order_in_container.asc())
                next_item = new_query.first()

        if not next_item:
            return None

        # ĐÃ THÊM: Lấy thống kê ban đầu cho thẻ sắp hiển thị
        initial_stats = FlashcardEngine.get_item_statistics(self.user_id, next_item.item_id)

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

        try:
            markers = db.session.query(UserItemMarker.marker_type).filter_by(
                user_id=self.user_id,
                item_id=next_item.item_id
            ).all()
            marker_list = [m[0] for m in markers]
        except Exception:
            marker_list = []

        except Exception:
            marker_list = []

        # [NEW] Calculate Preview Data (Simulation)
        preview_data = {}
        try:
            # 1. Fetch current progress state
            progress = LearningProgress.query.filter_by(
                user_id=self.user_id, item_id=next_item.item_id, learning_mode='flashcard'
            ).first()
            
            if progress:
                current_state = ProgressState(
                    status=progress.status,
                    mastery=getattr(progress, 'mastery', 0.0) or 0.0,
                    repetitions=progress.repetitions,
                    interval=progress.interval,
                    correct_streak=progress.correct_streak,
                    incorrect_streak=progress.incorrect_streak,
                    easiness_factor=progress.easiness_factor,
                    # Spec v8 fields from mode_data
                    custom_state=progress.mode_data.get('custom_state', 'new') if progress.mode_data else 'new',
                    hard_streak=progress.mode_data.get('hard_streak', 0) if progress.mode_data else 0,
                    learning_reps=progress.mode_data.get('learning_reps', 0) if progress.mode_data else 0,
                    precise_interval=progress.mode_data.get('precise_interval', 20.0) if progress.mode_data else 20.0
                )
                # Inject last_reviewed for Review Ahead
                current_state.last_reviewed = progress.last_reviewed
            else:
                # Default new state
                current_state = ProgressState(
                    status='new', mastery=0.0, repetitions=0, interval=0,
                    correct_streak=0, incorrect_streak=0, easiness_factor=2.5,
                    custom_state='new', hard_streak=0, learning_reps=0, precise_interval=20.0
                )

            # 2. Simulate outcomes for all qualities (0-7 for Spec v8)
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            for q in range(8): # 0 to 7
                # Simulate Memory Engine
                res = MemoryEngine.process_answer(current_state, q, now=now_utc)
                
                # Simulate Points
                points = ScoringEngine.quality_to_score(q)
                
                preview_data[str(q)] = {
                    'interval': res.new_state.interval,
                    'mastery': round(res.new_state.mastery * 100, 1), # %
                    'memory_power': round(res.memory_power * 100, 1), # %
                    'points': points,
                    'status': res.new_state.status
                }
        except Exception as e:
            current_app.logger.warning(f"Preview simulation failed for item {next_item.item_id}: {e}")
            pass

        item_dict = {

            'item_id': next_item.item_id,
            'container_id': next_item.container_id,
            'content': {
                # BBCode rendering applied to text fields
                'front': render_text_field(next_item.content.get('front', '')),
                'back': render_text_field(next_item.content.get('back', '')),
                'front_audio_content': render_text_field(next_item.content.get('front_audio_content', '')),
                'front_audio_url': self._get_media_absolute_url(next_item.content.get('front_audio_url'), 'audio'),
                'back_audio_content': render_text_field(next_item.content.get('back_audio_content', '')),
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
            'ai_explanation': render_text_field(next_item.ai_explanation),
            'initial_stats': initial_stats,  # Gửi kèm thống kê
            'can_edit': self._can_edit_container(next_item.container_id),
            'markers': marker_list, # [NEW] List of markers e.g. ['difficult', 'favorite']
            'preview': preview_data # [NEW] Simulation data
        }
        
        # REMOVED: self.processed_item_ids.append(next_item.item_id) - Move to process_flashcard_answer
        # to prevents skipping items on page reload.
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

    def process_flashcard_answer(self, item_id, user_answer_quality, duration_ms=0, user_answer_text=None):
        try:
            current_user_obj = User.query.get(self.user_id)
            current_user_total_score = current_user_obj.total_score if current_user_obj else 0

            score_change, updated_total_score, answer_result_type, new_progress_status, item_stats, memory_power_data = FlashcardEngine.process_answer(
                user_id=self.user_id,
                item_id=item_id,
                quality=user_answer_quality,
                current_user_total_score=current_user_total_score,
                mode=self.mode,
                duration_ms=duration_ms,
                user_answer_text=user_answer_text,
                # Session context fields
                session_id=getattr(self, 'db_session_id', None),
                container_id=self.set_id if isinstance(self.set_id, int) else None,
                learning_mode=self.mode
            )
            
            # [UPDATED] Add to processed list ONLY after answer (prevent skip on reload)
            if answer_result_type in ('correct', 'incorrect', 'vague'):
                if item_id not in self.processed_item_ids:
                    self.processed_item_ids.append(item_id)

            if answer_result_type == 'correct':
                self.correct_answers += 1
            elif answer_result_type == 'vague':
                self.vague_answers += 1
            elif answer_result_type == 'incorrect':
                self.incorrect_answers += 1
            elif answer_result_type == 'preview':
                if item_id in self.processed_item_ids:
                    self.processed_item_ids.remove(item_id)

            # [NEW] Track session points for persistence across reloads
            if score_change and score_change > 0:
                self.session_points += score_change

            # [NEW] Sync with Database Session
            if self.db_session_id:
                LearningSessionService.update_progress(
                    session_id=self.db_session_id,
                    item_id=item_id,
                    result_type=answer_result_type,
                    points=score_change if score_change and score_change > 0 else 0
                )

            session[self.SESSION_KEY] = self.to_dict()
            session.modified = True
            
            return {
                'success': True,
                'score_change': score_change,
                'updated_total_score': updated_total_score,
                'answer_result_type': answer_result_type,
                'new_progress_status': new_progress_status,
                'statistics': item_stats,
                'memory_power': memory_power_data,  # NEW: Include Memory Power metrics
                'session_points': self.session_points  # NEW: Return accumulated session points
            }
        except Exception as e:
            current_app.logger.error(f"Lỗi khi xử lý câu trả lời flashcard: {e}", exc_info=True)
            return {'error': f'Lỗi khi xử lý câu trả lời: {str(e)}'}


    @classmethod
    def end_flashcard_session(cls):
        if cls.SESSION_KEY in session:
            session_data = session.get(cls.SESSION_KEY)
            db_session_id = session_data.get('db_session_id') if session_data else None
            if db_session_id:
                LearningSessionService.complete_session(db_session_id)
            session.pop(cls.SESSION_KEY, None)
        return {'message': 'Phiên học đã kết thúc.'}

    @classmethod
    def get_session_status(cls):
        return session.get(cls.SESSION_KEY)
