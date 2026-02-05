"""
Centralized Utilities for Time Handling in MindStack.
Goal: Ensure consistent UTC storage and User-Timezone display.
"""
from datetime import datetime, timezone
import pytz
from flask import current_app
from flask_login import current_user

def utcnow() -> datetime:
    """
    Get the current timezone-aware UTC datetime.
    Always use this instead of datetime.utcnow() or datetime.now().
    """
    return datetime.now(timezone.utc)

def to_user_timezone(dt: datetime, user=None) -> datetime:
    """
    Convert a timezone-aware (or naive-as-UTC) datetime to the user's timezone.
    
    Args:
        dt: The datetime object to convert (usually UTC).
        user: The user object (optional). If None, tries current_user.
        
    Returns:
        datetime: Timezone-aware datetime in user's local time.
    """
    if dt is None:
        return None
        
    # Standardize input to UTC
    if not isinstance(dt, datetime):
        # Graceful handling if string passed accidentally
        try:
             dt = datetime.fromisoformat(str(dt).replace('Z', '+00:00'))
        except:
            return dt # Return as-is if parsing fails

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Determine target timezone
    tz_name = current_app.config.get('SYSTEM_TIMEZONE', 'UTC')
    
    target_user = user or current_user
    if target_user and getattr(target_user, 'is_authenticated', False):
        user_tz = getattr(target_user, 'timezone', None)
        if user_tz:
            tz_name = user_tz
            
    try:
        user_tz_obj = pytz.timezone(tz_name)
    except:
        user_tz_obj = pytz.UTC
        
    return dt.astimezone(user_tz_obj)

def format_user_time(dt: datetime, user=None, fmt: str = '%d/%m/%Y %H:%M') -> str:
    """
    Format a datetime string for display in the user's timezone.
    """
    local_dt = to_user_timezone(dt, user)
    if not local_dt:
        return ""
    return local_dt.strftime(fmt)
