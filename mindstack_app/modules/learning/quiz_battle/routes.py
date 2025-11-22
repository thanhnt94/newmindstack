"""REST endpoints that power the interactive quiz battle mode."""

from __future__ import annotations

from typing import Optional

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.sql import func

from .....models import (
    ContainerContributor,
    LearningContainer,
    LearningItem,
    QuizBattleAnswer,
    QuizBattleParticipant,
    QuizBattleRoom,
    QuizBattleRound,
    User,
    db,
)
from ..quiz_learning.quiz_logic import process_quiz_answer
from .services import (
    auto_advance_round_if_needed,
    complete_round_if_ready,
    ensure_question_order,
    generate_room_code,
    get_active_participants,
    get_active_round,
    serialize_room,
    start_round,
)

quiz_battle_bp = Blueprint('quiz_battle', __name__, template_folder='templates')


@quiz_battle_bp.route('/')
@login_required
def quiz_battle_dashboard():
    """Simple landing page that explains the quiz battle feature."""

    return render_template('quiz_battle/dashboard.html')


def _get_room_or_404(room_code: str) -> QuizBattleRoom:
    room = QuizBattleRoom.query.filter_by(room_code=room_code).first()
    if not room:
        abort(404, description='Không tìm thấy phòng thi đấu.')
    return room


def _require_host(room: QuizBattleRoom) -> None:
    if current_user.user_id != room.host_user_id and current_user.user_role != User.ROLE_ADMIN:
        abort(403, description='Bạn không có quyền quản lý phòng này.')


def _build_accessible_quiz_query():
    """Return a query for quiz sets that the current user can use."""

    base_query = LearningContainer.query.filter(
        LearningContainer.container_type == 'QUIZ_SET'
    )

    if current_user.user_role == User.ROLE_ADMIN:
        return base_query

    contributor_ids = db.session.query(ContainerContributor.container_id).filter(
        ContainerContributor.user_id == current_user.user_id
    )

    return base_query.filter(
        or_(
            LearningContainer.creator_user_id == current_user.user_id,
            LearningContainer.is_public.is_(True),
            LearningContainer.container_id.in_(contributor_ids),
        )
    )


def _generate_unique_room_code() -> str:
    for _ in range(12):
        code = generate_room_code()
        if not QuizBattleRoom.query.filter_by(room_code=code).first():
            return code
    raise RuntimeError('Không thể tạo mã phòng. Vui lòng thử lại.')


