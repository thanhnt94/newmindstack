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
    
    # 3. Load Themes (Presentation Layer) - SHOULD BE EARLY for template resolution
    load_themes(app)
    
    # 4. Auto-Discovery & Load Modules
    load_modules(app)
    
    # 5. Model Registry (SQLAlchemy visibility)
    register_all_models(app)

def init_infrastructure(app: Flask):
    """Khởi tạo các extensions lõi."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf_protect.init_app(app)
    
    # Initialize Dynamic Config Service (Database settings -> app.config)
    from mindstack_app.services.config_service import init_config_service
    init_config_service(app)
    
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
    # Force reload trigger
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
        # Dynamic import for consistency and better error reporting
        admin_theme_mod = importlib.import_module('mindstack_app.themes.admin')
        admin_theme_bp = getattr(admin_theme_mod, 'blueprint', None)
        if admin_theme_bp:
            app.register_blueprint(admin_theme_bp)
            
            # Explicitly add to Jinja loader as fallback for VPS/Gunicorn consistency
            from jinja2 import ChoiceLoader, FileSystemLoader
            admin_tpl_path = os.path.join(app.root_path, 'themes', 'admin', 'templates')
            if os.path.exists(admin_tpl_path):
                app.jinja_loader = ChoiceLoader([
                    app.jinja_loader,
                    FileSystemLoader(admin_tpl_path)
                ])
                logger.info(f"Admin templates added to global loader: {admin_tpl_path}")
            
            logger.info("Admin theme registered successfully.")
    except Exception as e:
        logger.warning(f"Failed to load Admin theme: {e}")

    # 2. Load Active Theme from Config
    active_theme = app.config.get('ACTIVE_THEME', 'aura_mobile')
    try:
        theme_mod = importlib.import_module(f'mindstack_app.themes.{active_theme}')
        theme_bp = getattr(theme_mod, 'blueprint', None)
        if theme_bp:
            app.register_blueprint(theme_bp)
            
            # Explicitly add to Jinja loader as fallback for VPS/Gunicorn consistency
            from jinja2 import ChoiceLoader, FileSystemLoader
            theme_tpl_path = os.path.join(app.root_path, 'themes', active_theme, 'templates')
            if os.path.exists(theme_tpl_path):
                # We always want the new loader to be at the front or added to existing ChoiceLoader
                if isinstance(app.jinja_loader, ChoiceLoader):
                    app.jinja_loader.loaders.append(FileSystemLoader(theme_tpl_path))
                else:
                    app.jinja_loader = ChoiceLoader([
                        app.jinja_loader,
                        FileSystemLoader(theme_tpl_path)
                    ])
                logger.info(f"Theme templates added to global loader: {theme_tpl_path}")
            
            logger.info(f"Theme activated: {active_theme}")
    except Exception as e:
        logger.warning(f"Failed to load theme {active_theme}: {e}")

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
