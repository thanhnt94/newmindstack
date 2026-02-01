"""
Custom Jinja2 template filters for MindStack.
"""
import os
from datetime import datetime, timezone
import pytz
from flask import url_for, current_app
from flask_login import current_user
from mindstack_app.utils.bbcode_parser import bbcode_to_html

def user_timezone_filter(dt, format='%d/%m/%Y %H:%M:%S'):
    """
    Format a datetime object according to the current user's timezone.
    
    Args:
        dt: Datetime object (usually UTC)
        format: String format for strftime
        
    Returns:
        Formatted string or empty string if dt is None
    """
    if not dt:
        return ""
    
    # Ensure dt is a datetime object
    if not isinstance(dt, datetime):
        try:
            # Try to parse if it's a string
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            else:
                return str(dt)
        except Exception:
            return str(dt)
        
    # Priority: 1. User Preference, 2. System Setting, 3. UTC
    tz_name = current_app.config.get('SYSTEM_TIMEZONE', 'UTC')
    if current_user and current_user.is_authenticated:
        user_tz_setting = getattr(current_user, 'timezone', None)
        if user_tz_setting:
            tz_name = user_tz_setting
    
    try:
        user_tz = pytz.timezone(tz_name)
    except Exception:
        user_tz = pytz.UTC
    
    # If dt is naive, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Convert to user timezone
    local_dt = dt.astimezone(user_tz)
    return local_dt.strftime(format)

def media_url_filter(path):
    """
    Convert a relative media path to a full URL using media_uploads route.
    """
    if not path:
        return ""
    
    # If it's already a full URL or absolute path, return as is
    if str(path).startswith(('http://', 'https://', '/')):
        return path
        
    # Otherwise, use url_for to generate the URL for media_uploads
    try:
        return url_for('media_uploads', filename=path)
    except Exception:
        # Fallback to /media/ prefix if url_for fails (e.g. during initialization)
        return f"/media/{path}"

def register_filters(app):
    """Register custom filters with the Flask app."""
    app.jinja_env.filters['user_timezone'] = user_timezone_filter
    app.jinja_env.filters['media_url'] = media_url_filter
    app.jinja_env.filters['bbcode'] = bbcode_to_html