@quiz_battle_bp.route('/rooms', methods=['POST'])
@login_required
def create_room():
    """Tạo phòng đấu quiz mới do người dùng hiện tại làm chủ phòng."""

    payload = request.get_json() or {}
    container_id = payload.get('container_id') if isinstance(payload, dict) else None
    try:
        container_id = int(container_id)
    except (TypeError, ValueError):
        abort(400, description='Thiếu thông tin bộ quiz để mở phòng.')

    container = LearningContainer.query.get_or_404(container_id)
    if not container.is_public and container.creator_user_id != current_user.user_id and current_user.user_role != User.ROLE_ADMIN:
        abort(403, description='Bạn chưa có quyền sử dụng bộ quiz này.')

    question_limit = payload.get('question_limit')
    if question_limit is not None:
        try:
            question_limit = int(question_limit)
        except (ValueError, TypeError):
            abort(400, description='Giới hạn câu hỏi phải là số nguyên dương.')
        if question_limit <= 0:
            abort(400, description='Giới hạn câu hỏi phải lớn hơn 0.')

    max_players = payload.get('max_players')
    if max_players is not None:
        try:
            max_players = int(max_players)
        except (ValueError, TypeError):
            abort(400, description='Số người chơi tối đa phải là số nguyên dương.')
        if max_players < 2:
            abort(400, description='Phòng đấu cần ít nhất hai người chơi.')

    title = payload.get('title') or f'Thi đấu: {container.title}'

    mode = payload.get('mode') or QuizBattleRoom.MODE_SLOW
    if isinstance(mode, str):
        mode = mode.strip().upper()
    if mode not in (QuizBattleRoom.MODE_SLOW, QuizBattleRoom.MODE_TIMED):
        abort(400, description='Chế độ thi đấu không hợp lệ.')

    time_per_question = payload.get('time_per_question_seconds')
    if mode == QuizBattleRoom.MODE_TIMED:
        if question_limit is None:
            abort(400, description='Vui lòng chọn số lượng câu hỏi cho chế độ giới hạn thời gian.')
        try:
            time_per_question = int(time_per_question)
        except (TypeError, ValueError):
            abort(400, description='Thời gian cho mỗi câu phải là số nguyên dương.')
        if time_per_question <= 0:
            abort(400, description='Thời gian cho mỗi câu phải lớn hơn 0.')
    else:
        time_per_question = None

    visibility = payload.get('visibility')
    if isinstance(visibility, str):
        visibility = visibility.strip().lower()
    is_public = False
    if visibility in {'public', 'private'}:
        is_public = visibility == 'public'
    elif 'is_public' in payload:
        is_public = bool(payload.get('is_public'))

    room = QuizBattleRoom(
        room_code=_generate_unique_room_code(),
        title=title,
        host_user_id=current_user.user_id,
        container_id=container_id,
        max_players=max_players,
        question_limit=question_limit,
        is_public=is_public,
        mode=mode,
        time_per_question_seconds=time_per_question,
    )
    db.session.add(room)

    host_participant = QuizBattleParticipant(
        room=room,
        user_id=current_user.user_id,
        is_host=True,
    )
    db.session.add(host_participant)

    ensure_question_order(room)
    if not room.question_order:
        db.session.rollback()
        abort(400, description='Bộ quiz này chưa có câu hỏi để thi đấu.')

    db.session.commit()
    return jsonify({'room': serialize_room(room, user_id=current_user.user_id)}), 201


@quiz_battle_bp.route('/available-quizzes', methods=['GET'])
@login_required
def list_available_quizzes():
    """Return quiz sets that the current user can host battles with."""

    search_query = (request.args.get('q') or '').strip()
    limit = request.args.get('limit', default=12, type=int)
    if not limit or limit < 1:
        limit = 12
    limit = min(limit, 50)

    query = _build_accessible_quiz_query().order_by(
        LearningContainer.updated_at.desc().nullslast(),
        LearningContainer.title.asc(),
    )

    if search_query:
        like_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                LearningContainer.title.ilike(like_pattern),
                LearningContainer.description.ilike(like_pattern),
                LearningContainer.tags.ilike(like_pattern),
            )
        )

    containers = query.limit(limit).all()
    container_ids = [container.container_id for container in containers]
    question_counts: dict[int, int] = {}
    if container_ids:
        question_counts = dict(
            db.session.query(
                LearningItem.container_id,
                func.count(LearningItem.item_id),
            )
            .filter(LearningItem.container_id.in_(container_ids))
            .group_by(LearningItem.container_id)
            .all()
        )

    return jsonify(
        {
            'containers': [
                {
                    'container_id': container.container_id,
                    'title': container.title,
                    'description': container.description,
                    'is_public': container.is_public,
                    'tags': container.tags,
                    'question_count': question_counts.get(container.container_id, 0),
                }
                for container in containers
            ]
        }
    )


@quiz_battle_bp.route('/rooms/public', methods=['GET'])
@login_required
def list_public_rooms():
    """Danh sách phòng công khai đang hoạt động."""

    limit = request.args.get('limit', default=12, type=int)
    limit = max(1, min(limit or 12, 50))

    active_statuses = (
        QuizBattleRoom.STATUS_LOBBY,
        QuizBattleRoom.STATUS_IN_PROGRESS,
        QuizBattleRoom.STATUS_AWAITING_HOST,
    )
    rooms = (
        QuizBattleRoom.query.filter(
            QuizBattleRoom.is_public.is_(True),
            QuizBattleRoom.status.in_(active_statuses),
        )
        .order_by(func.coalesce(QuizBattleRoom.updated_at, QuizBattleRoom.created_at).desc())
        .limit(limit)
        .all()
    )

    return jsonify({'rooms': [serialize_room(room, user_id=current_user.user_id) for room in rooms]})


