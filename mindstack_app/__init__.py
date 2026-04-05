# File: mindstack_app/__init__.py
# Ultra-Clean Application Factory

from flask import Flask
from .core.config import Config
from .core.bootstrap import bootstrap_system
from .core.extensions import db

def create_app(config_class=Config) -> Flask:
    """
    Application Factory: Khởi tạo Flask App và kích hoạt hệ thống Core.
    """
    # 1. Instantiate Flask (Presentation & Static folders are handled by Themes)
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 2. Infrastructure Initialization
    config_class.init_app(app)
    
    # 3. Bootstrap Core System (Discovery, Themes, Models)
    with app.app_context():
        bootstrap_system(app)
        
    # 3.1 NEW: Server-side Session Management (After DB is initialized in bootstrap)
    from flask_session import Session
    app.config['SESSION_SQLALCHEMY'] = db
    Session(app)
    
    # 3.2 Ensure all tables exist (including new SSO session tables)
    with app.app_context():
        db.create_all()

    # 3.3 Ensure config defaults and reload settings IF it failed previously during bootstrap
    with app.app_context():
        config_service = app.extensions.get("config_service")
        if config_service:
            config_service.ensure_defaults(config_service._default_settings_payload)
            config_service.load_settings(force=True)
        

    # STRICT ADMIN BYPASS: Standard Local Auth Only
    # --- ECOSYSTEM HEALTH CHECK ---
    from flask import jsonify
    @app.route('/api/health')
    def api_health():
        """Public endpoint for CentralAuth health checks."""
        return jsonify({"status": "online", "service": "mindstack"})

    @app.route('/api/sso-internal/user-list', methods=['POST'])
    def internal_user_list():
        """
        Internal API for CentralAuth to scan and sync users.
        Protected by Client Secret verification.
        """
        from flask import request
        secret_header = request.headers.get('X-Client-Secret')
        configured_secret = app.config.get('CENTRAL_AUTH_CLIENT_SECRET')

        if not secret_header or secret_header != configured_secret:
            return jsonify({"error": "Unauthorized"}), 401

        from mindstack_app.models.user import User
        users = User.query.all()
        
        user_list = []
        for user in users:
            user_list.append({
                "username": user.username,
                "email": user.email,
                "full_name": getattr(user, 'full_name', user.username),
                "central_auth_id": user.central_auth_id
            })
            
        return jsonify({"users": user_list}), 200

    return app
