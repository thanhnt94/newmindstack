# File: mindstack_app/modules/learning_history/interface.py
"""Public interface for learning_history module (Gatekeeper Rule)."""
from .services import HistoryRecorder

# Re-export for external access
record_interaction = HistoryRecorder.record_interaction
