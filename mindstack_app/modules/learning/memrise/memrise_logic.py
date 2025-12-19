# File: mindstack_app/modules/learning/memrise/memrise_logic.py
# Phiên bản: 2.0
# Mục đích: Logic xử lý game Memrise với SRS (Spaced Repetition System)

import random
import datetime
from typing import Optional
from sqlalchemy import func

from mindstack_app.db_instance import db
from mindstack_app.models import LearningContainer, LearningItem, MemriseProgress
from mindstack_app.models.memrise import MEMORY_INTERVALS, RELEARNING_INTERVAL


# ==============================================================================
# I. CONSTANTS
# ==============================================================================

MIN_CARDS_FOR_MEMRISE = 4  # Số thẻ tối thiểu cần có dữ liệu Memrise
SESSION_REPS_TARGET = 2    # Mỗi từ cần lặp lại ít nhất 2 lần trong session


# ==============================================================================
# II. HELPER FUNCTIONS
# ==============================================================================

def has_memrise_data(item: LearningItem) -> bool:
    """Kiểm tra xem một flashcard có đủ dữ liệu Memrise không."""
    if not item or not item.content:
        return False
    
    content = item.content
    memrise_prompt = content.get('memrise_prompt', '').strip()
    memrise_answers = content.get('memrise_answers', '').strip()
    
    return bool(memrise_prompt and memrise_answers)


def get_mcq_answer(memrise_answers: str) -> str:
    """
    Lấy đáp án MCQ từ chuỗi memrise_answers.
    Đáp án MCQ là đáp án đầu tiên (trước dấu phẩy đầu tiên).
    """
    if not memrise_answers:
        return ''
    
    answers = [a.strip() for a in memrise_answers.split(',') if a.strip()]
    return answers[0] if answers else ''


def get_all_typing_answers(memrise_answers: str) -> list[str]:
    """
    Lấy tất cả đáp án cho Typing từ chuỗi memrise_answers.
    """
    if not memrise_answers:
        return []
    
    return [a.strip().lower() for a in memrise_answers.split(',') if a.strip()]


# ==============================================================================
# III. CONTAINER QUERIES
# ==============================================================================

def get_memrise_eligible_containers(user_id: int) -> list[dict]:
    """
    Lấy danh sách các bộ flashcard đủ điều kiện để chơi Memrise.
    Điều kiện: có ít nhất MIN_CARDS_FOR_MEMRISE thẻ có đầy đủ dữ liệu Memrise.
    """
    # Lấy tất cả flashcard containers mà user có quyền truy cập
    containers = LearningContainer.query.filter(
        LearningContainer.container_type == 'FLASHCARD_SET',
        db.or_(
            LearningContainer.is_public == True,
            LearningContainer.creator_user_id == user_id
        )
    ).all()
    
    eligible = []
    
    for container in containers:
        # Đếm số thẻ có dữ liệu Memrise
        memrise_count = 0
        for item in container.items:
            if has_memrise_data(item):
                memrise_count += 1
        
        if memrise_count >= MIN_CARDS_FOR_MEMRISE:
            eligible.append({
                'container_id': container.container_id,
                'title': container.title,
                'description': container.description or '',
                'cover_image': container.cover_image,
                'memrise_card_count': memrise_count,
                'total_card_count': len(container.items),
                'creator_username': container.creator.username if container.creator else 'Unknown'
            })
    
    return eligible


def get_container_memrise_items(container_id: int) -> list[LearningItem]:
    """
    Lấy tất cả các thẻ có dữ liệu Memrise từ một container.
    """
    container = LearningContainer.query.get(container_id)
    if not container:
        return []
    
    return [item for item in container.items if has_memrise_data(item)]


# ==============================================================================
# IV. QUESTION GENERATION
# ==============================================================================

