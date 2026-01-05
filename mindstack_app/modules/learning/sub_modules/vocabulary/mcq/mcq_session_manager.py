# File: vocabulary/mcq/mcq_session_manager.py
# MCQ Session Management - Handles state persistence for MCQ learning mode.

import json
import random
from flask import session, current_app
from .logic import get_mcq_eligible_items, generate_mcq_question

class MCQSessionManager:
    """
    Manages the state of an MCQ (Multiple Choice Quiz) session.
    Persists data in the Database (UserContainerState.settings).
    """
    
    def __init__(self, user_id, set_id, params=None, questions=None, currentIndex=0, stats=None, answers=None):
        self.user_id = user_id
        self.set_id = set_id
        self.params = params or {}
        self.questions = questions or []
        self.currentIndex = currentIndex
        # stats includes 'correct', 'wrong', and now 'points'
        self.stats = stats or {'correct': 0, 'wrong': 0, 'points': 0}
        self.answers = answers or {} # Map: currentIndex (str) -> {'user_answer_index': int, ...}

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'set_id': self.set_id,
            'params': self.params,
            'questions': self.questions,
            'currentIndex': self.currentIndex,
            'stats': self.stats,
            'answers': self.answers
        }

    @classmethod
    def from_dict(cls, data):
        stats = data.get('stats') or {'correct': 0, 'wrong': 0, 'points': 0}
        if 'points' not in stats:
            stats['points'] = 0
            
        return cls(
            user_id=data.get('user_id'),
            set_id=data.get('set_id'),
            params=data.get('params'),
            questions=data.get('questions'),
            currentIndex=data.get('currentIndex', 0),
            stats=stats,
            answers=data.get('answers')
        )

    @classmethod
    def load_from_db(cls, user_id, set_id):
        """Loads session state from the database (UserContainerState)."""
        from mindstack_app.models import UserContainerState
        ucs = UserContainerState.query.filter_by(user_id=user_id, container_id=set_id).first()
        if ucs and ucs.settings and 'mcq_session_data' in ucs.settings:
            return cls.from_dict(ucs.settings['mcq_session_data'])
        return None

    def save_to_db(self):
        """Saves current state to the database (UserContainerState)."""
        from mindstack_app.models import UserContainerState, db
        from mindstack_app.utils.db_session import safe_commit
        import datetime

        def log_mcq(msg):
            with open('mcq_debug.log', 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.datetime.now()}] {msg}\n")

        try:
            ucs = UserContainerState.query.filter_by(user_id=self.user_id, container_id=self.set_id).first()
            if not ucs:
                ucs = UserContainerState(user_id=self.user_id, container_id=self.set_id, settings={})
                db.session.add(ucs)
            
            # Use current settings if they exist
            new_settings = dict(ucs.settings or {})
            new_settings['mcq_session_data'] = self.to_dict()
            
            ucs.settings = new_settings
            
            # Trigger SQLAlchemy change detection for JSON
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(ucs, "settings")
            
            safe_commit(db.session)
            log_mcq(f"DB SAVE success for set_id={self.set_id}, questions={len(self.questions)}")
        except Exception as e:
            log_mcq(f"DB SAVE ERROR: {str(e)}")
            import traceback
            log_mcq(traceback.format_exc())

    def initialize_session(self, count, mode, choices, custom_pairs):
        """Generates new questions and sets up the session."""
        self.params = {
            'count': count,
            'mode': mode,
            'choices': choices,
            'custom_pairs': custom_pairs
        }
        
        items = get_mcq_eligible_items(self.set_id)
        if len(items) < 2:
            return False, "Cần ít nhất 2 thẻ để chơi trắc nghiệm"
            
        random.shuffle(items)
        
        # If count <= 0, use all items (Unlimited mode)
        if count <= 0:
            selected_items = items
        else:
            selected_items = items[:min(count, len(items))]
        
        questions = []
        for item in selected_items:
            question = generate_mcq_question(
                item, items, 
                num_choices=choices, 
                mode=mode,
                custom_pairs=custom_pairs
            )
            questions.append(question)
            
        self.questions = questions
        self.currentIndex = 0
        self.stats = {'correct': 0, 'wrong': 0, 'points': 0}
        self.answers = {}
        
        self.save_to_db()
        return True, "Session initialized"

    def get_session_data(self):
        return {
            'success': True,
            'questions': self.questions,
            'currentIndex': self.currentIndex,
            'stats': self.stats,
            'answers': self.answers,
            'total': len(self.questions)
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
        
        self.save_to_db()
        
        return {
            'success': True,
            'is_correct': is_correct,
            'correct_index': question['correct_index'],
            'stats': self.stats
        }

    def next_item(self):
        """Advances the index if possible."""
        if self.currentIndex < len(self.questions) - 1:
            self.currentIndex += 1
            self.save_to_db()
            return True
        return False
