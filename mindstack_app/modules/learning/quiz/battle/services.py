"""Helper utilities that power the quiz battle module."""

from __future__ import annotations

import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from flask import current_app, url_for

from sqlalchemy.sql import func

from mindstack_app.models import (
    LearningItem,
    QuizBattleParticipant,
    QuizBattleRoom,
    QuizBattleRound,
    UserNote,
    db,
)

from ....shared.utils.media_paths import build_relative_media_path


def generate_room_code(length: int = 6) -> str:
    """Generate a short alphanumeric room code."""

    alphabet = string.ascii_uppercase + string.digits
    return ''.join(random.choice(alphabet) for _ in range(length))


def _get_media_folders_from_container(container) -> dict[str, str]:
    """Safely extract media folder mapping from a learning container."""

    if not container:
        return {}

    folders = getattr(container, 'media_folders', {}) or {}
    if folders:
        return dict(folders)
    return {}


def _build_absolute_media_url(file_path: Optional[str], media_folder: Optional[str]) -> Optional[str]:
    """Convert a stored media path into a URL usable by the client."""

    if not file_path:
        return None

    try:
        relative_path = build_relative_media_path(file_path, media_folder)
        if not relative_path:
            return None

        if relative_path.startswith(('http://', 'https://')):
            return relative_path

        static_path = relative_path.lstrip('/')
        return url_for('static', filename=static_path)
    except Exception as exc:  # pragma: no cover - defensive logging
        current_app.logger.warning(
            "Không thể tạo URL media tuyệt đối cho %s: %s", file_path, exc
        )
        return file_path


def _build_question_order(container_id: int, *, limit: Optional[int] = None) -> list[int]:
    """Return a deterministic list of quiz item IDs for the provided container."""

    query = (
        LearningItem.query.filter_by(container_id=container_id, item_type='QUIZ_MCQ')
        .order_by(LearningItem.order_in_container, LearningItem.item_id)
        .with_entities(LearningItem.item_id)
    )
    item_ids = [item_id for (item_id,) in query]
    if limit:
        return item_ids[:limit]
    return item_ids


def ensure_question_order(room: QuizBattleRoom) -> list[int]:
    """Ensure the room has a cached question order and return it."""

    if not room.question_order:
        room.question_order = _build_question_order(room.container_id, limit=room.question_limit) or []
        db.session.flush()
    return list(room.question_order or [])


def get_active_participants(room: QuizBattleRoom) -> list[QuizBattleParticipant]:
    """Return a list of participants that are still active in the room."""

    return [p for p in room.participants if p.status == QuizBattleParticipant.STATUS_ACTIVE]


def get_active_round(room: QuizBattleRoom) -> Optional[QuizBattleRound]:
    """Return the currently active round if any."""

    for round_obj in room.rounds:
        if round_obj.status == QuizBattleRound.STATUS_ACTIVE:
            return round_obj
    return None


def _now_utc() -> datetime:
    """Return the current UTC time as an aware datetime."""

    return datetime.now(timezone.utc)


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def auto_advance_round_if_needed(room: QuizBattleRoom) -> bool:
    """Advance the active round if the timer has elapsed in timed mode."""

    if room.mode != QuizBattleRoom.MODE_TIMED or not room.time_per_question_seconds:
        return False

    round_obj = get_active_round(room)
    if not round_obj or round_obj.status != QuizBattleRound.STATUS_ACTIVE:
        return False

    started_at = _ensure_utc(round_obj.started_at)
    if not started_at:
        return False

    deadline = started_at + timedelta(seconds=room.time_per_question_seconds)
    if _now_utc() < deadline:
        return False

    round_obj.status = QuizBattleRound.STATUS_COMPLETED
    round_obj.ended_at = func.now()

    question_order = ensure_question_order(room)
    has_next_round = round_obj.sequence_number < len(question_order)

    room.current_round_number = round_obj.sequence_number
    room.status = (
        QuizBattleRoom.STATUS_AWAITING_HOST if has_next_round else QuizBattleRoom.STATUS_COMPLETED
    )
    return True


def start_round(room: QuizBattleRoom, sequence_number: int) -> Optional[QuizBattleRound]:
    """Create (or return) the round for the provided sequence number."""

    existing = next((r for r in room.rounds if r.sequence_number == sequence_number), None)
    if existing:
        if existing.status != QuizBattleRound.STATUS_ACTIVE:
            existing.status = QuizBattleRound.STATUS_ACTIVE
            existing.started_at = func.now()
        room.current_round_number = sequence_number
        return existing

    question_order = ensure_question_order(room)
    if sequence_number < 1 or sequence_number > len(question_order):
        return None

    round_obj = QuizBattleRound(
        room=room,
        sequence_number=sequence_number,
        item_id=question_order[sequence_number - 1],
        status=QuizBattleRound.STATUS_ACTIVE,
        started_at=func.now(),
    )
    db.session.add(round_obj)
    room.current_round_number = sequence_number
    return round_obj


def complete_round_if_ready(round_obj: Optional[QuizBattleRound]) -> Optional[QuizBattleRound]:
    """Mark the round as completed when all active participants have answered."""

    if not round_obj or round_obj.status != QuizBattleRound.STATUS_ACTIVE:
        return None

    room = round_obj.room
    expected = {p.participant_id for p in get_active_participants(room)}
    if not expected:
        round_obj.status = QuizBattleRound.STATUS_COMPLETED
        round_obj.ended_at = func.now()
        room.status = QuizBattleRoom.STATUS_AWAITING_HOST
        return None

    answered = {answer.participant_id for answer in round_obj.answers}
    if not expected.issubset(answered):
        return None

    round_obj.status = QuizBattleRound.STATUS_COMPLETED
    round_obj.ended_at = func.now()

    question_order = ensure_question_order(room)
    room.current_round_number = round_obj.sequence_number
    has_next_round = round_obj.sequence_number < len(question_order)
    room.status = (
        QuizBattleRoom.STATUS_AWAITING_HOST if has_next_round else QuizBattleRoom.STATUS_COMPLETED
    )

    return None


