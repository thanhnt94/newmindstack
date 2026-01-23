"""
Streak Logic - Pure functions for streak calculation.

This module contains ONLY pure Python logic.
NO database, NO Flask, NO model dependencies allowed.
"""
from datetime import date, datetime, timedelta
from typing import List, Set, Union


def calculate_streak_from_dates(
    activity_dates: List[Union[date, datetime, str]], 
    today: date = None
) -> int:
    """
    Tính chuỗi ngày hoạt động liên tục từ list các ngày.
    
    Args:
        activity_dates: List các date objects, datetime objects, hoặc ISO date strings.
        today: Ngày hiện tại để tính streak (default: date.today()).
    
    Returns:
        Số ngày streak liên tục (int).
        
    Examples:
        >>> from datetime import date
        >>> dates = [date(2024, 1, 3), date(2024, 1, 2), date(2024, 1, 1)]
        >>> calculate_streak_from_dates(dates, today=date(2024, 1, 3))
        3
        
        >>> # Gap in dates
        >>> dates = [date(2024, 1, 3), date(2024, 1, 1)]  # Missing Jan 2
        >>> calculate_streak_from_dates(dates, today=date(2024, 1, 3))
        1
    """
    if not activity_dates:
        return 0
    
    # Normalize all dates to date objects
    learned_dates: Set[date] = set()
    for val in activity_dates:
        normalized = _normalize_to_date(val)
        if normalized:
            learned_dates.add(normalized)
    
    if not learned_dates:
        return 0
    
    # Use provided today or get current date
    if today is None:
        today = date.today()
    
    yesterday = today - timedelta(days=1)
    
    # Determine starting point for streak counting
    if today in learned_dates:
        current_check = today
    elif yesterday in learned_dates:
        # User hasn't learned today yet, but learned yesterday
        current_check = yesterday
    else:
        # No activity today or yesterday = streak broken
        return 0
    
    # Count consecutive days backwards
    streak = 0
    while current_check in learned_dates:
        streak += 1
        current_check -= timedelta(days=1)
    
    return streak


def _normalize_to_date(val: Union[date, datetime, str, None]) -> Union[date, None]:
    """
    Normalize various date representations to a date object.
    
    Args:
        val: Can be date, datetime, ISO string, or None.
        
    Returns:
        date object or None if conversion fails.
    """
    if val is None:
        return None
    
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    
    if isinstance(val, datetime):
        return val.date()
    
    if isinstance(val, str):
        try:
            # Try ISO format first (YYYY-MM-DD or full datetime)
            return datetime.fromisoformat(val).date()
        except ValueError:
            try:
                # Try common date format
                return datetime.strptime(val, '%Y-%m-%d').date()
            except ValueError:
                return None
    
    return None
