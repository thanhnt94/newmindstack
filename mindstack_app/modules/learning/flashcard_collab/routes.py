"""Endpoints for collaborative flashcard learning rooms."""

from __future__ import annotations

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required

from ....models import (
    FlashcardCollabParticipant,
    FlashcardCollabRoom,
    LearningContainer,
    User,
    db,
)
from ..flashcard_learning.algorithms import get_accessible_flashcard_set_ids
from ..flashcard_learning.config import FlashcardLearningConfig
from .services import (
    generate_room_code,
    get_next_shared_item,
    serialize_room,
)

flashcard_collab_bp = Blueprint(
    'flashcard_collab', __name__, url_prefix='/flashcard-collab', template_folder='templates'
)


@flashcard_collab_bp.route('/')
@login_required
def dashboard():
    """Simple landing page to introduce collaborative flashcard learning."""

    modes = FlashcardLearningConfig.FLASHCARD_MODES
    return render_template('flashcard_collab/dashboard.html', modes=modes)


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

    db.session.commit()
    return jsonify({'room': serialize_room(room)})


@flashcard_collab_bp.route('/rooms/<room_code>/next-card', methods=['GET'])
@login_required
def get_next_card(room_code: str):
    room = FlashcardCollabRoom.query.filter_by(room_code=room_code).first()
    if not room:
        abort(404, description='Không tìm thấy phòng học chung.')

    payload = get_next_shared_item(room)
    if not payload:
        abort(404, description='Không tìm thấy thẻ phù hợp cho phòng này.')

    return jsonify(payload)


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
