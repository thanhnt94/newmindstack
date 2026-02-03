# File: flashcard/engine/session_manager.py
# FlashcardSessionManager - Manages the session state and batching logic.

from flask import session, current_app, url_for
from flask_login import current_user
from typing import Optional
from datetime import datetime, timezone
import random

from mindstack_app.models import LearningContainer, LearningItem, db
from mindstack_app.modules.fsrs.models import ItemMemoryState
from mindstack_app.utils.content_renderer import render_content_dict
from .config import FlashcardLearningConfig
from .algorithms import (
    get_accessible_flashcard_set_ids
)
from .core import FlashcardEngine
from .services.query_builder import FlashcardQueryBuilder
from mindstack_app.utils.media_paths import build_relative_media_path
from .vocab_flashcard_mode import get_flashcard_mode_by_id

class FlashcardSessionManager:
    """
    Manages a user's flashcard session.
    """
    SESSION_KEY = 'flashcard_session'

    def __init__(self, user_id, set_id, mode, batch_size,
                 total_items_in_session, processed_item_ids,
                 correct_answers, incorrect_answers, vague_answers, session_points,
                 start_time, db_session_id=None, current_item_id=None):
        self.user_id = user_id
        self.set_id = set_id
        self.mode = mode
        self.batch_size = batch_size
        self.total_items_in_session = total_items_in_session
        self.processed_item_ids = processed_item_ids
        self.correct_answers = correct_answers
        self.incorrect_answers = incorrect_answers
        self.vague_answers = vague_answers
        self.session_points = session_points
        self.start_time = start_time
        self.db_session_id = db_session_id
        self.current_item_id = current_item_id

    @classmethod
    def from_dict(cls, data):
        return cls(
            user_id=data.get('user_id'),
            set_id=data.get('set_id'),
            mode=data.get('mode'),
            batch_size=data.get('batch_size'),
            total_items_in_session=data.get('total_items_in_session', 0),
            processed_item_ids=data.get('processed_item_ids', []),
            correct_answers=data.get('correct_answers', 0),
            incorrect_answers=data.get('incorrect_answers', 0),
            vague_answers=data.get('vague_answers', 0),
            session_points=data.get('session_points', 0),
            start_time=data.get('start_time'),
            db_session_id=data.get('db_session_id'),
            current_item_id=data.get('current_item_id')
        )

    @classmethod
    def from_db_session(cls, active_db_session):
        """Construct a manager instance from a LearningSession database model."""
        return cls(
            user_id=active_db_session.user_id,
            set_id=active_db_session.set_id_data,
            mode=active_db_session.mode_config_id,
            batch_size=1, # Default for aura_mobile
            total_items_in_session=active_db_session.total_items,
            processed_item_ids=active_db_session.processed_item_ids or [],
            correct_answers=active_db_session.correct_count,
            incorrect_answers=active_db_session.incorrect_count,
            vague_answers=active_db_session.vague_count,
            start_time=active_db_session.start_time.isoformat() if active_db_session.start_time else None,
            session_points=active_db_session.points_earned,
            db_session_id=active_db_session.session_id,
            current_item_id=active_db_session.current_item_id
        )

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'set_id': self.set_id,
            'mode': self.mode,
            'batch_size': self.batch_size,
            'total_items_in_session': self.total_items_in_session,
            'processed_item_ids': self.processed_item_ids,
            'correct_answers': self.correct_answers,
            'incorrect_answers': self.incorrect_answers,
            'vague_answers': self.vague_answers,
            'session_points': self.session_points,
            'start_time': self.start_time,
            'db_session_id': self.db_session_id,
            'current_item_id': self.current_item_id
        }

    @classmethod
    def start_new_flashcard_session(cls, set_id, mode, session_size=None, batch_size=1):
        """Starts a new flashcard session. session_size=None means unlimited."""
        user_id = current_user.user_id
        
        # Cleanup existing session
        if cls.SESSION_KEY in session:
            session.pop(cls.SESSION_KEY, None)

        # Validate mode
        # mode might be 'mixed_srs', 'due_only', 'new_only', 'all_review', 'sequential', 'hard_only'
        
        qb = FlashcardQueryBuilder(user_id)
        if set_id == 'all':
            accessible_ids = get_accessible_flashcard_set_ids(user_id)
            qb.filter_by_containers(accessible_ids)
        else:
            try:
                if isinstance(set_id, list):
                    s_ids = [int(s) for s in set_id]
                else:
                    s_ids = [int(set_id)]
                qb.filter_by_containers(s_ids)
            except:
                return False, 'ID bộ thẻ không hợp lệ.', None

        # Apply Mode Filter using Registry
        mode_obj = get_flashcard_mode_by_id(mode)
        if mode_obj and hasattr(qb, mode_obj.filter_method):
            filter_func = getattr(qb, mode_obj.filter_method)
            filter_func()
        else:
            # Fallback to mixed if mode not found or method missing
            qb.filter_mixed()
        
        total_available = qb.count()
        if session_size is None:
            total_items_in_session = total_available
        else:
            total_items_in_session = min(total_available, session_size)
        
        if total_items_in_session == 0:
            return False, 'Không có thẻ nào cho chế độ này.', None

        new_manager = cls(
            user_id=user_id,
            set_id=set_id,
            mode=mode,
            batch_size=batch_size,
            total_items_in_session=total_items_in_session,
            processed_item_ids=[],
            correct_answers=0,
            incorrect_answers=0,
            vague_answers=0,
            session_points=0,
            start_time=datetime.now(timezone.utc).isoformat(),
            db_session_id=None
        )

        # Create DB session
        from mindstack_app.modules.session.interface import SessionInterface
        db_sess = SessionInterface.create_session(
            user_id=user_id,
            learning_mode='flashcard',
            mode_config_id=mode,
            set_id_data=set_id,
            total_items=total_items_in_session
        )
        if db_sess:
            new_manager.db_session_id = db_sess.session_id

        session[cls.SESSION_KEY] = new_manager.to_dict()
        session.modified = True
        return True, 'Success', new_manager.db_session_id

    def get_next_batch(self, batch_size=1):
        """Get next batch of items with persistence and resume support."""
        if len(self.processed_item_ids) >= self.total_items_in_session:
            return None

        # 1. RESUME LOGIC: Check if we have an active but unanswered card from before
        items = []
        from mindstack_app.modules.session.interface import SessionInterface

        if self.db_session_id:
            db_sess = SessionInterface.get_session_by_id(self.db_session_id)
            if db_sess and db_sess.current_item_id:
                # If the item in DB is not yet answered, we MUST return it to maintain continuity
                if db_sess.current_item_id not in self.processed_item_ids:
                    item = LearningItem.query.get(db_sess.current_item_id)
                    if item:
                        items = [item]
                        current_app.logger.info(f"[SESSION RESUME] Restoring item {item.item_id} for session {self.db_session_id}")

        # 2. FETCH LOGIC: If no resume item, find the next one via QueryBuilder
        if not items:
            qb = FlashcardQueryBuilder(self.user_id)
            
            if self.set_id == 'all':
                accessible_ids = get_accessible_flashcard_set_ids(self.user_id)
                qb.filter_by_containers(accessible_ids)
            else:
                s_ids = self.set_id if isinstance(self.set_id, list) else [self.set_id]
                qb.filter_by_containers(s_ids)

            # Apply Mode Filter using Registry
            mode_obj = get_flashcard_mode_by_id(self.mode)
            if mode_obj and hasattr(qb, mode_obj.filter_method):
                filter_func = getattr(qb, mode_obj.filter_method)
                filter_func()
            else:
                # Fallback to mixed if mode not found or method missing
                qb.filter_mixed()
            
            # Exclude processed
            qb.exclude_items(self.processed_item_ids)
            
            items = qb.get_query().limit(batch_size).all()
        
        if not items:
            return None

        # 3. PREPARE RESPONSE
        items_data = []
        for item in items:
            # Check permission to edit (simplified)
            can_edit = False
            if item.container:
                can_edit = (item.container.creator_user_id == self.user_id or (hasattr(current_user, 'user_role') and current_user.user_role == 'admin'))
            
            edit_url = ''
            if can_edit:
                edit_url = url_for('content_management.edit_flashcard_item', set_id=item.container_id, item_id=item.item_id)

            # Get initial stats for UI
            initial_stats = FlashcardEngine.get_item_statistics(self.user_id, item.item_id)
            
            # Check if first time
            progress = ItemMemoryState.query.filter_by(
                user_id=self.user_id, item_id=item.item_id
            ).first()
            is_first_time_card = (progress is None or progress.state == 0) # 0=NEW

            item_content = render_content_dict(item.content) if item.content else {}

            # [FIX] Resolve audio paths for the frontend
            media_folder = item.container.media_audio_folder if item.container else None
            for field in ['front_audio_url', 'back_audio_url']:
                val = item_content.get(field)
                if val and not val.startswith(('http://', 'https://', '/')):
                    rel_path = build_relative_media_path(val, media_folder)
                    if rel_path:
                        item_content[field] = f"/media/{rel_path}"

            item_dict = {
                'item_id': item.item_id,
                'container_id': item.container_id,
                'content': item_content,
                'ai_explanation': item.ai_explanation,
                'can_edit': can_edit,
                'edit_url': edit_url,
                'initial_stats': initial_stats,
                'initial_streak': initial_stats.get('current_streak', 0),
                'is_first_time_card': is_first_time_card
            }
            items_data.append(item_dict)
            
            # [IMPORTANT] DO NOT append to self.processed_item_ids here!
            # We only mark it as processed in process_flashcard_answer.
            
            # [NEW] Persist the active card to the DB for cross-device resume
            if self.db_session_id:
                SessionInterface.set_current_item(self.db_session_id, item.item_id)
                self.current_item_id = item.item_id

        return {
            'items': items_data,
            'total_items_in_session': self.total_items_in_session,
            'session_processed_count': len(self.processed_item_ids)
        }

    def process_flashcard_answer(self, item_id, quality, duration_ms=0, user_answer_text=None):
        """Process answer via Engine."""
        current_user_score = current_user.total_score
        
        score_change, new_total, result_type, new_status, item_stats, srs_data = FlashcardEngine.process_answer(
            user_id=self.user_id,
            item_id=item_id,
            quality=quality,
            current_user_total_score=current_user_score,
            mode=self.mode,
            update_srs=True,
            duration_ms=duration_ms,
            user_answer_text=user_answer_text,
            session_id=self.db_session_id,
            container_id=None, # Engine can fetch it
            learning_mode='flashcard'
        )
        
        if result_type == 'correct': self.correct_answers += 1
        elif result_type == 'incorrect': self.incorrect_answers += 1
        else: self.vague_answers += 1
        
        self.session_points += score_change
        
        # [NEW] Explicitly add to local processed list AFTER answer
        if item_id not in self.processed_item_ids:
            self.processed_item_ids.append(item_id)

        # Update DB session stats
        if self.db_session_id:
            from mindstack_app.modules.session.interface import SessionInterface
            SessionInterface.update_progress(self.db_session_id, item_id, result_type, score_change)
            # SessionInterface.update_progress already clears current_item_id in DB
            self.current_item_id = None

        return {
            'score_change': score_change,
            'updated_total_score': new_total,
            'is_correct': result_type == 'correct',
            'new_progress_status': new_status,
            'statistics': item_stats,
            'srs_data': srs_data,
            'session_points': self.session_points
        }

    @classmethod
    def end_flashcard_session(cls):
        """End the session."""
        result = {'message': 'Phiên học kết thúc', 'stats': {}}
        if cls.SESSION_KEY in session:
            data = session[cls.SESSION_KEY]
            db_id = data.get('db_session_id')
            if db_id:
                from mindstack_app.modules.session.interface import SessionInterface
                SessionInterface.complete_session(db_id)
            
            result['stats'] = {
                'correct': data.get('correct_answers', 0),
                'incorrect': data.get('incorrect_answers', 0),
                'vague': data.get('vague_answers', 0),
                'points': data.get('session_points', 0)
            }
            session.pop(cls.SESSION_KEY, None)
        return result