def generate_mcq_question(item: LearningItem, all_items: list[LearningItem]) -> Optional[dict]:
    """
    Tạo câu hỏi MCQ từ một flashcard.
    
    Args:
        item: Flashcard để tạo câu hỏi
        all_items: Tất cả các flashcard trong set (để lấy distractors)
    
    Returns:
        dict với keys: question, options, correct_answer, item_id
    """
    if not has_memrise_data(item):
        return None
    
    content = item.content
    question = content.get('memrise_prompt', '')
    correct_answer = get_mcq_answer(content.get('memrise_answers', ''))
    
    if not question or not correct_answer:
        return None
    
    # Lấy distractors từ các thẻ khác (không trùng đáp án đúng)
    distractors = []
    correct_answer_lower = correct_answer.lower()
    
    for other_item in all_items:
        if other_item.item_id == item.item_id:
            continue
        
        if not has_memrise_data(other_item):
            continue
        
        other_answer = get_mcq_answer(other_item.content.get('memrise_answers', ''))
        
        # Tránh trùng đáp án (so sánh lowercase)
        if other_answer and other_answer.lower() != correct_answer_lower:
            if other_answer not in distractors:
                distractors.append(other_answer)
        
        if len(distractors) >= 3:
            break
    
    # Cần ít nhất 3 distractors để tạo MCQ 4 options
    if len(distractors) < 3:
        return None
    
    # Tạo options và shuffle
    options = [correct_answer] + distractors[:3]
    random.shuffle(options)
    
    return {
        'item_id': item.item_id,
        'question_type': 'mcq',
        'question': question,
        'options': options,
        'correct_answer': correct_answer
    }


def generate_typing_question(item: LearningItem) -> Optional[dict]:
    """
    Tạo câu hỏi Typing từ một flashcard.
    
    Args:
        item: Flashcard để tạo câu hỏi
    
    Returns:
        dict với keys: question, accepted_answers, item_id
    """
    if not has_memrise_data(item):
        return None
    
    content = item.content
    question = content.get('memrise_prompt', '')
    answers = get_all_typing_answers(content.get('memrise_answers', ''))
    
    if not question or not answers:
        return None
    
    return {
        'item_id': item.item_id,
        'question_type': 'typing',
        'question': question,
        'accepted_answers': answers,
        'hint': answers[0][0] if answers else ''  # First letter hint
    }


# ==============================================================================
# V. ANSWER CHECKING
# ==============================================================================

def check_mcq_answer(user_answer: str, correct_answer: str) -> bool:
    """Kiểm tra đáp án MCQ."""
    return user_answer.strip().lower() == correct_answer.strip().lower()


def check_typing_answer(user_input: str, memrise_answers: str) -> dict:
    """
    Kiểm tra đáp án Typing.
    
    Args:
        user_input: Đáp án user nhập
        memrise_answers: Chuỗi các đáp án chấp nhận (phân tách bằng dấu phẩy)
    
    Returns:
        dict với keys: is_correct, correct_answer
    """
    accepted = get_all_typing_answers(memrise_answers)
    user_normalized = user_input.strip().lower()
    
    is_correct = user_normalized in accepted
    
    return {
        'is_correct': is_correct,
        'correct_answer': accepted[0] if accepted else '',
        'user_answer': user_input.strip()
    }


# ==============================================================================
# VI. SESSION HELPERS
# ==============================================================================

def get_session_questions(container_id: int, question_count: int = 10, 
                          mode: str = 'mixed') -> list[dict]:
    """
    Tạo danh sách câu hỏi cho một session Memrise.
    
    Args:
        container_id: ID của container
        question_count: Số câu hỏi muốn tạo
        mode: 'mcq', 'typing', hoặc 'mixed'
    
    Returns:
        Danh sách các câu hỏi
    """
    items = get_container_memrise_items(container_id)
    
    if len(items) < MIN_CARDS_FOR_MEMRISE:
        return []
    
    # Shuffle items
    random.shuffle(items)
    
    questions = []
    items_pool = items.copy()
    
    for i in range(min(question_count, len(items))):
        item = items_pool[i % len(items_pool)]
        
        # Chọn loại câu hỏi
        if mode == 'mcq':
            q = generate_mcq_question(item, items)
        elif mode == 'typing':
            q = generate_typing_question(item)
        else:  # mixed
            if random.random() < 0.6:  # 60% MCQ, 40% Typing
                q = generate_mcq_question(item, items)
            else:
                q = generate_typing_question(item)
        
        if q:
            questions.append(q)
    
    return questions


# ==============================================================================
# VII. SRS FUNCTIONS
# ==============================================================================

