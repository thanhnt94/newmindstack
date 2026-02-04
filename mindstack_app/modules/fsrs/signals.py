from blinker import Namespace

# Define a signal namespace for FSRS
_signals = Namespace()

# Signal emitted after a card is reviewed and saved to DB
# Arguments:
# - sender: The SchedulerService instance
# - user_id: int
# - item_id: int
# - rating: int
# - new_state: dict (summary of new state)
card_reviewed = _signals.signal('card-reviewed')

# Signal emitted after user parameters are updated/optimized
# Arguments:
# - sender: The OptimizerService instance
# - user_id: int
parameters_updated = _signals.signal('parameters-updated')
