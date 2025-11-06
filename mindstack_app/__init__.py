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
)
from .extensions import db

__all__ = ["create_app", "app", "db"]


def create_app(config_class: type[Config] = Config) -> Flask:
    """Create and configure a Flask application instance."""

    app = Flask(__name__)
    app.config.from_object(config_class)

    configure_logging(app)
    register_extensions(app)
    configure_static_uploads(app)
    register_context_processors(app)
    register_blueprints(app)

    with app.app_context():
        initialize_database(app)

    return app


app = create_app()
