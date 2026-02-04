# File: mindstack_app/modules/content_management/signals.py
"""
Content Management Signals
==========================
Signals emitted by the content_management module when content changes.
These signals allow other modules (e.g., FSRS, stats) to react to content changes
without direct database coupling.
"""

from blinker import Namespace

_signals = Namespace()

# Emitted when a new container or item is created
# Kwargs: item_id (int), item_type (str), container_id (int), user_id (int)
content_created = _signals.signal('content-created')

# Emitted when existing content is updated
# Kwargs: item_id (int), item_type (str), changes (dict), user_id (int)
content_updated = _signals.signal('content-updated')

# Emitted when content is deleted
# Kwargs: item_id (int), item_type (str), container_id (int), user_id (int)
# CRITICAL: FSRS and Learning submodules MUST listen to this to clean up progress data
content_deleted = _signals.signal('content-deleted')

# Emitted when a container structure changes (reordered items, etc.)
# Kwargs: container_id (int), user_id (int)
container_structure_changed = _signals.signal('container-structure-changed')