def get_or_create_memrise_progress(user_id: int, item_id: int) -> MemriseProgress:
    """
    Lấy hoặc tạo mới MemriseProgress cho một user-item pair.
    """
    progress = MemriseProgress.query.filter_by(
        user_id=user_id, 
        item_id=item_id
    ).first()
    
    if not progress:
        progress = MemriseProgress(
            user_id=user_id,
            item_id=item_id,
            memory_level=0,
            interval=0,
            times_correct=0,
            times_incorrect=0,
            current_streak=0,
            session_reps=0
        )
        db.session.add(progress)
        db.session.flush()  # Get ID without committing
    
    return progress


def update_memrise_progress(user_id: int, item_id: int, is_correct: bool) -> dict:
    """
    Cập nhật tiến trình SRS sau khi user trả lời.
    
    Returns:
        dict với thông tin cập nhật: memory_level, level_name, next_due, etc.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    progress = get_or_create_memrise_progress(user_id, item_id)
    
    old_level = progress.memory_level
    
    if is_correct:
        # Tăng level và streak
        progress.times_correct += 1
        progress.current_streak += 1
        
        # Tăng memory level (max 7)
        if progress.memory_level < 7:
            progress.memory_level += 1
        
        # Tính interval dựa trên level mới
        new_interval = MEMORY_INTERVALS.get(progress.memory_level, 43200)
        progress.interval = new_interval
        progress.due_time = now + datetime.timedelta(minutes=new_interval)
        
    else:
        # Reset về level 1 và streak = 0
        progress.times_incorrect += 1
        progress.current_streak = 0
        progress.memory_level = 1  # Reset to level 1, not 0
        progress.interval = RELEARNING_INTERVAL
        progress.due_time = now + datetime.timedelta(minutes=RELEARNING_INTERVAL)
    
    progress.last_reviewed = now
    progress.session_reps += 1
    
    db.session.commit()
    
    return {
        'item_id': item_id,
        'old_level': old_level,
        'memory_level': progress.memory_level,
        'level_name': progress.level_name,
        'level_percentage': progress.level_percentage,
        'is_planted': progress.memory_level >= 7,
        'interval': progress.interval,
        'next_due': progress.due_time.isoformat() if progress.due_time else None,
        'current_streak': progress.current_streak,
        'times_correct': progress.times_correct,
        'times_incorrect': progress.times_incorrect,
        'level_changed': progress.memory_level != old_level,
        'level_up': progress.memory_level > old_level,
    }


def reset_session_reps(user_id: int, container_id: int):
    """
    Reset session_reps cho tất cả items trong container khi bắt đầu session mới.
    """
    items = get_container_memrise_items(container_id)
    item_ids = [item.item_id for item in items]
    
    MemriseProgress.query.filter(
        MemriseProgress.user_id == user_id,
        MemriseProgress.item_id.in_(item_ids)
    ).update({MemriseProgress.session_reps: 0}, synchronize_session=False)
    
    db.session.commit()


def get_smart_questions(user_id: int, container_id: int, question_count: int = 10,
                        mode: str = 'mixed') -> list[dict]:
    """
    Tạo danh sách câu hỏi với SRS-based selection.
    
    Priority:
    1. Items cần lặp lại trong session (session_reps < SESSION_REPS_TARGET)
    2. Items đến hạn ôn tập (due_time <= now)
    3. Items mới chưa học (memory_level = 0)
    4. Items đã học nhưng chưa thuộc (memory_level 1-6)
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    all_items = get_container_memrise_items(container_id)
    
    if len(all_items) < MIN_CARDS_FOR_MEMRISE:
        return []
    
    # Get or create progress for all items
    item_ids = [item.item_id for item in all_items]
    existing_progress = {
        p.item_id: p for p in MemriseProgress.query.filter(
            MemriseProgress.user_id == user_id,
            MemriseProgress.item_id.in_(item_ids)
        ).all()
    }
    
    # Categorize items
    due_items = []      # Items that are due for review
    new_items = []      # Items never learned (level 0)
    learning_items = [] # Items in learning (level 1-6)
    session_repeat = [] # Items that need more reps in this session
    
    for item in all_items:
        progress = existing_progress.get(item.item_id)
        
        if not progress:
            # New item - never seen
            new_items.append((item, None))
        elif progress.memory_level == 0:
            # Level 0 but has progress record - treat as new
            new_items.append((item, progress))
        elif progress.session_reps < SESSION_REPS_TARGET and progress.session_reps > 0:
            # Needs more repetition in this session
            session_repeat.append((item, progress))
        elif progress.due_time:
            # Normalize due_time to be timezone-aware for comparison
            due_time = progress.due_time
            if due_time.tzinfo is None:
                due_time = due_time.replace(tzinfo=datetime.timezone.utc)
            if due_time <= now:
                # Due for review
                due_items.append((item, progress))
        elif progress.memory_level < 7:
            # Learning but not due yet
            learning_items.append((item, progress))
    
    # Build question list with priority
    selected_items = []
    
    # 1. First, items that need session repetition
    random.shuffle(session_repeat)
    selected_items.extend(session_repeat[:3])
    
    # 2. Due items - prioritize by how overdue they are
    due_items.sort(key=lambda x: x[1].due_time if x[1] and x[1].due_time else now)
    selected_items.extend(due_items[:4])
    
    # 3. New items to introduce
    random.shuffle(new_items)
    selected_items.extend(new_items[:3])
    
    # 4. Fill remaining with learning items
    random.shuffle(learning_items)
    remaining = question_count - len(selected_items)
    if remaining > 0:
        selected_items.extend(learning_items[:remaining])
    
    # Shuffle the final list but keep some structure
    random.shuffle(selected_items)
    selected_items = selected_items[:question_count]
    
    # Generate questions
    questions = []
    all_items_for_distractors = all_items  # For MCQ distractors
    
    for item, progress in selected_items:
        # Determine question type
        if mode == 'mcq':
            q = generate_mcq_question(item, all_items_for_distractors)
        elif mode == 'typing':
            q = generate_typing_question(item)
        else:  # mixed
            # Prefer MCQ for new items, typing for learning items
            if progress is None or (progress and progress.memory_level <= 2):
                # New or early learning - use MCQ (easier)
                q = generate_mcq_question(item, all_items_for_distractors)
            elif progress and progress.memory_level >= 5:
                # Advanced learning - use typing (harder)
                q = generate_typing_question(item)
            else:
                # Middle levels - random
                if random.random() < 0.5:
                    q = generate_mcq_question(item, all_items_for_distractors)
                else:
                    q = generate_typing_question(item)
        
        if q:
            # Add progress info to question
            q['memory_level'] = progress.memory_level if progress else 0
            q['level_name'] = progress.level_name if progress else 'Chưa học'
            questions.append(q)
    
    return questions


