class AccessControlError(Exception):
    """Base exception for access control module."""
    pass

class PermissionDeniedError(AccessControlError):
    """Raised when a user lacks the required permission."""
    def __init__(self, permission_key: str, message: str = "Permission denied"):
        self.permission_key = permission_key
        self.message = message
        super().__init__(message)

class QuotaExceededError(AccessControlError):
    """Raised when a user exceeds a resource quota."""
    def __init__(self, limit_key: str, current_usage: int, limit: int, message: str = "Quota exceeded"):
        self.limit_key = limit_key
        self.current_usage = current_usage
        self.limit = limit
        self.message = message
        super().__init__(message)
