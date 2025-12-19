# File: vocabulary/matching/logic.py
# Matching Learning Mode Logic

import random
from mindstack_app.models import LearningItem


def get_matching_items(container_id, count=6):
    """Get items for matching game.
    
    Args:
        container_id: The container to get items from
        count: Number of pairs to include (default 6)
    
    Returns:
        List of items with left (term) and right (definition) pairs
    """
    items = LearningItem.query.filter_by(
        container_id=container_id,
        item_type='FLASHCARD'
    ).all()
    
    eligible = []
    for item in items:
        content = item.content or {}
        if content.get('front') and content.get('back'):
            eligible.append({
                'item_id': item.item_id,
                'term': content.get('front'),
                'definition': content.get('back'),
            })
    
    # Shuffle and pick items
    random.shuffle(eligible)
    selected = eligible[:min(count, len(eligible))]
    
    return selected


def generate_matching_game(container_id, count=6):
    """Generate a matching game with shuffled left and right columns.
    
    Returns:
        {
            'left': [{'id': 'L1', 'item_id': 1, 'text': 'apple'}, ...],
            'right': [{'id': 'R1', 'item_id': 1, 'text': 'táo'}, ...],
            'pairs': {item_id: {'left_id': 'L1', 'right_id': 'R1'}, ...}
        }
    """
    items = get_matching_items(container_id, count)
    
    if len(items) < 4:
        return None
    
    # Create left and right columns
    left = []
    right = []
    pairs = {}
    
    for i, item in enumerate(items):
        left_id = f'L{i}'
        right_id = f'R{i}'
        
        left.append({
            'id': left_id,
            'item_id': item['item_id'],
            'text': item['term']
        })
        
        right.append({
            'id': right_id,
            'item_id': item['item_id'],
            'text': item['definition']
        })
        
        pairs[item['item_id']] = {
            'left_id': left_id,
            'right_id': right_id
        }
    
    # Shuffle right column only (left stays in order)
    random.shuffle(right)
    
    return {
        'left': left,
        'right': right,
        'pairs': pairs,
        'total': len(items)
    }


def check_match(item_id, left_id, right_id, game_data):
    """Check if a match is correct."""
    pairs = game_data.get('pairs', {})
    correct_pair = pairs.get(str(item_id))
    
    if not correct_pair:
        return {'correct': False, 'message': 'Invalid item'}
    
    is_correct = correct_pair['left_id'] == left_id and correct_pair['right_id'] == right_id
    
    return {'correct': is_correct}
