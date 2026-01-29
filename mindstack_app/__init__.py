"""Application factory for the Mindstack app."""

from __future__ import annotations

from flask import Flask

from .config import Config
from .core.bootstrap import (
    configure_logging,
    configure_static_media_routes,
    configure_module_access_control,
    initialize_database,
    register_blueprints,
    register_context_processors,
    register_extensions,
    register_error_handlers,
)
from .extensions import db
from .services.config_service import init_config_service
from .core.maintenance import init_maintenance_mode

__all__ = ["create_app", "app", "db"]


def create_app(config_class: type[Config] = Config) -> Flask:
    """Create and configure a Flask application instance."""

    # Use default static_folder (mindstack_app/static)
    app = Flask(__name__)
    app.config.from_object(config_class)

    configure_logging(app)
    register_error_handlers(app)
    register_extensions(app)
    configure_module_access_control(app)
    configure_static_media_routes(app)
    register_context_processors(app)
    register_blueprints(app)

    with app.app_context():
        initialize_database(app)
        init_config_service(app)
        init_maintenance_mode(app)

    return app


app = create_app()
