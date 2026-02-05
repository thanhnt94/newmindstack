"""
Custom Jinja2 template filters for MindStack.
"""
import os
from datetime import datetime, timezone
import pytz
from flask import url_for, current_app
from flask_login import current_user
from mindstack_app.utils.bbcode_parser import bbcode_to_html

from mindstack_app.utils.time_utils import to_user_timezone

def user_timezone_filter(dt, format='%d/%m/%Y %H:%M:%S'):
    """
    Format a datetime object according to the current user's timezone.
    Delegates to mindstack_app.utils.time_utils.
    """
    local_dt = to_user_timezone(dt, current_user)
    if not local_dt:
        return ""
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
