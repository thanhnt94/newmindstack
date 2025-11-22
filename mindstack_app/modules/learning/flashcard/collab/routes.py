"""Endpoints for collaborative flashcard learning rooms."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.sql import func

from ....models import (
    FlashcardCollabAnswer,
    FlashcardCollabParticipant,
    FlashcardCollabRoom,
    FlashcardCollabRound,
    LearningContainer,
    UserContainerState,
    User,
    db,
)
from ..individual.algorithms import get_accessible_flashcard_set_ids
from ..individual.config import FlashcardLearningConfig
from ..individual.flashcard_logic import process_flashcard_answer
from .services import build_round_payload, ensure_active_round, generate_room_code, serialize_room

flashcard_collab_bp = Blueprint(
    'flashcard_collab', __name__, url_prefix='/flashcard-collab', template_folder='templates'
)


@flashcard_collab_bp.route('/')
@login_required
def dashboard():
    """Chuyển sang dashboard dùng chung của Flashcard."""

    return redirect(url_for('learning.flashcard.dashboard'))


@flashcard_collab_bp.route('/rooms', methods=['POST'])
@login_required
def create_room():
    payload = request.get_json(silent=True) or {}
    container_id = payload.get('container_id')
    mode = (payload.get('mode') or 'mixed_srs').strip().lower()
    is_public = bool(payload.get('is_public'))
    title = payload.get('title') or 'Học Flashcard chung'

    try:
        container_id = int(container_id)
    except (TypeError, ValueError):
        abort(400, description='Thiếu thông tin bộ flashcard để mở phòng.')

    allowed_modes = {mode_def['id'] for mode_def in FlashcardLearningConfig.FLASHCARD_MODES}
    if mode not in allowed_modes:
        abort(400, description='Chế độ học không hợp lệ.')

    container = LearningContainer.query.get_or_404(container_id)
    if container.container_type != 'FLASHCARD_SET':
        abort(400, description='Chỉ hỗ trợ mở phòng cho bộ flashcard.')

    accessible_ids = set(get_accessible_flashcard_set_ids(current_user.user_id))
    if current_user.user_role != User.ROLE_ADMIN and container_id not in accessible_ids:
        abort(403, description='Bạn chưa có quyền sử dụng bộ flashcard này.')

    room_code = generate_room_code()
    for _ in range(10):
        if not FlashcardCollabRoom.query.filter_by(room_code=room_code).first():
            break
        room_code = generate_room_code()
    else:
        abort(500, description='Không thể tạo mã phòng. Vui lòng thử lại.')

    room = FlashcardCollabRoom(
        room_code=room_code,
        title=title,
        host_user_id=current_user.user_id,
        container_id=container_id,
        mode=mode,
        is_public=is_public,
    )
    db.session.add(room)

    host_participant = FlashcardCollabParticipant(room=room, user_id=current_user.user_id, is_host=True)
    db.session.add(host_participant)
    db.session.commit()

    return jsonify({'room': serialize_room(room)}), 201


@flashcard_collab_bp.route('/rooms/<room_code>/view', methods=['GET'])
@login_required
def view_room(room_code: str):
    """Hiển thị trang phòng học nhóm và tự động thêm người dùng vào phòng."""

    room = FlashcardCollabRoom.query.filter_by(room_code=room_code).first()
    if not room:
        abort(404, description='Không tìm thấy phòng học chung.')

    accessible_ids = set(get_accessible_flashcard_set_ids(current_user.user_id))
    if current_user.user_role != User.ROLE_ADMIN and room.container_id not in accessible_ids:
        abort(403, description='Bạn chưa có quyền sử dụng bộ flashcard này.')

    participant = FlashcardCollabParticipant.query.filter_by(
        room_id=room.room_id, user_id=current_user.user_id
    ).first()
    if participant:
        participant.status = FlashcardCollabParticipant.STATUS_ACTIVE
    else:
        participant = FlashcardCollabParticipant(room=room, user_id=current_user.user_id)
        db.session.add(participant)

    _touch_user_container_state(room.container_id)

    db.session.commit()

    room_payload = serialize_room(room)

    return render_template(
        'flashcard_collab/room.html',
        room=room,
        room_payload=room_payload,
    )


@flashcard_collab_bp.route('/rooms/public', methods=['GET'])
@login_required
def list_public_rooms():
    """Danh sách phòng công khai đang hoạt động."""

    limit = request.args.get('limit', default=12, type=int)
    limit = max(1, min(limit or 12, 50))

    active_statuses = (FlashcardCollabRoom.STATUS_LOBBY, FlashcardCollabRoom.STATUS_ACTIVE)
    rooms = (
        FlashcardCollabRoom.query.filter(
            FlashcardCollabRoom.is_public.is_(True),
            FlashcardCollabRoom.status.in_(active_statuses),
        )
        .order_by(func.coalesce(FlashcardCollabRoom.updated_at, FlashcardCollabRoom.created_at).desc())
        .limit(limit)
        .all()
    )

    return jsonify({'rooms': [serialize_room(room) for room in rooms]})


@flashcard_collab_bp.route('/rooms/my-active', methods=['GET'])
@login_required
def list_my_active_rooms():
    """Trả về các phòng mà người dùng hiện đang tham gia."""

    active_statuses = (FlashcardCollabRoom.STATUS_LOBBY, FlashcardCollabRoom.STATUS_ACTIVE)

    participations = (
        FlashcardCollabParticipant.query.join(FlashcardCollabRoom)
        .filter(
            FlashcardCollabParticipant.user_id == current_user.user_id,
            FlashcardCollabParticipant.status == FlashcardCollabParticipant.STATUS_ACTIVE,
            FlashcardCollabRoom.status.in_(active_statuses),
        )
        .order_by(func.coalesce(FlashcardCollabRoom.updated_at, FlashcardCollabRoom.created_at).desc())
        .all()
    )

    seen_room_ids: set[int] = set()
    rooms: list[FlashcardCollabRoom] = []
    for participation in participations:
        if participation.room_id in seen_room_ids:
            continue
        if participation.room:
            rooms.append(participation.room)
            seen_room_ids.add(participation.room_id)

    return jsonify({'rooms': [serialize_room(room) for room in rooms]})


@flashcard_collab_bp.route('/rooms/<room_code>', methods=['GET'])
@login_required
def get_room(room_code: str):
    room = FlashcardCollabRoom.query.filter_by(room_code=room_code).first()
    if not room:
        abort(404, description='Không tìm thấy phòng học chung.')
    return jsonify({'room': serialize_room(room)})


@flashcard_collab_bp.route('/rooms/<room_code>/join', methods=['POST'])
@login_required
def join_room(room_code: str):
    room = FlashcardCollabRoom.query.filter_by(room_code=room_code).first()
    if not room:
        abort(404, description='Không tìm thấy phòng học chung.')

    participant = FlashcardCollabParticipant.query.filter_by(room_id=room.room_id, user_id=current_user.user_id).first()
    if participant:
        participant.status = FlashcardCollabParticipant.STATUS_ACTIVE
    else:
        participant = FlashcardCollabParticipant(room=room, user_id=current_user.user_id)
        db.session.add(participant)

    _touch_user_container_state(room.container_id)

    db.session.commit()
    return jsonify({'room': serialize_room(room)})


@flashcard_collab_bp.route('/rooms/<room_code>/next-card', methods=['GET'])
@login_required
def get_next_card(room_code: str):
    room = FlashcardCollabRoom.query.filter_by(room_code=room_code).first()
    if not room:
        abort(404, description='Không tìm thấy phòng học chung.')

    active_round = ensure_active_round(room)
    if not active_round:
        abort(404, description='Không tìm thấy thẻ phù hợp cho phòng này.')

    payload = build_round_payload(active_round, room)
    if not payload:
        abort(404, description='Không tìm thấy thẻ phù hợp cho phòng này.')

    return jsonify(payload)


def _map_answer_to_quality(raw_answer: str, button_count: int | None) -> int | None:
    """Map textual answer labels to a numeric quality value."""

    normalized = (raw_answer or '').strip().lower()
    if not normalized or normalized == 'continue':
        return None

    if button_count == 4:
        mapping = {'again': 0, 'hard': 1, 'good': 3, 'easy': 5}
    elif button_count == 6:
        mapping = {'fail': 0, 'very_hard': 1, 'hard': 2, 'medium': 3, 'good': 4, 'very_easy': 5}
    else:
        mapping = {'quên': 0, 'mơ_hồ': 3, 'nhớ': 5}

    return mapping.get(normalized)


def _touch_user_container_state(container_id: int) -> None:
    """Đảm bảo bộ thẻ được đánh dấu là đang học và cập nhật thời điểm truy cập."""

    state = UserContainerState.query.filter_by(
        user_id=current_user.user_id, container_id=container_id
    ).first()

    now = func.now()
    if state:
        state.is_archived = False
        state.last_accessed = now
    else:
        db.session.add(
            UserContainerState(
                user_id=current_user.user_id,
                container_id=container_id,
                is_archived=False,
                is_favorite=False,
                last_accessed=now,
            )
        )


@flashcard_collab_bp.route('/rooms/<room_code>/answer', methods=['POST'])
@login_required
def submit_collab_answer(room_code: str):
    """Submit an answer for the current shared flashcard round."""

    room = FlashcardCollabRoom.query.filter_by(room_code=room_code).first()
    if not room:
        abort(404, description='Không tìm thấy phòng học chung.')

    participant = FlashcardCollabParticipant.query.filter_by(
        room_id=room.room_id, user_id=current_user.user_id
    ).first()
    if not participant or participant.status != FlashcardCollabParticipant.STATUS_ACTIVE:
        abort(403, description='Bạn không có quyền trả lời trong phòng này.')

    payload = request.get_json(silent=True) or {}
    item_id = payload.get('item_id')
    answer_label = payload.get('answer')
    answer_quality = payload.get('answer_quality')

    try:
        item_id = int(item_id)
    except (TypeError, ValueError):
        abort(400, description='Thiếu thông tin thẻ cần trả lời.')

    active_round = ensure_active_round(room)
    if not active_round or active_round.item_id != item_id:
        abort(400, description='Phòng đang hiển thị một thẻ khác. Hãy đồng bộ lại.')

    if isinstance(answer_quality, str):
        try:
            answer_quality = int(answer_quality)
        except ValueError:
            answer_quality = None

    if not isinstance(answer_quality, int):
        answer_quality = _map_answer_to_quality(answer_label, participant.user.flashcard_button_count)

    score_change, updated_total_score, answer_result, progress_status, item_stats = process_flashcard_answer(
        current_user.user_id,
        item_id,
        answer_quality,
        getattr(current_user, 'total_score', 0) or 0,
        mode=room.mode,
    )

    existing_answer = FlashcardCollabAnswer.query.filter_by(
        round_id=active_round.round_id, user_id=current_user.user_id
    ).first()

    now = datetime.now(timezone.utc)
    if existing_answer:
        existing_answer.answer_label = answer_label
        existing_answer.answer_quality = answer_quality
        existing_answer.updated_at = now
    else:
        new_answer = FlashcardCollabAnswer(
            round_id=active_round.round_id,
            user_id=current_user.user_id,
            answer_label=answer_label,
            answer_quality=answer_quality,
            created_at=now,
        )
        db.session.add(new_answer)

    _touch_user_container_state(room.container_id)

    db.session.commit()

    active_participant_ids = {
        participant.user_id
        for participant in room.participants
        if participant.status == FlashcardCollabParticipant.STATUS_ACTIVE
    }
    answered_user_ids = {
        answer.user_id
        for answer in FlashcardCollabAnswer.query.filter_by(round_id=active_round.round_id).all()
        if answer.user_id in active_participant_ids
    }

    if active_participant_ids and answered_user_ids >= active_participant_ids:
        active_round.status = FlashcardCollabRound.STATUS_COMPLETED
        active_round.completed_at = now
        room.updated_at = now
        db.session.commit()

    round_payload = build_round_payload(active_round, room)

    return jsonify(
        {
            'round': round_payload,
            'result': {
                'score_change': score_change,
                'updated_total_score': updated_total_score,
                'answer_result': answer_result,
                'progress_status': progress_status,
                'statistics': item_stats,
            },
        }
    )


@flashcard_collab_bp.route('/available-sets', methods=['GET'])
@login_required
def list_available_sets():
    search_query = (request.args.get('q') or '').strip().lower()
    accessible_ids = get_accessible_flashcard_set_ids(current_user.user_id)
    query = LearningContainer.query.filter(
        LearningContainer.container_id.in_(accessible_ids),
        LearningContainer.container_type == 'FLASHCARD_SET',
    ).order_by(LearningContainer.updated_at.desc().nullslast(), LearningContainer.title.asc())

    if search_query:
        query = query.filter(LearningContainer.title.ilike(f'%{search_query}%'))

    containers = [
        {
            'container_id': container.container_id,
            'title': container.title,
            'description': container.description,
            'is_public': container.is_public,
        }
        for container in query.limit(50).all()
    ]
    return jsonify({'containers': containers})
