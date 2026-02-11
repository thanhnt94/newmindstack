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
    from mindstack_app.modules.session.interface import DriverRegistry
    from .driver import VocabularyDriver

    _VOCAB_MODES = ['flashcard', 'mcq', 'typing', 'listening', 'matching', 'speed']
    for mode in _VOCAB_MODES:
        if not DriverRegistry.is_registered(mode):
            DriverRegistry.register(mode, VocabularyDriver)

    # Register Signals, Context Processors, etc.
    @app.context_processor
    def inject_vocab_metadata():
        return {'vocab_module': module_metadata}

    # ── Sub-blueprint Registration ───────────────────────────────────
    # Register child blueprints with ORIGINAL names so all existing
    # url_for('vocab_flashcard.xxx') calls in templates keep working.
    from .flashcard import flashcard_bp, register_flashcard_routes
    from .mcq import mcq_bp, register_mcq_routes
    from .listening import listening_bp, register_listening_routes
    from .typing import typing_bp, register_typing_routes
    from .matching import matching_bp, register_matching_routes
    from .speed import speed_bp, register_speed_routes

    # Attach routes to sub-blueprints
    register_flashcard_routes()
    register_mcq_routes()
    register_listening_routes()
    register_typing_routes()
    register_matching_routes()
    register_speed_routes()

    # Register sub-blueprints with the app
    app.register_blueprint(flashcard_bp, url_prefix='/learn/vocab-flashcard')
    app.register_blueprint(mcq_bp, url_prefix='/learn/vocab-mcq')
    app.register_blueprint(listening_bp, url_prefix='/learn/vocab-listening')
    app.register_blueprint(typing_bp, url_prefix='/learn/vocab-typing')
    app.register_blueprint(matching_bp, url_prefix='/learn/vocab-matching')
    app.register_blueprint(speed_bp, url_prefix='/learn/vocab-speed')