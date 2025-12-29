
import random
import datetime
from typing import Optional, List, Dict
from sqlalchemy import func

from mindstack_app.models import LearningContainer, LearningItem, db
from mindstack_app.models.learning_progress import LearningProgress
from mindstack_app.modules.learning.services.srs_service import SrsService

# --- HELPER: Data Strategy ---

def get_learning_content(item: LearningItem) -> dict:
    """
    Get content for LEARNING phase (Standard Flashcard).
    Uses 'front' (Term) and 'back' (Definition) + Audio.
    """
    c = item.content or {}
    return {
        'term': c.get('front', ''),
        'definition': c.get('back', ''),
        'audio': c.get('front_audio_url') or c.get('back_audio_url')
    }

def get_testing_content(item: LearningItem) -> dict:
    """
    Get content for TESTING phase (MCQ/Typing).
    PRIORITY: Memrise Fields > Standard Fields (Fallback).
    """
    c = item.content or {}
    
    # Try Memrise fields first
    question = c.get('memrise_prompt', '').strip()
    # Handle multiple answers usually stored as csv in 'memrise_answers'
    answers_str = c.get('memrise_answers', '').strip()
    answers = [a.strip() for a in answers_str.split(',') if a.strip()] if answers_str else []
    
    # Fallback to standard
    if not question:
        question = c.get('front', '') # Use Front as Question
    if not answers:
        answers = [c.get('back', '').strip()] # Back as Answer

    return {
        'question': question,
        'accepted_answers': answers,
        'primary_answer': answers[0] if answers else ''
    }

def get_distractors(target_item_id: int, container_id: int, count: int = 3) -> list:
    """Get distractors from other items in the same container."""
    # This query could be optimized
    items = LearningItem.query.filter(
        LearningItem.container_id == container_id,
        LearningItem.item_id != target_item_id
    ).order_by(func.random()).limit(count).all()
    
    distractors = []
    for item in items:
        content = get_testing_content(item)
        if content['primary_answer']:
            distractors.append(content['primary_answer'])
    return distractors

# --- LOGIC: Question Generation ---

def generate_question_payload(user_id: int, item: LearningItem, progress: LearningProgress = None):
    """
    Generate the question payload based on item state (New vs Review).
    """
    # 1. NEW ITEM -> LEARN CARD
    if not progress or progress.status == 'new' or progress.status is None:
        content = get_learning_content(item)
        return {
            'type': 'learn',
            'item_id': item.item_id,
            'term': content['term'],
            'definition': content['definition'],
            'audio': content['audio'],
            'instruction': "Học từ mới"
        }

    # 2. REVIEW ITEM -> TEST (MCQ/Typing/Audio)
    # Determine test type based on mastery level? 
    # For now simplify: Randomly pick MCQ or Typing.
    test_type = random.choice(['mcq', 'typing'])
    
    test_content = get_testing_content(item)
    if not test_content['question'] or not test_content['primary_answer']:
         # Fallback if data missing to learn card? or skip?
         return None

    quest = {
        'item_id': item.item_id,
        'question': test_content['question'],
        'srs_quality': 0 # Placeholder
    }
    
    # Add SRS Info for UI (Retention Rate)
    # Calculate retention
    if progress.last_reviewed and progress.interval:
         quest['retention_rate'] = SrsService.calculate_retention_rate(
             progress.last_reviewed, progress.interval
         )
    else:
         quest['retention_rate'] = 0

    if test_type == 'mcq':
        quest['type'] = 'mcq'
        distractors = get_distractors(item.item_id, item.container_id)
        options = distractors + [test_content['primary_answer']]
        random.shuffle(options)
        quest['options'] = options
    
    elif test_type == 'typing':
        quest['type'] = 'typing'
        # Hint: First letter
        ans = test_content['primary_answer']
        quest['hint'] = ans[0] if ans else ''
        
    return quest


def get_memrise_session_items(user_id: int, container_id: int, limit: int = 10):
    """
    Smart Selection for Memrise Session.
    Priority:
    1. Due Items (SRS).
    2. New Items (Limit per session to avoid overwhelm).
    3. Learning Items (Reinforcement).
    """
    all_items = LearningItem.query.filter_by(container_id=container_id).all()
    if not all_items: return []
    
    item_map = {i.item_id: i for i in all_items}
    item_ids = list(item_map.keys())
    
    progresses = LearningProgress.query.filter(
        LearningProgress.user_id == user_id,
        LearningProgress.item_id.in_(item_ids),
        LearningProgress.learning_mode == 'flashcard'
    ).all()
    
    prog_map = {p.item_id: p for p in progresses}
    
    now = datetime.datetime.now(datetime.timezone.utc)
    
    due = []
    new_items = []
    learning = []
    
    for item in all_items:
        p = prog_map.get(item.item_id)
        if not p or p.status == 'new':
            new_items.append(item)
        elif p.due_time and p.due_time.replace(tzinfo=datetime.timezone.utc) <= now:
            due.append(item)
        elif p.status == 'learning':
            learning.append(item)
            
    # Selection Strategy
    # 50% Due, 30% New, 20% Learning
    selected = []
    
    # 1. Due
    random.shuffle(due)
    selected.extend([(x, prog_map.get(x.item_id)) for x in due[:5]])
    
    # 2. New
    random.shuffle(new_items)
    selected.extend([(x, None) for x in new_items[:3]])
    
    # 3. Fill rest
    remain = limit - len(selected)
    if remain > 0:
        pool = learning + due[5:] + new_items[3:]
        random.shuffle(pool)
        for x in pool[:remain]:
            selected.append((x, prog_map.get(x.item_id)))
            
    return selected

