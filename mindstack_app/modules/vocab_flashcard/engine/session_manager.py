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
from mindstack_app.modules.learning.models import LearningProgress
from .algorithms import (
    get_new_only_items,
    get_due_items,
    get_hard_items,
    get_mixed_items,
    get_all_review_items,
    get_all_items_for_autoplay,
    get_sequential_items,
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
import threading
from mindstack_app.modules.vocab_flashcard.services import AudioService

# [NEW] Imports for Preview Simulation
from mindstack_app.modules.learning.logics.scoring_engine import ScoringEngine

from mindstack_app.utils.media_paths import build_relative_media_path
from mindstack_app.utils.content_renderer import render_text_field

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
                 session_points=0, db_session_id=None, dispatched_item_ids=None):
        self.user_id = user_id
        self.set_id = set_id
        self.mode = mode
        self.total_items_in_session = total_items_in_session
        self.processed_item_ids = processed_item_ids
        self.dispatched_item_ids = dispatched_item_ids or [] # Track items sent but not answered
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
            db_session_id=session_dict.get('db_session_id'),
            dispatched_item_ids=session_dict.get('dispatched_item_ids', [])
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
            'dispatched_item_ids': self.dispatched_item_ids,
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
        from mindstack_app.modules.vocab_flashcard.services.session_service import LearningSessionService
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
            return False, "Chế độ học không hợp lệ.", None

        algorithm_func = {
            'sequential': get_sequential_items,
            'all_review': get_all_review_items,
            'new_only': get_new_only_items,
            'hard_only': get_hard_items,
            'autoplay_all': get_all_items_for_autoplay,
            'autoplay_learned': get_all_review_items,
        }.get(mode)
        if not algorithm_func: return False, "Không tìm thấy thuật toán cho chế độ này.", None

        accessible_ids = set(get_accessible_flashcard_set_ids(user_id))
        normalized_set_id = set_id

        if set_id == 'all':
            if not accessible_ids:
                return False, "Bạn chưa có bộ thẻ nào khả dụng.", None
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
                return False, "Không có bộ thẻ nào khả dụng trong danh sách đã chọn.", None

            normalized_set_id = filtered_ids
        else:
            try:
                set_id_int = int(set_id)
            except (TypeError, ValueError):
                return False, "ID bộ thẻ không hợp lệ.", None

            if set_id_int not in accessible_ids:
                return False, "Bạn không có quyền truy cập bộ thẻ này.", None

            normalized_set_id = set_id_int

        total_items_in_session = algorithm_func(user_id, normalized_set_id, None).count()
        if total_items_in_session == 0:
            if mode == 'due_only':
                return False, "Không có thẻ nào đến hạn ôn tập.", None
            elif mode == 'hard_only':
                return False, "Không có thẻ nào được đánh dấu là khó.", None
            elif mode == 'new_only':
                return False, "Không còn thẻ mới nào để học.", None
            else:
                return False, "Không tìm thấy thẻ nào phù hợp cho chế độ này.", None

        # [NEW] Check for existing active session to RESUME
        # This prevents duplicate sessions/wiping progress when user re-enters
        existing_session = LearningSessionService.get_active_session(user_id, learning_mode='flashcard', set_id_data=normalized_set_id)
        if existing_session and existing_session.mode_config_id == mode:
            # Resume existing session
            current_app.logger.info(f"Resuming existing session {existing_session.session_id} for user {user_id}")
            
            # Reconstruct manager
            resumed_manager = cls(
                user_id=existing_session.user_id,
                set_id=existing_session.set_id_data,
                mode=existing_session.mode_config_id,
                total_items_in_session=existing_session.total_items,
                processed_item_ids=existing_session.processed_item_ids or [],
                correct_answers=existing_session.correct_count,
                incorrect_answers=existing_session.incorrect_count,
                vague_answers=existing_session.vague_count,
                start_time=existing_session.start_time.isoformat() if existing_session.start_time else None,
                session_points=existing_session.points_earned,
                db_session_id=existing_session.session_id
            )
            
            session[cls.SESSION_KEY] = resumed_manager.to_dict()
            session.modified = True
            return True, "Tiếp tục phiên học hiện tại.", existing_session.session_id

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
        return True, "Bắt đầu phiên học thành công.", new_session_manager.db_session_id

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
            
            # User uploads are served via /media/, not /static/
            return url_for('media_uploads', filename=relative_path.lstrip('/'))
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

    def get_next_batch(self, batch_size: int = 5):
        # 1. Cleanup dispatched items (remove those already processed)
        self.dispatched_item_ids = [iid for iid in self.dispatched_item_ids if iid not in self.processed_item_ids]
        
        # 2. Start building the next batch
        next_items = []
        
        # Priority: Items already in the "active hand" but not yet answered
        if self.dispatched_item_ids:
             from sqlalchemy import case
             # Fetch specifically these items in their original order
             id_list = self.dispatched_item_ids
             # Create a mapping to preserve order
             items_query = LearningItem.query.filter(LearningItem.item_id.in_(id_list))
             found_items = {itm.item_id: itm for itm in items_query.all()}
             next_items = [found_items[iid] for iid in id_list if iid in found_items]
             
             # If we have enough in dispatched, we can potentially stop early if it meets batch_size
             if len(next_items) >= batch_size:
                  # This happens if user reloads and the old batch was large
                  next_items = next_items[:batch_size]
                  # We don't need to fetch more
        
        # 3. If we don't have enough pending items, fetch new ones
        if len(next_items) < batch_size:
            needed = batch_size - len(next_items)
            
            # Use exclusion covering both processed AND currently dispatched
            exclusion_all = set(self.processed_item_ids) | set(self.dispatched_item_ids)
            exclusion_condition = None
            if exclusion_all:
                exclusion_condition = LearningItem.item_id.notin_(exclusion_all)

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
                query = apply_exclusion(get_new_only_items(self.user_id, self.set_id, None))
                query = query.order_by(LearningItem.order_in_container.asc(), LearningItem.item_id.asc())
                next_items.extend(query.limit(needed).all())
            elif self.mode == 'all_review' or self.mode == 'autoplay_learned':
                query = apply_exclusion(get_all_review_items(self.user_id, self.set_id, None))
                query = query.order_by(func.random())
                next_items.extend(query.limit(needed).all())
            elif self.mode == 'hard_only':
                query = apply_exclusion(get_hard_items(self.user_id, self.set_id, None))
                query = query.order_by(func.random())
                next_items.extend(query.limit(needed).all())
            elif self.mode == 'autoplay_all':
                query = apply_exclusion(get_all_items_for_autoplay(self.user_id, self.set_id, None))
                query = query.order_by(LearningItem.order_in_container.asc(), LearningItem.item_id.asc())
                next_items.extend(query.limit(needed).all())
            elif self.mode == 'sequential':
                due_query = apply_exclusion(get_due_items(self.user_id, self.set_id, None))
                due_items = due_query.limit(needed).all()
                next_items.extend(due_items)
                
                if len(next_items) < batch_size:
                    fill_needed = batch_size - len(next_items)
                    new_query = apply_exclusion(get_new_only_items(self.user_id, self.set_id, None))
                    new_query = new_query.order_by(LearningItem.order_in_container.asc(), LearningItem.item_id.asc())
                    next_items.extend(new_query.limit(fill_needed).all())
            elif self.mode == 'random':
                query = apply_exclusion(get_all_items_for_autoplay(self.user_id, self.set_id, None))
                query = query.order_by(func.random())
                next_items.extend(query.limit(needed).all())
            else:
                # DEFAULT / MIXED SRS
                due_query = apply_exclusion(get_due_items(self.user_id, self.set_id, None))
                due_items = due_query.limit(needed).all()
                next_items.extend(due_items)
                
                if len(next_items) < batch_size:
                    fill_needed = batch_size - len(next_items)
                    new_query = apply_exclusion(get_new_only_items(self.user_id, self.set_id, None))
                    new_query = new_query.order_by(LearningItem.order_in_container.asc())
                    next_items.extend(new_query.limit(fill_needed).all())

        # Sync registry
        for itm in next_items:
            if itm.item_id not in self.dispatched_item_ids:
                self.dispatched_item_ids.append(itm.item_id)

        if not next_items:
            return None

        batch_items_data = []
        for next_item in next_items:
            # ĐÃ THÊM: Lấy thống kê ban đầu cho thẻ sắp hiển thị
            initial_stats = FlashcardEngine.get_item_statistics(self.user_id, next_item.item_id)

            container_capabilities = set()
            container_title = ""
            try:
                container = LearningContainer.query.get(next_item.container_id)
                if container:
                    container_title = container.title or ""
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
                container_title = ""

            try:
                markers = db.session.query(UserItemMarker.marker_type).filter_by(
                    user_id=self.user_id,
                    item_id=next_item.item_id
                ).all()
                marker_list = [m[0] for m in markers]
            except Exception:
                marker_list = []

            # [NEW] Calculate Preview Data (Simulation) using FSRS-5
            preview_data = {}
            try:
                # Import FSRS engine
                from mindstack_app.modules.learning.logics.hybrid_fsrs import HybridFSRSEngine, CardState, Rating
                from mindstack_app.modules.learning.logics.scoring_engine import ScoringEngine
                
                # 1. Fetch current progress state
                progress = LearningProgress.query.filter_by(
                    user_id=self.user_id, item_id=next_item.item_id, learning_mode='flashcard'
                ).first()
                
                # Build CardState from progress
                if progress:
                    # === USE NATIVE FSRS COLUMNS ===
                    fsrs_stability = float(progress.fsrs_stability or 0.0)
                    fsrs_difficulty = float(progress.fsrs_difficulty or 5.0)
                    last_reviewed = progress.fsrs_last_review or progress.last_reviewed
                    
                    card_state = CardState(
                        stability=fsrs_stability,
                        difficulty=fsrs_difficulty,
                        reps=progress.repetitions or 0,
                        lapses=progress.lapses or 0,
                        state=int(progress.fsrs_state) if progress.fsrs_state is not None else 0,
                        last_review=last_reviewed
                    )
                else:
                    card_state = CardState()  # New card
                
                # 2. Use HybridFSRSEngine to preview states for rating 1-4
                from mindstack_app.modules.learning.services.memory_power_config_service import MemoryPowerConfigService
                desired_retention = MemoryPowerConfigService.get('FSRS_DESIRED_RETENTION', 0.9)
                engine = HybridFSRSEngine(desired_retention=desired_retention)
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                simulated_states = engine.preview_states(card_state, now_utc)
                
                # 3. Build preview data for each rating (1-4)
                # [FIX] Check if this is first time for this card (for bonus calculation)
                is_first_time_card = (progress is None or progress.fsrs_state == LearningProgress.STATE_NEW)
                
                for rating in [Rating.Again, Rating.Hard, Rating.Good, Rating.Easy]:
                    sim_state = simulated_states.get(rating, {})
                    interval_days = sim_state.get('interval', 0.0)
                    interval_minutes = int(interval_days * 1440)  # Convert to minutes
                    
                    # Calculate points preview (include first-time bonus and scaling)
                    points = ScoringEngine.calculate_answer_points(
                        mode='flashcard', 
                        quality=int(rating), 
                        is_correct=(rating >= Rating.Good),
                        is_first_time=is_first_time_card, 
                        correct_streak=(progress.correct_streak or 0) if progress else 0,
                        stability=card_state.stability,
                        difficulty=card_state.difficulty
                    ).total_points
                    
                    # FSRS metrics for frontend
                    is_correct = (rating >= Rating.Good)
                    new_stability = sim_state.get('stability', 0.0)
                    new_difficulty = sim_state.get('difficulty', 5.0)
                    current_retrievability = engine.get_realtime_retention(card_state, now_utc) * 100.0
                    
                    preview_data[str(rating)] = {
                        'interval': interval_minutes,
                        'stability': round(float(new_stability), 2),  # Days
                        'difficulty': round(float(new_difficulty), 2),  # [NEW] FSRS D
                        'retrievability': round(current_retrievability, 1),  # %
                        'points': points,
                        'status': 'review' if is_correct else 'learning'
                    }
            except Exception as e:
                current_app.logger.warning(f"Preview simulation failed for item {next_item.item_id}: {e}")
                pass

            item_dict = {
                'item_id': next_item.item_id,
                'container_id': next_item.container_id,
                'content': {
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
                'initial_stats': initial_stats,
                'can_edit': self._can_edit_container(next_item.container_id),
                'container_title': container_title,
                'markers': marker_list,
                'preview': preview_data
            }
            batch_items_data.append(item_dict)

        session[self.SESSION_KEY] = self.to_dict()
        session.modified = True

        # [PROACTIVE AUDIO] Safe Background Generation
        def generate_audio_batch_safe(app_obj, item_data_list):
            with app_obj.app_context():
                # We use localized imports for thread safety
                from mindstack_app.models import LearningItem
                from mindstack_app.modules.vocab_flashcard.services import AudioService
                
                app_obj.logger.info(f"[PROACTIVE AUDIO] Background worker starting for {len(item_data_list)} items")
                
                for item_id in item_data_list:
                    try:
                        # Find the item in this thread's session
                        item = LearningItem.query.get(item_id)
                        if not item:
                            continue
                            
                        # AudioService.ensure_audio_for_item now handles internal DB saving
                        # for both existing files with missing links AND fresh generation.
                        AudioService.ensure_audio_for_item(item, side='front', auto_save_to_db=True)
                        AudioService.ensure_audio_for_item(item, side='back', auto_save_to_db=True)
                        
                    except Exception as e:
                         app_obj.logger.error(f"[PROACTIVE AUDIO] Error for item {item_id}: {e}")

        # Prepare simple data list to avoid ORM/Lazy-loading issues in thread
        item_data_list = [itm.item_id for itm in next_items]

        # Pass actual Flask app object to the thread
        app_to_pass = current_app._get_current_object()
        thread = threading.Thread(target=generate_audio_batch_safe, args=(app_to_pass, item_data_list), daemon=True)
        thread.start()
        current_app.logger.info(f"[PROACTIVE AUDIO] Spawned thread to pre-generate {len(item_data_list)} items")
        

        return {
            'items': batch_items_data,
            'total_items_in_session': self.total_items_in_session,
            'container_name': container_title or "Bộ thẻ",
            'session_correct_answers': self.correct_answers,
            'session_incorrect_answers': self.incorrect_answers,
            'session_vague_answers': self.vague_answers,
            'session_total_answered': self.correct_answers + self.incorrect_answers + self.vague_answers
        }

    def process_flashcard_answer(self, item_id, user_answer_quality, duration_ms=0, user_answer_text=None):
        from mindstack_app.modules.vocab_flashcard.services.session_service import LearningSessionService
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
        from mindstack_app.modules.vocab_flashcard.services.session_service import LearningSessionService
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
