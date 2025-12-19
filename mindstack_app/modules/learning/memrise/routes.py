# File: mindstack_app/modules/learning/memrise/routes.py
# Phiên bản: 2.0 - SRS Integration
# Mục đích: Routes cho module Memrise với SRS

from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user

from . import memrise_bp
from .memrise_logic import (
    get_memrise_eligible_containers,
    get_container_memrise_items,
    get_session_questions,
    get_smart_questions,
    update_memrise_progress,
    reset_session_reps,
    get_container_srs_stats,
    check_mcq_answer,
    check_typing_answer,
    get_mcq_answer,
    MIN_CARDS_FOR_MEMRISE
)
from mindstack_app.models import LearningContainer, LearningItem


# ==============================================================================
# I. DASHBOARD ROUTES
# ==============================================================================

@memrise_bp.route('/')
@memrise_bp.route('/dashboard')
@login_required
def dashboard():
    """Trang dashboard Memrise - step-based flow."""
    return render_template(
        'memrise/dashboard/index.html',
        min_cards=MIN_CARDS_FOR_MEMRISE
    )


@memrise_bp.route('/api/sets-partial')
@login_required
def api_get_sets_partial():
    """API trả về danh sách bộ thẻ đủ điều kiện Memrise."""
    eligible_containers = get_memrise_eligible_containers(current_user.user_id)
    
    return render_template(
        'memrise/dashboard/_sets_list.html',
        containers=eligible_containers,
        min_cards=MIN_CARDS_FOR_MEMRISE
    )


@memrise_bp.route('/api/modes-partial')
@login_required
def api_get_modes_partial():
    """API trả về danh sách mode học với số lượng thẻ."""
    set_ids_str = request.args.get('set_ids', '')
    
    if not set_ids_str:
        return '<p class="text-center text-gray-500">Chọn ít nhất 1 bộ thẻ</p>', 400
    
    try:
        set_ids = [int(s) for s in set_ids_str.split(',') if s]
    except ValueError:
        return '<p class="text-center text-red-500">ID bộ thẻ không hợp lệ</p>', 400
    
    # Count total Memrise-eligible items across selected sets
    total_items = 0
    for set_id in set_ids:
        items = get_container_memrise_items(set_id)
        total_items += len(items)
    
    modes = [
        {'id': 'mixed', 'name': 'Hỗn hợp (SRS)', 'icon': 'fas fa-random', 'count': total_items, 'color': 'purple'},
        {'id': 'mcq', 'name': 'Trắc nghiệm', 'icon': 'fas fa-list-ul', 'count': total_items, 'color': 'blue'},
        {'id': 'typing', 'name': 'Gõ đáp án', 'icon': 'fas fa-keyboard', 'count': total_items, 'color': 'green'},
        {'id': 'flashcard', 'name': 'Flashcard', 'icon': 'fas fa-clone', 'count': total_items, 'color': 'indigo', 'is_flashcard': True},
    ]
    
    return render_template(
        'memrise/dashboard/_modes_list.html',
        modes=modes,
        selected_set_ids=set_ids
    )


# ==============================================================================
# II. SESSION ROUTES
# ==============================================================================

@memrise_bp.route('/session/<int:container_id>')
@login_required
def session(container_id):
    """Trang game session Memrise."""
    container = LearningContainer.query.get_or_404(container_id)
    
    # Kiểm tra quyền truy cập
    if not container.is_public and container.creator_user_id != current_user.user_id:
        abort(403)
    
    # Kiểm tra đủ điều kiện
    memrise_items = get_container_memrise_items(container_id)
    if len(memrise_items) < MIN_CARDS_FOR_MEMRISE:
        abort(400, description=f"Bộ thẻ cần ít nhất {MIN_CARDS_FOR_MEMRISE} thẻ có dữ liệu Memrise")
    
    # Lấy mode từ query params
    mode = request.args.get('mode', 'mixed')
    if mode not in ['mcq', 'typing', 'mixed']:
        mode = 'mixed'
    
    return render_template(
        'memrise/session/index.html',
        container=container,
        mode=mode,
        total_memrise_cards=len(memrise_items)
    )


# ==============================================================================
# III. API ROUTES
# ==============================================================================

@memrise_bp.route('/api/questions/<int:container_id>')
@login_required
def api_get_questions(container_id):
    """API lấy danh sách câu hỏi cho session."""
    container = LearningContainer.query.get_or_404(container_id)
    
    # Kiểm tra quyền
    if not container.is_public and container.creator_user_id != current_user.user_id:
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    
    # Sử dụng SRS-based selection cho mixed mode
    mode = request.args.get('mode', 'mixed')
    count = request.args.get('count', 10, type=int)
    count = min(count, 50)  # Giới hạn tối đa 50 câu
    use_srs = request.args.get('srs', 'true').lower() == 'true'
    
    if use_srs and mode == 'mixed':
        # Reset session reps khi bắt đầu session mới
        reset_session_reps(current_user.user_id, container_id)
        questions = get_smart_questions(current_user.user_id, container_id, count, mode)
    else:
        questions = get_session_questions(container_id, count, mode)
    
    if not questions:
        return jsonify({
            'success': False, 
            'message': f'Không đủ thẻ có dữ liệu Memrise (cần ít nhất {MIN_CARDS_FOR_MEMRISE})'
        }), 400
    
    # Ẩn đáp án đúng cho client (sẽ kiểm tra server-side)
    client_questions = []
    for q in questions:
        client_q = {
            'item_id': q['item_id'],
            'question_type': q['question_type'],
            'question': q['question']
        }
        if q['question_type'] == 'mcq':
            client_q['options'] = q['options']
        elif q['question_type'] == 'typing':
            client_q['hint'] = q.get('hint', '')
        
        # Include memory level if available
        if 'memory_level' in q:
            client_q['memory_level'] = q['memory_level']
            client_q['level_name'] = q.get('level_name', '')
        
        client_questions.append(client_q)
    
    # Get SRS stats
    srs_stats = get_container_srs_stats(current_user.user_id, container_id)
    
    return jsonify({
        'success': True,
        'questions': client_questions,
        'total': len(client_questions),
        'srs_stats': srs_stats
    })


@memrise_bp.route('/api/check-answer', methods=['POST'])
@login_required
def api_check_answer():
    """API kiểm tra đáp án."""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ'}), 400
    
    item_id = data.get('item_id')
    question_type = data.get('question_type')
    user_answer = data.get('answer', '').strip()
    
    if not item_id or not question_type or not user_answer:
        return jsonify({'success': False, 'message': 'Thiếu thông tin'}), 400
    
    # Lấy item
    item = LearningItem.query.get(item_id)
    if not item or not item.content:
        return jsonify({'success': False, 'message': 'Không tìm thấy thẻ'}), 404
    
    memrise_answers = item.content.get('memrise_answers', '')
    correct_answer = get_mcq_answer(memrise_answers)
    
    if question_type == 'mcq':
        is_correct = check_mcq_answer(user_answer, correct_answer)
    elif question_type == 'typing':
        result = check_typing_answer(user_answer, memrise_answers)
        is_correct = result['is_correct']
        correct_answer = result['correct_answer']
    else:
        return jsonify({'success': False, 'message': 'Loại câu hỏi không hợp lệ'}), 400
    
    # Update SRS progress
    progress_update = update_memrise_progress(
        user_id=current_user.user_id,
        item_id=item_id,
        is_correct=is_correct
    )
    
    return jsonify({
        'success': True,
        'is_correct': is_correct,
        'correct_answer': correct_answer,
        'progress': progress_update
    })