def generate_session_questions(user_id: int, container_id: int, limit: int = 10):
    candidates = get_memrise_session_items(user_id, container_id, limit)
    questions = []
    for item, progress in candidates:
        q = generate_question_payload(user_id, item, progress)
        if q:
            questions.append(q)
    return questions

def process_answer(user_id: int, item_id: int, type: str, answer: str):
    """
    Check answer and update SRS.
    """
    item = LearningItem.query.get(item_id)
    if not item: return {'is_correct': False}
    
    if type == 'learn':
        # "Got it" acknowledgement
        # Force update to status 'learning' -> Quality 4 (Good start)
        SrsService.process_interaction(user_id, item_id, 'flashcard', {'quality': 4})
        return {'is_correct': True, 'message': 'Started learning'}
        
    # Test checking
    test_content = get_testing_content(item)
    accepted = [a.lower() for a in test_content['accepted_answers']]
    user_val = answer.strip().lower()
    
    is_correct = user_val in accepted
    
    # Update SRS
    mode = 'mcq' if type == 'mcq' else 'typing'
    srs_res = SrsService.process_interaction(
        user_id, item_id, mode, 
        {'is_correct': is_correct, 'accuracy': 1.0 if is_correct else 0.0}
    )
    
    return {
        'is_correct': is_correct,
        'correct_answer': test_content['primary_answer'],
        'srs': srs_res
    }

def get_course_overview_stats(user_id: int, container_id: int, page: int = 1, per_page: int = 20):
    """
    Get detailed Learning Stats for a Container (Memrise Course Overview).
    Returns:
    - total_progress: % of items learned (status != new/None).
    - items: Paginated list of items with:
        - term (front)
        - definition (back)
        - status (new/learning/reviewing/mastered)
        - retention_rate (0-100%)
    - pagination: {total, pages, current}
    """
    # 1. Base Query
    query = LearningItem.query.filter_by(container_id=container_id)
    total_items = query.count()
    
    if total_items == 0:
        return {'progress': 0, 'items': [], 'pagination': {'total': 0, 'pages': 0, 'page': page}}

    # 2. Get Progress for ALL items (to calc total %)
    all_items = query.all()
    item_ids = [i.item_id for i in all_items]
    
    progress_records = LearningProgress.query.filter(
        LearningProgress.user_id == user_id,
        LearningProgress.item_id.in_(item_ids),
        LearningProgress.learning_mode == 'flashcard'
    ).all()
    
    prog_map = {p.item_id: p for p in progress_records}
    
    learned_count = sum(1 for p in progress_records if p.status and p.status != 'new')
    progress_percent = int((learned_count / total_items) * 100)
    
    # 3. Pagination with Sorting (Retention Rate ASC - Worst First, New Last)
    # Sort: Non-new items by retention ASC, then new items last
    from sqlalchemy import case
    
    sorted_query = db.session.query(LearningItem, LearningProgress).outerjoin(
        LearningProgress, 
        (LearningProgress.item_id == LearningItem.item_id) & 
        (LearningProgress.user_id == user_id) &
        (LearningProgress.learning_mode == 'flashcard')
    ).filter(
        LearningItem.container_id == container_id
    ).order_by(
        # New items go last
        case(
            (LearningProgress.status == 'new', 1),
            (LearningProgress.status == None, 1),
            else_=0
        ).asc(),
        # For non-new items, sort by retention rate (calculated via interval)
        # Lower interval = needs review sooner = higher priority
        LearningProgress.interval.asc().nulls_last(),
        LearningItem.item_id.asc() # Fallback
    )
    
    pagination = sorted_query.paginate(page=page, per_page=per_page, error_out=False)
    
    items_data = []
    
    now = datetime.datetime.now(datetime.timezone.utc)
    
    for item, p in pagination.items:
        # p is LearningProgress object or None
        
        status = p.status if p else 'new'
        retention = 0
        if p and p.last_reviewed and p.interval:
            retention = SrsService.calculate_retention_rate(p.last_reviewed, p.interval)
        elif status == 'new':
            retention = 0 
        else:
            retention = 0
            
        content = item.content or {}
        
        items_data.append({
            'item_id': item.item_id,
            'term': content.get('front', 'Unknown'),
            'definition': content.get('back', 'Unknown'),
            'status': status,
            'retention_rate': retention,
            'mastery': int(p.mastery * 100) if p else 0,
            'is_due': (p.due_time.replace(tzinfo=datetime.timezone.utc) <= now) if (p and p.due_time) else False
        })
        
    return {
        'progress': progress_percent,
        'learned_count': learned_count,
        'total_count': total_items,
        'items': items_data,
        'pagination': {
            'total': pagination.total,
            'pages': pagination.pages,
            'current': page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    }

