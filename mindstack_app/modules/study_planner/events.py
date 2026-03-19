"""
Event Listeners for the Study Planner module.

Listens to the `card_reviewed` signal to track new cards learned
and update the active study plan progress in real-time.
"""

from __future__ import annotations

from flask import current_app
from mindstack_app.core.signals import card_reviewed


@card_reviewed.connect
def on_card_reviewed(sender, **kwargs):
    """
    Handle card_reviewed signal.
    
    Only counts a card as "newly learned" if it was previously in state 0 (New).
    This prevents double-counting from review sessions.
    """
    user_id = kwargs.get('user_id')
    item_id = kwargs.get('item_id')

    if not user_id or not item_id:
        return

    try:
        from mindstack_app.models import LearningItem, ItemMemoryState

        # Get the item's container
        item = LearningItem.query.get(item_id)
        if not item:
            return

        # Check if this item was JUST learned (state transitions from 0 to non-0)
        # The signal fires AFTER FSRS has updated the state.
        # We check: if the item now has a state != 0 AND repetitions == 1,
        # it means this was the FIRST review (transition from New -> Learning).
        memory_state = ItemMemoryState.query.filter_by(
            user_id=user_id,
            item_id=item_id
        ).first()

        if not memory_state:
            return

        # Only count as "new card learned" if this is the first repetition
        if memory_state.repetitions != 1:
            return

        # Record this in the planner
        from .services.planner_service import PlannerService
        PlannerService.record_new_card_learned(user_id, item.container_id)

        current_app.logger.debug(
            f"[PLANNER] Recorded new card learned: user={user_id}, item={item_id}, container={item.container_id}"
        )
    except Exception as e:
        # Never let planner errors break the main learning flow
        current_app.logger.error(f"[PLANNER] Error in on_card_reviewed: {e}", exc_info=True)
