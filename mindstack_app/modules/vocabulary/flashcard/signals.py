# File: mindstack_app/modules/vocab_flashcard/signals.py
"""
Vocab Flashcard Module Signals
==============================
Defines module-specific signals for cross-module communication.

Signals allow loose coupling between modules. Other modules can listen
to these signals without creating direct dependencies.

Note: The core `card_reviewed` signal is defined in `mindstack_app.core.signals`
and is used for general gamification integration.
"""

from blinker import signal

# Emitted when a flashcard session is started
# Sender: session dict with keys: user_id, session_id, set_id, mode
flashcard_session_started = signal('flashcard_session_started')

# Emitted when a flashcard session is completed (not cancelled)
# Sender: session dict with keys: user_id, session_id, stats
flashcard_session_completed = signal('flashcard_session_completed')

# Emitted when a flashcard batch is loaded
# Sender: batch dict with keys: user_id, session_id, item_count
flashcard_batch_loaded = signal('flashcard_batch_loaded')
