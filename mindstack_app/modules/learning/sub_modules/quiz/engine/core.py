# Quiz Engine Module
# Core logic for quiz/MCQ learning.
# Handles question generation, answer verification, and SRS updates.

import random
from mindstack_app.models import LearningItem, db
from mindstack_app.modules.learning.services.fsrs_service import FsrsService
from mindstack_app.modules.gamification.services.scoring_service import ScoreService
from mindstack_app.utils.db_session import safe_commit


class QuizEngine:
    """
    Centralized engine for Quiz (MCQ) learning logic.
    Handles question generation and answer verification.
    """

    @staticmethod
    def get_eligible_items(container_id):
        """Get all items eligible for MCQ from a container."""
        items = LearningItem.query.filter_by(
            container_id=container_id,
            item_type='FLASHCARD'
        ).all()
        
        eligible = []
        for item in items:
            content = item.content or {}
            # Check if has memrise data OR flashcard data
            if content.get('memrise_prompt') and content.get('memrise_answers'):
                eligible.append({
                    'item_id': item.item_id,
                    'prompt': content.get('memrise_prompt'),
                    'answers': content.get('memrise_answers', []),
                    'audio_url': content.get('memrise_audio_url'),
                    'content': content,
                })
            elif content.get('front') and content.get('back'):
                # Fallback to flashcard front/back
                eligible.append({
                    'item_id': item.item_id,
                    'prompt': content.get('front'),
                    'answers': [content.get('back')],
                    'audio_url': None,
                    'content': content,
                })
        
        return eligible

    @staticmethod
    def get_eligible_items_multi(container_ids):
        """Get all items eligible for MCQ from multiple containers."""
        if isinstance(container_ids, str) and container_ids == 'all':
            items = LearningItem.query.filter_by(item_type='FLASHCARD').all()
        else:
            items = LearningItem.query.filter(
                LearningItem.container_id.in_(container_ids),
                LearningItem.item_type == 'FLASHCARD'
            ).all()
        
        eligible = []
        for item in items:
            content = item.content or {}
            if content.get('memrise_prompt') and content.get('memrise_answers'):
                eligible.append({
                    'item_id': item.item_id,
                    'container_id': item.container_id,
                    'prompt': content.get('memrise_prompt'),
                    'answers': content.get('memrise_answers', []),
                    'audio_url': content.get('memrise_audio_url'),
                    'content': content,
                })
            elif content.get('front') and content.get('back'):
                eligible.append({
                    'item_id': item.item_id,
                    'container_id': item.container_id,
                    'prompt': content.get('front'),
                    'answers': [content.get('back')],
                    'audio_url': None,
                    'content': content,
                })
        
        return eligible

    @staticmethod
    def get_available_content_keys(container_id):
        """
        Scan items in the container to find available keys in the content JSON.
        Returns a list of keys that are present in at least one item, excluding system keys.
        """
        items = LearningItem.query.filter_by(
            container_id=container_id,
            item_type='FLASHCARD'
        ).all()
        
        keys = set()
        system_keys = {'audio_url', 'image_url', 'video_url', 'memrise_audio_url', 'front_audio_url', 'back_audio_url', 'front_img', 'back_img'}
        
        for item in items:
            content = item.content or {}
            for k in content.keys():
                if k not in system_keys and isinstance(content[k], (str, int, float)):
                     keys.add(k)
        
        return sorted(list(keys))

    @classmethod
    def generate_question(cls, item, all_items, num_choices=4, mode='front_back', question_key=None, answer_key=None, custom_pairs=None):
        """
        Generate an MCQ question with distractors.
        mode: 'front_back', 'back_front', 'mixed', 'custom'
        """
        
        # Determine direction for this question
        current_mode = mode
        if mode == 'mixed':
            current_mode = random.choice(['front_back', 'back_front'])
        
        # Define primary prompt and answer based on mode
        question_prompt = ''
        correct_answer = ''
        
        # Handle Custom Pairs (Random Selection)
        if current_mode == 'custom' and custom_pairs:
            pair = random.choice(custom_pairs)
            question_key = pair.get('q')
            answer_key = pair.get('a')
        
        # Standard modes mapping attempt
        if 'prompt' in item and 'answers' in item:
            question_prompt = item['prompt']
            correct_answer = item['answers'][0] if item['answers'] else ''
        
        if current_mode == 'back_front':
            question_prompt = item['answers'][0] if item['answers'] else '???'
            correct_answer = item['prompt']
        
        elif current_mode == 'custom':
            content = item.get('content', {})
            question_prompt = content.get(question_key, '???')
            raw_answer = content.get(answer_key, '')
            if isinstance(raw_answer, list):
                 correct_answer = raw_answer[0] if raw_answer else ''
            else:
                 correct_answer = str(raw_answer)

        # Get distractors
        distractors = []
        distractor_item_ids = []
        other_items = [i for i in all_items if i['item_id'] != item['item_id']]
        random.shuffle(other_items)
        
        for other in other_items:
            distractor_val = ''
            if current_mode == 'front_back':
                 distractor_val = other['answers'][0] if other['answers'] else ''
            elif current_mode == 'back_front':
                 distractor_val = other['prompt']
            elif current_mode == 'custom':
                 content = other.get('content', {})
                 raw_dist = content.get(answer_key, '')
                 if isinstance(raw_dist, list):
                     distractor_val = raw_dist[0] if raw_dist else ''
                 else:
                     distractor_val = str(raw_dist)
                
            if distractor_val and distractor_val != correct_answer and distractor_val not in distractors:
                distractors.append(distractor_val)
                distractor_item_ids.append(other['item_id'])
                if len(distractors) >= num_choices - 1:
                    break
        
        # Build choices
        choices = [correct_answer] + distractors
        choice_item_ids = [item['item_id']] + distractor_item_ids
        
        # Shuffle together
        combined = list(zip(choices, choice_item_ids))
        random.shuffle(combined)
        choices, choice_item_ids = zip(*combined) if combined else ([], [])
        
        return {
            'item_id': item['item_id'],
            'prompt': question_prompt,
            'audio_url': item.get('audio_url') if current_mode == 'front_back' else None, 
            'choices': list(choices),
            'choice_item_ids': list(choice_item_ids),
            'answer': correct_answer,
            'correct_answer': correct_answer,
            'correct_index': choices.index(correct_answer) if correct_answer in choices else 0,
            'answer_key': answer_key,
            'question_key': question_key
        }

    @staticmethod
    def check_answer(item_id, user_answer, user_id=None, answer_key=None, duration_ms=0, user_answer_key=None,
                     session_id=None, container_id=None, mode=None, streak_position=0):
        """
        Check if user's MCQ answer is correct.
        If user_id is provided, updates SRS progress and awards points.
        
        Args:
            item_id: ID of the learning item
            user_answer: The answer text user submitted (could be value or key)
            user_id: Optional user ID for SRS/scoring updates
            answer_key: The content key to use for finding correct answer
            duration_ms: Response time in milliseconds
            user_answer_key: The option key (A/B/C/D) that user selected - for storing in ReviewLog
            session_id: Learning session ID for context
            container_id: Container ID for faster queries
            mode: Learning mode ('new', 'review', 'difficult', etc.)
            streak_position: Position in correct answer streak
        """
        item = LearningItem.query.get(item_id)
        if not item:
            return {'correct': False, 'message': 'Item not found'}
        
        content = item.content or {}
        correct_answers = []
        
        if answer_key:
            val = content.get(answer_key)
            if isinstance(val, list):
                correct_answers = [str(v) for v in val]
            elif val is not None:
                 correct_answers = [str(val)]
                 
        if not correct_answers:
            # Try various common keys
            potential_keys = ['correct_answer', 'answer', 'memrise_answers', 'back']
            for pk in potential_keys:
                pk_val = content.get(pk)
                if pk_val:
                    if isinstance(pk_val, list):
                        correct_answers = [str(v) for v in pk_val if v]
                    else:
                        correct_answers = [str(pk_val)]
                    if correct_answers:
                        break
        
        is_correct = False
        if correct_answers:
            is_correct = user_answer.strip().lower() in [a.strip().lower() for a in correct_answers if a]
        
        if user_id:
            # Determine quality: 4 (Good) if correct, 1 (Again) if incorrect
            quality = 4 if is_correct else 1
            
            # Fetch old progress for delta calculation
            from mindstack_app.models.learning_progress import LearningProgress
            old_progress = LearningProgress.query.filter_by(
                user_id=user_id, item_id=item_id, learning_mode='quiz'
            ).first()
            old_mastery = min((old_progress.fsrs_stability or 0)/21.0, 1.0) if old_progress else 0.0
            
            # Update SRS using FSRS Process Answer
            progress, srs_result = FsrsService.process_answer(
                user_id=user_id,
                item_id=item_id,
                quality=quality,
                mode='quiz',
                is_first_time=False,  # TODO: track first-time properly
                response_time_seconds=duration_ms / 1000.0 if duration_ms else None
            )
            
            # Use score from SrsResult
            score_change = getattr(srs_result, 'score_points', 0)
            
            ScoreService.award_points(
                user_id=user_id,
                amount=score_change,
                reason=f"Quiz Answer (Correct: {is_correct})",
                item_id=item_id,
                item_type='QUIZ_MCQ'
            )
            
            # Log to ReviewLog table with user_answer and response_time
            from mindstack_app.models import ReviewLog
            import datetime
            now = datetime.datetime.now(datetime.timezone.utc)
            # Use user_answer_key (A/B/C/D) if provided, else use user_answer
            stored_answer = user_answer_key if user_answer_key else user_answer
            log_entry = ReviewLog(
                user_id=user_id,
                item_id=item_id,
                timestamp=now,
                rating=1 if is_correct else 0,  # 1=correct, 0=incorrect for quiz
                review_type='quiz',
                user_answer=stored_answer,
                is_correct=is_correct,
                score_change=score_change,
                duration_ms=duration_ms,
                mastery_snapshot=getattr(srs_result, 'mastery', None),
                # Session context fields
                session_id=session_id,
                container_id=container_id or item.container_id,
                mode=mode,
                streak_position=streak_position
            )
            db.session.add(log_entry)
            
            safe_commit(db.session)

            new_mastery_pct = round((srs_result.mastery or 0.0) * 100, 1)
            old_mastery_pct = round((old_mastery or 0.0) * 100, 1)
            mastery_delta = round(new_mastery_pct - old_mastery_pct, 1)

            return {
                'correct': is_correct,
                'correct_answer': correct_answers[0] if correct_answers else '',
                'score_change': score_change,
                'mastery_delta': mastery_delta,
                'new_mastery_pct': new_mastery_pct,
                'points_breakdown': getattr(srs_result, 'score_breakdown', {})
            }

        return {
            'correct': is_correct,
            'correct_answer': correct_answers[0] if correct_answers else '',
        }