def get_container_srs_stats(user_id: int, container_id: int) -> dict:
    """
    Lấy thống kê SRS cho một container.
    """
    items = get_container_memrise_items(container_id)
    item_ids = [item.item_id for item in items]
    
    progress_list = MemriseProgress.query.filter(
        MemriseProgress.user_id == user_id,
        MemriseProgress.item_id.in_(item_ids)
    ).all()
    
    progress_by_id = {p.item_id: p for p in progress_list}
    
    now = datetime.datetime.now(datetime.timezone.utc)
    
    stats = {
        'total_items': len(items),
        'new': 0,           # Level 0
        'learning': 0,      # Level 1-6
        'planted': 0,       # Level 7
        'due_count': 0,     # Due for review
        'level_distribution': {i: 0 for i in range(8)},
    }
    
    for item in items:
        progress = progress_by_id.get(item.item_id)
        
        if not progress or progress.memory_level == 0:
            stats['new'] += 1
            stats['level_distribution'][0] += 1
        elif progress.memory_level >= 7:
            stats['planted'] += 1
            stats['level_distribution'][7] += 1
        else:
            stats['learning'] += 1
            stats['level_distribution'][progress.memory_level] += 1
        
        if progress and progress.due_time:
            due_time = progress.due_time
            if due_time.tzinfo is None:
                due_time = due_time.replace(tzinfo=datetime.timezone.utc)
            if due_time <= now:
                stats['due_count'] += 1
    
    return stats

