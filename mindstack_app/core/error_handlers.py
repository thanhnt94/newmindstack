"""
Error Handlers for MindStack

Provides:
- Custom exception classes
- Consistent error response format
- Flask error handlers
"""

from flask import jsonify, request, current_app
from typing import Optional, Dict, Any


class MindStackError(Exception):
    """Base exception class for MindStack."""
    
    def __init__(
        self,
        message: str,
        code: str = 'UNKNOWN_ERROR',
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> dict:
        """Convert error to dictionary for JSON response."""
        return {
            'success': False,
            'message': self.message,
            'code': self.code,
            'details': self.details
        }


class NotFoundError(MindStackError):
    """Resource not found."""
    
    def __init__(self, message: str = 'Resource not found', resource: str = None):
        super().__init__(
            message=message,
            code='NOT_FOUND',
            status_code=404,
            details={'resource': resource} if resource else None
        )


class ValidationError(MindStackError):
    """Input validation failed."""
    
    def __init__(self, message: str = 'Validation failed', errors: Dict = None):
        super().__init__(
            message=message,
            code='VALIDATION_ERROR',
            status_code=400,
            details={'errors': errors} if errors else None
        )


class AuthorizationError(MindStackError):
    """Access denied."""
    
    def __init__(self, message: str = 'Access denied'):
        super().__init__(
            message=message,
            code='UNAUTHORIZED',
            status_code=403
        )


class RateLimitError(MindStackError):
    """Rate limit exceeded."""
    
    def __init__(self, message: str = 'Rate limit exceeded', retry_after: int = None):
        super().__init__(
            message=message,
            code='RATE_LIMITED',
            status_code=429,
            details={'retry_after': retry_after} if retry_after else None
        )


def error_response(
    message: str,
    code: str = 'ERROR',
    status_code: int = 400,
    details: Dict = None
) -> tuple:
    """Create a standardized error response."""
    response = {
        'success': False,
        'message': message,
        'code': code
    }
    if details:
        response['details'] = details
    
    return jsonify(response), status_code


def success_response(data: Any = None, message: str = None) -> dict:
    """Create a standardized success response."""
    response = {'success': True}
    if data is not None:
        response['data'] = data
    if message:
        response['message'] = message
    return response


def register_error_handlers(app):
    """Register error handlers with Flask app."""
    
    @app.errorhandler(MindStackError)
    def handle_mindstack_error(error):
        current_app.logger.error(f"{error.code}: {error.message}")
        return jsonify(error.to_dict()), error.status_code
    
    @app.errorhandler(404)
    def handle_not_found(error):
        if request.path.startswith('/api/'):
            return error_response('Endpoint not found', 'NOT_FOUND', 404)
        return error
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        current_app.logger.exception('Internal server error')
        if request.path.startswith('/api/'):
            return error_response('Internal server error', 'SERVER_ERROR', 500)
        return error