def serialize_participant(participant: QuizBattleParticipant) -> dict[str, object]:
    """Return a JSON friendly representation of a participant."""

    return {
        'participant_id': participant.participant_id,
        'user_id': participant.user_id,
        'username': getattr(participant.user, 'username', None),
        'is_host': participant.is_host,
        'status': participant.status,
        'session_score': participant.session_score,
        'correct_answers': participant.correct_answers,
        'incorrect_answers': participant.incorrect_answers,
        'joined_at': participant.joined_at.isoformat() if participant.joined_at else None,
        'left_at': participant.left_at.isoformat() if participant.left_at else None,
    }


def _serialize_question(
    round_obj: QuizBattleRound,
    *,
    user_id: Optional[int] = None,
) -> Optional[dict[str, object]]:
    item = round_obj.item
    if not item:
        item = LearningItem.query.get(round_obj.item_id)
    if not item:
        return None

    content = dict(item.content or {})
    options = content.get('options')
    if not options:
        options = {
            key: content.get(f'option_{key.lower()}')
            for key in ('A', 'B', 'C', 'D')
            if content.get(f'option_{key.lower()}') is not None
        }

    media_folders = _get_media_folders_from_container(item.container if item else None)
    image_folder = media_folders.get('image')
    audio_folder = media_folders.get('audio')

    if content.get('question_image_file'):
        content['question_image_file'] = _build_absolute_media_url(
            content.get('question_image_file'), image_folder
        )

    if content.get('question_audio_file'):
        content['question_audio_file'] = _build_absolute_media_url(
            content.get('question_audio_file'), audio_folder
        )

    note_content = ''
    if user_id:
        note = UserNote.query.filter_by(user_id=user_id, item_id=item.item_id).first()
        note_content = note.content if note else ''

    return {
        'item_id': item.item_id,
        'question': content.get('question'),
        'pre_question_text': content.get('pre_question_text'),
        'options': options,
        'passage_text': content.get('passage_text'),
        'explanation': content.get('explanation'),
        'question_image_file': content.get('question_image_file'),
        'question_audio_file': content.get('question_audio_file'),
        'ai_explanation': item.ai_explanation,
        'note_content': note_content,
    }


def serialize_round(
    round_obj: QuizBattleRound,
    *,
    include_answers: bool = False,
    user_id: Optional[int] = None,
) -> dict[str, object]:
    """Serialize a round with optional answer details."""

    payload: dict[str, object] = {
        'round_id': round_obj.round_id,
        'sequence_number': round_obj.sequence_number,
        'status': round_obj.status,
        'started_at': round_obj.started_at.isoformat() if round_obj.started_at else None,
        'ended_at': round_obj.ended_at.isoformat() if round_obj.ended_at else None,
        'question': _serialize_question(round_obj, user_id=user_id),
    }

    room = round_obj.room
    if (
        room
        and room.mode == QuizBattleRoom.MODE_TIMED
        and room.time_per_question_seconds
        and round_obj.started_at
        and round_obj.status == QuizBattleRound.STATUS_ACTIVE
    ):
        started = _ensure_utc(round_obj.started_at)
        if started:
            deadline = started + timedelta(seconds=room.time_per_question_seconds)
            remaining = (deadline - _now_utc()).total_seconds()
            payload['time_remaining_seconds'] = max(0, int(remaining))

    if include_answers:
        payload['answers'] = [
            {
                'participant_id': answer.participant_id,
                'user_id': answer.participant.user_id if answer.participant else None,
                'selected_option': answer.selected_option,
                'is_correct': answer.is_correct,
                'score_delta': answer.score_delta,
                'correct_option': answer.correct_option,
                'answered_at': answer.answered_at.isoformat() if answer.answered_at else None,
            }
            for answer in round_obj.answers
        ]
    return payload


def serialize_room(
    room: QuizBattleRoom,
    *,
    include_round_history: bool = False,
    user_id: Optional[int] = None,
) -> dict[str, object]:
    """Serialize a room and optionally include the entire round history."""

    question_order = ensure_question_order(room)
    payload: dict[str, object] = {
        'room_code': room.room_code,
        'title': room.title,
        'status': room.status,
        'is_locked': room.is_locked,
        'is_public': room.is_public,
        'host_user_id': room.host_user_id,
        'container_id': room.container_id,
        'max_players': room.max_players,
        'question_limit': room.question_limit,
        'mode': room.mode,
        'time_per_question_seconds': room.time_per_question_seconds,
        'question_total': len(question_order),
        'current_round_number': room.current_round_number,
        'created_at': room.created_at.isoformat() if room.created_at else None,
        'updated_at': room.updated_at.isoformat() if room.updated_at else None,
        'participants': [serialize_participant(p) for p in room.participants],
    }

    active_round = get_active_round(room)
    if not active_round and room.rounds:
        active_round = room.rounds[-1]
    payload['active_round'] = (
        serialize_round(active_round, include_answers=True, user_id=user_id)
        if active_round
        else None
    )

    if include_round_history:
        payload['round_history'] = [
            serialize_round(r, include_answers=True, user_id=user_id)
            for r in room.rounds
        ]

    return payload

