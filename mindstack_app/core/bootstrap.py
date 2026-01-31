# File: mindstack_app/core/bootstrap.py
# Infrastructure Layer: System Bootstrapper (Discovery & Registry)

import os
import importlib
import logging
from flask import Flask, Blueprint
from .module_registry import get_module_key_by_blueprint
from .extensions import db, login_manager, csrf_protect, scheduler, migrate

logger = logging.getLogger(__name__)

def bootstrap_system(app: Flask):
    """
    Trái tim của hệ thống: Khởi động toàn bộ Infrastructure, Modules và Themes.
    """
    # 1. Initialize Infrastructure
    init_infrastructure(app)
    
    # 2. Register Global Handlers
    from .error_handlers import register_error_handlers
    register_error_handlers(app)
    
    # Register Template Filters
    from mindstack_app.utils.template_filters import register_filters
    register_filters(app)
    
    # 3. Auto-Discovery & Load Modules
    load_modules(app)
    
    # 4. Load Themes (Presentation Layer)
    load_themes(app)
    
    # 5. Model Registry (SQLAlchemy visibility)
    register_all_models(app)

def init_infrastructure(app: Flask):
    """Khởi tạo các extensions lõi."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf_protect.init_app(app)
    
    # Register media serving route
    from flask import send_from_directory
    @app.route('/media/<path:filename>')
    def media_uploads(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    # Register user_loader for Flask-Login
    from mindstack_app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        try:
            scheduler.init_app(app)
            if not scheduler.running:
                scheduler.start()
        except Exception as e:
            logger.error(f"Scheduler failed: {e}")

def load_modules(app: Flask):
    """Quét và nạp các module từ mindstack_app/modules/"""
    modules_dir = os.path.join(app.root_path, 'modules')
    
    for module_name in os.listdir(modules_dir):
        module_path = os.path.join(modules_dir, module_name)
        if os.path.isdir(module_path) and os.path.exists(os.path.join(module_path, '__init__.py')):
            try:
                # Import module package
                mod = importlib.import_module(f'mindstack_app.modules.{module_name}')
                
                # Look for blueprint attribute (naming convention: blueprint or <name>_bp)
                blueprint = getattr(mod, 'blueprint', None) or getattr(mod, f'{module_name}_bp', None)
                
                if isinstance(blueprint, Blueprint):
                    # 1. Call setup_module FIRST to attach routes to the blueprint
                    setup_func = getattr(mod, 'setup_module', None)
                    if callable(setup_func):
                        setup_func(app)
                        logger.debug(f"Executed setup_module for: {module_name}")

                    # 2. Get prefix from metadata
                    metadata = getattr(mod, 'module_metadata', {})
                    url_prefix = metadata.get('url_prefix')
                    
                    # 3. Register the blueprint to the app ONLY IF not already registered
                    if blueprint.name not in app.blueprints:
                        app.register_blueprint(blueprint, url_prefix=url_prefix)
                        logger.debug(f"Module registered: {module_name} at {url_prefix or '/'}")
                    else:
                        logger.debug(f"Module {module_name} (blueprint {blueprint.name}) was already registered.")
                    
            except Exception as e:
                logger.error(f"Failed to load module {module_name}: {e}")

def load_themes(app: Flask):
    """Nạp giao diện hệ thống (Admin & Active User Theme)"""
    # 1. Always load Admin Theme
    try:
        from mindstack_app.themes.admin import blueprint as admin_theme_bp
        app.register_blueprint(admin_theme_bp)
    except ImportError:
        logger.warning("Admin theme not found in themes/admin")

    # 2. Load Active Theme from Config
    active_theme = app.config.get('ACTIVE_THEME', 'aura_mobile')
    try:
        theme_mod = importlib.import_module(f'mindstack_app.themes.{active_theme}')
        theme_bp = getattr(theme_mod, 'blueprint', None)
        if theme_bp:
            app.register_blueprint(theme_bp)
            logger.info(f"Theme activated: {active_theme}")
    except Exception as e:
        logger.error(f"Failed to load theme {active_theme}: {e}")

def register_all_models(app: Flask):
    """SQLAlchemy Model Registry: Đảm bảo tất cả models được import."""
    # Quét tất cả models trong mindstack_app/models/
    models_dir = os.path.join(app.root_path, 'models')
    for file in os.listdir(models_dir):
        if file.endswith('.py') and not file.startswith('__'):
            module_name = file[:-3]
            importlib.import_module(f'mindstack_app.models.{module_name}')
    
    # Quét models trong từng module (nếu có)
    modules_dir = os.path.join(app.root_path, 'modules')
    for module_name in os.listdir(modules_dir):
        model_file = os.path.join(modules_dir, module_name, 'models.py')
        if os.path.exists(model_file):
            importlib.import_module(f'mindstack_app.modules.{module_name}.models')
