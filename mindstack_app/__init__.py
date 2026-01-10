"""Application factory for the Mindstack app."""

from __future__ import annotations

from flask import Flask

from .config import Config
from .core.bootstrap import (
    configure_logging,
    configure_static_uploads,
    initialize_database,
    register_blueprints,
    register_context_processors,
    register_extensions,
    register_error_handlers,
)
from .extensions import db
from .services.config_service import init_config_service

__all__ = ["create_app", "app", "db"]


def create_app(config_class: type[Config] = Config) -> Flask:
    """Create and configure a Flask application instance."""

    # Set static_folder to UPLOAD_FOLDER so /static/ serves from uploads directory
    app = Flask(__name__, static_folder=config_class.UPLOAD_FOLDER)
    app.config.from_object(config_class)

    configure_logging(app)
    register_error_handlers(app)
    register_extensions(app)
    configure_static_uploads(app)
    register_context_processors(app)
    register_blueprints(app)

    with app.app_context():
        initialize_database(app)
        init_config_service(app)

    return app


app = create_app()
