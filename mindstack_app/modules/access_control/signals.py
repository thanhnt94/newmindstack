from blinker import Namespace

_signals = Namespace()

# Signal fired when a permission check fails
# Arguments: app, user_id, permission_key
access_denied = _signals.signal('access-denied')

# Signal fired when a user's role is updated
# Arguments: app, user_id, old_role, new_role
role_changed = _signals.signal('role-changed')
