"""Generic chat endpoints shared across collaborative room types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Type

from flask import abort, jsonify, request
from flask_login import current_user, login_required

from ...db_instance import db
from ...models import (
    FlashcardCollabMessage,
    FlashcardCollabParticipant,
    FlashcardCollabRoom,
    QuizBattleMessage,
    QuizBattleParticipant,
    QuizBattleRoom,
)
from . import chat_bp
from .service import create_chat_message, get_recent_messages, serialize_chat_message


@dataclass(frozen=True)
class ChatHandler:
    """Describe how to validate and store chat data for a room type."""

    fetch_room: Callable[[str], object]
    ensure_member: Callable[[object, int], object]
    message_model: Type


def _get_handler(room_type: str) -> ChatHandler:
    handler = _CHAT_HANDLERS.get(room_type)
    if not handler:
        abort(404, description='Không hỗ trợ loại phòng này.')
    return handler


def _ensure_quiz_battle_member(room: QuizBattleRoom, user_id: int) -> QuizBattleParticipant:
    participant = QuizBattleParticipant.query.filter_by(room_id=room.room_id, user_id=user_id).first()
    if not participant or participant.status == QuizBattleParticipant.STATUS_KICKED:
        abort(403, description='Bạn cần tham gia phòng để trò chuyện cùng mọi người.')
    return participant


def _ensure_flashcard_member(room: FlashcardCollabRoom, user_id: int) -> FlashcardCollabParticipant:
    participant = FlashcardCollabParticipant.query.filter_by(room_id=room.room_id, user_id=user_id).first()
    if not participant or participant.status != FlashcardCollabParticipant.STATUS_ACTIVE:
        abort(403, description='Bạn cần tham gia phòng để trò chuyện cùng mọi người.')
    return participant


_CHAT_HANDLERS: dict[str, ChatHandler] = {
    'quiz-battle': ChatHandler(
        fetch_room=lambda code: QuizBattleRoom.query.filter_by(room_code=code).first(),
        ensure_member=_ensure_quiz_battle_member,
        message_model=QuizBattleMessage,
    ),
    'flashcard-collab': ChatHandler(
        fetch_room=lambda code: FlashcardCollabRoom.query.filter_by(room_code=code).first(),
        ensure_member=_ensure_flashcard_member,
        message_model=FlashcardCollabMessage,
    ),
}


@chat_bp.route('/<room_type>/<string:room_code>/messages', methods=['GET'])
@login_required
def list_chat_messages(room_type: str, room_code: str):
    """Return the newest chat messages for the given room."""

    handler = _get_handler(room_type)
    room = handler.fetch_room(room_code)
    if not room:
        abort(404, description='Không tìm thấy phòng để trò chuyện.')

    handler.ensure_member(room, current_user.user_id)

    limit = request.args.get('limit', default=50, type=int)
    messages = get_recent_messages(handler.message_model, room.room_id, limit)
    payload = [serialize_chat_message(message) for message in reversed(messages)]

    return jsonify({'messages': payload})


@chat_bp.route('/<room_type>/<string:room_code>/messages', methods=['POST'])
@login_required
def post_chat_message(room_type: str, room_code: str):
    """Allow a room participant to send a chat message."""

    handler = _get_handler(room_type)
    room = handler.fetch_room(room_code)
    if not room:
        abort(404, description='Không tìm thấy phòng để trò chuyện.')

    handler.ensure_member(room, current_user.user_id)

    payload = request.get_json() or {}
    content = payload.get('content')
    if not content or not str(content).strip():
        abort(400, description='Tin nhắn không được để trống.')

    message = create_chat_message(handler.message_model, room.room_id, current_user.user_id, str(content))
    db.session.refresh(message)
    return jsonify({'message': serialize_chat_message(message)})
