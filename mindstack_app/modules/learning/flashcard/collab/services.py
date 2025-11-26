"""Service helpers for collaborative flashcard learning."""

from __future__ import annotations

from datetime import datetime, timezone
import string
import random
from typing import Callable, Iterable, Optional

from flask import url_for

from .....models import (
    FlashcardCollabAnswer,
    FlashcardCollabParticipant,
    FlashcardCollabRoom,
    FlashcardCollabRound,
    FlashcardProgress,
    LearningContainer,
    LearningItem,
    User,
    db,
)
from ..individual import algorithms


def generate_room_code(length: int = 6) -> str:
    """Generate a short alphanumeric room code."""

    alphabet = string.ascii_uppercase + string.digits
    return ''.join(random.choice(alphabet) for _ in range(length))


def _first_item(query) -> Optional[LearningItem]:
    """Safely fetch the first item from a SQLAlchemy query."""

    try:
        return query.first()
    except Exception:
        return None


def _normalize_due_time(value: Optional[datetime]) -> datetime:
    if not value:
        return datetime.max.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _build_item_payload(item: LearningItem) -> dict[str, object]:
    """Serialize a flashcard item for API responses."""

    content = item.content or {}

    def _media_url(value: Optional[str], media_type: str) -> Optional[str]:
        if not value:
            return None
        if value.startswith(('http://', 'https://')):
            return value
        if value.startswith('/'):
            return url_for('static', filename=value.lstrip('/'))
        return url_for('static', filename=value)

    return {
        'item_id': item.item_id,
        'container_id': item.container_id,
        'content': {
            'front': content.get('front', ''),
            'back': content.get('back', ''),
            'front_audio_content': content.get('front_audio_content', ''),
            'front_audio_url': _media_url(content.get('front_audio_url'), 'audio'),
            'back_audio_content': content.get('back_audio_content', ''),
            'back_audio_url': _media_url(content.get('back_audio_url'), 'audio'),
            'front_img': _media_url(content.get('front_img'), 'image'),
            'back_img': _media_url(content.get('back_img'), 'image'),
        },
        'ai_explanation': item.ai_explanation,
    }


def _pick_next_item_for_user(user_id: int, container_id: int, mode: str) -> Optional[LearningItem]:
    """Return the next flashcard for a single user based on mode."""

    normalized = (mode or '').strip().lower()
    exclusion = None

    if normalized == 'new_only':
        query = algorithms.get_new_only_items(user_id, container_id, None)
        query = query.order_by(LearningItem.order_in_container.asc())
        return _first_item(query)

    if normalized == 'due_only':
        query = algorithms.get_due_items(user_id, container_id, None)
        query = query.order_by(FlashcardProgress.due_time.asc())
        return _first_item(query)

    if normalized == 'hard_only':
        query = algorithms.get_hard_items(user_id, container_id, None)
        query = query.order_by(FlashcardProgress.due_time.asc(), LearningItem.item_id.asc())
        return _first_item(query)

    if normalized == 'all_review':
        query = algorithms.get_all_review_items(user_id, container_id, None)
        query = query.order_by(FlashcardProgress.due_time.asc(), LearningItem.item_id.asc())
        return _first_item(query)

    # Capability-based practice modes fall back to ordered items from their specific query
    practice_modes: dict[str, Callable[[int, int, Optional[int]], Iterable[LearningItem]]] = {
        'pronunciation_practice': algorithms.get_pronunciation_items,
        'writing_practice': algorithms.get_writing_items,
        'quiz_practice': algorithms.get_quiz_items,
        'essay_practice': algorithms.get_essay_items,
        'listening_practice': algorithms.get_listening_items,
        'speaking_practice': algorithms.get_speaking_items,
    }

    practice_func = practice_modes.get(normalized)
    if practice_func:
        query = practice_func(user_id, container_id, None)
        query = query.order_by(LearningItem.order_in_container.asc(), LearningItem.item_id.asc())
        return _first_item(query)

    # Autoplay style modes use the broader selection with deterministic ordering
    if normalized in {'autoplay_learned', 'autoplay_all'}:
        query = algorithms.get_all_items_for_autoplay(user_id, container_id, None)
        query = query.order_by(LearningItem.order_in_container.asc(), LearningItem.item_id.asc())
        return _first_item(query)

    # Default mixed SRS: prioritize due cards then new ones
    due_query = algorithms.get_due_items(user_id, container_id, None).order_by(FlashcardProgress.due_time.asc())
    due_item = _first_item(due_query)
    if due_item:
        return due_item

    new_query = algorithms.get_new_only_items(user_id, container_id, None).order_by(
        LearningItem.order_in_container.asc()
    )
    return _first_item(new_query)


