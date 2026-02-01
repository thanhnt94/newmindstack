"""Core helpers for wiring application components together."""

from .module_registry import (
    DEFAULT_MODULES,
    ModuleDefinition,
    register_default_modules,
    register_modules,
)

__all__ = [
    "DEFAULT_MODULES",
    "ModuleDefinition",
    "register_default_modules",
    "register_modules",
]
