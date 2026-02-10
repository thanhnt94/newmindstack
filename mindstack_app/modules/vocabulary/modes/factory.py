# File: mindstack_app/modules/vocabulary/modes/factory.py
"""
Mode Factory
============
Creates ``BaseVocabMode`` instances by mode name.

New modes are registered here.  To add a mode:
1. Create ``your_mode.py`` with a class extending ``BaseVocabMode``.
2. Import and add it to ``_BUILTIN_MODES`` below.
"""

from __future__ import annotations

from typing import Dict, Optional, Type

from .base_mode import BaseVocabMode


class ModeFactory:
    """
    Factory for vocabulary learning modes.

    Supports both built-in auto-registration and runtime registration
    via ``register()``.
    """

    _modes: Dict[str, Type[BaseVocabMode]] = {}
    _initialised: bool = False

    @classmethod
    def _ensure_builtins(cls) -> None:
        """Lazy-load built-in modes on first access."""
        if cls._initialised:
            return

        from .flashcard_mode import FlashcardMode
        from .mcq_mode import MCQMode

        _BUILTIN_MODES = [
            FlashcardMode,
            MCQMode,
            # Future: TypingMode, ListeningMode, MatchingMode, SpeedMode
        ]

        for mode_class in _BUILTIN_MODES:
            instance = mode_class()
            cls._modes[instance.get_mode_id()] = mode_class

        cls._initialised = True

    # ── public API ───────────────────────────────────────────────────

    @classmethod
    def register(cls, mode_class: Type[BaseVocabMode]) -> None:
        """Register a custom mode at runtime."""
        cls._ensure_builtins()
        instance = mode_class()
        cls._modes[instance.get_mode_id()] = mode_class

    @classmethod
    def create(cls, mode_name: str) -> BaseVocabMode:
        """
        Instantiate a mode by name.

        Args:
            mode_name: e.g. ``'mcq'``, ``'flashcard'``, ``'typing'``.

        Raises:
            KeyError: If no mode is registered under *mode_name*.
        """
        cls._ensure_builtins()

        mode_class = cls._modes.get(mode_name)
        if mode_class is None:
            raise KeyError(
                f"Unknown vocabulary mode: {mode_name!r}. "
                f"Available: {list(cls._modes.keys())}"
            )
        return mode_class()

    @classmethod
    def available_modes(cls) -> list[str]:
        """Return registered mode names."""
        cls._ensure_builtins()
        return list(cls._modes.keys())
