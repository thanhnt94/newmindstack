# File: mindstack_app/modules/vocabulary/__init__.py
from flask import Blueprint

vocabulary_bp = Blueprint('vocabulary', __name__)

# Module Metadata
module_metadata = {
    'name': 'Học từ vựng (Vocab Hub)',
    'icon': 'book-open',
    'category': 'Learning',
    'url_prefix': '/learn/vocabulary',
    'admin_route': None, # Managed via content_management or flashcard dashboard
    'enabled': True
}

def setup_module(app):
    """Standard module setup."""
    # Importing routes attaches them to the vocabulary_bp
    from . import routes
    
    # Register Flashcard Modes for Vocabulary context
    from .logics.flashcard_modes import register_vocabulary_flashcard_modes
    register_vocabulary_flashcard_modes()

    # ── Session Driver Registration ──────────────────────────────────
    # Register VocabularyDriver for all vocabulary-type learning modes.
    # The Session module will resolve the correct driver via DriverRegistry.
    from mindstack_app.modules.session.drivers.registry import DriverRegistry
    from .driver import VocabularyDriver

    _VOCAB_MODES = ['flashcard', 'mcq', 'typing', 'listening', 'matching', 'speed']
    for mode in _VOCAB_MODES:
        if not DriverRegistry.is_registered(mode):
            DriverRegistry.register(mode, VocabularyDriver)

    # Register Signals, Context Processors, etc.
    @app.context_processor
    def inject_vocab_metadata():
        return {'vocab_module': module_metadata}