def _select_next_item(room: FlashcardCollabRoom) -> Optional[tuple[LearningItem, int, datetime]]:
    """Select the next flashcard item shared across participants."""

    candidates: list[tuple[LearningItem, int, datetime]] = []
    for participant in room.participants:
        if participant.status != FlashcardCollabParticipant.STATUS_ACTIVE:
            continue
        item = _pick_next_item_for_user(participant.user_id, room.container_id, room.mode)
        if not item:
            continue
        progress = FlashcardProgress.query.filter_by(user_id=participant.user_id, item_id=item.item_id).first()
        due_time = _normalize_due_time(progress.due_time if progress else None)
        candidates.append((item, participant.user_id, due_time))

    if not candidates:
        return None

    candidates.sort(key=lambda item_tuple: (item_tuple[2], item_tuple[0].item_id))
    next_item, scheduled_for_user_id, due_time = candidates[0]
    return next_item, scheduled_for_user_id, due_time


def get_next_shared_item(room: FlashcardCollabRoom) -> Optional[dict[str, object]]:
    """Pick the next flashcard that the room should study together."""

    selection = _select_next_item(room)
    if not selection:
        return None

    next_item, scheduled_for_user_id, due_time = selection
    return {
        'item': _build_item_payload(next_item),
        'scheduled_for_user_id': scheduled_for_user_id,
        'scheduled_due_at': due_time.isoformat() if due_time else None,
    }


def ensure_active_round(room: FlashcardCollabRoom) -> Optional[FlashcardCollabRound]:
    """Return the active round for a room or create one if missing."""

    active_round = (
        FlashcardCollabRound.query.filter_by(room_id=room.room_id, status=FlashcardCollabRound.STATUS_ACTIVE)
        .order_by(FlashcardCollabRound.started_at.desc())
        .first()
    )
    if active_round:
        return active_round

    selection = _select_next_item(room)
    if not selection:
        return None

    next_item, scheduled_for_user_id, due_time = selection
    active_round = FlashcardCollabRound(
        room_id=room.room_id,
        item_id=next_item.item_id,
        status=FlashcardCollabRound.STATUS_ACTIVE,
        scheduled_for_user_id=scheduled_for_user_id,
        scheduled_due_at=due_time,
    )
    db.session.add(active_round)
    db.session.commit()
    return active_round


def build_round_payload(round_obj: FlashcardCollabRound, room: FlashcardCollabRoom) -> Optional[dict[str, object]]:
    """Serialize current round state including who has answered."""

    item = LearningItem.query.get(round_obj.item_id)
    if not item:
        return None

    answers_by_user = {answer.user_id: answer for answer in (round_obj.answers or [])}
    participants_payload: list[dict[str, object]] = []
    active_participants = [
        participant for participant in room.participants if participant.status == FlashcardCollabParticipant.STATUS_ACTIVE
    ]

    for participant in active_participants:
        answer = answers_by_user.get(participant.user_id)
        participants_payload.append(
            {
                'user_id': participant.user_id,
                'username': getattr(participant.user, 'username', None),
                'has_answered': answer is not None,
                'answered_at': answer.created_at.isoformat() if answer and answer.created_at else None,
            }
        )

    all_answered = bool(active_participants) and all(p['has_answered'] for p in participants_payload)

    return {
        'round_id': round_obj.round_id,
        'item': _build_item_payload(item),
        'scheduled_for_user_id': round_obj.scheduled_for_user_id,
        'scheduled_due_at': round_obj.scheduled_due_at.isoformat() if round_obj.scheduled_due_at else None,
        'participants': participants_payload,
        'all_answered': all_answered,
        'status': round_obj.status,
        'completed_at': round_obj.completed_at.isoformat() if round_obj.completed_at else None,
        'button_count': getattr(room, 'button_count', None),
    }


def serialize_participant(participant: FlashcardCollabParticipant) -> dict[str, object]:
    """Serialize a participant record for API responses."""

    return {
        'participant_id': participant.participant_id,
        'user_id': participant.user_id,
        'username': getattr(participant.user, 'username', None),
        'is_host': participant.is_host,
        'status': participant.status,
        'joined_at': participant.joined_at.isoformat() if participant.joined_at else None,
        'left_at': participant.left_at.isoformat() if participant.left_at else None,
    }


def serialize_room(room: FlashcardCollabRoom) -> dict[str, object]:
    """Serialize room details including participants."""

    return {
        'room_code': room.room_code,
        'room_id': room.room_id,
        'title': room.title,
        'mode': room.mode,
        'button_count': room.button_count,
        'container_id': room.container_id,
        'container_title': getattr(room.container, 'title', None),
        'host_user_id': room.host_user_id,
        'host_username': getattr(room.host, 'username', None),
        'is_public': room.is_public,
        'status': room.status,
        'created_at': room.created_at.isoformat() if room.created_at else None,
        'updated_at': room.updated_at.isoformat() if room.updated_at else None,
        'participant_count': len(room.participants) if room.participants else 0,
        'participants': [serialize_participant(p) for p in room.participants],
    }
