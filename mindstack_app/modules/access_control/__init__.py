from .routes import blueprint, views
from .events import register_events
from .exceptions import PermissionDeniedError, QuotaExceededError
from .decorators import handle_access_control_error

def setup_module(app):
    """
    Initialize the Access Control module.
    1. Register Blueprint.
    2. Register Error Handlers.
    3. Connect Signals/Events.
    """
    app.register_blueprint(blueprint)
    
    # Register error handlers for the specific exceptions
    # Note: Flask requires error code or exception class
    app.register_error_handler(PermissionDeniedError, handle_access_control_error)
    app.register_error_handler(QuotaExceededError, handle_access_control_error)
    
    register_events()
    
    app.logger.info("Access Control Module Initialized.")
