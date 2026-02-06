from functools import wraps
from flask import request, abort, jsonify
from flask_login import current_user
from .interface import AccessControlInterface
from .exceptions import AccessControlError, PermissionDeniedError, QuotaExceededError

def require_permission(permission_key: str):
    """
    Route decorator to enforce permission check.
    If check fails, raises PermissionDeniedError (handled by error handlers) or aborts 403.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
                
            if not AccessControlInterface.check(current_user, permission_key):
                raise PermissionDeniedError(permission_key)
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_quota(limit_key: str, usage_getter=None):
    """
    Advanced usage: Use logic inside the route instead.
    This is a placeholder if you need strictly decorator-based checking
    where usage is known beforehand or static.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Complex to implement without context of 'usage'
            # So we usually rely on manual Interface calls inside the route.
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def handle_access_control_error(error: AccessControlError):
    """
    Standard error handler for access control exceptions.
    Returns structured JSON response.
    """
    response = {
        "success": False,
        "error": error.__class__.__name__,
        "message": str(error)
    }
    
    if isinstance(error, PermissionDeniedError):
        response["permission_key"] = error.permission_key
        return jsonify(response), 403
        
    if isinstance(error, QuotaExceededError):
        response["limit_key"] = error.limit_key
        response["limit"] = error.limit
        response["current"] = error.current_usage
        return jsonify(response), 403 # Or 429 Too Many Requests? 403 is safer for policy limits.
        
    return jsonify(response), 403