@quiz_battle_bp.route('/rooms/my-active', methods=['GET'])
@login_required
def list_my_active_rooms():
    """Trả về các phòng mà người dùng hiện đang tham gia."""

    active_statuses = (
        QuizBattleRoom.STATUS_LOBBY,
        QuizBattleRoom.STATUS_IN_PROGRESS,
        QuizBattleRoom.STATUS_AWAITING_HOST,
    )

    participations = (
        QuizBattleParticipant.query.join(QuizBattleRoom)
        .filter(
            QuizBattleParticipant.user_id == current_user.user_id,
            QuizBattleParticipant.status == QuizBattleParticipant.STATUS_ACTIVE,
            QuizBattleRoom.status.in_(active_statuses),
        )
        .order_by(func.coalesce(QuizBattleRoom.updated_at, QuizBattleRoom.created_at).desc())
        .all()
    )

    seen_room_ids: set[int] = set()
    rooms: list[QuizBattleRoom] = []
    for participation in participations:
        if participation.room_id in seen_room_ids:
            continue
        if participation.room:
            rooms.append(participation.room)
            seen_room_ids.add(participation.room_id)

    return jsonify({'rooms': [serialize_room(room, user_id=current_user.user_id) for room in rooms]})


@quiz_battle_bp.route('/rooms/<string:room_code>', methods=['GET'])
@login_required
def get_room(room_code: str):
    """Trả về trạng thái hiện tại của phòng thi đấu."""

    room = _get_room_or_404(room_code)
    if auto_advance_round_if_needed(room):
        db.session.commit()
    return jsonify(
        {
            'room': serialize_room(
                room,
                include_round_history=True,
                user_id=current_user.user_id,
            )
        }
    )


@quiz_battle_bp.route('/rooms/<string:room_code>/view', methods=['GET'])
@login_required
def view_room(room_code: str):
    """Giao diện trực quan của một phòng quiz battle đang diễn ra."""

    room = _get_room_or_404(room_code)
    participant = next((p for p in room.participants if p.user_id == current_user.user_id), None)
    if current_user.user_role != User.ROLE_ADMIN and not participant:
        abort(403, description='Bạn cần tham gia phòng này trước khi xem giao diện thi đấu.')

    room_payload = serialize_room(
        room,
        include_round_history=True,
        user_id=current_user.user_id,
    )
    return render_template(
        'quiz_battle/room.html',
        room_code=room.room_code,
        room_title=room.title,
        initial_room=room_payload,
        is_host=bool(participant and participant.is_host),
        participant_id=participant.participant_id if participant else None,
        current_user_id=current_user.user_id,
    )


@quiz_battle_bp.route('/rooms/<string:room_code>/join', methods=['POST'])
@login_required
def join_room(room_code: str):
    """Thêm người chơi vào phòng ở trạng thái sảnh chờ."""

    room = _get_room_or_404(room_code)
    if room.status != QuizBattleRoom.STATUS_LOBBY or room.is_locked:
        abort(400, description='Phòng đã khóa hoặc đang diễn ra, không thể tham gia thêm.')

    existing = QuizBattleParticipant.query.filter_by(room_id=room.room_id, user_id=current_user.user_id).first()
    if existing:
        if existing.status == QuizBattleParticipant.STATUS_KICKED:
            abort(403, description='Bạn đã bị loại khỏi phòng này.')
        if existing.status == QuizBattleParticipant.STATUS_ACTIVE:
            return jsonify({'room': serialize_room(room, user_id=current_user.user_id)})
        existing.status = QuizBattleParticipant.STATUS_ACTIVE
        existing.left_at = None
    else:
        if room.max_players and len(get_active_participants(room)) >= room.max_players:
            abort(400, description='Phòng đã đủ số lượng người chơi cho phép.')
        participant = QuizBattleParticipant(room=room, user_id=current_user.user_id)
        db.session.add(participant)

    db.session.commit()
    return jsonify({'room': serialize_room(room, user_id=current_user.user_id)})


