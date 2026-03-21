from flask import Blueprint

blueprint = Blueprint('watchtogether', __name__, template_folder='templates')

def setup_watchtogether(app):
    """
    Called by start_mindstack_app.py to initialize WatchTogether locally.
    """
    from .database import init_db
    init_db()

    # Import and register routes/events so they attach to the blueprint
    from . import auth, routes, socket_events
    
    # Khởi tạo SocketIO
    socket_events.init_sockets(app)
    
    # Miễn trừ kiểm tra CSRF cho WatchTogether (do chạy hoàn toàn biệt lập và có socketio)
    try:
        from mindstack_app.core.extensions import csrf_protect
        csrf_protect.exempt(blueprint)
    except ImportError:
        pass
        
    # Register blueprint via setup instead of app directly if needed, but we can do it here
    app.register_blueprint(blueprint, url_prefix='/watchtogether')
