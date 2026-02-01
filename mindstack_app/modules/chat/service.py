"""Reusable chat helpers for collaborative rooms."""

from __future__ import annotations

from typing import Iterable, Type

from mindstack_app.core.extensions import db


def serialize_chat_message(message) -> dict[str, object]:
    """Convert a chat message model instance to a JSON-safe dict."""

    return {
        'message_id': getattr(message, 'message_id', None),
        'room_id': getattr(message, 'room_id', None),
        'user_id': getattr(message, 'user_id', None),
        'username': getattr(getattr(message, 'user', None), 'username', None),
        'content': getattr(message, 'content', ''),
        'created_at': message.created_at.isoformat() if getattr(message, 'created_at', None) else None,
    }


def get_recent_messages(message_model: Type, room_id: int, limit: int = 50) -> Iterable:
    """Return the newest messages for a room, capped by ``limit``."""

    limit = max(1, min(limit, 200))
    return (
        message_model.query.filter_by(room_id=room_id)
        .order_by(message_model.created_at.desc())
        .limit(limit)
        .all()
    )


def create_chat_message(message_model: Type, room_id: int, user_id: int, content: str):
    """Persist a new chat message for the given room."""

    message = message_model(room_id=room_id, user_id=user_id, content=content.strip())
    db.session.add(message)
    db.session.commit()
    return message
