# modules/maintenance/events.py
from blinker import Namespace

_signals = Namespace()

maintenance_started = _signals.signal('maintenance_started')
maintenance_ended = _signals.signal('maintenance_ended')
