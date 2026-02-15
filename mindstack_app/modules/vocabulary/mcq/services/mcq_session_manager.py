# File: vocabulary/mcq/mcq_session_manager.py
# MCQ Session Management - Handles state persistence for MCQ learning mode.

import json
import random
from flask import session, current_app
from ..interface import VocabMCQInterface

class MCQSessionManager:
    """
    Manages the state of an MCQ (Multiple Choice Quiz) session.
    Persists data in the Database (UserContainerState.settings).
    """
    
    def __init__(self, user_id, set_id, params=None, questions=None, currentIndex=0, stats=None, answers=None, db_session_id=None):
        self.user_id = user_id
        self.set_id = set_id
        self.params = params or {}
        self.questions = questions or []
        self.currentIndex = currentIndex
        # stats includes 'correct', 'wrong', and now 'points'
        self.stats = stats or {'correct': 0, 'wrong': 0, 'points': 0}
        self.answers = answers or {} # Map: currentIndex (str) -> {'user_answer_index': int, ...}
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
            
        # [FIX] Backfill/Normalize audio for restored sessions
        questions = data.get('questions') or []
        if questions:
            # Trigger if missing OR if they look relative (no leading slash and not external)
            first_q = questions[0]
            front_url = first_q.get('front_audio') or first_q.get('question_audio')
            needs_fix = not front_url or not str(front_url).startswith(('/', 'http://', 'https://'))
            
            if needs_fix:
                try:
                    from ..services.mcq_service import MCQService
                    from mindstack_app.models import LearningItem, LearningContainer
                    
                    # [NEW] Get container for folder context
                    container = LearningContainer.query.get(data.get('set_id'))
                    
                    # Collect IDs for items that either miss audio OR have relative paths
                    item_ids = []
                    for q in questions:
                        f_url = q.get('front_audio') or q.get('question_audio')
                        if not f_url or not str(f_url).startswith(('/', 'http://', 'https://')):
                            item_ids.append(q['item_id'])

                    if item_ids:
                        items = LearningItem.query.filter(LearningItem.item_id.in_(item_ids)).all()
                        item_map = {i.item_id: i for i in items}
                        for q in questions:
                            f_url = q.get('front_audio')
                            if not f_url or not str(f_url).startswith(('/', 'http://', 'https://')):
                                item = item_map.get(q['item_id'])
                                if item:
                                    # [FIX] Capture the returned content dict which contains absolute URLs
                                    content = MCQService.ensure_audio_urls(item, container)
                                    
                                    # Patch question object
                                    q['front_audio'] = content.get('front_audio') or content.get('front_audio_url')
                                    q['back_audio'] = content.get('back_audio') or content.get('back_audio_url')
                                    
                                    # Determine mode for this question to map question_audio
                                    # Fallback: check session params
                                    mode = data.get('params', {}).get('mode', 'front_back')
                                    is_back_front = (mode == 'back_front')
                                    if q.get('question_key') == 'back':
                                        is_back_front = True
                                        
                                    if is_back_front:
                                        q['question_audio'] = q['back_audio']
                                        q['answer_audio'] = q['front_audio']
                                    else:
                                        q['question_audio'] = q['front_audio']
                                        q['answer_audio'] = q['back_audio']
                except Exception as e:
                    print(f"Error backfilling MCQ audio: {e}")

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
        if ucs and ucs.settings and 'mcq_session_data' in ucs.settings:
            data = ucs.settings['mcq_session_data']
            if data:
                return cls.from_dict(data)
        return None

    def save_to_db(self):
        """Saves current state to the database (UserContainerState)."""
        from mindstack_app.models import UserContainerState, db
        from mindstack_app.utils.db_session import safe_commit
        import datetime

        try:
            ucs = UserContainerState.query.filter_by(user_id=self.user_id, container_id=self.set_id).first()
            if not ucs:
                ucs = UserContainerState(user_id=self.user_id, container_id=self.set_id, settings={})
                db.session.add(ucs)
            
            # Use current settings if they exist, or initialize
            if ucs.settings is None: ucs.settings = {}
            
            # [CRITICAL] Modify the settings dict directly to ensure we are using the live object
            ucs.settings['mcq_session_data'] = self.to_dict()
            
            # Trigger SQLAlchemy change detection for JSON
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(ucs, "settings")
            
            db.session.commit()
            
            # [DEBUG] [V3] Verify what was actually saved
            db.session.refresh(ucs)
            saved_data = (ucs.settings or {}).get('mcq_session_data', {})
            saved_answers = saved_data.get('answers', {})
            current_app.logger.info(f"[VOCAB_MCQ] [V3] DB SAVE success for set_id={self.set_id}. Current index {self.currentIndex}. Answers recorded: {len(saved_answers)}")
            if str(self.currentIndex) in saved_answers:
                 current_app.logger.info(f"[VOCAB_MCQ] [V3] Index {self.currentIndex} data in DB: {saved_answers[str(self.currentIndex)]}")
        except Exception as e:
            current_app.logger.error(f"[VOCAB_MCQ] [V3] DB SAVE ERROR: {str(e)}")

    def initialize_session(self, count, mode, choices, custom_pairs):
        """Generates new questions and sets up the session."""
        from ..services.mcq_service import MCQService
        self.params = {
            'count': count,
            'mode': mode,
            'choices': choices if choices is not None else 0,
            'custom_pairs': custom_pairs
        }
        
        # Use Service to generate questions (filters for learned items automatically)
        questions = MCQService.generate_session_questions(
            self.set_id, 
            config=self.params,
            user_id=self.user_id
        )
        
        if not questions:
            return False, "Không tìm thấy đủ từ vựng đã học để tạo trắc nghiệm"
            
        self.questions = questions
        self.currentIndex = 0
        self.stats = {'correct': 0, 'wrong': 0, 'points': 0}
        self.answers = {}
        
        # [NEW] Create DB Session via Service
        try:
            from mindstack_app.modules.session.interface import SessionInterface
            db_session = SessionInterface.create_session(
                user_id=self.user_id,
                learning_mode='mcq',
                mode_config_id=mode,
                set_id_data=self.set_id,
                total_items=len(self.questions)
            )
            if db_session:
                self.db_session_id = db_session.session_id
        except Exception as e:
            print(f"Error creating DB session for checking: {e}")

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

    def check_answer(self, user_answer_index):
        """Updates stats and records the answer."""
        if self.currentIndex >= len(self.questions):
            return {'success': False, 'message': 'Index out of bounds'}
            
        question = self.questions[self.currentIndex]
        is_correct = (question['correct_index'] == user_answer_index)
        
        if is_correct:
            self.stats['correct'] += 1
            self.stats['points'] += 10 # Default points for correct MCQ
        else:
            self.stats['wrong'] += 1
            
        # Record the answer (as string key for JSON compatibility in session)
        self.answers[str(self.currentIndex)] = {
            'user_answer_index': user_answer_index,
            'is_correct': is_correct
        }
        
        # [NEW] Update DB Session Progress
        if self.db_session_id:
            try:
                from mindstack_app.modules.session.interface import SessionInterface
                
                # Assume item_id is stored in the question object. 
                # If not, we might need to adjust generate_mcq_question, 
                # but typically MCQ questions retain item_id reference.
                item_id = question.get('item_id') 
                
                SessionInterface.update_progress(
                    session_id=self.db_session_id,
                    item_id=item_id,
                    result_type='correct' if is_correct else 'incorrect',
                    points=10 if is_correct else 0
                )
                
                # Check for completion
                if self.currentIndex >= len(self.questions) - 1:
                    SessionInterface.complete_session(self.db_session_id)
                    
            except Exception as e:
                print(f"Error updating DB session for MCQ: {e}")
        
        self.save_to_db()
        
        return {
            'success': True,
            'is_correct': is_correct,
            'correct_index': question['correct_index'],
            'stats': self.stats
        }

    def update_answer_srs(self, index, srs_data):
        """Updates a specific answer with SRS metadata and persists to DB."""
        key = str(index)
        if key in self.answers:
            self.answers[key].update(srs_data)
            self.save_to_db()
            return True
        return False

    def next_item(self):
        """Advances the index if possible."""
        if self.currentIndex < len(self.questions) - 1:
            self.currentIndex += 1
            self.save_to_db()
            return True
        return False

    def start_next_cycle(self):
        """
        Reshuffles the current questions and starts a new cycle.
        Preserves the question pool but changes the order.
        """
        if self.questions:
            # Fisher-Yates shuffle (random.shuffle is in-place)
            random.shuffle(self.questions)
            self.currentIndex = 0
            self.save_to_db()
            return True
        return False

    def clear_session(self):
        """Clears the session data from the database."""
        from mindstack_app.models import UserContainerState, db
        from mindstack_app.utils.db_session import safe_commit
        
        try:
            ucs = UserContainerState.query.filter_by(user_id=self.user_id, container_id=self.set_id).first()
            if ucs and ucs.settings and 'mcq_session_data' in ucs.settings:
                new_settings = dict(ucs.settings)
                del new_settings['mcq_session_data']
                ucs.settings = new_settings
                
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(ucs, "settings")
                
                safe_commit(db.session)
        except Exception as e:
            print(f"Error clearing MCQ session: {e}")

    @staticmethod
    def static_clear_session(user_id, set_id):
        """
        Statically clears session data. 
        Useful when load_from_db fails but we still want to clean up.
        """
        from mindstack_app.models import UserContainerState, db
        from mindstack_app.utils.db_session import safe_commit
        
        try:
            ucs = UserContainerState.query.filter_by(user_id=user_id, container_id=set_id).first()
            if ucs and ucs.settings and 'mcq_session_data' in ucs.settings:
                new_settings = dict(ucs.settings)
                del new_settings['mcq_session_data']
                ucs.settings = new_settings
                
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(ucs, "settings")
                
                safe_commit(db.session)
                return True
        except Exception as e:
            print(f"Error static clearing MCQ session: {e}")
        return False
