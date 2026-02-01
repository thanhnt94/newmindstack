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
            # First try the import_path itself (if it's a package)
            pkg = import_string(module.import_path, silent=True)
            setup_func = getattr(pkg, "setup_module", None)
            
            # If not found or not callable, try the parent package
            if not setup_func or not callable(setup_func):
                package_path = ".".join(module.import_path.split(".")[:-1])
                pkg = import_string(package_path, silent=True)
                setup_func = getattr(pkg, "setup_module", None)
                
            if setup_func and callable(setup_func):
                setup_func(app)
                app.logger.debug("Called setup_module for %s", module.import_path)
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
    ModuleDefinition("mindstack_app.modules.auth", "auth_bp", url_prefix="/auth", display_name="Xác thực"),
    ModuleDefinition("mindstack_app.modules.landing", "blueprint", display_name="Trang chủ"),
    ModuleDefinition("mindstack_app.modules.dashboard", "blueprint", display_name="Bảng điều khiển người dùng"),
    ModuleDefinition("mindstack_app.modules.stats", "blueprint", url_prefix="/stats", display_name="Thống kê & Bảng xếp hạng"),
    ModuleDefinition("mindstack_app.modules.gamification", "blueprint", url_prefix="/admin/gamification", display_name="Game hóa (Badges/Scores)"),
    ModuleDefinition("mindstack_app.modules.admin", "admin_bp", url_prefix="/admin", display_name="Quản trị hệ thống"),
    ModuleDefinition(
        "mindstack_app.modules.user_management.user_routes",
        "user_management_bp",
        url_prefix="/admin/users",
        display_name="Quản lý người dùng",
    ),
    ModuleDefinition("mindstack_app.modules.user_profile", "blueprint", url_prefix="/profile", display_name="Hồ sơ cá nhân"),
    ModuleDefinition(
        "mindstack_app.modules.content_management",
        "blueprint",
        url_prefix="/content",
        display_name="Quản lý nội dung (CMS)",
    ),
    ModuleDefinition("mindstack_app.modules.learning", "blueprint", url_prefix="/learn", display_name="Hệ thống học tập"),
    ModuleDefinition("mindstack_app.modules.learning.routes.api", "markers_bp", display_name="API Markers học tập"),
    ModuleDefinition("mindstack_app.modules.course", "blueprint", display_name="Khóa học tự học (Course)"),
    ModuleDefinition("mindstack_app.modules.goals", "blueprint", url_prefix="/goals", display_name="Mục tiêu học tập"),
    ModuleDefinition("mindstack_app.modules.quiz", "blueprint", display_name="Hệ thống Quiz"),
    ModuleDefinition("mindstack_app.modules.AI", "blueprint", display_name="Tính năng AI Coach"),
    ModuleDefinition("mindstack_app.modules.notes", "blueprint", display_name="Ghi chú cá nhân"),
    ModuleDefinition("mindstack_app.modules.chat", "blueprint", url_prefix="/chat", display_name="Trò chuyện (Chat)"),
    ModuleDefinition("mindstack_app.modules.feedback", "blueprint", url_prefix="/feedback", display_name="Phản hồi hệ thống"),
    ModuleDefinition("mindstack_app.modules.telegram_bot", "blueprint", url_prefix="/telegram", display_name="Telegram Bot"),
    ModuleDefinition("mindstack_app.modules.notification", "blueprint", url_prefix="/notifications", display_name="Thông báo (Web Push)"),
    ModuleDefinition("mindstack_app.modules.translator", "blueprint", url_prefix="/translator", display_name="Dịch thuật & Từ điển"),
    ModuleDefinition("mindstack_app.modules.audio", "audio_bp", url_prefix="/admin/audio", display_name="Xử lý Audio (Studio)"),
    ModuleDefinition("mindstack_app.modules.fsrs", "fsrs_bp", url_prefix="/admin/fsrs", display_name="Thuật toán FSRS"),
)