@quiz_battle_bp.route('/rooms/<string:room_code>/leave', methods=['POST'])
@login_required
def leave_room(room_code: str):
    """Đánh dấu một người chơi rời phòng."""

    room = _get_room_or_404(room_code)
    participant = QuizBattleParticipant.query.filter_by(room_id=room.room_id, user_id=current_user.user_id).first()
    if not participant:
        abort(404, description='Bạn không ở trong phòng này.')

    participant.status = QuizBattleParticipant.STATUS_LEFT
    participant.left_at = func.now()
    active_round = get_active_round(room)
    complete_round_if_ready(active_round)
    if participant.is_host and room.status != QuizBattleRoom.STATUS_COMPLETED:
        room.status = QuizBattleRoom.STATUS_AWAITING_HOST

    db.session.commit()
    return jsonify({'room': serialize_room(room, user_id=current_user.user_id)})


@quiz_battle_bp.route('/rooms/<string:room_code>/kick', methods=['POST'])
@login_required
def kick_participant(room_code: str):
    """Cho phép chủ phòng loại một thành viên."""

    room = _get_room_or_404(room_code)
    _require_host(room)

    payload = request.get_json() or {}
    user_id = payload.get('user_id')
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        abort(400, description='Thiếu thông tin người chơi cần loại.')

    participant = QuizBattleParticipant.query.filter_by(room_id=room.room_id, user_id=user_id).first()
    if not participant:
        abort(404, description='Không tìm thấy người chơi.')
    if participant.is_host:
        abort(400, description='Không thể loại chủ phòng.')

    participant.status = QuizBattleParticipant.STATUS_KICKED
    participant.left_at = func.now()
    participant.kicked_by = current_user.user_id

    active_round = get_active_round(room)
    complete_round_if_ready(active_round)

    db.session.commit()
    return jsonify({'room': serialize_room(room, user_id=current_user.user_id)})


@quiz_battle_bp.route('/rooms/<string:room_code>/start', methods=['POST'])
@login_required
def start_room(room_code: str):
    """Khởi động lượt thi đấu, khóa sảnh chờ."""

    room = _get_room_or_404(room_code)
    _require_host(room)

    if room.status != QuizBattleRoom.STATUS_LOBBY:
        abort(400, description='Phòng đã được khởi động hoặc đã kết thúc.')

    if len(get_active_participants(room)) < 2:
        abort(400, description='Cần ít nhất 2 người chơi để bắt đầu thi đấu.')

    ensure_question_order(room)
    if not room.question_order:
        abort(400, description='Bộ quiz chưa có câu hỏi để thi đấu.')

    room.status = QuizBattleRoom.STATUS_IN_PROGRESS
    room.is_locked = True
    start_round(room, 1)

    db.session.commit()
    return jsonify({'room': serialize_room(room, user_id=current_user.user_id)})


@quiz_battle_bp.route('/rooms/<string:room_code>/end', methods=['POST'])
@login_required
def end_room(room_code: str):
    """Chủ phòng kết thúc phiên đấu và mở kết quả."""

    room = _get_room_or_404(room_code)
    _require_host(room)

    ensure_question_order(room)
    room.status = QuizBattleRoom.STATUS_COMPLETED
    room.is_locked = True
    room.current_round_number = max(room.current_round_number, len(room.question_order or []))

    db.session.commit()
    return jsonify(
        {
            'room': serialize_room(
                room,
                include_round_history=True,
                user_id=current_user.user_id,
            )
        }
    )


