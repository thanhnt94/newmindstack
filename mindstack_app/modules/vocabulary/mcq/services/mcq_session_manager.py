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
        params = data.get('params') or {}
        
        if questions:
            # Trigger if missing OR if they look relative
            first_q = questions[0]
            q_audio_url = first_q.get('question_audio')
            needs_fix = not q_audio_url or not str(q_audio_url).startswith(('/', 'http://', 'https://'))
            
            if needs_fix:
                try:
                    from ..services.mcq_service import MCQService
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
                                content = MCQService.ensure_audio_urls(item, container, q_key=q_key, a_key=a_key)
                                
                                # Dynamic Audio Mapping
                                active_q_key = q.get('question_key') or q_key
                                active_a_key = q.get('answer_key') or a_key
                                
                                q['question_audio'] = content.get(f"{active_q_key}_audio") or content.get('front_audio') or content.get('front_audio_url')
                                q['answer_audio'] = content.get(f"{active_a_key}_audio") or content.get('front_audio') or content.get('front_audio_url')
                                
                                # Keep reference keys
                                q['front_audio'] = content.get('front_audio') or content.get('front_audio_url')
                                q['back_audio'] = content.get('back_audio') or content.get('back_audio_url')
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

    def initialize_session(self, count, mode, choices, custom_pairs, study_mode='review'):
        """Generates raw items and sets up the session (Lazy Generation)."""
        import time
        start_time = time.time()
        
        from ..services.mcq_service import MCQService
        self.params = {
            'count': count,
            'mode': mode,
            'choices': choices if choices is not None else 0,
            'custom_pairs': custom_pairs,
            'study_mode': study_mode
        }
        
        # [LAZY] Get raw items instead of generating full questions
        raw_items = MCQService.get_raw_session_items(
            self.set_id, 
            config=self.params,
            user_id=self.user_id
        )
        
        if not raw_items:
            return False, "Không tìm thấy đủ từ vựng đã học để tạo trắc nghiệm"
            
        self.questions = raw_items
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
                total_items=len(self.questions),
                extra_data={'mode': study_mode}
            )
            if db_session:
                self.db_session_id = db_session.session_id
        except Exception as e:
            print(f"Error creating DB session for checking: {e}")

        self.save_to_db()
        
        duration = time.time() - start_time
        current_app.logger.info(f"[VOCAB_MCQ] [LAZY] Session initialized in {duration:.4f}s for {len(self.questions)} items.")
        
        return True, "Session initialized"

    def ensure_question_generated(self, index: int) -> bool:
        """
        Just-In-Time Generation: Ensures the question at the given index 
        has full MCQ payload (choices, correct_index, etc.)
        """
        if index < 0 or index >= len(self.questions):
            return False
            
        question = self.questions[index]
        
        # Check if already generated (contains choices)
        if 'choices' in question and 'correct_index' in question:
            return True
            
        # Not generated yet - Generate it now
        try:
            from ..services.mcq_service import MCQService
            from ..engine.mcq_engine import MCQEngine
            from mindstack_app.models import LearningContainer
            
            # 1. Prepare config
            container = LearningContainer.query.get(self.set_id)
            mcq_settings = (container.settings or {}).get('mcq', {}) if container else {}
            
            merged_config = {
                'mode': self.params.get('mode') or mcq_settings.get('mode', 'front_back'),
                'num_choices': self.params.get('choices') or mcq_settings.get('choices', 4),
                'question_key': self.params.get('question_key') or mcq_settings.get('question_key'),
                'answer_key': self.params.get('answer_key') or mcq_settings.get('answer_key'),
                'custom_pairs': self.params.get('custom_pairs') or mcq_settings.get('pairs'),
                'audio_folder': container.media_audio_folder if container else None,
                'image_folder': container.media_image_folder if container else None,
            }

            # 2. Get distractors pool (Lazy: Fetch only when needed or use a cached pool)
            all_distractors = MCQService.get_all_items_for_distractors(self.set_id)
            
            # 3. Ensure audio URLs for the specific item
            updated_content = MCQService.ensure_audio_urls(
                question, 
                container, 
                q_key=merged_config['question_key'], 
                a_key=merged_config['answer_key']
            )
            question['content'] = updated_content
            
            # 4. Generate the specific MCQ question
            generated = MCQEngine.generate_question(question, all_distractors, merged_config)
            
            # 5. Update the question in the list (preserve existing SRS data)
            srs_data = question.get('srs')
            self.questions[index] = generated
            if srs_data:
                self.questions[index]['srs'] = srs_data
                
            # [CRITICAL] Save immediately to ensure correct_index is persisted for check_answer
            self.save_to_db()
            return True
            
        except Exception as e:
            current_app.logger.error(f"[VOCAB_MCQ] [LAZY] Failed to generate question at index {index}: {e}")
            return False

    def get_session_data(self):
        # Ensure current question is generated
        self.ensure_question_generated(self.currentIndex)
        
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
        from mindstack_app.modules.scoring.interface import ScoringInterface
        from ..engine.mcq_engine import MCQEngine
        
        if self.currentIndex >= len(self.questions):
            return {'success': False, 'message': 'Index out of bounds'}
            
        # Ensure generated (Safety check)
        self.ensure_question_generated(self.currentIndex)
            
        question = self.questions[self.currentIndex]
        
        # Use simplified engine check (Pure logic)
        result = MCQEngine.check_answer(question['correct_index'], user_answer_index)
        is_correct = result['is_correct']
        
        # Delegate scoring to Scoring Module
        # We fetch the standard bonus value through the interface
        point_value = 0
        if is_correct:
            self.stats['correct'] += 1
            point_value = ScoringInterface.get_score_value('VOCAB_MCQ_CORRECT_BONUS')
            self.stats['points'] += point_value
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
                item_id = question.get('item_id') 
                
                SessionInterface.update_progress(
                    session_id=self.db_session_id,
                    item_id=item_id,
                    result_type='correct' if is_correct else 'incorrect',
                    points=point_value if is_correct else 0
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
            'stats': self.stats,
            'score_change': point_value
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
            # [LAZY] Prefetch next question for smoothness
            self.ensure_question_generated(self.currentIndex)
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
