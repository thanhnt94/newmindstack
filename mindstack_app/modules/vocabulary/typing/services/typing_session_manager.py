# File: vocabulary/typing/typing_session_manager.py
# Typing Session Management - Handles state persistence for Typing learning mode.

import json
import random
from flask import session, current_app
from ..interface import VocabTypingInterface

class TypingSessionManager:
    """
    Manages the state of a Typing practice session.
    Persists data in the Database (UserContainerState.settings).
    """
    
    def __init__(self, user_id, set_id, params=None, questions=None, currentIndex=0, stats=None, answers=None, db_session_id=None):
        self.user_id = user_id
        self.set_id = set_id
        self.params = params or {}
        self.questions = questions or []
        self.currentIndex = currentIndex
        self.stats = stats or {'correct': 0, 'wrong': 0, 'points': 0}
        self.answers = answers or {} # Map: currentIndex (str) -> {'user_input': str, 'is_correct': bool, ...}
        self.db_session_id = db_session_id

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'set_id': self.set_id,
            'params': self.params,
            'questions': self.questions,
            'currentIndex': self.currentIndex,
            'stats': self.stats,
            'answers': self.answers,
            'db_session_id': self.db_session_id
        }

    @classmethod
    def from_dict(cls, data):
        stats = data.get('stats') or {'correct': 0, 'wrong': 0, 'points': 0}
        if 'points' not in stats:
            stats['points'] = 0
            
        questions = data.get('questions') or []
        params = data.get('params') or {}
        
        # Audio backfill logic (similar to MCQ)
        if questions:
            first_q = questions[0]
            q_audio_url = first_q.get('question_audio')
            needs_fix = not q_audio_url or not str(q_audio_url).startswith(('/', 'http://', 'https://'))
            
            if needs_fix:
                try:
                    from ..services.typing_service import TypingService
                    from mindstack_app.models import LearningItem, LearningContainer
                    
                    container = LearningContainer.query.get(data.get('set_id'))
                    q_key = params.get('question_key')
                    a_key = params.get('answer_key')

                    item_ids = [q['item_id'] for q in questions]
                    if item_ids:
                        items = LearningItem.query.filter(LearningItem.item_id.in_(item_ids)).all()
                        item_map = {i.item_id: i for i in items}
                        for q in questions:
                            item = item_map.get(q['item_id'])
                            if item:
                                content = TypingService.ensure_audio_urls(item, container, q_key=q_key, a_key=a_key)
                                
                                active_q_key = q.get('question_key') or q_key
                                active_a_key = q.get('answer_key') or a_key
                                
                                q['question_audio'] = content.get(f"{active_q_key}_audio") or content.get('front_audio') or content.get('front_audio_url')
                                q['answer_audio'] = content.get(f"{active_a_key}_audio") or content.get('front_audio') or content.get('front_audio_url')
                                q['front_audio'] = content.get('front_audio') or content.get('front_audio_url')
                                q['back_audio'] = content.get('back_audio') or content.get('back_audio_url')
                except Exception as e:
                    print(f"Error backfilling Typing audio: {e}")

        return cls(
            user_id=data.get('user_id'),
            set_id=data.get('set_id'),
            params=data.get('params'),
            questions=questions,
            currentIndex=data.get('currentIndex', 0),
            stats=stats,
            answers=data.get('answers'),
            db_session_id=data.get('db_session_id')
        )

    @classmethod
    def load_from_db(cls, user_id, set_id):
        """Loads session state from the database (UserContainerState)."""
        from mindstack_app.models import UserContainerState
        ucs = UserContainerState.query.filter_by(user_id=user_id, container_id=set_id).first()
        if ucs and ucs.settings and 'typing_session_data' in ucs.settings:
            data = ucs.settings['typing_session_data']
            if data:
                return cls.from_dict(data)
        return None

    def save_to_db(self):
        """Saves current state to the database (UserContainerState)."""
        from mindstack_app.models import UserContainerState, db
        from sqlalchemy.orm.attributes import flag_modified

        try:
            ucs = UserContainerState.query.filter_by(user_id=self.user_id, container_id=self.set_id).first()
            if not ucs:
                ucs = UserContainerState(user_id=self.user_id, container_id=self.set_id, settings={})
                db.session.add(ucs)
            
            if ucs.settings is None: ucs.settings = {}
            ucs.settings['typing_session_data'] = self.to_dict()
            flag_modified(ucs, "settings")
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"[VOCAB_TYPING] DB SAVE ERROR: {str(e)}")

    def initialize_session(self, count, mode, custom_pairs, study_mode='review'):
        """Generates new questions and sets up the session."""
        from ..services.typing_service import TypingService
        self.params = {
            'count': count,
            'mode': mode,
            'custom_pairs': custom_pairs,
            'study_mode': study_mode
        }
        
        questions = TypingService.generate_session_questions(
            self.set_id, 
            config=self.params,
            user_id=self.user_id
        )
        
        if not questions:
            return False, "Không tìm thấy đủ từ vựng đã học để tạo luyện gõ"
            
        self.questions = questions
        self.currentIndex = 0
        self.stats = {'correct': 0, 'wrong': 0, 'points': 0}
        self.answers = {}
        
        # Create DB Session
        try:
            from mindstack_app.modules.session.interface import SessionInterface
            db_session = SessionInterface.create_session(
                user_id=self.user_id,
                learning_mode='typing',
                mode_config_id=mode,
                set_id_data=self.set_id,
                total_items=len(self.questions),
                extra_data={'mode': study_mode}
            )
            if db_session:
                self.db_session_id = db_session.session_id
        except Exception as e:
            print(f"Error creating DB session for typing: {e}")

        self.save_to_db()
        return True, "Session initialized"

    def get_session_data(self):
        return {
            'success': True,
            'questions': self.questions,
            'currentIndex': self.currentIndex,
            'stats': self.stats,
            'answers': self.answers,
            'total': len(self.questions),
            'db_session_id': self.db_session_id
        }

    def check_answer(self, user_input):
        """Updates stats and records the answer."""
        from mindstack_app.modules.scoring.interface import ScoringInterface
        
        if self.currentIndex >= len(self.questions):
            return {'success': False, 'message': 'Index out of bounds'}
            
        question = self.questions[self.currentIndex]
        from ..services.typing_service import TypingService
        result = TypingService.check_result(user_input, question['correct_answer'])
        is_correct = result['is_correct']
        
        # [NEW] [V3] Lấy giá trị điểm từ hệ thống scoring trung tâm
        point_value = ScoringInterface.get_score_value('VOCAB_TYPING_CORRECT_BONUS')
        
        if is_correct:
            self.stats['correct'] += 1
            # Ưu tiên params nếu có, nếu không lấy từ scoring module
            session_points = self.params.get('TYPING_CORRECT_SCORE', point_value)
            self.stats['points'] += session_points
            
            # [REMOVED] Double awarding fix. Awarding is handled by card_reviewed signal in views.
        else:
            self.stats['wrong'] += 1
            
        self.answers[str(self.currentIndex)] = {
            'user_input': user_input,
            'is_correct': is_correct
        }
        
        if self.db_session_id:
            try:
                from mindstack_app.modules.session.interface import SessionInterface
                item_id = question.get('item_id') 
                
                SessionInterface.update_progress(
                    session_id=self.db_session_id,
                    item_id=item_id,
                    result_type='correct' if is_correct else 'incorrect',
                    points=point_value if is_correct else 0
                )
                
                if self.currentIndex >= len(self.questions) - 1:
                    SessionInterface.complete_session(self.db_session_id)
                    
            except Exception as e:
                print(f"Error updating DB session for Typing: {e}")
        
        self.save_to_db()
        
        return {
            'success': True,
            'is_correct': is_correct,
            'correct_answer': question['correct_answer'],
            'stats': self.stats
        }

    def update_answer_srs(self, index, srs_data):
        key = str(index)
        if key in self.answers:
            self.answers[key].update(srs_data)
            self.save_to_db()
            return True
        return False

    def next_item(self):
        if self.currentIndex < len(self.questions) - 1:
            self.currentIndex += 1
            self.save_to_db()
            return True
        return False

    def start_next_cycle(self):
        if self.questions:
            random.shuffle(self.questions)
            self.currentIndex = 0
            self.save_to_db()
            return True
        return False

    def clear_session(self):
        from mindstack_app.models import UserContainerState, db
        from mindstack_app.utils.db_session import safe_commit
        
        try:
            ucs = UserContainerState.query.filter_by(user_id=self.user_id, container_id=self.set_id).first()
            if ucs and ucs.settings and 'typing_session_data' in ucs.settings:
                new_settings = dict(ucs.settings)
                del new_settings['typing_session_data']
                ucs.settings = new_settings
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(ucs, "settings")
                safe_commit(db.session)
        except Exception as e:
            print(f"Error clearing Typing session: {e}")
