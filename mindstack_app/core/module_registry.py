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
    display_name: str = ""

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

    @property
    def config_key(self) -> str:
        """Unique key for identifying this module in database settings."""
        return self.attribute.replace('_bp', '')


# Global registry mapping blueprint names to their config keys
_BLUEPRINT_TO_MODULE_KEY: dict[str, str] = {}


def register_modules(app: Flask, modules: Sequence[ModuleDefinition]) -> None:
    """Register all modules in the provided iterable with the Flask app."""

    for module in modules:
        # Load blueprint
        blueprint = module.load_blueprint()
        app.register_blueprint(blueprint, url_prefix=module.url_prefix)
        
        # Store mapping for access control
        _BLUEPRINT_TO_MODULE_KEY[blueprint.name] = module.config_key
        
        # Optional: Call setup_module(app) if it exists in the module's package
        try:
            # e.g., if import_path is 'mindstack_app.modules.AI.routes',
            # look for 'mindstack_app.modules.AI.setup_module'
            package_path = ".".join(module.import_path.split(".")[:-1])
            pkg = import_string(package_path, silent=True)
            setup_func = getattr(pkg, "setup_module", None)
            if setup_func and callable(setup_func):
                setup_func(app)
                app.logger.debug("Called setup_module for %s", package_path)
        except Exception as e:
            app.logger.error("Error during setup_module for %s: %s", module.import_path, e)

        app.logger.debug(
            "Registered module %s (version %s) at prefix %s",
            module.import_path,
            module.version,
            module.url_prefix or "<root>",
        )


def get_module_key_by_blueprint(blueprint_name: str) -> Optional[str]:
    """Retrieve the config key for a given blueprint name."""
    return _BLUEPRINT_TO_MODULE_KEY.get(blueprint_name)


def register_default_modules(app: Flask) -> None:
    """Convenience helper that registers the built-in Mindstack modules."""

    register_modules(app, DEFAULT_MODULES)


DEFAULT_MODULES: Iterable[ModuleDefinition] = (
    ModuleDefinition("mindstack_app.modules.auth.routes", "auth_bp", url_prefix="/auth", display_name="Xác thực"),
    ModuleDefinition("mindstack_app.modules.landing.routes", "landing_bp", display_name="Trang chủ"),
    ModuleDefinition("mindstack_app.modules.dashboard.routes", "dashboard_bp", display_name="Bảng điều khiển người dùng"),
    ModuleDefinition("mindstack_app.modules.stats", "stats_bp", url_prefix="/stats", display_name="Thống kê & Bảng xếp hạng"),
    ModuleDefinition("mindstack_app.modules.gamification", "gamification_bp", url_prefix="/admin/gamification", display_name="Game hóa (Badges/Scores)"),
    ModuleDefinition("mindstack_app.modules.admin", "admin_bp", url_prefix="/admin", display_name="Quản trị hệ thống"),
    ModuleDefinition(
        "mindstack_app.modules.admin.user_management.user_routes",
        "user_management_bp",
        url_prefix="/admin/users",
        display_name="Quản lý người dùng",
    ),
    ModuleDefinition(
        "mindstack_app.modules.admin.api_key_management.routes",
        "api_key_management_bp",
        url_prefix="/admin/api-keys",
        display_name="Quản lý API Key (AI)",
    ),
    ModuleDefinition("mindstack_app.modules.user_profile", "user_profile_bp", url_prefix="/profile", display_name="Hồ sơ cá nhân"),
    ModuleDefinition(
        "mindstack_app.modules.content_management.routes",
        "content_management_bp",
        url_prefix="/content",
        display_name="Quản lý nội dung (CMS)",
    ),
    ModuleDefinition("mindstack_app.modules.learning.routes", "learning_bp", url_prefix="/learn", display_name="Hệ thống học tập"),
    ModuleDefinition("mindstack_app.modules.learning.api.markers", "markers_bp", display_name="API Markers học tập"),
    ModuleDefinition("mindstack_app.modules.goals.routes", "goals_bp", url_prefix="/goals", display_name="Mục tiêu học tập"),
    ModuleDefinition("mindstack_app.modules.AI.routes", "ai_bp", display_name="Tính năng AI Coach"),
    ModuleDefinition("mindstack_app.modules.notes.routes", "notes_bp", display_name="Ghi chú cá nhân"),
    ModuleDefinition("mindstack_app.modules.chat", "chat_bp", url_prefix="/chat", display_name="Trò chuyện (Chat)"),
    ModuleDefinition("mindstack_app.modules.feedback", "feedback_bp", url_prefix="/feedback", display_name="Phản hồi hệ thống"),
    ModuleDefinition("mindstack_app.modules.telegram_bot", "telegram_bot_bp", url_prefix="/telegram", display_name="Telegram Bot"),
    ModuleDefinition("mindstack_app.modules.notification", "notification_bp", url_prefix="/notifications", display_name="Thông báo (Web Push)"),
    ModuleDefinition("mindstack_app.modules.translator", "translator_bp", url_prefix="/translator", display_name="Dịch thuật & Từ điển"),
    ModuleDefinition("mindstack_app.modules.audio.routes", "audio_bp", display_name="Xử lý Audio (Studio)"),
)
