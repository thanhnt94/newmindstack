"""
Session Logic - Pure functions for session building.

This module contains ONLY pure Python logic.
NO database, NO Flask, NO model dependencies allowed.

Functions here handle:
- Filtering items based on due dates
- Sorting items by priority (state-based)
- Building session queues with limits
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# State constants (mirrored from FSRS)
STATE_NEW = 0
STATE_LEARNING = 1
STATE_REVIEW = 2
STATE_RELEARNING = 3

# Default priority: Relearning > Learning > New > Review
DEFAULT_PRIORITY_ORDER = [STATE_RELEARNING, STATE_LEARNING, STATE_NEW, STATE_REVIEW]


def filter_due_items(
    items: List[Dict[str, Any]], 
    now: datetime = None,
    include_new: bool = True
) -> List[Dict[str, Any]]:
    """
    Filter items that are due for review.
    
    Args:
        items: List of item dicts with 'due' (datetime or None) and 'state' (int) keys.
        now: Current datetime (default: utcnow).
        include_new: Whether to include new items (state=0, no due date).
    
    Returns:
        List of items that are due for review.
        
    Examples:
        >>> items = [
        ...     {'id': 1, 'due': datetime(2024, 1, 1), 'state': 2},
        ...     {'id': 2, 'due': datetime(2024, 1, 10), 'state': 2},
        ...     {'id': 3, 'due': None, 'state': 0},
        ... ]
        >>> filter_due_items(items, now=datetime(2024, 1, 5))
        [{'id': 1, ...}, {'id': 3, ...}]  # Item 2 not due yet
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Ensure now is timezone-aware
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    result = []
    for item in items:
        due = item.get('due')
        state = item.get('state', STATE_NEW)
        
        # New items with no due date
        if due is None:
            if include_new and state == STATE_NEW:
                result.append(item)
            continue
        
        # Ensure due is timezone-aware for comparison
        if hasattr(due, 'tzinfo') and due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        
        # Item is due if due <= now
        if due <= now:
            result.append(item)
    
    return result


def sort_by_priority(
    items: List[Dict[str, Any]], 
    priority_order: List[int] = None
) -> List[Dict[str, Any]]:
    """
    Sort items by state priority.
    
    Default priority (most urgent first):
    1. Relearning (state=3) - Failed items need immediate re-study
    2. Learning (state=1) - New items being learned
    3. New (state=0) - Fresh items to introduce
    4. Review (state=2) - Graduated items for maintenance
    
    Args:
        items: List of item dicts with 'state' (int) key.
        priority_order: Custom priority order (list of state ints).
    
    Returns:
        Sorted list of items.
    """
    if priority_order is None:
        priority_order = DEFAULT_PRIORITY_ORDER
    
    # Create priority map: state -> priority index (lower = higher priority)
    priority_map = {state: idx for idx, state in enumerate(priority_order)}
    max_priority = len(priority_order)
    
    def get_priority(item: Dict[str, Any]) -> int:
        state = item.get('state', STATE_NEW)
        return priority_map.get(state, max_priority)
    
    return sorted(items, key=get_priority)


def sort_by_due_date(
    items: List[Dict[str, Any]],
    ascending: bool = True
) -> List[Dict[str, Any]]:
    """
    Sort items by due date.
    
    Args:
        items: List of item dicts with 'due' (datetime or None) key.
        ascending: If True, oldest due first. If False, newest due first.
    
    Returns:
        Sorted list of items. Items with None due are placed last.
    """
    def get_due(item: Dict[str, Any]):
        due = item.get('due')
        if due is None:
            # Place None at end
            return datetime.max.replace(tzinfo=timezone.utc)
        if hasattr(due, 'tzinfo') and due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        return due
    
    return sorted(items, key=get_due, reverse=not ascending)


def build_session_queue(
    items: List[Dict[str, Any]],
    now: datetime = None,
    limit: int = None,
    priority_order: List[int] = None,
    include_new: bool = True,
    new_limit: int = None
) -> List[Dict[str, Any]]:
    """
    Build a prioritized session queue from items.
    
    This is the main entry point that combines filtering, sorting, and limiting.
    
    Args:
        items: List of item dicts with 'due', 'state' keys.
        now: Current datetime for due filtering.
        limit: Maximum number of items to return (None = no limit).
        priority_order: Custom state priority order.
        include_new: Whether to include new items.
        new_limit: Maximum number of new items to include (None = no limit).
    
    Returns:
        List of items ready for a learning session.
        
    Examples:
        >>> items = [...]  # Your learning items
        >>> queue = build_session_queue(items, limit=20, new_limit=5)
    """
    # Step 1: Filter due items
    due_items = filter_due_items(items, now=now, include_new=include_new)
    
    # Step 2: Apply new item limit if specified
    if new_limit is not None:
        new_items = [i for i in due_items if i.get('state', STATE_NEW) == STATE_NEW]
        other_items = [i for i in due_items if i.get('state', STATE_NEW) != STATE_NEW]
        
        # Limit new items
        if len(new_items) > new_limit:
            new_items = new_items[:new_limit]
        
        due_items = other_items + new_items
    
    # Step 3: Sort by priority
    sorted_items = sort_by_priority(due_items, priority_order=priority_order)
    
    # Step 4: Apply total limit
    if limit is not None and len(sorted_items) > limit:
        sorted_items = sorted_items[:limit]
    
    return sorted_items
