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

# Signal: Fired when score is awarded to a user
# Payload includes: user_id, amount, reason, new_total, item_type
score_awarded = learning_signals.signal('score_awarded')

# ============================================
# Content Management Signals
# ============================================
content_signals = Namespace()

# Signal: Fired when content (Course/Set) is created or imported
# Payload: user_id, content_type ('course', 'flashcard_set', 'quiz_set', 'flashcard_import'), 
#          content_id, title, items_count (optional)
content_created = content_signals.signal('content_created')

# Signal: Fired when content is deleted
# Payload: user_id, content_type, content_id
content_deleted = content_signals.signal('content_deleted')

# ============================================
# AI Services Signals
# ============================================
ai_signals = Namespace()

# Signal: Fired when AI consumes tokens
# Payload: user_id, feature (str), provider (str), model (str), 
#          input_tokens (int), output_tokens (int), cost_estimate (float)
ai_token_used = ai_signals.signal('ai_token_used')

# Future signals can be added here:
# badge_earned = learning_signals.signal('badge_earned')
# daily_goal_reached = learning_signals.signal('daily_goal_reached')
