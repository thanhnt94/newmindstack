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
        

    # --- ECOSYSTEM SYNC API ---
    @app.route('/api/sso-internal/user-list', methods=['POST'])
    def internal_user_list():
        """
        Standard Internal API for CentralAuth User Synchronization.
        Protected by Client Secret verification.
        """
        from flask import request, jsonify, current_app
        from mindstack_app.modules.auth.models import User
        
        secret_header = request.headers.get('X-Client-Secret')
        configured_secret = app.config.get('CENTRAL_AUTH_CLIENT_SECRET')

        print(f"[SYNC-DEBUG] Header Secret: {secret_header}", flush=True)
        print(f"[SYNC-DEBUG] Config Secret: {configured_secret}", flush=True)

        if not secret_header or secret_header != configured_secret:
            current_app.logger.warning(f"Sync Auth Failed: Secret mismatch for Sync API")
            return jsonify({"error": "Unauthorized"}), 401

        users = User.query.all()
        print(f"[SYNC-DEBUG] Found {len(users)} users in MindStack")
        
        user_list = []
        for user in users:
            user_list.append({
                "username": user.username,
                "email": user.email,
                "full_name": getattr(user, 'full_name', user.username),
                "central_auth_id": user.central_auth_id
            })
            
        return jsonify({"users": user_list}), 200

    @app.route('/api/sso-internal/link-user', methods=['POST'])
    def internal_link_user():
        """Update a user's central_auth_id for ecosystem linking."""
        from flask import request, jsonify
        from mindstack_app.modules.auth.models import User
        
        secret_header = request.headers.get('X-Client-Secret')
        configured_secret = app.config.get('CENTRAL_AUTH_CLIENT_SECRET')

        if not secret_header or secret_header != configured_secret:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json()
        email = data.get('email')
        ca_id = data.get('central_auth_id')
        username = data.get('username')
        full_name = data.get('full_name')
        
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"error": f"User {email} not found"}), 404
        
        user.central_auth_id = str(ca_id)
        if username:
            user.username = username
        if full_name:
            user.full_name = full_name
            
        db.session.commit()
        return jsonify({"status": "ok", "message": f"Linked {email} and synced profile to CentralAuth."}), 200

    # Ensure CSRF exemption for sync APIs
    try:
        from mindstack_app.core.extensions import csrf_protect
        csrf_protect.exempt(internal_user_list)
        csrf_protect.exempt(internal_link_user)
    except Exception as e:
        app.logger.error(f"Failed to exempt sync-api from CSRF: {e}")

    return app