@quiz_battle_bp.route('/rooms/<string:room_code>/rounds/<int:sequence_number>/answer', methods=['POST'])
@login_required
def submit_round_answer(room_code: str, sequence_number: int):
    """Ghi nhận câu trả lời cho một vòng đấu cụ thể."""

    room = _get_room_or_404(room_code)
    if auto_advance_round_if_needed(room):
        db.session.commit()
    participant = QuizBattleParticipant.query.filter_by(room_id=room.room_id, user_id=current_user.user_id).first()
    if not participant or participant.status != QuizBattleParticipant.STATUS_ACTIVE:
        abort(403, description='Bạn không thể trả lời trong phòng này.')

    round_obj = QuizBattleRound.query.filter_by(room_id=room.room_id, sequence_number=sequence_number).first()
    if not round_obj:
        abort(404, description='Không tìm thấy vòng thi đấu.')
    if round_obj.status != QuizBattleRound.STATUS_ACTIVE:
        if room.mode == QuizBattleRoom.MODE_TIMED:
            abort(400, description='Vòng thi này đã kết thúc do hết thời gian.')
        abort(400, description='Vòng thi này đã kết thúc hoặc chưa mở.')

    existing_answer = QuizBattleAnswer.query.filter_by(round_id=round_obj.round_id, participant_id=participant.participant_id).first()
    if existing_answer:
        abort(400, description='Bạn đã trả lời vòng này rồi.')

    payload = request.get_json() or {}
    selected_option = payload.get('selected_option')
    if not selected_option:
        abort(400, description='Vui lòng chọn đáp án.')
    selected_option = str(selected_option).strip().upper()

    user_total_score = participant.user.total_score or 0
    score_change, updated_total_score, is_correct, correct_option_char, explanation = process_quiz_answer(
        participant.user_id,
        round_obj.item_id,
        selected_option,
        user_total_score,
    )

    answer = QuizBattleAnswer(
        round_id=round_obj.round_id,
        participant_id=participant.participant_id,
        selected_option=selected_option,
        is_correct=is_correct,
        score_delta=score_change,
        correct_option=correct_option_char,
        explanation=explanation,
    )
    db.session.add(answer)

    if is_correct:
        participant.correct_answers += 1
    else:
        participant.incorrect_answers += 1
    participant.session_score += score_change

    db.session.flush()
    next_round = complete_round_if_ready(round_obj)
    db.session.commit()

    return jsonify(
        {
            'answer': {
                'is_correct': is_correct,
                'score_delta': score_change,
                'correct_option': correct_option_char,
                'explanation': explanation,
                'updated_total_score': updated_total_score,
            },
            'room': serialize_room(room, user_id=current_user.user_id),
            'next_round_number': next_round.sequence_number if next_round else None,
            'room_status': room.status,
        }
    )


@quiz_battle_bp.route('/history', methods=['GET'])
@login_required
def battle_history():
    """Trả về danh sách phiên đấu mà người dùng đã tham gia."""

    limit = request.args.get('limit', default=10, type=int)
    limit = max(1, min(limit, 50))

    participations = (
        QuizBattleParticipant.query.join(QuizBattleRoom)
        .filter(
            QuizBattleParticipant.user_id == current_user.user_id,
            QuizBattleRoom.status == QuizBattleRoom.STATUS_COMPLETED,
        )
        .order_by(QuizBattleRoom.updated_at.desc(), QuizBattleRoom.created_at.desc())
        .limit(limit)
        .all()
    )

    history_payload = []
    for participation in participations:
        room = participation.room
        question_order = ensure_question_order(room)
        history_payload.append(
            {
                'room_code': room.room_code,
                'title': room.title,
                'host_user_id': room.host_user_id,
                'question_total': len(question_order),
                'final_score': participation.session_score,
                'correct_answers': participation.correct_answers,
                'incorrect_answers': participation.incorrect_answers,
                'status': participation.status,
                'finished_at': (room.updated_at or room.created_at).isoformat() if (room.updated_at or room.created_at) else None,
            }
        )

    return jsonify({'history': history_payload})
