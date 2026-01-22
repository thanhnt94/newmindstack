"""
Central Signal Registry for Event-Driven Architecture.

Uses Flask's built-in blinker integration to enable decoupled
communication between modules.

Usage:
    # Publisher (sender)
    from mindstack_app.core.signals import card_reviewed
    card_reviewed.send(None, user_id=1, item_id=2, ...)
    
    # Subscriber (receiver) - in module's events.py
    @card_reviewed.connect
    def on_card_reviewed(sender, **kwargs):
        ...
"""
from blinker import Namespace

# Create namespace for learning-related signals
learning_signals = Namespace()

# Signal: Fired when a card is reviewed (flashcard, quiz, typing)
# Payload includes: user_id, item_id, quality, is_correct, learning_mode, score_points
card_reviewed = learning_signals.signal('card_reviewed')

# Signal: Fired when a learning session is completed
# Payload includes: user_id, items_reviewed, items_correct, session_duration_minutes
session_completed = learning_signals.signal('session_completed')

# Future signals can be added here:
# badge_earned = learning_signals.signal('badge_earned')
# daily_goal_reached = learning_signals.signal('daily_goal_reached')
