"""Utilities for declaratively registering application modules.

The registry allows each blueprint/module to be described with metadata so that
module discovery and registration can be automated. This makes the application
structure more modular and simplifies future maintenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from flask import Blueprint, Flask
from werkzeug.utils import import_string


@dataclass(frozen=True)
class ModuleDefinition:
    """Describe how a blueprint-backed module is registered with the app."""

    import_path: str
    attribute: str
    url_prefix: Optional[str] = None
    version: str = "1.0"

    def load_blueprint(self) -> Blueprint:
        """Import and return the blueprint described by this definition."""

        module = import_string(self.import_path)
        blueprint = getattr(module, self.attribute, None)
        if not isinstance(blueprint, Blueprint):
            raise TypeError(
                "Expected attribute '%s' in '%s' to be a Flask Blueprint, got %r instead"
                % (self.attribute, self.import_path, type(blueprint))
            )
        return blueprint


def register_modules(app: Flask, modules: Sequence[ModuleDefinition]) -> None:
    """Register all modules in the provided iterable with the Flask app."""

    for module in modules:
        blueprint = module.load_blueprint()
        app.register_blueprint(blueprint, url_prefix=module.url_prefix)
        app.logger.debug(
            "Registered module %s (version %s) at prefix %s",
            module.import_path,
            module.version,
            module.url_prefix or "<root>",
        )


def register_default_modules(app: Flask) -> None:
    """Convenience helper that registers the built-in Mindstack modules."""

    register_modules(app, DEFAULT_MODULES)


DEFAULT_MODULES: Iterable[ModuleDefinition] = (
    ModuleDefinition("mindstack_app.modules.auth.routes", "auth_bp", url_prefix="/auth", version="1.0"),
    ModuleDefinition("mindstack_app.modules.landing.routes", "landing_bp", version="1.0"),
    ModuleDefinition("mindstack_app.modules.dashboard.routes", "dashboard_bp", version="1.0"),
    ModuleDefinition("mindstack_app.modules.admin", "admin_bp", url_prefix="/admin", version="1.0"),
    ModuleDefinition(
        "mindstack_app.modules.admin.user_management.user_routes",
        "user_management_bp",
        url_prefix="/admin/users",
        version="1.0",
    ),
    ModuleDefinition(
        "mindstack_app.modules.admin.api_key_management.routes",
        "api_key_management_bp",
        url_prefix="/admin/api-keys",
        version="1.0",
    ),
    ModuleDefinition("mindstack_app.modules.user_profile", "user_profile_bp", url_prefix="/profile", version="1.0"),
    ModuleDefinition(
        "mindstack_app.modules.content_management.routes",
        "content_management_bp",
        url_prefix="/content",
        version="1.0",
    ),
    ModuleDefinition("mindstack_app.modules.learning.routes", "learning_bp", url_prefix="/learn", version="1.0"),
    ModuleDefinition("mindstack_app.modules.goals.routes", "goals_bp", url_prefix="/goals", version="1.0"),
    ModuleDefinition("mindstack_app.modules.ai_services.routes", "ai_services_bp", version="1.0"),
    ModuleDefinition("mindstack_app.modules.notes.routes", "notes_bp", version="1.0"),
    ModuleDefinition("mindstack_app.modules.shared", "shared_bp", version="1.0"),
    ModuleDefinition("mindstack_app.modules.stats.routes", "stats_bp", url_prefix="/stats", version="1.0"),
    ModuleDefinition("mindstack_app.modules.feedback", "feedback_bp", url_prefix="/feedback", version="1.0"),
    ModuleDefinition("mindstack_app.modules.telegram_bot", "telegram_bot_bp", url_prefix="/telegram", version="1.0"),
    ModuleDefinition("mindstack_app.modules.notification", "notification_bp", url_prefix="/notifications", version="1.0"),
    ModuleDefinition("mindstack_app.modules.translator", "translator_bp", url_prefix="/translator", version="1.0"),
    ModuleDefinition("mindstack_app.modules.gamification", "gamification_bp", version="1.0"),
    ModuleDefinition("mindstack_app.modules.gamification", "gamification_api_bp", version="1.0"),
)
