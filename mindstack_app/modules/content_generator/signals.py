from blinker import Namespace

_signals = Namespace()

# Sent when a generation task is queued
# Payload: sender=module, log_id=int
generation_queued = _signals.signal('generation-queued')

# Sent when a generation task successfully finishes
# Payload: sender=module, log_id=int, result=dict
generation_completed = _signals.signal('generation-completed')

# Sent when a generation task fails
# Payload: sender=module, log_id=int, error=str
generation_failed = _signals.signal('generation-failed')
