# modules/backup/events.py
from blinker import Namespace

_signals = Namespace()

backup_completed = _signals.signal('backup_completed')
restore_completed = _signals.signal('restore_completed')
