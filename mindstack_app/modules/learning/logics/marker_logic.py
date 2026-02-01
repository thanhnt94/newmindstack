from mindstack_app.models import db, UserItemMarker
from sqlalchemy.exc import IntegrityError

def toggle_user_marker(user_id, item_id, marker_type):
    """
    Toggle a user marker for an item.
    If it exists, remove it. If it doesn't, create it.
    Returns: True if marked, False if unmarked.
    """
    existing = UserItemMarker.query.filter_by(
        user_id=user_id, 
        item_id=item_id, 
        marker_type=marker_type
    ).first()
    
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return False
    else:
        new_marker = UserItemMarker(
            user_id=user_id, 
            item_id=item_id, 
            marker_type=marker_type
        )
        db.session.add(new_marker)
        try:
            db.session.commit()
            return True
        except IntegrityError:
            db.session.rollback()
            # Race condition, already exists, so treat as marked (or could retry toggle)
            return True

def get_user_markers_for_items(user_id, item_ids):
    """
    Get all markers for a list of items for a specific user.
    Returns a dict: {item_id: [marker_type1, marker_type2]}
    """
    if not item_ids:
        return {}
        
    markers = UserItemMarker.query.filter(
        UserItemMarker.user_id == user_id,
        UserItemMarker.item_id.in_(item_ids)
    ).all()
    
    result = {}
    for m in markers:
        if m.item_id not in result:
            result[m.item_id] = []
        result[m.item_id].append(m.marker_type)
        
    return result

def get_ignored_item_ids(user_id):
    """Get list of item IDs marked as ignored by the user."""
    query = db.session.query(UserItemMarker.item_id).filter_by(
        user_id=user_id, 
        marker_type='ignored'
    ).all()
    return [row[0] for row in query]

def get_difficult_item_ids(user_id):
    """Get list of item IDs marked as difficult by the user."""
    query = db.session.query(UserItemMarker.item_id).filter_by(
        user_id=user_id, 
        marker_type='difficult'
    ).all()
    return [row[0] for row in query]
