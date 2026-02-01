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
        
    return app
