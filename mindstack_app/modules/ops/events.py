# modules/ops/events.py
from blinker import Namespace

_signals = Namespace()

system_reset_performed = _signals.signal('system_reset_performed')
learning_progress_cleared = _signals.signal('learning_progress_cleared')
