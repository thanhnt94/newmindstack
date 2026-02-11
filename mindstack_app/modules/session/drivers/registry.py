# File: mindstack_app/modules/session/drivers/registry.py
"""
Driver Registry
===============
Central registry that maps ``learning_mode`` strings to concrete
``BaseSessionDriver`` subclasses.

Usage (at app startup – e.g. in ``module_registry.py``)::

    from mindstack_app.modules.session.drivers import DriverRegistry

    # (Drivers register themselves during their module's setup_module)

Usage (at runtime)::

    driver = DriverRegistry.resolve('mcq')
    state  = driver.initialize_session(container_id, user_id, settings)
"""

from __future__ import annotations

from typing import Dict, Optional, Type

from .base import BaseSessionDriver


class DriverRegistry:
    """Singleton-style registry backed by a class-level dict."""

    _drivers: Dict[str, Type[BaseSessionDriver]] = {}

    # ── registration ─────────────────────────────────────────────────

    @classmethod
    def register(cls, learning_mode: str, driver_class: Type[BaseSessionDriver]) -> None:
        """
        Register a driver class for a given ``learning_mode``.

        Args:
            learning_mode: e.g. ``'flashcard'``, ``'mcq'``, ``'quiz'``.
            driver_class:  A **class** (not instance) that extends
                           ``BaseSessionDriver``.

        Raises:
            TypeError: If *driver_class* is not a subclass of
                       ``BaseSessionDriver``.
        """
        if not (isinstance(driver_class, type) and issubclass(driver_class, BaseSessionDriver)):
            raise TypeError(
                f"{driver_class!r} is not a subclass of BaseSessionDriver"
            )
        cls._drivers[learning_mode] = driver_class

    # ── resolution ───────────────────────────────────────────────────

    @classmethod
    def resolve(cls, learning_mode: str) -> BaseSessionDriver:
        """
        Instantiate and return the driver registered for *learning_mode*.

        Raises:
            KeyError: If no driver has been registered for the mode.
        """
        driver_class = cls._drivers.get(learning_mode)
        if driver_class is None:
            raise KeyError(
                f"No driver registered for learning_mode={learning_mode!r}. "
                f"Available: {list(cls._drivers.keys())}"
            )
        return driver_class()

    # ── introspection ────────────────────────────────────────────────

    @classmethod
    def available_modes(cls) -> list[str]:
        """Return the list of registered learning modes."""
        return list(cls._drivers.keys())

    @classmethod
    def is_registered(cls, learning_mode: str) -> bool:
        return learning_mode in cls._drivers

    @classmethod
    def clear(cls) -> None:
        """Remove all registrations (useful in tests)."""
        cls._drivers.clear()
